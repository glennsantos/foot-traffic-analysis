import osmnx as ox
import pandas as pd

def extract_osm_foot_traffic_indicators(lat, lon, radius_m=500):
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

    pois = ox.features_from_point(location_point, tags=poi_tags, dist=radius_m)

    def count_tag(pois_df, key, values=None):
        if key not in pois_df.columns:
            return 0
        if values is None:
            return pois_df[key].notnull().sum()
        return pois_df[pois_df[key].isin(values)].shape[0]

    counts = {
        "latitude": lat,
        "longitude": lon,
        "restaurants_and_cafes": count_tag(pois, "amenity", ["restaurant", "cafe", "fast_food", "bar", "food_court"]),
        "schools_universities": count_tag(pois, "amenity", ["school", "university", "college"]),
        "hospitals_clinics": count_tag(pois, "amenity", ["hospital", "clinic"]),
        "markets": count_tag(pois, "amenity", ["marketplace"]),
        "places_of_worship": count_tag(pois, "amenity", ["place_of_worship"]),
        "tourist_sites": count_tag(pois, "tourism"),
        "leisure_places": count_tag(pois, "leisure"),
        "shops": count_tag(pois, "shop"),
        "bus_stops": count_tag(pois, "highway", ["bus_stop"]),
        "pedestrian_crossings": count_tag(pois, "highway", ["crossing"])
    }

    G = ox.graph_from_point(location_point, dist=radius_m, network_type='walk')
    # Count intersections by counting nodes with more than one edge
    nodes, edges = ox.graph_to_gdfs(G)
    intersection_count = len(nodes[nodes.street_count > 1])

    counts["intersection_count"] = intersection_count

    return pd.DataFrame([counts])

# Example: Intramuros, Manila
df = extract_osm_foot_traffic_indicators(14.5896, 120.9747)
print(df)

# Save results to JSON file
df.to_json('foot_traffic_results.json', orient='records')
print("\nResults have been saved to 'foot_traffic_results.json'")