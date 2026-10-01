"""Exercise the Overpass request budget without network access or OSMnx wheels."""

import importlib.util
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace


osmnx = ModuleType("osmnx")
osmnx.settings = SimpleNamespace(
    requests_timeout=180,
    max_query_area_size=2_500_000_000,
    overpass_rate_limit=True,
)
osmnx._overpass = SimpleNamespace(_overpass_request=lambda data, pause=None, error_pause=60: data)
sys.modules["osmnx"] = osmnx

path = Path(__file__).resolve().parents[1] / "foot_traffic_analysis.py"
spec = importlib.util.spec_from_file_location("analysis_under_test", path)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)

assert osmnx.settings.max_query_area_size == 2_500_000_000
assert osmnx.settings.requests_timeout == 20
assert analysis._bounded_overpass_request({"query": "ok"}) == {"query": "ok"}

deadline_token = analysis._analysis_deadline.set(time.monotonic() - 1)
try:
    try:
        analysis._bounded_overpass_request({"query": "late"})
        raise AssertionError("Expired analysis did not stop")
    except analysis.AnalysisTimeoutError as error:
        assert str(error) == "Analysis timed out during Overpass request"
finally:
    analysis._analysis_deadline.reset(deadline_token)

attempts_token = analysis._overpass_attempts.set(0)
analysis._original_overpass_request = lambda data, pause=None, error_pause=60: analysis._bounded_overpass_request(data)
try:
    try:
        analysis._bounded_overpass_request({"query": "retry"})
        raise AssertionError("Recursive Overpass retries did not stop")
    except analysis.AnalysisTimeoutError as error:
        assert str(error) == "Overpass exceeded the analysis request limit"
        assert analysis._overpass_attempts.get() == 9
finally:
    analysis._overpass_attempts.reset(attempts_token)

sys.modules["foot_traffic_analysis"] = analysis
pdf = ModuleType("pdf_report_generator")
pdf.LocationViabilityReportGenerator = type("LocationViabilityReportGenerator", (), {})
sys.modules["pdf_report_generator"] = pdf
analysis.extract_osm_foot_traffic_indicators = lambda *args, **kwargs: (_ for _ in ()).throw(
    analysis.AnalysisTimeoutError("Analysis timed out during POI fetch")
)
app_path = path.with_name("app.py")
app_spec = importlib.util.spec_from_file_location("app_under_test", app_path)
app_module = importlib.util.module_from_spec(app_spec)
app_spec.loader.exec_module(app_module)
response = app_module.app.test_client().post(
    "/analyze", json={"lat": 14.6123, "lon": 120.9775, "radius": 300}
)
assert response.status_code == 503
assert response.json == {
    "code": "analysis_timeout",
    "error": "Analysis timed out during POI fetch",
}

analysis.extract_osm_foot_traffic_indicators = lambda *args, **kwargs: (_ for _ in ()).throw(
    analysis.AnalysisUpstreamError("Failed to fetch OSM street network after 3 attempts")
)
response = app_module.app.test_client().post(
    "/analyze", json={"lat": 14.6123, "lon": 120.9775, "radius": 300}
)
assert response.status_code == 503
assert response.json == {
    "code": "analysis_upstream_unavailable",
    "error": "Failed to fetch OSM street network after 3 attempts",
}

print("analysis budget checks passed")
