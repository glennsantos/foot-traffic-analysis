import osmnx as ox
from osmnx import _overpass
import pandas as pd
import json
import traceback
import time
import os
import requests
import contextvars
import logging

logger = logging.getLogger(__name__)
ANALYSIS_TIMEOUT_SECONDS = 180
_analysis_deadline = contextvars.ContextVar("analysis_deadline", default=None)
_overpass_attempts = contextvars.ContextVar("overpass_attempts", default=0)


class AnalysisTimeoutError(Exception):
    pass


class AnalysisUpstreamError(Exception):
    pass


class OverpassAttemptLimitError(Exception):
    pass


def _check_deadline(stage):
    deadline = _analysis_deadline.get()
    if deadline is not None and time.monotonic() >= deadline:
        raise AnalysisTimeoutError(f"Analysis timed out during {stage}")


# OSMnx 1.9.4 recursively retries Overpass 429/504 responses without a limit.
# Intercept each attempt, including its recursive calls, for this request only.
_original_overpass_request = _overpass._overpass_request


def _bounded_overpass_request(data, pause=None, error_pause=60):
    _check_deadline("Overpass request")
    attempt = _overpass_attempts.get() + 1
    _overpass_attempts.set(attempt)
    if attempt > 2:
        raise OverpassAttemptLimitError("Overpass exceeded the request attempt limit")
    return _original_overpass_request(data, pause=pause, error_pause=min(error_pause, 5))


_overpass._overpass_request = _bounded_overpass_request

"""OSM data extraction and analysis utilities."""

# Configure OSMnx with more robust settings (v1 compatible, v2-ready)
try:
    # Prefer new names when available (silence deprecation warnings)
    if hasattr(ox.settings, "requests_timeout"):
        ox.settings.requests_timeout = 20
    else:
        ox.settings.timeout = 20  # fallback for older versions
except Exception:
    pass

# Keep OSMnx's default query area. A 50,000 m² limit subdivided even
# the default 300 m radius into multiple public Overpass requests.

# Use local cache to reduce calls
ox.settings.use_cache = True
ox.settings.cache_folder = '/tmp/osmnx-cache' if os.getenv('VERCEL') else 'cache'

# Avoid calling Overpass status (prevents UnboundLocalError in some environments)
ox.settings.overpass_rate_limit = False

def _parse_overpass_endpoints_from_env():
    env_value = os.getenv("OVERPASS_ENDPOINTS", "").strip()
    if not env_value:
        return None
    endpoints = [e.strip() for e in env_value.split(",") if e.strip()]
    return endpoints or None

# List of alternative Overpass endpoints (safe defaults)
# OSMnx appends /interpreter to this base URL.
OVERPASS_ENDPOINTS = _parse_overpass_endpoints_from_env() or [
    "https://overpass.private.coffee/api",
    "https://overpass-api.de/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
]

def _status_url_for(endpoint: str) -> str:
    # Convert .../api/interpreter -> .../api/status
    if endpoint.endswith("/interpreter"):
        return endpoint.rsplit("/", 1)[0] + "/status"
    # Fallback: append status
    return endpoint.rstrip("/") + "/status"

def _normalize_overpass_urls(endpoint: str):
    """Return a base URL and its interpreter URL for either input form."""
    s = (endpoint or "").strip().rstrip("/")
    if not s:
        return s, s
    if s.endswith("/interpreter"):
        base = s.rsplit("/", 1)[0]
        url = s
    else:
        base = s
        url = s + "/interpreter"
    return base, url

def test_overpass_endpoint(endpoint: str) -> bool:
    """Test if an Overpass endpoint is accessible via its status URL."""
    try:
        status_url = _status_url_for(endpoint)
        response = requests.get(status_url, timeout=5)
        return 200 <= response.status_code < 400
    except Exception:
        return False

def get_working_endpoint():
    """Select the first endpoint; the actual query determines availability."""
    env_url = os.getenv("OVERPASS_URL", "").strip()
    if env_url:
        print(f"Using OVERPASS_URL from environment: {env_url}")
        return env_url
    return OVERPASS_ENDPOINTS[0]

