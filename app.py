from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
import json
from datetime import datetime, timezone
import os
import requests
import traceback
from functools import wraps
import logging
import math
import threading
import time
from urllib.parse import quote
import io
import hashlib
import tempfile
from pathlib import Path
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from analysis_cache import AnalysisCache, analysis_key, ANALYSIS_VERSION

STORAGE_ROOT = '/tmp' if os.getenv('VERCEL') else '.'
if os.getenv('VERCEL'):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS from environment (default open for dev)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins == "*":
    CORS(app)
else:
    CORS(app, resources={r"/*": {"origins": [o.strip() for o in allowed_origins.split(",") if o.strip()]}})

def load_secret_key():
    configured = os.getenv('SECRET_KEY')
    if configured:
        return configured
    if os.getenv('VERCEL'):
        logger.warning('Set a shared SECRET_KEY on Vercel for report downloads across instances')
        return os.urandom(32)
    # Publish a complete key atomically so local Gunicorn workers share it.
    key_path = Path(STORAGE_ROOT) / 'cache' / 'report-secret'
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        with tempfile.NamedTemporaryFile(dir=key_path.parent, delete=False) as saved:
            saved.write(os.urandom(32))
            saved.flush()
            temporary_path = saved.name
        try:
            try:
                os.link(temporary_path, key_path)
            except FileExistsError:
                pass
        finally:
            os.unlink(temporary_path)
    return key_path.read_bytes()


app.secret_key = load_secret_key()

logger.info("Flask application starting up...")

# Simple in-memory storage for demo (replace with a database in production)
last_searches = {}

# Places Aggregate API (also marketed as Places Insights) returns aggregate
# geography counts, the appropriate signal for site selection.
PLACES_INSIGHTS_URL = "https://areainsights.googleapis.com/v1:computeInsights"
PLACES_INSIGHTS_DOCS = "https://developers.google.com/maps/documentation/places-aggregate/reference/rest/v1/TopLevel/computeInsights"
MIN_INSIGHTS_RADIUS_METERS = 40
MAX_INSIGHTS_RADIUS_METERS = 50000


def _positive_int_env(name, default):
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        logger.warning("Ignoring invalid %s; using %s", name, default)
        return default


PLACES_INSIGHTS_CACHE_TTL_SECONDS = _positive_int_env("PLACES_INSIGHTS_CACHE_TTL_SECONDS", 900)
PLACES_INSIGHTS_CACHE_MAX_ENTRIES = _positive_int_env("PLACES_INSIGHTS_CACHE_MAX_ENTRIES", 512)
ANALYSIS_CACHE_TTL_SECONDS = _positive_int_env("ANALYSIS_CACHE_TTL_SECONDS", 3600)
REPORT_TOKEN_TTL_SECONDS = _positive_int_env("REPORT_TOKEN_TTL_SECONDS", 86400)
analysis_cache = AnalysisCache(
    os.getenv("ANALYSIS_CACHE_PATH", os.path.join(STORAGE_ROOT, 'cache', 'analyses.sqlite3')),
    ttl=ANALYSIS_CACHE_TTL_SECONDS,
    max_entries=_positive_int_env("ANALYSIS_CACHE_MAX_ENTRIES", 512),
    redis_url=os.getenv("REDIS_URL"),
)
_places_insights_cache = {}
_places_insights_cache_lock = threading.Lock()

# A deliberate subset of Google's supported Table A types. A smaller contract
# is safer than accepting arbitrary strings and failing after a billable call.
FRANCHISE_PLACE_TYPES = {
    "bakery", "bar", "cafe", "car_wash", "clothing_store", "convenience_store",
    "dentist", "drugstore", "gas_station", "grocery_store", "gym", "hair_salon",
    "hotel", "laundry", "pharmacy", "pet_store", "restaurant", "shopping_mall",
    "spa", "supermarket",
}
FRANCHISE_TYPE_ALIASES = {
    "coffee_shop": "cafe", "fast_food": "restaurant", "fitness_center": "gym",
    "quick_service_restaurant": "restaurant", "qsr": "restaurant",
}
DEMAND_PRIMARY_TYPES = ("shopping_mall", "transit_station", "tourist_attraction", "university")
SUPPORTING_PRIMARY_TYPES = ("cafe", "convenience_store", "gas_station", "parking", "pharmacy", "supermarket")


