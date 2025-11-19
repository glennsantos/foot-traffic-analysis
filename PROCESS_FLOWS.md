# Process Flows and Data Flows

## Table of Contents

1. [User Interaction Flows](#user-interaction-flows)
2. [Analysis Process Flow](#analysis-process-flow)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [State Diagrams](#state-diagrams)
5. [Error Handling Flows](#error-handling-flows)
6. [Sequence Diagrams](#sequence-diagrams)

---

## User Interaction Flows

### 1. Initial Page Load Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER OPENS APPLICATION                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              Browser Requests GET /                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Flask: index() renders index.html                    │
│         - Injects NOMINATIM_EMAIL from env                   │
│         - Returns HTML with embedded JS/CSS                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              Browser: DOMContentLoaded Event                 │
│         - Initialize Leaflet map (default: Manila)           │
│         - Load OpenStreetMap tiles                           │
│         - Setup map click handler                            │
│         - Setup search functionality                         │
│         - Setup radius control                               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         JavaScript: loadLastSearch()                         │
│         - AJAX GET /api/last-search                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              Found │                 │ Not Found
                    ↓                 ↓
        ┌───────────────────┐  ┌──────────────┐
        │ Restore Last      │  │ Show Default │
        │ Search Location   │  │ Map View     │
        │ - Center map      │  └──────────────┘
        │ - Place marker    │
        │ - Draw radius     │
        │ - Set radius input│
        └───────────────────┘
                    │
                    ↓
        ┌───────────────────────────────────────┐
        │    MAP READY FOR USER INTERACTION     │
        └───────────────────────────────────────┘
```

### 2. Location Selection Flow - Map Click

```
┌─────────────────────────────────────────────────────────────┐
│              USER CLICKS ON MAP                              │
│              Coordinates: (lat, lng)                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         JavaScript: map.on('click') Handler                  │
│         - Extract lat/lng from event                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
                    ┌────────┴────────┐
                    │                 │
              Marker│                 │ No Marker
              Exists│                 │
                    ↓                 ↓
        ┌───────────────────┐  ┌──────────────────┐
        │ Update Marker     │  │ Create New       │
        │ Position          │  │ Marker           │
        │ marker.setLatLng()│  │ L.marker().addTo()│
        └───────────────────┘  └──────────────────┘
                    │                 │
                    └────────┬────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Store Analysis Coordinates in Marker                 │
│         marker._analysisLat = lat                            │
│         marker._analysisLng = lng                            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Attach Click Handler to Marker                       │
│         marker.on('click', analyzeLocation)                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Update/Create Radius Circle                          │
│         - Get radius from input (default 300m)               │
│         - L.circle([lat, lng], radius)                       │
│         - Style: blue, 10% opacity                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Display Instruction Message                          │
│         "Click on the marker to start analysis"              │
└─────────────────────────────────────────────────────────────┘
```

### 3. Location Selection Flow - Search

```
┌─────────────────────────────────────────────────────────────┐
│         USER TYPES IN SEARCH BOX                             │
│         Input: "Makati City, Manila"                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         JavaScript: searchBox.on('input')                    │
│         - Debounce 200ms                                     │
│         - Check minimum 3 characters                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
            < 3 chars│                 │ >= 3 chars
                    ↓                 ↓
        ┌───────────────────┐  ┌──────────────────────────┐
        │ Hide Search       │  │ Wait 200ms (debounce)    │
        │ Results           │  └──────────┬───────────────┘
        └───────────────────┘             │
                                          ↓
                             ┌────────────────────────────────┐
                             │ AJAX GET to Nominatim API      │
                             │ URL: nominatim.../search       │
                             │ Params:                        │
                             │   - format=json                │
                             │   - q=<query>                  │
                             │   - limit=5                    │
                             │   - email=<if configured>      │
                             └────────────┬───────────────────┘
                                          │
                                 ┌────────┴────────┐
                                 │                 │
                          Success│                 │ Error
                                 ↓                 ↓
                    ┌─────────────────────┐  ┌──────────────┐
                    │ Parse Results       │  │ Hide Results │
                    │ Loop through 5 items│  │ Log Error    │
                    └──────────┬──────────┘  └──────────────┘
                               │
                      ┌────────┴────────┐
                      │                 │
               No Results│               │ Has Results
                      ↓                 ↓
          ┌───────────────────┐  ┌──────────────────────┐
          │ Show "No results  │  │ Create Result Items  │
          │  found"           │  │ - Main address       │
          └───────────────────┘  │ - Full address       │
                                 │ - Click handler      │
                                 └──────────┬───────────┘
                                            │
                                            ↓
                             ┌──────────────────────────────┐
                             │ Display Results Dropdown     │
                             └──────────────────────────────┘
                                            │
┌───────────────────────────────────────────┴──────────┐
│              USER CLICKS RESULT                       │
└────────────────────────────┬──────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Handle Result Click                                  │
│         - Fill search box with selected address              │
│         - Hide results dropdown                              │
│         - Center map: map.setView([lat, lon], 16)            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
                    ┌────────┴────────┐
                    │                 │
              Marker│                 │ No Marker
              Exists│                 │
                    ↓                 ↓
        ┌───────────────────┐  ┌──────────────────┐
        │ Update Marker     │  │ Create Marker    │
        │ + Click Handler   │  │ + Click Handler  │
        └───────────────────┘  └──────────────────┘
                    │                 │
                    └────────┬────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Store Coordinates & Draw Radius Circle               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         Show Analysis Instruction                            │
└─────────────────────────────────────────────────────────────┘
```

### 4. Radius Adjustment Flow

```
┌─────────────────────────────────────────────────────────────┐
│         USER ADJUSTS RADIUS INPUT                            │
│         Input changes: 300m → 500m                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         JavaScript: radiusInput.on('input')                  │
│         - Parse integer value                                │
│         - Validate range (100-2000)                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
           No Marker│                 │ Marker Exists
                    ↓                 ↓
        ┌───────────────────┐  ┌──────────────────────────┐
        │ Do Nothing        │  │ Get Marker Coordinates   │
        │ (no location yet) │  │ marker._analysisLat/Lng  │
        └───────────────────┘  └──────────┬───────────────┘
                                          │
                                          ↓
                             ┌────────────────────────────────┐
                             │ Remove Old Radius Circle       │
                             │ map.removeLayer(radiusCircle)  │
                             └────────────┬───────────────────┘
                                          │
                                          ↓
                             ┌────────────────────────────────┐
                             │ Create New Radius Circle       │
                             │ L.circle([lat, lng], newRadius)│
                             │ - Color: #007bff               │
                             │ - Fill opacity: 0.1            │
                             └────────────┬───────────────────┘
                                          │
                                          ↓
                             ┌────────────────────────────────┐
                             │ Add Circle to Map              │
                             │ radiusCircle.addTo(map)        │
                             └────────────────────────────────┘
```

---

## Analysis Process Flow

### Complete Analysis Workflow

```
┌─────────────────────────────────────────────────────────────┐
│         USER CLICKS MARKER → CONFIRMATION DIALOG             │
│         "Start analysis for this location?"                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               Cancel│                │ OK
                    ↓                 ↓
        ┌───────────────────┐  ┌──────────────────────────┐
        │ Do Nothing        │  │ Call analyzeLocation()   │
        └───────────────────┘  └──────────┬───────────────┘
                                          │
                                          ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 1: FRONTEND PREPARATION                        │
├─────────────────────────────────────────────────────────────┤
│ 1. Test Network Connectivity                                │
│    - GET /api/last-search (test endpoint)                   │
│    - If fails: Show error, abort                            │
│                                                              │
│ 2. Validate Coordinates                                     │
│    - Check lat/lng are present                              │
│    - Get from marker if not provided                        │
│                                                              │
│ 3. Get Analysis Radius                                      │
│    - Read from input field                                  │
│    - Default to 300m if invalid                             │
│                                                              │
│ 4. Update UI State                                          │
│    - Show loading indicator                                 │
│    - Hide previous errors                                   │
│    - Clear previous results                                 │
│    - Show "Analyzing... Please wait"                        │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 2: LOCATION NAME LOOKUP                        │
├─────────────────────────────────────────────────────────────┤
│ Frontend: getLocationName(lat, lng)                         │
│   ↓                                                          │
│ GET https://nominatim.openstreetmap.org/reverse             │
│   - Params: lat, lon, format=json                           │
│   - Headers: User-Agent with email (if configured)          │
│   - Timeout: 20s                                            │
│   ↓                                                          │
│ Parse Response:                                             │
│   - Extract: road, suburb, city                             │
│   - Format: "Road, Suburb, City" or "Suburb, City"         │
│   - Fallback: "Location name not available"                │
│   ↓                                                          │
│ Update UI:                                                  │
│   - Display location name in results section                │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 3: SEND ANALYSIS REQUEST                       │
├─────────────────────────────────────────────────────────────┤
│ POST /analyze                                               │
│ Headers:                                                    │
│   - Content-Type: application/json                          │
│ Body:                                                       │
│   {                                                         │
│     "lat": 14.5995,                                         │
│     "lon": 120.9842,                                        │
│     "radius": 300                                           │
│   }                                                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 4: BACKEND REQUEST HANDLING                    │
├─────────────────────────────────────────────────────────────┤
│ Flask: analyze() route                                      │
│                                                              │
│ 1. Get Client IP                                            │
│    - Check X-Forwarded-For header                           │
│    - Fallback to request.remote_addr                        │
│                                                              │
│ 2. Parse Request Data                                       │
│    - Extract lat, lon, radius from JSON                     │
│    - Validate types (float, float, int)                     │
│    - Default radius: 300m                                   │
│                                                              │
│ 3. Store in Session                                         │
│    - last_searches[client_ip] = {lat, lon, radius, time}    │
│                                                              │
│ 4. Log Request                                              │
│    - "=== ANALYSIS REQUEST START ==="                       │
│    - Log coordinates and radius                             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 5: OSM DATA EXTRACTION                         │
├─────────────────────────────────────────────────────────────┤
│ Call: extract_osm_foot_traffic_indicators(lat, lon, radius) │
│                                                              │
│ SUB-PHASE 5A: ENDPOINT SELECTION                            │
│ ├─→ Check OVERPASS_URL env var                              │
│ ├─→ If not set, test endpoints from OVERPASS_ENDPOINTS      │
│ ├─→ For each endpoint:                                      │
│ │   ├─→ GET <endpoint>/status (timeout: 10s)               │
│ │   ├─→ Check HTTP 2xx/3xx response                        │
│ │   └─→ Return first working endpoint                      │
│ └─→ If none work, use first default                        │
│                                                              │
│ SUB-PHASE 5B: CONFIGURE OSMNX                               │
│ ├─→ Normalize endpoint URL (handle v1/v2 formats)           │
│ ├─→ Set ox.settings.overpass_endpoint (v1 base form)        │
│ ├─→ Set ox.settings.overpass_url (v2 full form)             │
│ └─→ Already configured: timeout=300s, cache=enabled         │
│                                                              │
│ SUB-PHASE 5C: FETCH POIs (with retry)                       │
│ ├─→ Attempt 1:                                              │
│ │   ├─→ ox.features_from_point(location, tags, dist)       │
│ │   ├─→ If success: Got POIs, continue                     │
│ │   └─→ If fail: Log error, wait 5s                        │
│ ├─→ Attempt 2:                                              │
│ │   ├─→ Rotate to next endpoint                            │
│ │   ├─→ Update OSMnx settings                              │
│ │   ├─→ Retry ox.features_from_point()                     │
│ │   └─→ If fail: Log error, wait 10s                       │
│ ├─→ Attempt 3 (final):                                      │
│ │   ├─→ Rotate to next endpoint                            │
│ │   ├─→ Retry ox.features_from_point()                     │
│ │   └─→ If fail: Raise exception with helpful message      │
│ └─→ Success: Continue with POIs GeoDataFrame                │
│                                                              │
│ SUB-PHASE 5D: PROCESS POIs                                  │
│ ├─→ For each indicator category:                            │
│ │   ├─→ Filter POIs by tag and values                      │
│ │   ├─→ Extract place names (priority order):              │
│ │   │   1. name tag                                        │
│ │   │   2. name:en tag                                     │
│ │   │   3. brand tag                                       │
│ │   │   4. operator tag                                    │
│ │   │   5. type tag (shop, amenity, etc.)                 │
│ │   │   6. "Unnamed" fallback                              │
│ │   ├─→ Extract coordinates:                               │
│ │   │   - For points: geometry.y, geometry.x               │
│ │   │   - For polygons: centroid.y, centroid.x             │
│ │   ├─→ Extract address:                                   │
│ │   │   - addr:housenumber                                 │
│ │   │   - addr:street                                      │
│ │   │   - addr:city                                        │
│ │   └─→ Store: {count, places[], detailed_places[]}        │
│ └─→ Combine categories where needed (tourist+leisure, etc.) │
│                                                              │
│ SUB-PHASE 5E: FETCH STREET NETWORK                          │
│ ├─→ ox.graph_from_point(location, dist, network_type='walk')│
│ ├─→ If success:                                             │
│ │   ├─→ ox.graph_to_gdfs(G) → nodes, edges                 │
│ │   └─→ Count intersections (nodes.street_count > 1)       │
│ └─→ If fail (with retries):                                 │
│     └─→ Set intersection_count = 0, log warning             │
│                                                              │
│ SUB-PHASE 5F: BUILD ANALYSIS DICT                           │
│ ├─→ Create analysis dictionary with all indicators          │
│ ├─→ Create DataFrame with counts only (for compatibility)   │
│ └─→ Return: (DataFrame, analysis_dict)                      │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 6: LOCATION NAME (Backend)                     │
├─────────────────────────────────────────────────────────────┤
│ Call: get_location_name(lat, lon)                          │
│   ↓                                                          │
│ GET https://nominatim.openstreetmap.org/reverse             │
│   - Add email query param if configured                     │
│   - Headers: User-Agent with email                          │
│   - Timeout: 20s                                            │
│   ↓                                                          │
│ Parse and sanitize:                                         │
│   - Remove non-alphanumeric (except space, underscore)      │
│   - Use for filename generation                             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 7: SAVE JSON ANALYSIS                          │
├─────────────────────────────────────────────────────────────┤
│ Create filename:                                            │
│   analysis_YYYYMMDD_HHMMSS_<location>_<radius>m.json        │
│                                                              │
│ Build JSON structure:                                       │
│   {                                                         │
│     "timestamp": ISO-8601,                                  │
│     "location_name": string,                                │
│     "latitude": float,                                      │
│     "longitude": float,                                     │
│     "radius_meters": int,                                   │
│     "analysis": {                                           │
│       "<indicator>": {                                      │
│         "count": int,                                       │
│         "places": [strings],                               │
│         "detailed_places": [{name, lat, lon, addr}]        │
│       }                                                     │
│     }                                                       │
│   }                                                         │
│                                                              │
│ Write to: analyses_new/<filename>                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 8: PDF REPORT GENERATION                       │
├─────────────────────────────────────────────────────────────┤
│ Create: LocationViabilityReportGenerator()                 │
│                                                              │
│ SUB-PHASE 8A: CALCULATE SCORES                              │
│ ├─→ For each indicator:                                     │
│ │   ├─→ Get count from analysis data                       │
│ │   ├─→ Get threshold and weight from criteria             │
│ │   ├─→ Calculate base_score:                              │
│ │   │   - If count >= threshold: 100%                      │
│ │   │   - Else: (count/threshold) * 100                    │
│ │   │   - Bonus if count > threshold*2: +20 (max 120)     │
│ │   ├─→ Calculate weighted_score:                          │
│ │   │   - base_score * weight                              │
│ │   └─→ Store: {indicator, count, threshold, base_score,   │
│ │              weighted_score, weight, meets_criteria,     │
│ │              description, places}                         │
│ └─→ Sort scores by weighted_score (descending)              │
│                                                              │
│ SUB-PHASE 8B: CALCULATE VIABILITY                           │
│ ├─→ total_weighted = sum(all weighted_scores)               │
│ ├─→ max_possible = sum(100 * weight for all criteria)       │
│ ├─→ viability_% = (total_weighted / max_possible) * 100     │
│ └─→ Determine rating:                                       │
│     - >= 98%: BEST                                          │
│     - >= 95%: OUTSTANDING                                   │
│     - >= 85%: EXCELLENT                                     │
│     - >= 80%: GOOD                                          │
│     - >= 70%: MODERATE                                      │
│     - < 70%: POOR                                           │
│                                                              │
│ SUB-PHASE 8C: GENERATE PDF                                  │
│ ├─→ Create PDF document (A4 page size)                      │
│ ├─→ Add title: "FOOT TRAFFIC VIABILITY ANALYSIS"           │
│ ├─→ Add executive summary:                                  │
│ │   - Location details                                     │
│ │   - Viability score and rating                           │
│ │   - Criteria met count                                   │
│ │   - Top 3 indicators                                     │
│ │   - Bottom 2 indicators                                  │
│ │   - Recommendation                                       │
│ ├─→ Add overall score (large, color-coded)                  │
│ ├─→ Add indicators table (ranked)                           │
│ ├─→ For each indicator (in rank order):                     │
│ │   ├─→ Indicator name and score                           │
│ │   ├─→ Status (meets/below threshold)                     │
│ │   ├─→ Details (count, threshold, weight)                 │
│ │   ├─→ Description/rationale                              │
│ │   └─→ Places table (name, lat, lon, address)            │
│ ├─→ Add conclusion section                                  │
│ ├─→ Add footer (timestamp, attribution)                     │
│ └─→ Save to: reports/<filename>.pdf                         │
│                                                              │
│ Return: {viability_%, rating, summary, scores}              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 9: BUILD RESPONSE                              │
├─────────────────────────────────────────────────────────────┤
│ Merge data:                                                 │
│   - analysis_data (from DataFrame)                          │
│   - analysis (detailed dict with places)                    │
│   - viability_score                                         │
│   - viability_rating                                        │
│   - viability_summary (HTML)                                │
│   - pdf_report (filename)                                   │
│   - saved_file (JSON path)                                  │
│   - radius_meters                                           │
│   - lat, lon                                                │
│                                                              │
│ Convert to JSON-safe:                                       │
│   - Recursively convert numpy types to Python types         │
│   - Handle: np.int64, np.float64, etc.                      │
│   - Call .item() on numpy scalars                           │
│                                                              │
│ Log success: "=== ANALYSIS REQUEST SUCCESS ==="             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 10: SEND RESPONSE                              │
├─────────────────────────────────────────────────────────────┤
│ Return: jsonify(response_data), 200                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│         PHASE 11: FRONTEND DISPLAY                           │
├─────────────────────────────────────────────────────────────┤
│ JavaScript: displayResults(data)                            │
│                                                              │
│ 1. Update Location Info:                                    │
│    - Display lat/lon (4 decimals)                           │
│    - Display analysis radius                                │
│                                                              │
│ 2. Show Viability Summary:                                  │
│    - Score with color coding                                │
│    - Rating (BEST, EXCELLENT, etc.)                         │
│    - Summary text (strip HTML, format)                      │
│                                                              │
│ 3. Enable PDF Download:                                     │
│    - Set link href: /download-report/<filename>             │
│    - Show download button                                   │
│                                                              │
│ 4. Show Save Info:                                          │
│    - Display JSON file path                                 │
│                                                              │
│ 5. Populate Indicators Table:                               │
│    - Create row for each indicator                          │
│    - Display: name, count, description                      │
│    - Add checkmark (✓/✗) if meets criteria                  │
│    - Add criteria note                                      │
│    - Add "Show Places" toggle if places exist               │
│                                                              │
│ 6. Hide Loading Indicator                                   │
│                                                              │
│ 7. Show Results Section                                     │
└─────────────────────────────────────────────────────────────┘
```

### Error Handling in Analysis Flow

```
┌─────────────────────────────────────────────────────────────┐
│              ERROR OCCURS AT ANY PHASE                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
             Backend│                 │ Frontend
                    ↓                 ↓
┌──────────────────────────┐  ┌──────────────────────────┐
│ BACKEND ERROR HANDLING   │  │ FRONTEND ERROR HANDLING  │
│                          │  │                          │
│ 1. Log Error:            │  │ 1. Parse Error:          │
│    - Full traceback      │  │    - HTTP status code    │
│    - Context (lat/lon)   │  │    - Error message       │
│    - Timestamp           │  │    - Response body       │
│                          │  │                          │
│ 2. Identify Error Type:  │  │ 2. Categorize:           │
│    - Network (Overpass)  │  │    - Network error       │
│    - Validation          │  │    - Timeout             │
│    - Processing          │  │    - Server error        │
│    - PDF generation      │  │    - Invalid data        │
│                          │  │                          │
│ 3. Handle:               │  │ 3. Display to User:      │
│    - Retry if possible   │  │    - Hide loading        │
│    - Fallback values     │  │    - Show error div      │
│    - Continue w/o PDF    │  │    - Clear error msg     │
│                          │  │    - Add suggestions     │
│ 4. Return Response:      │  │                          │
│    - HTTP 400/500        │  │ 4. Log to Console:       │
│    - JSON error object   │  │    - Full error details  │
│    - Clear message       │  │    - Stack trace         │
└──────────────────────────┘  └──────────────────────────┘
```

---

## Data Flow Diagrams

### 1. OSM Data Retrieval Data Flow

```
┌──────────────┐
│   Frontend   │
│  JavaScript  │
└──────┬───────┘
       │ {lat, lon, radius}
       ↓
┌──────────────────────────────────────────────────────────┐
│                   Flask Backend                          │
│ ┌──────────────────────────────────────────────────────┐ │
│ │              extract_osm_foot_traffic_indicators     │ │
│ └──────┬───────────────────────────────────────────────┘ │
│        │                                                  │
│        │ 1. Find Working Endpoint                        │
│        ↓                                                  │
│ ┌──────────────────┐                                     │
│ │ Test Endpoints   │──→ GET /status ──→ Overpass API    │
│ │ - kumi.systems   │←── 200 OK ←────────┘               │
│ │ - overpass-api.de│                                     │
│ └──────┬───────────┘                                     │
│        │ Selected endpoint URL                           │
│        ↓                                                  │
│ ┌──────────────────────────────────────────────────────┐ │
│ │           Configure OSMnx Settings                   │ │
│ │  - overpass_endpoint = working_url                   │ │
│ │  - timeout = 300s                                    │ │
│ │  - cache = enabled                                   │ │
│ │  - rate_limit = false                                │ │
│ └──────┬───────────────────────────────────────────────┘ │
│        │                                                  │
│        │ 2. Fetch POIs                                   │
│        ↓                                                  │
│ ┌──────────────────────────────────────────────────────┐ │
│ │              OSMnx Library                           │ │
│ │  ox.features_from_point(                             │ │
│ │    point=(lat, lon),                                 │ │
│ │    tags={amenity:[], shop:True, ...},               │ │
│ │    dist=radius                                       │ │
│ │  )                                                   │ │
│ └──────┬───────────────────────────────────────────────┘ │
│        │ Overpass QL Query                               │
│        ↓                                                  │
└────────┼──────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────┐
│          Overpass API Server                   │
│  - Receives query via POST                     │
│  - Searches OSM database                       │
│  - Filters by bounding box (radius from point) │
│  - Filters by tags (amenity, shop, etc.)       │
│  - Returns XML/JSON                            │
└────────┬───────────────────────────────────────┘
         │ OSM Data (GeoJSON/XML)
         ↓
┌────────────────────────────────────────────────────────────┐
│                   Flask Backend                            │
│ ┌────────────────────────────────────────────────────────┐ │
│ │              OSMnx Processing                          │ │
│ │  - Parse response                                      │ │
│ │  - Create GeoDataFrame                                 │ │
│ │  - Columns: geometry, name, amenity, shop, tags, etc.  │ │
│ └──────┬─────────────────────────────────────────────────┘ │
│        │ GeoDataFrame (POIs)                               │
│        ↓                                                    │
│ ┌────────────────────────────────────────────────────────┐ │
│ │         Process and Categorize POIs                    │ │
│ │  For each indicator:                                   │ │
│ │    - Filter by tag                                     │ │
│ │    - Extract names                                     │ │
│ │    - Extract coordinates                               │ │
│ │    - Extract addresses                                 │ │
│ │    - Build:                                            │ │
│ │      {                                                 │ │
│ │        count: int,                                     │ │
│ │        places: [strings],                             │ │
│ │        detailed_places: [                             │ │
│ │          {name, lat, lon, address}                    │ │
│ │        ]                                               │ │
│ │      }                                                 │ │
│ └──────┬─────────────────────────────────────────────────┘ │
│        │ Processed Indicators                              │
│        ↓                                                    │
│ ┌────────────────────────────────────────────────────────┐ │
│ │              3. Fetch Street Network                   │ │
│ │  ox.graph_from_point(                                  │ │
│ │    point=(lat, lon),                                   │ │
│ │    dist=radius,                                        │ │
│ │    network_type='walk'                                 │ │
│ │  )                                                     │ │
│ └──────┬─────────────────────────────────────────────────┘ │
│        │ Overpass QL Query (ways, nodes)                   │
└────────┼────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────┐
│          Overpass API Server                   │
│  - Fetch road network data                     │
│  - Return nodes and ways                       │
└────────┬───────────────────────────────────────┘
         │ OSM Network Data
         ↓
┌────────────────────────────────────────────────────────────┐
│                   Flask Backend                            │
│ ┌────────────────────────────────────────────────────────┐ │
│ │           OSMnx Network Processing                     │ │
│ │  - Create NetworkX graph                               │ │
│ │  - Nodes: intersections, dead-ends                     │ │
│ │  - Edges: street segments                              │ │
│ │  - Calculate street_count per node                     │ │
│ │  - Count intersections (street_count > 1)              │ │
│ └──────┬─────────────────────────────────────────────────┘ │
│        │ intersection_count                                │
│        ↓                                                    │
│ ┌────────────────────────────────────────────────────────┐ │
│ │             Build Final Analysis Dict                  │ │
│ │  {                                                     │ │
│ │    "latitude": lat,                                    │ │
│ │    "longitude": lon,                                   │ │
│ │    "restaurants_and_cafes": {...},                     │ │
│ │    "shops": {...},                                     │ │
│ │    "intersection_count": int,                          │ │
│ │    ...                                                 │ │
│ │  }                                                     │ │
│ └──────┬─────────────────────────────────────────────────┘ │
│        │ Complete Analysis                                 │
│        ↓                                                    │
│    Return (DataFrame, analysis_dict)                       │
└────────────────────────────────────────────────────────────┘
```

### 2. PDF Generation Data Flow

```
┌──────────────────────────────────────────────────────────┐
│              Analysis Dict (from OSM)                    │
│  {                                                       │
│    "restaurants_and_cafes": {                            │
│      count: 12,                                          │
│      places: ["Cafe A", ...],                           │
│      detailed_places: [{name, lat, lon, addr}, ...]     │
│    },                                                    │
│    "shops": {...},                                       │
│    "intersection_count": 25,                             │
│    ...                                                   │
│  }                                                       │
└──────┬───────────────────────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────────────────────┐
│      LocationViabilityReportGenerator                    │
│                                                          │
│  STEP 1: Calculate Scores                               │
│  ┌────────────────────────────────────────────────────┐ │
│  │  For each indicator:                               │ │
│  │                                                    │ │
│  │  Input:                                            │ │
│  │    - count (from analysis)                         │ │
│  │    - threshold (from criteria)                     │ │
│  │    - weight (from criteria)                        │ │
│  │                                                    │ │
│  │  Calculate:                                        │ │
│  │    base_score = count >= threshold                │ │
│  │                 ? 100                              │ │
│  │                 : (count/threshold)*100            │ │
│  │                                                    │ │
│  │    if count > threshold*2:                         │ │
│  │      base_score = min(120, base_score + 20)       │ │
│  │                                                    │ │
│  │    weighted_score = base_score * weight           │ │
│  │                                                    │ │
│  │  Output:                                           │ │
│  │    {                                               │ │
│  │      indicator: "restaurants_and_cafes",          │ │
│  │      count: 12,                                    │ │
│  │      threshold: 4,                                 │ │
│  │      base_score: 120,                             │ │
│  │      weighted_score: 15.6,                        │ │
│  │      weight: 0.13,                                 │ │
│  │      meets_criteria: true,                        │ │
│  │      description: "...",                           │ │
│  │      places: [...]                                 │ │
│  │    }                                               │ │
│  └────┬───────────────────────────────────────────────┘ │
│       │ List of scored indicators                       │
│       ↓                                                  │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Sort by weighted_score (descending)               │ │
│  └────┬───────────────────────────────────────────────┘ │
│       │ Ranked scores                                   │
│       ↓                                                  │
│  STEP 2: Calculate Overall Viability                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │  total_weighted = sum(all weighted_scores)         │ │
│  │  max_possible = sum(100 * weight for all)          │ │
│  │  viability_% = (total_weighted/max_possible)*100   │ │
│  │                                                    │ │
│  │  Example:                                          │ │
│  │    total_weighted = 87.5                           │ │
│  │    max_possible = 100                              │ │
│  │    viability_% = 87.5%                             │ │
│  │    rating = "EXCELLENT"                            │ │
│  │    color = colors.blue                             │ │
│  └────┬───────────────────────────────────────────────┘ │
│       │ {viability_%, rating, color}                    │
│       ↓                                                  │
│  STEP 3: Generate Content Sections                      │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Executive Summary (HTML):                         │ │
│  │    - Location: name, coords, radius                │ │
│  │    - Overall viability: score, rating              │ │
│  │    - Criteria met: 10/12                           │ │
│  │    - Top 3 indicators                              │ │
│  │    - Bottom 2 indicators                           │ │
│  │    - Recommendation                                │ │
│  ├────────────────────────────────────────────────────┤ │
│  │  Indicators Table Data:                            │ │
│  │    [                                               │ │
│  │      ['Rank','Indicator','Count','Threshold',...], │ │
│  │      ['1', 'Shops', '15', '8', '187.5%', '✓'],    │ │
│  │      ['2', 'Restaurants', '12', '4', '120%', '✓'],│ │
│  │      ...                                           │ │
│  │    ]                                               │ │
│  ├────────────────────────────────────────────────────┤ │
│  │  For each indicator:                               │ │
│  │    Detailed Section:                               │ │
│  │      - Header (name, score)                        │ │
│  │      - Status (meets/below)                        │ │
│  │      - Details (count, threshold, weight)          │ │
│  │      - Description                                 │ │
│  │      - Places table (if available)                 │ │
│  ├────────────────────────────────────────────────────┤ │
│  │  Conclusion:                                       │ │
│  │    - Overall assessment                            │ │
│  │    - Recommendations based on rating               │ │
│  │    - Top 3 strengths                               │ │
│  │    - Areas for improvement                         │ │
│  └────┬───────────────────────────────────────────────┘ │
│       │ Content components                              │
│       ↓                                                  │
│  STEP 4: Build PDF with ReportLab                       │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Create Document:                                  │ │
│  │    - Page size: A4                                 │ │
│  │    - Margins: default                              │ │
│  │                                                    │ │
│  │  Story (page elements):                            │ │
│  │    1. Title Paragraph                              │ │
│  │       - Style: CustomTitle (24pt, centered, blue) │ │
│  │       - Text: "FOOT TRAFFIC VIABILITY ANALYSIS"   │ │
│  │    2. Spacer (20pt)                                │ │
│  │    3. Executive Summary Paragraph                  │ │
│  │       - Style: Summary (grey bg, bordered)         │ │
│  │       - Content: formatted HTML                    │ │
│  │    4. Spacer (20pt)                                │ │
│  │    5. Score Paragraph                              │ │
│  │       - Style: Large, centered, color-coded        │ │
│  │       - Text: "87.5% (EXCELLENT)"                  │ │
│  │    6. Spacer (20pt)                                │ │
│  │    7. Section Header                               │ │
│  │    8. Indicators Table                             │ │
│  │       - TableStyle: headers, borders, alternating  │ │
│  │    9. Spacer (20pt)                                │ │
│  │   10. Detailed Sections (for each indicator)       │ │
│  │       - Heading paragraph                          │ │
│  │       - Details paragraphs                         │ │
│  │       - Places table (if available)                │ │
│  │       - Spacer                                     │ │
│  │   11. Page Break                                   │ │
│  │   12. Conclusion Section                           │ │
│  │   13. Footer                                       │ │
│  │                                                    │ │
│  │  Build:                                            │ │
│  │    doc.build(story)                                │ │
│  └────┬───────────────────────────────────────────────┘ │
│       │ PDF binary data                                 │
│       ↓                                                  │
│  STEP 5: Write to File                                  │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Output path:                                      │ │
│  │    reports/viability_report_<timestamp>_           │ │
│  │            <location>_<radius>m.pdf                │ │
│  │                                                    │ │
│  │  Save binary PDF data to disk                      │ │
│  └────┬───────────────────────────────────────────────┘ │
│       │                                                  │
│       ↓                                                  │
│  Return: {viability_%, rating, summary, scores}         │
└──────────────────────────────────────────────────────────┘
```

### 3. Complete Request-Response Data Flow

```
USER                 BROWSER              FLASK              OSM APIS          FILE SYSTEM
  │                     │                   │                    │                  │
  │ Click Marker        │                   │                    │                  │
  │────────────────────→│                   │                    │                  │
  │                     │                   │                    │                  │
  │                     │ POST /analyze     │                    │                  │
  │                     │  {lat,lon,radius} │                    │                  │
  │                     │──────────────────→│                    │                  │
  │                     │                   │                    │                  │
  │                     │                   │ Parse & Validate   │                  │
  │                     │                   │ Store in session   │                  │
  │                     │                   │                    │                  │
  │                     │                   │ GET /reverse       │                  │
  │                     │                   │  (Nominatim)       │                  │
  │                     │                   │───────────────────→│                  │
  │                     │                   │                    │                  │
  │                     │                   │   Location Name    │                  │
  │                     │                   │←───────────────────│                  │
  │                     │                   │                    │                  │
  │                     │                   │ Test endpoints     │                  │
  │                     │                   │  GET /status       │                  │
  │                     │                   │───────────────────→│                  │
  │                     │                   │    200 OK          │                  │
  │                     │                   │←───────────────────│                  │
  │                     │                   │                    │                  │
  │                     │                   │ POST /interpreter  │                  │
  │                     │                   │  (Overpass QL)     │                  │
  │                     │                   │  - Query POIs      │                  │
  │                     │                   │───────────────────→│                  │
  │                     │                   │                    │ Search OSM DB    │
  │                     │                   │                    │ Filter by tags   │
  │                     │                   │   GeoJSON/XML      │                  │
  │                     │                   │←───────────────────│                  │
  │                     │                   │                    │                  │
  │                     │                   │ Process POIs       │                  │
  │                     │                   │ - Extract names    │                  │
  │                     │                   │ - Coordinates      │                  │
  │                     │                   │ - Addresses        │                  │
  │                     │                   │                    │                  │
  │                     │                   │ POST /interpreter  │                  │
  │                     │                   │  - Query network   │                  │
  │                     │                   │───────────────────→│                  │
  │                     │                   │   Network data     │                  │
  │                     │                   │←───────────────────│                  │
  │                     │                   │                    │                  │
  │                     │                   │ Count intersections│                  │
  │                     │                   │                    │                  │
  │                     │                   │                    │   Write JSON     │
  │                     │                   │────────────────────┼─────────────────→│
  │                     │                   │                    │                  │
  │                     │                   │ Generate PDF       │                  │
  │                     │                   │ - Calculate scores │                  │
  │                     │                   │ - Create report    │                  │
  │                     │                   │                    │   Write PDF      │
  │                     │                   │────────────────────┼─────────────────→│
  │                     │                   │                    │                  │
  │                     │                   │ Build response     │                  │
  │                     │                   │ - Merge all data   │                  │
  │                     │                   │ - Convert to JSON  │                  │
  │                     │                   │                    │                  │
  │                     │   200 OK          │                    │                  │
  │                     │   {analysis data} │                    │                  │
  │                     │←──────────────────│                    │                  │
  │                     │                   │                    │                  │
  │                     │ Parse & Display   │                    │                  │
  │                     │ - Update UI       │                    │                  │
  │                     │ - Show viability  │                    │                  │
  │                     │ - Enable PDF link │                    │                  │
  │                     │                   │                    │                  │
  │  Results Displayed  │                   │                    │                  │
  │←────────────────────│                   │                    │                  │
  │                     │                   │                    │                  │
  │ Click Download PDF  │                   │                    │                  │
  │────────────────────→│                   │                    │                  │
  │                     │                   │                    │                  │
  │                     │ GET /download-    │                    │                  │
  │                     │  report/<file>    │                    │                  │
  │                     │──────────────────→│                    │                  │
  │                     │                   │                    │   Read PDF       │
  │                     │                   │────────────────────┼─────────────────→│
  │                     │                   │    PDF bytes       │                  │
  │                     │                   │←───────────────────┼──────────────────│
  │                     │   200 OK          │                    │                  │
  │                     │   PDF file        │                    │                  │
  │                     │←──────────────────│                    │                  │
  │                     │                   │                    │                  │
  │  PDF Downloaded     │                   │                    │                  │
  │←────────────────────│                   │                    │                  │
```

---

## State Diagrams

### Application State Machine

```
┌─────────────────────────────────────────────────────────┐
│                    INITIAL STATE                        │
│  - Map loaded (default center)                          │
│  - No marker                                            │
│  - No analysis                                          │
│  - Last search: checking...                             │
└─────────────────┬───────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
   No Last│                 │ Has Last
    Search│                 │ Search
         ↓                 ↓
    ┌─────────┐    ┌───────────────┐
    │ DEFAULT │    │ LAST_RESTORED │
    │  STATE  │    │    STATE      │
    └────┬────┘    └───────┬───────┘
         │                 │
         └────────┬────────┘
                  │
                  │ User Action: Click Map OR Search
                  ↓
┌─────────────────────────────────────────────────────────┐
│                 LOCATION_SELECTED STATE                 │
│  - Marker placed on map                                 │
│  - Radius circle visible                                │
│  - Instruction: "Click marker to analyze"               │
│  - Analysis results: hidden                             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ User Action: Adjust Radius
                  ↓
┌─────────────────────────────────────────────────────────┐
│              RADIUS_ADJUSTED STATE                      │
│  - Radius circle updated                                │
│  - Marker remains                                       │
│  - Still awaiting analysis trigger                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ User Action: Click Marker → Confirm
                  ↓
┌─────────────────────────────────────────────────────────┐
│                  ANALYZING STATE                        │
│  - Loading indicator visible                            │
│  - UI disabled                                          │
│  - "Analyzing... Please wait"                           │
│  - Backend request in flight                            │
└─────────────────┬───────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
     Error│                 │ Success
         ↓                 ↓
┌─────────────────┐  ┌─────────────────────────────────┐
│  ERROR STATE    │  │    RESULTS_DISPLAYED STATE      │
│  - Error msg    │  │  - Analysis table populated     │
│  - Loading off  │  │  - Viability summary shown      │
│  - Can retry    │  │  - PDF download enabled         │
│  - Marker OK    │  │  - Loading indicator hidden     │
└─────────────────┘  └──────────┬──────────────────────┘
         │                      │
         │                      │ User Action: Download PDF
         │                      ↓
         │            ┌──────────────────────┐
         │            │ PDF_DOWNLOADING STATE│
         │            │  - Request PDF file  │
         │            │  - Browser downloads │
         │            └──────────┬───────────┘
         │                      │
         │                      ↓
         │            ┌──────────────────────┐
         │            │ PDF_DOWNLOADED STATE │
         │            │  - Results still OK  │
         │            │  - Can analyze again │
         │            └──────────────────────┘
         │                      │
         └──────────┬───────────┘
                    │
                    │ User Action: New Location
                    ↓
          Back to LOCATION_SELECTED
```

### Session Data State

```
┌────────────────────────────────────────┐
│     SESSION DATA (Server-side)         │
│                                        │
│  Structure:                            │
│  last_searches = {                     │
│    "client_ip": {                      │
│      "lat": float,                     │
│      "lon": float,                     │
│      "radius": int,                    │
│      "timestamp": ISO-8601             │
│    }                                   │
│  }                                     │
└────────┬───────────────────────────────┘
         │
         │ Initial State: {}
         │
         ↓
┌────────────────────────────────────────┐
│  Event: POST /analyze                  │
│  Action: Store search                  │
└────────┬───────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────┐
│  Updated State:                        │
│  last_searches = {                     │
│    "192.168.1.100": {                  │
│      "lat": 14.5995,                   │
│      "lon": 120.9842,                  │
│      "radius": 300,                    │
│      "timestamp": "2023-11-18T..."     │
│    }                                   │
│  }                                     │
└────────┬───────────────────────────────┘
         │
         │ Retention: In-memory (lost on restart)
         │ Scope: Per client IP
         │
         ↓
┌────────────────────────────────────────┐
│  Event: GET /api/last-search           │
│  Action: Retrieve by client IP         │
│  Response: Last search or 404          │
└────────────────────────────────────────┘
```

---

## Error Handling Flows

### Network Error Recovery Flow

```
┌─────────────────────────────────────────┐
│    Overpass API Request Failed          │
│    (Connection timeout, DNS error, etc.)│
└─────────────────┬───────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│  Determine Attempt Number                       │
│  - Attempt 1, 2, or 3?                          │
└─────────────────┬───────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
  Attempt│                 │ Attempt
    1-2  │                 │   3
         ↓                 ↓
┌──────────────────┐  ┌────────────────────┐
│  RETRY LOGIC     │  │  FAIL & RAISE      │
│                  │  │  EXCEPTION         │
│ 1. Log error     │  │                    │
│ 2. Rotate to     │  │ - Log full error   │
│    next endpoint │  │ - Include context  │
│ 3. Update OSMnx  │  │ - Suggest actions  │
│    settings      │  │ - Raise Exception  │
│ 4. Calculate     │  └─────────┬──────────┘
│    backoff:      │            │
│    - Attempt 1:  │            ↓
│      5 seconds   │  ┌─────────────────────┐
│    - Attempt 2:  │  │ Backend catches     │
│      10 seconds  │  │ Returns 400 error   │
│ 5. Sleep         │  │ with message        │
│ 6. Retry request │  └─────────┬───────────┘
└──────┬───────────┘            │
       │                        ↓
       │              ┌──────────────────────┐
       │              │ Frontend displays    │
       │              │ error to user        │
       │              │ - Show error div     │
       │              │ - Suggest retry      │
       │              │ - Mention network    │
       │              └──────────────────────┘
       │
       ↓
┌──────────────────┐
│  Request Success │
│  Continue flow   │
└──────────────────┘
```

### PDF Generation Error Flow

```
┌─────────────────────────────────────────┐
│  PDF Generation Starts                  │
└─────────────────┬───────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│  Try:                                   │
│    - Calculate scores                   │
│    - Generate report                    │
│    - Write PDF file                     │
└─────────────────┬───────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    Error│                 │ Success
         ↓                 ↓
┌──────────────────────┐  ┌─────────────────────┐
│  CATCH EXCEPTION     │  │  PDF GENERATED OK   │
│                      │  │                     │
│  1. Log error:       │  │  - Save file path   │
│     - Full traceback │  │  - Return report    │
│     - Context        │  │    data             │
│                      │  └─────────────────────┘
│  2. Do NOT raise     │            │
│     (non-blocking)   │            │
│                      │            ↓
│  3. Continue with    │  ┌─────────────────────┐
│     analysis         │  │  Include in         │
│     response         │  │  Response:          │
└──────┬───────────────┘  │  - viability_score  │
       │                  │  - viability_rating │
       ↓                  │  - viability_summary│
┌──────────────────────┐  │  - pdf_report=file  │
│  Return Response:    │  └─────────────────────┘
│  - viability_score   │
│  - viability_rating  │
│  - viability_summary │
│  - pdf_report=None   │
│  - All other data OK │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│  Frontend Receives Response              │
│                                          │
│  Check pdf_report field:                 │
│  - If null: Hide download button         │
│  - If present: Enable download           │
│                                          │
│  User still gets:                        │
│  - Full analysis data                    │
│  - Viability score                       │
│  - Indicators table                      │
└──────────────────────────────────────────┘
```

---

## Sequence Diagrams

### Complete Analysis Sequence

```
User    Browser    Flask     foot_traffic_analysis    Nominatim    Overpass    pdf_generator    FileSystem
 │         │          │                │                   │            │            │              │
 │ Click   │          │                │                   │            │            │              │
 │ Marker  │          │                │                   │            │            │              │
 ├────────→│          │                │                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │ Confirm? │                │                   │            │            │              │
 │         ├─────────→│                │                   │            │            │              │
 │   Yes   │          │                │                   │            │            │              │
 │←────────┤          │                │                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │ Test     │                │                   │            │            │              │
 │         │ Network  │                │                   │            │            │              │
 │         │──────────┼───────────────→│                   │            │            │              │
 │         │←─────────┼────────────────│                   │            │            │              │
 │         │   OK     │                │                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │ Get Loc  │                │                   │            │            │              │
 │         │ Name     │                │                   │            │            │              │
 │         │──────────┼────────────────┼──────────────────→│            │            │              │
 │         │          │                │    /reverse       │            │            │              │
 │         │←─────────┼────────────────┼───────────────────│            │            │              │
 │         │          │                │   Location name   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │ POST     │                │                   │            │            │              │
 │         │ /analyze │                │                   │            │            │              │
 │         │──────────→│                │                   │            │            │              │
 │         │          │ Parse          │                   │            │            │              │
 │         │          │ Store session  │                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │ Call extract_  │                   │            │            │              │
 │         │          │ osm_indicators │                   │            │            │              │
 │         │          │───────────────→│                   │            │            │              │
 │         │          │                │ Test endpoints    │            │            │              │
 │         │          │                │───────────────────┼───────────→│            │              │
 │         │          │                │←──────────────────┼────────────│            │              │
 │         │          │                │                   │  200 OK    │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │                │ Fetch POIs        │            │            │              │
 │         │          │                │───────────────────┼───────────→│            │              │
 │         │          │                │                   │ /interpreter│           │              │
 │         │          │                │                   │ (Overpass) │            │              │
 │         │          │                │←──────────────────┼────────────│            │              │
 │         │          │                │   GeoJSON data    │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │                │ Process POIs      │            │            │              │
 │         │          │                │ Extract places    │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │                │ Fetch network     │            │            │              │
 │         │          │                │───────────────────┼───────────→│            │              │
 │         │          │                │←──────────────────┼────────────│            │              │
 │         │          │                │   Network data    │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │                │ Count             │            │            │              │
 │         │          │                │ intersections     │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │←───────────────│                   │            │            │              │
 │         │          │ (df, analysis) │                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │ Get location   │                   │            │            │              │
 │         │          │ name           │                   │            │            │              │
 │         │          │───────────────→│                   │            │            │              │
 │         │          │←───────────────│                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │ Save JSON      │                   │            │            │              │
 │         │          │───────────────────────────────────────────────────────────────────────────→│
 │         │          │←───────────────────────────────────────────────────────────────────────────│
 │         │          │                │                   │            │            │              │
 │         │          │ Generate PDF   │                   │            │            │              │
 │         │          │───────────────────────────────────────────────→│            │              │
 │         │          │                │                   │            │ Calculate  │              │
 │         │          │                │                   │            │ scores     │              │
 │         │          │                │                   │            │            │              │
 │         │          │                │                   │            │ Build PDF  │              │
 │         │          │                │                   │            │            │              │
 │         │          │                │                   │            │ Write file │              │
 │         │          │                │                   │            │───────────────────────────→│
 │         │          │                │                   │            │←───────────────────────────│
 │         │          │←───────────────────────────────────────────────│            │              │
 │         │          │                │   report_data     │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │          │ Build response │                   │            │            │              │
 │         │          │ Convert to JSON│                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │←─────────│                │                   │            │            │              │
 │         │ 200 OK   │                │                   │            │            │              │
 │         │ {data}   │                │                   │            │            │              │
 │         │          │                │                   │            │            │              │
 │         │ Display  │                │                   │            │            │              │
 │         │ results  │                │                   │            │            │              │
 │←────────│          │                │                   │            │            │              │
 │ Results │          │                │                   │            │            │              │
```

---

**Last Updated:** 2025-11-19
**Version:** 1.0