def extract_osm_foot_traffic_indicators(lat, lon, radius_m=300, max_retries=3):
    deadline_token = _analysis_deadline.set(time.monotonic() + ANALYSIS_TIMEOUT_SECONDS)
    attempts_token = _overpass_attempts.set(0)
    try:
        print(f"\nStarting analysis for coordinates: {lat}, {lon} with radius {radius_m}m")
        
        # Find a working endpoint before starting.
        working_endpoint = get_working_endpoint()
        _check_deadline("endpoint selection")
        base_url, _ = _normalize_overpass_urls(working_endpoint)
        ox.settings.overpass_endpoint = base_url
        if hasattr(ox.settings, "overpass_url"):
            ox.settings.overpass_url = base_url
        
        location_point = (lat, lon)

        poi_tags = {
            "amenity": [
                "restaurant", "cafe", "fast_food", "bar", "food_court",
                "school", "university", "college", "hospital", "clinic",
                "place_of_worship", "marketplace", "parking"
            ],
            "shop": True,
            "leisure": True,
            "tourism": True,
            "public_transport": True,
            "highway": ["bus_stop", "crossing"],
            "building": ["office", "commercial"],
            "office": True
        }

        print("Fetching POIs from OpenStreetMap...")
        
        # Keep retries within the same analysis deadline.
        pois = None
        for attempt in range(max_retries):
            try:
                _check_deadline("POI fetch")
                started = time.monotonic()
                _overpass_attempts.set(0)
                print(f"Attempt {attempt + 1}/{max_retries} using endpoint: {ox.settings.overpass_endpoint}")
                pois = ox.features_from_point(location_point, tags=poi_tags, dist=radius_m)
                logger.info("analysis stage=pois duration_seconds=%.2f endpoint=%s", time.monotonic() - started, ox.settings.overpass_endpoint)
                _check_deadline("POI fetch")
                print(f"✓ Successfully fetched {len(pois)} POIs")
                break  # If successful, exit the retry loop
            except AnalysisTimeoutError:
                raise
            except Exception as e:
                logger.warning("analysis stage=pois attempt=%s duration_seconds=%.2f endpoint=%s error=%s", attempt + 1, time.monotonic() - started, ox.settings.overpass_endpoint, e)
                print(f"✗ Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == max_retries - 1:  # Last attempt
                    raise AnalysisUpstreamError(f"Failed to fetch OSM POIs after {max_retries} attempts: {e}") from e
                
                # Try next endpoint
                next_endpoint = OVERPASS_ENDPOINTS[(attempt + 1) % len(OVERPASS_ENDPOINTS)]
                base_url, _ = _normalize_overpass_urls(next_endpoint)
                ox.settings.overpass_endpoint = base_url
                if hasattr(ox.settings, "overpass_url"):
                    ox.settings.overpass_url = base_url
                
                wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                print(f"Waiting {wait_time} seconds before retry with endpoint: {next_endpoint}")
                _check_deadline("POI retry")
                time.sleep(min(wait_time, max(0, _analysis_deadline.get() - time.monotonic())))

        if pois is None:
            raise Exception("Failed to fetch POI data from any endpoint")

        def get_place_details(row):
            try:
                # Handle both dict-like and Series objects
                name = None
                
                # Try various name-related fields
                name_fields = ['name', 'name:en', 'brand', 'operator', 'shop', 'amenity', 'tourism', 'leisure', 'office']
                for field in name_fields:
                    if hasattr(row, 'get'):
                        value = row.get(field, '')
                    elif hasattr(row, '__getitem__') and field in row:
                        value = row[field]
                    else:
                        continue
                    
                    if value and str(value) not in ['', 'nan', 'None']:
                        name = str(value)
                        break
                
                if not name:
                    name = 'Unnamed'
                
                # Get street address if available
                addr = row.get('addr:street', '') if hasattr(row, 'get') else (row['addr:street'] if 'addr:street' in row else '')
                if addr and str(addr) not in ['', 'nan', 'None']:
                    return f"{name} ({addr})"
                return name
            except Exception as e:
                print(f"Error getting place details: {str(e)}")
                return "Unknown Place"

        def get_detailed_place_info(row):
            """Get detailed place information including coordinates and address"""
            try:
                # Handle both dict-like and Series objects
                name = None
                
                # Try various name-related fields
                name_fields = ['name', 'name:en', 'brand', 'operator', 'shop', 'amenity', 'tourism', 'leisure', 'office']
                for field in name_fields:
                    if hasattr(row, 'get'):
                        value = row.get(field, '')
                    elif hasattr(row, '__getitem__') and field in row:
                        value = row[field]
                    else:
                        continue
                    
                    if value and str(value) not in ['', 'nan', 'None']:
                        name = str(value)
                        break
                
                if not name:
                    name = 'Unnamed'
                
                # Get coordinates from geometry
                lat, lon = None, None
                if hasattr(row, 'geometry') and row.geometry is not None:
                    if hasattr(row.geometry, 'centroid'):
                        # For polygons, use centroid
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                    elif hasattr(row.geometry, 'y') and hasattr(row.geometry, 'x'):
                        # For points
                        lat, lon = row.geometry.y, row.geometry.x
                
                # Get address information
                street = row.get('addr:street', '') if hasattr(row, 'get') else (row['addr:street'] if 'addr:street' in row else '')
                housenumber = row.get('addr:housenumber', '') if hasattr(row, 'get') else (row['addr:housenumber'] if 'addr:housenumber' in row else '')
                city = row.get('addr:city', '') if hasattr(row, 'get') else (row['addr:city'] if 'addr:city' in row else '')
                
                address_parts = []
                if housenumber and str(housenumber) not in ['', 'nan', 'None']:
                    address_parts.append(str(housenumber))
                if street and str(street) not in ['', 'nan', 'None']:
                    address_parts.append(str(street))
                if city and str(city) not in ['', 'nan', 'None']:
                    address_parts.append(str(city))
                
                address = ', '.join(address_parts) if address_parts else 'Address not available'
                
                return {
                    'name': name,
                    'latitude': lat,
                    'longitude': lon,
                    'address': address
                }
            except Exception as e:
                print(f"Error getting detailed place info: {str(e)}")
                return {
                    'name': 'Unknown Place',
                    'latitude': None,
                    'longitude': None,
                    'address': 'Address not available'
                }

        def collect_places(pois_df, key, values=None):
            try:
                if key not in pois_df.columns:
                    return {'count': 0, 'places': [], 'detailed_places': []}
                
                if values is None:
                    filtered_df = pois_df[pois_df[key].notnull()]
                else:
                    filtered_df = pois_df[pois_df[key].isin(values)]
                
                places = []
                detailed_places = []
                for _, row in filtered_df.iterrows():
                    place_detail = get_place_details(row)
                    if place_detail and place_detail != 'nan (nan)':  # Exclude 'nan (nan)' entries
                        places.append(place_detail)
                        detailed_places.append(get_detailed_place_info(row))
                
                return {
                    'count': len(places),
                    'places': places,
                    'detailed_places': detailed_places
                }
            except Exception as e:
                print(f"Error collecting places for {key}: {str(e)}")
                return {'count': 0, 'places': [], 'detailed_places': []}

        print("Processing POIs by category...")
        food_places = collect_places(pois, "amenity", ["restaurant", "cafe", "fast_food", "bar", "food_court"])
        education = collect_places(pois, "amenity", ["school", "university", "college"])
        healthcare = collect_places(pois, "amenity", ["hospital", "clinic"])
        markets = collect_places(pois, "amenity", ["marketplace"])
        worship = collect_places(pois, "amenity", ["place_of_worship"])

        # Combine tourist sites and leisure places
        tourist_places = collect_places(pois, "tourism")
        leisure_places = collect_places(pois, "leisure")
        combined_tourist_leisure = {
            'count': tourist_places['count'] + leisure_places['count'],
            'places': tourist_places['places'] + leisure_places['places'],
            'detailed_places': tourist_places['detailed_places'] + leisure_places['detailed_places']
        }

        shops = collect_places(pois, "shop")
        bus_stops = collect_places(pois, "highway", ["bus_stop"])
        crossings = collect_places(pois, "highway", ["crossing"])

        # Office buildings - collect from building=office, building=commercial, and office tags
        office_buildings_building = collect_places(pois, "building", ["office", "commercial"])
        office_buildings_office = collect_places(pois, "office")
        combined_office_buildings = {
            'count': office_buildings_building['count'] + office_buildings_office['count'],
            'places': office_buildings_building['places'] + office_buildings_office['places'],
            'detailed_places': office_buildings_building['detailed_places'] + office_buildings_office['detailed_places']
        }

        # Parking lots - collect from amenity=parking
        parking_lots = collect_places(pois, "amenity", ["parking"])

        print("Analyzing street network...")
        # Use the same retry logic for street network
        G = None
        for attempt in range(max_retries):
            try:
                _check_deadline("street network fetch")
                started = time.monotonic()
                _overpass_attempts.set(0)
                G = ox.graph_from_point(location_point, dist=radius_m, network_type='walk')
                logger.info("analysis stage=street_network duration_seconds=%.2f endpoint=%s", time.monotonic() - started, ox.settings.overpass_endpoint)
                _check_deadline("street network fetch")
                break
            except AnalysisTimeoutError:
                raise
            except Exception as e:
                logger.warning("analysis stage=street_network attempt=%s duration_seconds=%.2f endpoint=%s error=%s", attempt + 1, time.monotonic() - started, ox.settings.overpass_endpoint, e)
                print(f"Street network attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise AnalysisUpstreamError(f"Failed to fetch OSM street network after {max_retries} attempts: {e}") from e
                current_endpoint = ox.settings.overpass_endpoint
                candidates = [_normalize_overpass_urls(endpoint)[0] for endpoint in OVERPASS_ENDPOINTS]
                next_index = (candidates.index(current_endpoint) + 1) % len(candidates) if current_endpoint in candidates else 0
                next_endpoint = OVERPASS_ENDPOINTS[next_index]
                base_url, _ = _normalize_overpass_urls(next_endpoint)
                ox.settings.overpass_endpoint = base_url
                ox.settings.overpass_url = base_url
                _check_deadline("street network retry")
                time.sleep(min(5, max(0, _analysis_deadline.get() - time.monotonic())))
        
        if G is not None:
            nodes, edges = ox.graph_to_gdfs(G)
            intersection_count = len(nodes[nodes.street_count > 1])
            print(f"Found {intersection_count} intersections")
        else:
            intersection_count = 0

        analysis = {
            "latitude": lat,
            "longitude": lon,
            "restaurants_and_cafes": food_places,
            "schools_universities": education,
            "hospitals_clinics": healthcare,
            "markets": markets,
            "places_of_worship": worship,
            "tourist_sites": combined_tourist_leisure,  # Combined tourist and leisure places
            "shops": shops,
            "transport_hubs": bus_stops,
            "pedestrian_crossings": crossings,
            "intersection_count": intersection_count,
            "office_buildings": combined_office_buildings,
            "parking_lots": parking_lots
        }

        # Create a DataFrame with just the counts for backward compatibility
        counts = {k: v['count'] if isinstance(v, dict) else v 
                for k, v in analysis.items()}
        
        print("Analysis completed successfully")
        return pd.DataFrame([counts]), analysis

    except (AnalysisTimeoutError, AnalysisUpstreamError):
        raise
    except Exception as e:
        error_msg = f"Error in extract_osm_foot_traffic_indicators: {str(e)}"
        print(f"FULL ERROR: {error_msg}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        raise Exception(error_msg)
    finally:
        _analysis_deadline.reset(deadline_token)
        _overpass_attempts.reset(attempts_token)