class PlacesInsightsError(Exception):
    """Expected Google configuration or upstream error with safe API semantics."""

    def __init__(self, message, code="places_insights_unavailable", retryable=False, http_status=503):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.http_status = http_status


def _parse_places_insights_request(data):
    """Validate the deliberately small public contract for site analysis."""
    if not isinstance(data, dict):
        raise ValueError("A JSON object is required.")
    location = data.get("location") or {}
    if not isinstance(location, dict):
        raise ValueError("location must be an object with latitude and longitude.")
    raw_lat = location.get("latitude", data.get("lat"))
    raw_lon = location.get("longitude", location.get("lng", data.get("lon")))
    if raw_lat is None or raw_lon is None:
        raise ValueError("location.latitude and location.longitude are required.")
    try:
        lat, lon = float(raw_lat), float(raw_lon)
    except (TypeError, ValueError):
        raise ValueError("Coordinates must be numbers.")
    raw_radius = data.get("radius_meters", data.get("radius", 500))
    if isinstance(raw_radius, bool):
        raise ValueError("radius_meters must be an integer.")
    if isinstance(raw_radius, int):
        radius = raw_radius
    elif isinstance(raw_radius, str) and raw_radius.strip().isdigit():
        radius = int(raw_radius.strip())
    else:
        raise ValueError("radius_meters must be an integer.")
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("Coordinates must be valid WGS84 latitude (-90..90) and longitude (-180..180).")
    if not MIN_INSIGHTS_RADIUS_METERS <= radius <= MAX_INSIGHTS_RADIUS_METERS:
        raise ValueError(f"radius_meters must be between {MIN_INSIGHTS_RADIUS_METERS} and {MAX_INSIGHTS_RADIUS_METERS}.")
    place_type = data.get("place_type", data.get("business_type", "restaurant"))
    if not isinstance(place_type, str):
        raise ValueError("place_type must be a supported franchise concept or Google primary type.")
    place_type = FRANCHISE_TYPE_ALIASES.get(place_type.strip().lower(), place_type.strip().lower())
    if place_type not in FRANCHISE_PLACE_TYPES:
        supported = ", ".join(sorted(FRANCHISE_PLACE_TYPES))
        raise ValueError(f"Unsupported place_type. Use one of: {supported}.")
    return {"latitude": lat, "longitude": lon, "radius_meters": radius, "place_type": place_type}


def _insights_request_payload(query, included_primary_types):
    return {"insights": ["INSIGHT_COUNT"], "filter": {
        "locationFilter": {"circle": {"latLng": {"latitude": query["latitude"], "longitude": query["longitude"]}, "radius": query["radius_meters"]}},
        "typeFilter": {"includedPrimaryTypes": list(included_primary_types)},
        "operatingStatus": ["OPERATING_STATUS_OPERATIONAL"],
    }}


