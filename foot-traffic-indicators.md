| **Indicator**                             | **Free Data Source**                                                                 | **How to Use** |
|-------------------------------------------|--------------------------------------------------------------------------------------|----------------|
| 🥡 Restaurants, Cafes, Shops, Markets      | [OpenStreetMap (OSM)](https://www.openstreetmap.org/) via Overpass API or tools like `osmnx` | Query POIs with tags like `amenity=restaurant`, `shop=*`, etc. |
| 🔀 Intersections & Street Density          | OSM street network via `osmnx`                                                      | Use `osmnx.graph_from_point()` and `count_intersections()` |
| 🚶 Walkability Infrastructure (grids, sidewalks) | OSM                                                                             | Use `highway=footway`, `sidewalk=both`, or `crossing=*` |
| 🚆 MRT/LRT Stations                        | OSM or [Department of Transportation (DOTr)](https://dotr.gov.ph/) maps             | Use OSM tags like `railway=station` and `station=subway` |
| 🚍 Jeepney or Bus Stops                    | OSM (limited), or [LTFRB Open Data Portal](https://ltfrb.gov.ph/) (manual PDFs)     | In OSM: `highway=bus_stop`, `route=bus` |
| 🏢 Residential/Business Zones              | OSM land use (`landuse=residential`, `commercial`) + building footprints            | For density: count building footprints or compute floor-area ratio (FAR) |
| 🏫 Schools, Universities, Hospitals        | OSM                                                                                 | Tags: `amenity=school`, `university`, `college`, `hospital`, `clinic` |
| 🛍️ Malls, Plazas, Markets                 | OSM                                                                                 | Tags: `shop=mall`, `amenity=marketplace`, `leisure=park`, `public_square` |
| 🚸 Pedestrian Crossings, Traffic-Calming   | OSM                                                                                 | Tags: `highway=crossing`, `traffic_calming=*`, `sidewalk=*` |
| 🎭 Event Venues, Tourist Attractions       | OSM + [DOT Philippines Tourism Site](https://beta.tourism.gov.ph/)                 | Tags: `tourism=attraction`, `amenity=place_of_worship`, `leisure=*`, `historic=*` |
| ⛪ **Places of Worship**                  | OSM                                                                                 | Use tag: `amenity=place_of_worship`; optionally filter by religion (e.g., `religion=christian`) |

🍽️ Heuristics for Food Business Location Scoring (200m Radius)

| **Indicator**                     | **Adjusted Threshold (200m)**            | **Why It Matters** |
|----------------------------------|------------------------------------------|--------------------|
| **Restaurants & Cafes**          | ≥ 4 POIs                                  | Indicates demand clustering; food hubs attract more diners. |
| **Shops / Retail POIs**          | ≥ 8 POIs                                  | Retail zones have consistent footfall and service workers. |
| **Intersections (Density)**      | ≥ 20 intersections                        | Denser grids improve visibility and walkability. |
| **Schools / Universities**       | ≥ 1 school or within proximity of campus  | Students provide reliable, low-ticket demand. |
| **Hospitals / Clinics**          | ≥ 1 clinic or small medical facility      | Generates consistent daytime demand from staff and visitors. |
| **Bus / Jeepney Stops**          | ≥ 2 transit stops                         | Transit access = steady pedestrian flow. |
| **Pedestrian Crossings / Sidewalks** | ≥ 3 pedestrian features (crossings, sidewalks) | Key to walk-in access and safety. |
| **Residential Buildings**        | ≥ 5 apartment/condo buildings             | Evening/weekend customer base. |
| **Malls / Markets**              | ≥ 1 small community market or strip mall | Local hubs drive micro-scale shopping and dining traffic. |
| **Tourist or Leisure POIs**      | ≥ 1 park, church, or attraction           | Leisure walkers often dine out. |
| **Places of Worship**            | ≥ 1 large church/mosque OR ≥ 2 small chapels | Spikes foot traffic around services and religious events. |