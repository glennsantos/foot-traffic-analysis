| **Indicator** | **Free Data Source** | **How to Use** |
|---------------|----------------------|----------------|
| 🥡 Restaurants, Cafes, Shops, Markets | [OpenStreetMap (OSM)](https://www.openstreetmap.org/) via Overpass API or tools like `osmnx` | Query POIs with tags like `amenity=restaurant`, `shop=*`, etc. |
| 🔀 Intersections & Street Density | OSM street network via `osmnx` | Use `osmnx.graph_from_point()` and `count_intersections()` |
| 🚶 Walkability Infrastructure (grids, sidewalks) | OSM | Use `highway=footway`, `sidewalk=both`, or `crossing=*` |
| 🚆 MRT/LRT stations | OSM or [Department of Transportation (DOTr)](https://dotr.gov.ph/) maps | OSM tags like `railway=station` and `station=subway` |
| 🚍 Jeepney or Bus Stops | OSM (limited), or [LTFRB Open Data Portal](https://ltfrb.gov.ph/) (manual PDFs) | In OSM: `highway=bus_stop`, `route=bus` |
| 🏢 Residential/Business Zones | OSM land use (`landuse=residential`, `commercial`) + building footprints | For density: count building footprints or compute floor-area ratio (FAR) |
| 🏫 Schools, Universities, Hospitals | OSM | Tags: `amenity=school`, `university`, `college`, `hospital`, `clinic` |
| 🛍️ Malls, Plazas, Markets | OSM | Tags: `shop=mall`, `amenity=marketplace`, `leisure=park`, `public_square` |
| 🚸 Pedestrian Crossings, Traffic-Calming | OSM | Tags: `highway=crossing`, `traffic_calming=*`, `sidewalk=*` |
| 🎭 Event Venues, Tourist Attractions | OSM + [DOT Philippines Tourism Site](https://beta.tourism.gov.ph/) | Tags: `tourism=attraction`, `amenity=place_of_worship`, `leisure=*`, `historic=*` |