def _fetch_places_insights_count(query, included_primary_types):
    """Call Google's Places Aggregate API and return one aggregate count."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    headers = {"Content-Type": "application/json"}
    # The Google reference documents cloud-platform OAuth. An optional token
    # keeps production deployments compatible while preserving the API-key path.
    access_token = os.getenv("GOOGLE_PLACES_INSIGHTS_ACCESS_TOKEN")
    if not api_key and not access_token:
        raise PlacesInsightsError("Google Places Insights credentials are not configured", "places_insights_not_configured")
    if api_key:
        headers["X-Goog-Api-Key"] = api_key
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    cache_key = (query["latitude"], query["longitude"], query["radius_meters"], tuple(included_primary_types))
    now = time.monotonic()
    with _places_insights_cache_lock:
        cached = _places_insights_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1], True
    response = None
    for attempt in range(2):
        try:
            response = requests.post(PLACES_INSIGHTS_URL, headers=headers, json=_insights_request_payload(query, included_primary_types), timeout=12)
        except requests.RequestException as exc:
            if attempt == 0:
                time.sleep(0.25)
                continue
            raise PlacesInsightsError(f"Places Insights request failed: {exc.__class__.__name__}", retryable=True)
        if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
            time.sleep(0.25)
            continue
        break
    if response is None:
        raise PlacesInsightsError("Places Insights network request did not produce a response", retryable=True)
    if not response.ok:
        status = response.status_code
        logger.warning("Places Insights upstream failure: status=%s", status)
        if status in (401, 403):
            raise PlacesInsightsError("Google rejected Places Insights credentials", "places_insights_authentication_failed", http_status=502)
        if status == 400:
            raise PlacesInsightsError("Google rejected the Places Insights request", "places_insights_request_rejected", http_status=502)
        raise PlacesInsightsError(f"Places Insights returned HTTP {status}", retryable=status in (429, 500, 502, 503, 504))
    try:
        response_data = response.json()
        if not isinstance(response_data, dict) or "count" not in response_data:
            raise ValueError("missing count")
        count = int(response_data["count"])
    except (ValueError, TypeError, AttributeError):
        raise PlacesInsightsError("Places Insights returned an invalid count", "places_insights_invalid_response", http_status=502)
    with _places_insights_cache_lock:
        expired_keys = [key for key, value in _places_insights_cache.items() if value[0] <= time.monotonic()]
        for expired_key in expired_keys:
            _places_insights_cache.pop(expired_key, None)
        while len(_places_insights_cache) >= PLACES_INSIGHTS_CACHE_MAX_ENTRIES:
            _places_insights_cache.pop(next(iter(_places_insights_cache)))
        _places_insights_cache[cache_key] = (time.monotonic() + PLACES_INSIGHTS_CACHE_TTL_SECONDS, count)
    return count, False


def _normalise_places_insights(query, direct_count, demand_count, supporting_count, cached):
    supporting_types = [place_type for place_type in SUPPORTING_PRIMARY_TYPES if place_type != query["place_type"]]
    return {"success": True,
            "query": {"location": {"latitude": query["latitude"], "longitude": query["longitude"]}, "radius_meters": query["radius_meters"], "place_type": query["place_type"]},
            "source": {"provider": "Google Places Insights / Places Aggregate API", "mode": "live", "documentation": PLACES_INSIGHTS_DOCS, "cached": cached, "cache_ttl_seconds": PLACES_INSIGHTS_CACHE_TTL_SECONDS},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "demand": {"count": demand_count, "primary_types": list(DEMAND_PRIMARY_TYPES), "meaning": "Potential trip or destination generators in the catchment."},
            "direct_competition": {"count": direct_count, "primary_type": query["place_type"], "meaning": "Places whose Google primary type matches the selected franchise concept."},
            "supporting_categories": {"count": supporting_count, "primary_types": supporting_types, "meaning": "Supporting destination categories, queried separately from direct competition."},
            "caveats": ["These are separate non-additive counts. Do not sum them: a place can satisfy multiple category queries.", "Place counts are not pedestrian foot-traffic or sales measurements.", "Use observed visits, rent, visibility, access, parking, demographics, and unit economics before a site decision."],
            "next_evidence_steps": ["Count people and vehicles at the candidate site by daypart.", "Check lease economics, visibility, access, and parking on site.", "Compare local demand, cannibalization, and sales performance with existing units."]}


@app.route('/api/places-insights', methods=['POST'])
def places_insights():
    """Franchise-friendly site-screening counts from Google Places Insights."""
    try:
        query = _parse_places_insights_request(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    try:
        direct_count, direct_cached = _fetch_places_insights_count(query, (query["place_type"],))
        demand_count, demand_cached = _fetch_places_insights_count(query, DEMAND_PRIMARY_TYPES)
        supporting_types = tuple(place_type for place_type in SUPPORTING_PRIMARY_TYPES if place_type != query["place_type"])
        supporting_count, supporting_cached = _fetch_places_insights_count(query, supporting_types)
        return jsonify(_normalise_places_insights(query, direct_count, demand_count, supporting_count, direct_cached and demand_cached and supporting_cached))
    except PlacesInsightsError as exc:
        logger.warning("Places Insights unavailable: %s", exc)
        error = {"code": exc.code, "message": "Live Google Places Insights data is unavailable. Check Google configuration or try again later.", "retryable": exc.retryable}
        if exc.retryable:
            error["retry_after_seconds"] = 60
        return jsonify({"success": False, "status": "unavailable", "query": {"location": {"latitude": query["latitude"], "longitude": query["longitude"]}, "radius_meters": query["radius_meters"], "place_type": query["place_type"]}, "source": {"provider": "Google Places Insights / Places Aggregate API", "mode": "unavailable", "documentation": PLACES_INSIGHTS_DOCS}, "error": error}), exc.http_status

def nominatim_headers():
    """Build headers for Nominatim requests per usage policy."""
    contact = os.getenv("NOMINATIM_EMAIL", "")
    ua = f"FootTrafficAnalysis/1.0 ({contact})" if contact else "FootTrafficAnalysis/1.0"
    return {"User-Agent": ua}

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def _to_json_safe(obj):
    """Recursively convert common non-serializable types (e.g., numpy types) to JSON-safe primitives."""
    try:
        import numpy as np  # available via pandas dependency
    except Exception:
        np = None

    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    # numpy scalar types
    if np is not None and isinstance(obj, np.generic):
        try:
            return obj.item()
        except Exception:
            pass
    # other objects exposing .item() to get python scalar
    if hasattr(obj, 'item') and callable(getattr(obj, 'item')):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, (int, float, bool, str)) or obj is None:
        return obj
    # Fallback to string representation
    return str(obj)

# Create directories if they don't exist
for directory in ['analyses_new', 'reports']:
    path = os.path.join(STORAGE_ROOT, directory)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created {directory} directory")

# Global error handler to ensure JSON responses for API consumers
@app.errorhandler(500)
def handle_internal_error(e):
    logger.error("Unhandled server error", exc_info=True)
    try:
        # Prefer JSON if client accepts it
        if request.accept_mimetypes and request.accept_mimetypes.accept_json:
            return jsonify({'error': 'Internal server error'}), 500
    except Exception:
        pass
    return "Internal server error", 500

def get_location_name(lat, lon):
    try:
        logger.info(f"Fetching location name for coordinates: {lat}, {lon}")
        email = os.getenv('NOMINATIM_EMAIL', '')
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        if email:
            url += f"&email={quote(email)}"
        response = requests.get(
            url,
            headers=nominatim_headers(),
            timeout=5,
        )
        data = response.json()
        road = data.get('address', {}).get('road', '')
        suburb = data.get('address', {}).get('suburb', '')
        city = data.get('address', {}).get('city', '')
        location_name = road if road else f"{suburb}, {city}"
        logger.info(f"Location name resolved: {location_name}")
        return location_name
    except Exception as e:
        logger.error(f"Error getting location name: {str(e)}")
        return "unknown_location"

@app.route('/')
def index():
    logger.info(f"Index page requested from {get_client_ip()}")
    return render_template('index.html', nominatim_email=os.getenv('NOMINATIM_EMAIL', ''))

@app.route('/api/last-search', methods=['GET'])
def get_last_search():
    try:
        client_ip = get_client_ip()
        logger.info(f"Last search requested from {client_ip}")
        last_search = last_searches.get(client_ip)
        if last_search:
            logger.info(f"Returning last search for {client_ip}: {last_search}")
            return jsonify({
                'success': True,
                'lat': last_search['lat'],
                'lon': last_search['lon'],
                'radius': last_search['radius']
            })
        logger.info(f"No previous search found for {client_ip}")
        return jsonify({'success': False, 'message': 'No previous search found'}), 404
    except Exception as e:
        logger.error(f"Error in get_last_search: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/healthz', methods=['GET'])
def healthz():
    """Simple health check endpoint."""
    try:
        return jsonify({
            'status': 'ok',
            'last_search_count': len(last_searches),
            'time': datetime.now().isoformat()
        }), 200
    except Exception:
        return jsonify({'status': 'error'}), 500

@app.route('/download-report/<filename>')
def download_report(filename):
    """Download PDF report"""
    try:
        # Prevent directory traversal
        if os.path.basename(filename) != filename:
            return jsonify({'error': 'Invalid filename'}), 400
        report_path = os.path.join(STORAGE_ROOT, 'reports', filename)
        if os.path.exists(report_path):
            logger.info(f"Serving report download: {filename}")
            return send_file(report_path, as_attachment=True, download_name=filename)
        else:
            logger.error(f"Report file not found: {filename}")
            return jsonify({'error': 'Report not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({'error': str(e)}), 500

def report_serializer():
    return URLSafeTimedSerializer(app.secret_key, salt='retail-report-v1')


@app.route('/api/report', methods=['POST'])
def create_report():
    """Build the exact signed analysis snapshot without relying on local files."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('report_token'), str):
        return jsonify({'error': 'A report token is required.'}), 400
    if len(data['report_token']) > 2_000_000:
        return jsonify({'error': 'Report token is too large.'}), 413
    try:
        snapshot = report_serializer().loads(data['report_token'], max_age=REPORT_TOKEN_TTL_SECONDS)
    except SignatureExpired:
        return jsonify({'error': 'This report has expired. Analyze the location again.'}), 410
    except BadSignature:
        return jsonify({'error': 'Invalid report token. Analyze the location again.'}), 400
    if snapshot.get('analysis_version') != ANALYSIS_VERSION:
        return jsonify({'error': 'The analysis model has changed. Analyze the location again.'}), 410
    try:
        from pdf_report_generator import LocationViabilityReportGenerator
        output = io.BytesIO()
        started = time.monotonic()
        LocationViabilityReportGenerator().generate_report(
            snapshot['analysis'], snapshot['location_name'], snapshot['latitude'],
            snapshot['longitude'], snapshot['radius_meters'], output,
        )
        logger.info('analysis stage=pdf_generation duration_seconds=%.2f', time.monotonic() - started)
        output.seek(0)
        return send_file(output, mimetype='application/pdf', as_attachment=True,
                         download_name=snapshot['pdf_report'])
    except Exception:
        logger.exception('Report generation failed')
        return jsonify({'error': 'The PDF could not be generated. Try downloading it again.'}), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True)
    try:
        if not isinstance(data, dict):
            raise ValueError('A JSON object is required.')
        if isinstance(data.get('lat'), bool) or isinstance(data.get('lon'), bool):
            raise ValueError('Coordinates must be numbers.')
        lat, lon = float(data['lat']), float(data['lon'])
        if not math.isfinite(lat) or not -90 <= lat <= 90 or not math.isfinite(lon) or not -180 <= lon <= 180:
            raise ValueError('Coordinates are out of range.')
        raw_radius = data.get('radius', 300)
        if isinstance(raw_radius, bool) or float(raw_radius) != int(raw_radius):
            raise ValueError('Radius must be an integer.')
        radius = int(raw_radius)
        if not 100 <= radius <= 2000:
            raise ValueError('Radius must be between 100 and 2000 meters.')
        location_name = data.get('location_name', '')
        if not isinstance(location_name, str) or len(location_name) > 500:
            raise ValueError('Location name must be a string of at most 500 characters.')
        location_name = location_name.strip()
        refresh = data.get('refresh', False)
        if not isinstance(refresh, bool):
            raise ValueError('Refresh must be a boolean.')
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return jsonify({'error': str(error)}), 400

    from analysis_errors import AnalysisTimeoutError, AnalysisUpstreamError
    try:
        started = time.monotonic()
        client_ip = get_client_ip()
        last_searches[client_ip] = {'lat': lat, 'lon': lon, 'radius': radius,
                                   'timestamp': datetime.now().isoformat()}
        key = analysis_key(lat, lon, radius)
        cached_result = None if refresh else analysis_cache.get(key)
        cached = cached_result is not None
        if cached:
            snapshot = cached_result
        else:
            from foot_traffic_analysis import extract_osm_foot_traffic_indicators
            stage_started = time.monotonic()
            _, analysis = extract_osm_foot_traffic_indicators(lat, lon, radius_m=radius)
            logger.info('analysis stage=osm_extraction duration_seconds=%.2f', time.monotonic() - stage_started)
            snapshot = {
                'analysis': _to_json_safe(analysis), 'latitude': lat, 'longitude': lon,
                'radius_meters': radius, 'location_name': '',
                'analysis_version': ANALYSIS_VERSION,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        # Search labels are presentation input, never stored for other users.
        cache_changed = not cached
        if not location_name:
            if not snapshot['location_name']:
                stage_started = time.monotonic()
                snapshot['location_name'] = get_location_name(lat, lon)
                logger.info('analysis stage=reverse_geocoding duration_seconds=%.2f', time.monotonic() - stage_started)
                cache_changed = True
            location_name = snapshot['location_name']
        if cache_changed:
            analysis_cache.set(key, snapshot)

        from pdf_report_generator import LocationViabilityReportGenerator
        snapshot = dict(snapshot, location_name=location_name)
        report_data = LocationViabilityReportGenerator().summarize(
            snapshot['analysis'], location_name, lat, lon, radius,
        )
        # Content identifiers avoid collisions between simultaneous requests.
        identifier = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:24]
        snapshot['pdf_report'] = f'viability_report_{identifier}.pdf'
        filename = f'analysis_{identifier}.json'
        json_filepath = os.path.join(STORAGE_ROOT, 'analyses_new', filename)
        if not os.path.exists(json_filepath):
            with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(json_filepath), delete=False) as saved:
                temporary_path = saved.name
                try:
                    json.dump(snapshot, saved, allow_nan=False)
                    saved.close()
                    os.replace(temporary_path, json_filepath)
                finally:
                    if os.path.exists(temporary_path):
                        os.unlink(temporary_path)
        response_data = dict(snapshot['analysis'])
        response_data.update({
            'lat': lat, 'lon': lon, 'radius_meters': radius, 'location_name': location_name,
            'saved_file': json_filepath, 'pdf_report': snapshot['pdf_report'],
            'report_token': report_serializer().dumps(snapshot),
            'viability_score': report_data['viability_percentage'],
            'viability_rating': report_data['rating'], 'viability_summary': report_data['summary'],
            'cache': {'hit': cached, 'analyzed_at': snapshot['timestamp'],
                      'ttl_seconds': ANALYSIS_CACHE_TTL_SECONDS},
        })
        logger.info('analysis stage=total duration_seconds=%.2f cache_hit=%s', time.monotonic() - started, cached)
        return jsonify(_to_json_safe(response_data))
    except AnalysisTimeoutError as error:
        return jsonify({'error': str(error), 'code': 'analysis_timeout'}), 503
    except AnalysisUpstreamError as error:
        return jsonify({'error': str(error), 'code': 'analysis_upstream_unavailable'}), 503
    except Exception:
        logger.exception('Analysis failed')
        return jsonify({'error': 'The analysis could not be completed. Try again.'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', '1010'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f"Starting Flask server on port {port} (debug={debug})...")
    app.run(debug=debug, host='0.0.0.0', port=port) 
