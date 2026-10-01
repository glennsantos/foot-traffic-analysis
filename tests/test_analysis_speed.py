"""Behavior checks for cached results and deferred reports."""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import app as app_module
from analysis_cache import AnalysisCache
from analysis_errors import AnalysisUpstreamError
from pdf_report_generator import LocationViabilityReportGenerator


QUERY = {'lat': 14.5995, 'lon': 120.9842, 'radius': 300, 'location_name': 'Manila'}
ANALYSIS = {'shops': {'count': 10, 'places': ['Example shop'], 'detailed_places': []},
            'intersection_count': 20}


def test_repeated_analysis_reuses_results_without_pdf_or_geocoding(test_client):
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)) as extract, \
         patch('app.get_location_name') as geocode, \
         patch.object(LocationViabilityReportGenerator, 'generate_report') as pdf:
        fresh = test_client.post('/analyze', json=QUERY)
        repeated = test_client.post('/analyze', json=QUERY)
        assert fresh.status_code == repeated.status_code == 200
        assert fresh.json['cache']['hit'] is False
        assert repeated.json['cache']['hit'] is True
        assert fresh.json['viability_score'] == repeated.json['viability_score']
        assert extract.call_count == 1
        geocode.assert_not_called()
        pdf.assert_not_called()
        assert 'pdf_report_base64' not in fresh.json


def test_refresh_and_different_radius_recompute(test_client):
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)) as extract:
        for query in (QUERY, dict(QUERY, refresh=True), dict(QUERY, radius=500)):
            response = test_client.post('/analyze', json=query)
            assert response.status_code == 200
            assert response.json['cache']['hit'] is False
        assert extract.call_count == 3


def test_search_labels_do_not_leak_into_other_requests(test_client):
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)), \
         patch('app.get_location_name', return_value='Resolved map location') as geocode:
        test_client.post('/analyze', json=QUERY)
        point_query = {key: value for key, value in QUERY.items() if key != 'location_name'}
        mapped = test_client.post('/analyze', json=point_query)
        repeated = test_client.post('/analyze', json=point_query)
        assert mapped.json['location_name'] == repeated.json['location_name'] == 'Resolved map location'
        geocode.assert_called_once()


def test_download_builds_real_pdf_after_analysis(test_client):
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)):
        result = test_client.post('/analyze', json=QUERY).json
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', side_effect=AssertionError('OSM must not run')):
        report = test_client.post('/api/report', json={'report_token': result['report_token']})
    assert report.status_code == 200
    assert report.mimetype == 'application/pdf'
    assert report.data.startswith(b'%PDF')
    assert result['pdf_report'] in report.headers['Content-Disposition']
    assert result['viability_score'] == LocationViabilityReportGenerator().summarize(ANALYSIS, 'Manila', QUERY['lat'], QUERY['lon'], 300)['viability_percentage']


def test_report_works_in_another_process_without_saved_analysis(test_client):
    app_module.app.secret_key = 'shared-test-key'
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)):
        token = test_client.post('/analyze', json=QUERY).json['report_token']
    code = """
import sys, app
app.app.secret_key = 'shared-test-key'
app.STORAGE_ROOT = '/nonexistent-analysis-storage'
response = app.app.test_client().post('/api/report', json={'report_token': sys.stdin.read()})
assert response.status_code == 200, response.json
assert response.data.startswith(b'%PDF')
print('cross-process PDF passed')
"""
    result = subprocess.run([sys.executable, '-c', code], input=token, text=True, capture_output=True, check=True)
    assert 'cross-process PDF passed' in result.stdout


def test_tampered_and_expired_reports_are_rejected(test_client):
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)):
        token = test_client.post('/analyze', json=QUERY).json['report_token']
    assert test_client.post('/api/report', json={'report_token': token + 'tampered'}).status_code == 400
    with patch('itsdangerous.timed.TimestampSigner.get_timestamp', return_value=0):
        expired = app_module.report_serializer().dumps({'analysis': ANALYSIS})
    assert test_client.post('/api/report', json={'report_token': expired}).status_code == 410
    old_model = app_module.report_serializer().dumps({'analysis_version': 'old-model'})
    assert test_client.post('/api/report', json={'report_token': old_model}).status_code == 410


def test_failures_are_not_cached(test_client):
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', side_effect=AnalysisUpstreamError('Offline')) as extract:
        for _ in range(2):
            assert test_client.post('/analyze', json=QUERY).status_code == 503
        assert extract.call_count == 2


@pytest.mark.parametrize('overrides', [
    {'lat': float('nan')}, {'lon': 181}, {'radius': 100.5}, {'radius': 0},
    {'refresh': 'yes'}, {'location_name': ['invalid']},
])
def test_invalid_analysis_inputs_are_rejected(test_client, overrides):
    assert test_client.post('/analyze', json=dict(QUERY, **overrides)).status_code == 400


def test_cache_is_shared_bounded_and_expires(tmp_path):
    first = AnalysisCache(tmp_path / 'cache.sqlite3', ttl=10, max_entries=2)
    second = AnalysisCache(first.path, ttl=10)
    with patch('analysis_cache.time.time', return_value=100):
        first.set('a', {'count': 1})
    with patch('analysis_cache.time.time', return_value=101):
        assert second.get('a') == {'count': 1}
        first.set('b', {'count': 2})
    with patch('analysis_cache.time.time', return_value=102):
        first.set('c', {'count': 3})
        assert second.get('a') is None
        assert second.get('b') == {'count': 2}
    with patch('analysis_cache.time.time', return_value=112):
        assert second.get('b') is None
        assert second.get('c') is None


def test_enriching_name_does_not_extend_osm_freshness(tmp_path):
    cache = AnalysisCache(tmp_path / 'cache.sqlite3', ttl=10)
    snapshot = {'timestamp': datetime.fromtimestamp(100, timezone.utc).isoformat(), 'location_name': 'Manila'}
    with patch('analysis_cache.time.time', return_value=109):
        cache.set('a', snapshot)
        assert cache.get('a') == snapshot
    with patch('analysis_cache.time.time', return_value=110):
        assert cache.get('a') is None


def test_cache_outage_does_not_break_analysis(test_client, tmp_path):
    path = tmp_path / 'not-a-directory'
    path.write_text('occupied')
    app_module.analysis_cache = AnalysisCache(path / 'cache.sqlite3')
    with patch('foot_traffic_analysis.extract_osm_foot_traffic_indicators', return_value=(None, ANALYSIS)):
        assert test_client.post('/analyze', json=QUERY).status_code == 200


def test_local_workers_share_an_atomically_created_secret(tmp_path, monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.setattr(app_module, 'STORAGE_ROOT', str(tmp_path))
    with ThreadPoolExecutor(max_workers=4) as pool:
        keys = list(pool.map(lambda _: app_module.load_secret_key(), range(8)))
    assert all(key == keys[0] for key in keys)
    assert len(keys[0]) == 32
    assert (tmp_path / 'cache' / 'report-secret').stat().st_mode & 0o777 == 0o600
