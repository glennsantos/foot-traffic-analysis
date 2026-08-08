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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('app.log')  # File output
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS from environment (default open for dev)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins == "*":
    CORS(app)
else:
    CORS(app, resources={r"/*": {"origins": [o.strip() for o in allowed_origins.split(",") if o.strip()]}})

# Secret key from env (fallback random for local dev)
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24)

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
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
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
            timeout=20,
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
        report_path = os.path.join('reports', filename)
        if os.path.exists(report_path):
            logger.info(f"Serving report download: {filename}")
            return send_file(report_path, as_attachment=True, download_name=filename)
        else:
            logger.error(f"Report file not found: {filename}")
            return jsonify({'error': 'Report not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Kept only for the legacy endpoint.  Keeping this import local lets
        # the Google Places Insights product start without the retired OSM
        # analysis stack installed.
        from foot_traffic_analysis import extract_osm_foot_traffic_indicators
        from pdf_report_generator import LocationViabilityReportGenerator
        client_ip = get_client_ip()
        logger.info(f"=== ANALYSIS REQUEST START === from {client_ip}")
        
        # Parse request data
        data = request.json
        logger.info(f"Request data: {data}")
        
        lat = float(data['lat'])
        lon = float(data['lon'])
        radius = int(data.get('radius', 300))  # Default to 300m if not specified
        
        logger.info(f"Parsed coordinates: lat={lat}, lon={lon}, radius={radius}m")
        
        # Store the search in session
        last_searches[client_ip] = {
            'lat': lat,
            'lon': lon,
            'radius': radius,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Stored search in session for {client_ip}")
        
        # Get analysis results
        logger.info("Starting OSM data extraction...")
        results, analysis = extract_osm_foot_traffic_indicators(lat, lon, radius_m=radius)
        logger.info("OSM data extraction completed")
        
        analysis_data = results.to_dict('records')[0]
        logger.info(f"Analysis data keys: {list(analysis_data.keys())}")
        
        # Get location name for the file
        location_name = get_location_name(lat, lon)
        safe_location_name = "".join(x for x in location_name if x.isalnum() or x in [' ', '_']).strip()
        
        # Create filename with timestamp and location
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analysis_{timestamp}_{safe_location_name}_{radius}m.json"
        json_filepath = f"analyses_new/{filename}"
        
        # Save analysis to file
        logger.info(f"Saving analysis to file: {json_filepath}")
        with open(json_filepath, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'location_name': location_name,
                'latitude': lat,
                'longitude': lon,
                'radius_meters': radius,
                'analysis': analysis
            }, f, indent=2)
            
        logger.info(f"Analysis saved successfully to: {json_filepath}")
        
        # Generate PDF Report
        logger.info("Generating PDF viability report...")
        try:
            report_generator = LocationViabilityReportGenerator()
            pdf_filename = f"viability_report_{timestamp}_{safe_location_name}_{radius}m.pdf"
            pdf_filepath = f"reports/{pdf_filename}"
            
            # Generate the report and get summary data
            report_data = report_generator.generate_report(
                analysis, location_name, lat, lon, radius, pdf_filepath
            )
            
            logger.info(f"PDF report generated successfully: {pdf_filepath}")
            
            # Add report data to response
            analysis_data.update(analysis)  # Include detailed place information
            analysis_data['saved_file'] = json_filepath
            analysis_data['radius_meters'] = radius
            analysis_data['pdf_report'] = pdf_filename
            analysis_data['viability_score'] = report_data['viability_percentage']
            analysis_data['viability_rating'] = report_data['rating']
            analysis_data['viability_summary'] = report_data['summary']
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            # Continue without PDF if generation fails
            analysis_data.update(analysis)
            analysis_data['saved_file'] = json_filepath
            analysis_data['radius_meters'] = radius
            analysis_data['pdf_report'] = None
            analysis_data['viability_score'] = None
            analysis_data['viability_rating'] = None
            analysis_data['viability_summary'] = "PDF report generation failed"
        
        # Ensure consistent property names with frontend
        response_data = analysis_data.copy()
        response_data['lat'] = lat
        response_data['lon'] = lon
        response_data = _to_json_safe(response_data)
        
        logger.info(f"Returning response with keys: {list(response_data.keys())}")
        logger.info("=== ANALYSIS REQUEST SUCCESS ===")
        
        return jsonify(response_data)
    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        logger.error(f"=== ANALYSIS REQUEST FAILED ===")
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', '1010'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f"Starting Flask server on port {port} (debug={debug})...")
    app.run(debug=debug, host='0.0.0.0', port=port) 
