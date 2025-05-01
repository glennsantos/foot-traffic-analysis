import osmnx as ox
import pandas as pd
import json
import traceback

def extract_osm_foot_traffic_indicators(lat, lon, radius_m=300):
    try:
        print(f"\nStarting analysis for coordinates: {lat}, {lon} with radius {radius_m}m")
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
        pois = ox.features_from_point(location_point, tags=poi_tags, dist=radius_m)
        print(f"Found {len(pois)} POIs")

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
        G = ox.graph_from_point(location_point, dist=radius_m, network_type='walk')
        nodes, edges = ox.graph_to_gdfs(G)
        intersection_count = len(nodes[nodes.street_count > 1])
        print(f"Found {intersection_count} intersections")

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
        error_msg = f"Error in extract_osm_foot_traffic_indicators: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise Exception(error_msg)