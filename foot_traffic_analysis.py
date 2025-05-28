import osmnx as ox
import pandas as pd
import json
import traceback
import time
import requests

# Configure OSMnx with more robust settings
ox.settings.timeout = 300  # Increase timeout to 5 minutes
ox.settings.max_query_area_size = 50_000  # Increase max query area size
ox.settings.memory = 1024 * 1024 * 1024  # 1GB memory limit

# List of alternative Overpass endpoints
OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter", 
    "https://overpass.nchc.org.tw/api/interpreter"
]

def test_overpass_endpoint(endpoint):
    """Test if an Overpass endpoint is accessible"""
    try:
        response = requests.get(endpoint, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_working_endpoint():
    """Find a working Overpass endpoint"""
    for endpoint in OVERPASS_ENDPOINTS:
        print(f"Testing endpoint: {endpoint}")
        if test_overpass_endpoint(endpoint):
            print(f"✓ Endpoint working: {endpoint}")
            return endpoint
        else:
            print(f"✗ Endpoint failed: {endpoint}")
    
    # If no endpoint works, return the default and let OSMnx handle it
    print("⚠ No endpoints responding, using default")
    return OVERPASS_ENDPOINTS[0]

def extract_osm_foot_traffic_indicators(lat, lon, radius_m=300, max_retries=3):
    try:
        print(f"\nStarting analysis for coordinates: {lat}, {lon} with radius {radius_m}m")
        
        # Find a working endpoint before starting
        working_endpoint = get_working_endpoint()
        ox.settings.overpass_endpoint = working_endpoint
        
        location_point = (lat, lon)

        poi_tags = {
            "amenity": [
                "restaurant", "cafe", "fast_food", "bar", "food_court",
                "school", "university", "college", "hospital", "clinic",
                "place_of_worship", "marketplace"
            ],
            "shop": True,
            "leisure": True,
            "tourism": True,
            "public_transport": True,
            "highway": ["bus_stop", "crossing"]
        }

        print("Fetching POIs from OpenStreetMap...")
        
        # Implement retry logic with exponential backoff
        pois = None
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries} using endpoint: {ox.settings.overpass_endpoint}")
                pois = ox.features_from_point(location_point, tags=poi_tags, dist=radius_m)
                print(f"✓ Successfully fetched {len(pois)} POIs")
                break  # If successful, exit the retry loop
            except Exception as e:
                print(f"✗ Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == max_retries - 1:  # Last attempt
                    raise Exception(f"Failed to fetch data after {max_retries} attempts. Last error: {str(e)}")
                
                # Try next endpoint
                next_endpoint = OVERPASS_ENDPOINTS[(attempt + 1) % len(OVERPASS_ENDPOINTS)]
                ox.settings.overpass_endpoint = next_endpoint
                
                wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                print(f"Waiting {wait_time} seconds before retry with endpoint: {next_endpoint}")
                time.sleep(wait_time)

        if pois is None:
            raise Exception("Failed to fetch POI data from any endpoint")

        def get_place_details(row):
            try:
                name = row.get('name', '')
                if not name:
                    # Try to get some identifying information if name is missing
                    if 'brand' in row:
                        name = row['brand']
                    elif 'operator' in row:
                        name = row['operator']
                    else:
                        name = 'Unnamed'
                
                addr = row.get('addr:street', '')
                if addr:
                    return f"{name} ({addr})"
                return name
            except Exception as e:
                print(f"Error getting place details: {str(e)}")
                return "Unknown Place"

        def collect_places(pois_df, key, values=None):
            try:
                if key not in pois_df.columns:
                    return {'count': 0, 'places': []}
                
                if values is None:
                    filtered_df = pois_df[pois_df[key].notnull()]
                else:
                    filtered_df = pois_df[pois_df[key].isin(values)]
                
                places = []
                for _, row in filtered_df.iterrows():
                    place_detail = get_place_details(row)
                    if place_detail and place_detail != 'nan (nan)':  # Exclude 'nan (nan)' entries
                        places.append(place_detail)
                
                return {
                    'count': len(places),
                    'places': places
                }
            except Exception as e:
                print(f"Error collecting places for {key}: {str(e)}")
                return {'count': 0, 'places': []}

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
            'places': tourist_places['places'] + leisure_places['places']
        }

        shops = collect_places(pois, "shop")
        bus_stops = collect_places(pois, "highway", ["bus_stop"])
        crossings = collect_places(pois, "highway", ["crossing"])

        print("Analyzing street network...")
        # Use the same retry logic for street network
        G = None
        for attempt in range(max_retries):
            try:
                G = ox.graph_from_point(location_point, dist=radius_m, network_type='walk')
                break
            except Exception as e:
                print(f"Street network attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    print("⚠ Street network analysis failed, using 0 intersections")
                    intersection_count = 0
                    break
                time.sleep(5)
        
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
            "bus_stops": bus_stops,
            "pedestrian_crossings": crossings,
            "intersection_count": intersection_count
        }

        # Create a DataFrame with just the counts for backward compatibility
        counts = {k: v['count'] if isinstance(v, dict) else v 
                for k, v in analysis.items()}
        
        print("Analysis completed successfully")
        return pd.DataFrame([counts]), analysis

    except Exception as e:
        error_msg = f"Error in extract_osm_foot_traffic_indicators: {str(e)}"
        print(f"FULL ERROR: {error_msg}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        raise Exception(error_msg)