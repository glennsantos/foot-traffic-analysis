# Foot Traffic Analysis Tool - Comprehensive Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [API Endpoints](#api-endpoints)
6. [Frontend Implementation](#frontend-implementation)
7. [Analysis Engine](#analysis-engine)
8. [PDF Report Generation](#pdf-report-generation)
9. [Configuration](#configuration)
10. [Deployment](#deployment)
11. [Error Handling & Resilience](#error-handling--resilience)
12. [File Structure](#file-structure)
13. [Development Guide](#development-guide)

---

## Overview

The Foot Traffic Analysis Tool is a web-based application that analyzes foot traffic potential for any location worldwide using OpenStreetMap (OSM) data. It provides:

- **Interactive map interface** for location selection
- **12 foot traffic indicators** with weighted scoring
- **Automated viability analysis** with clear ratings (Best, Outstanding, Excellent, Good, Moderate, Poor)
- **PDF report generation** with detailed recommendations
- **Resilient data fetching** with automatic endpoint failover

### Key Features

- Global location search via Nominatim geocoding
- Configurable analysis radius (100-2000 meters, default 300m)
- Real-time OSM data extraction via Overpass API
- Weighted scoring system based on business viability criteria
- Comprehensive PDF reports with place details
- Persistent storage of analysis results (JSON)
- Health check endpoint for monitoring
- Docker containerization for easy deployment

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   Web Browser   │
│   (Frontend)    │
└────────┬────────┘
         │ HTTP/AJAX
         ↓
┌─────────────────────────────────────────┐
│         Flask Application (app.py)       │
│  ┌──────────────────────────────────┐   │
│  │  Routes & Request Handling       │   │
│  └──────────────────────────────────┘   │
└────────┬──────────────────────┬──────────┘
         │                      │
         ↓                      ↓
┌────────────────────┐  ┌──────────────────┐
│ foot_traffic_      │  │ pdf_report_      │
│ analysis.py        │  │ generator.py     │
│ (OSM Analysis)     │  │ (PDF Reports)    │
└────────┬───────────┘  └──────────────────┘
         │
         ↓
┌────────────────────────────────────────┐
│     External APIs                      │
│  ┌────────────┐  ┌──────────────────┐ │
│  │ Nominatim  │  │ Overpass API     │ │
│  │ (Geocoding)│  │ (OSM Data)       │ │
│  └────────────┘  └──────────────────┘ │
└────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- Flask 3.0.3 - Web framework
- Flask-CORS 5.0.0 - Cross-origin resource sharing
- OSMnx 1.9.4 - OpenStreetMap network analysis
- Pandas 2.2.3 - Data manipulation
- GeoPandas 0.14.4 - Geospatial data handling
- Requests 2.32.3 - HTTP client
- ReportLab 4.2.5 - PDF generation
- Matplotlib 3.10.3 - Data visualization
- Gunicorn 22.0.0 - Production WSGI server

**Frontend:**
- Leaflet 1.9.4 - Interactive maps
- Vanilla JavaScript - UI interactions
- HTML5/CSS3 - Layout and styling

**Infrastructure:**
- Docker - Containerization
- Docker Compose - Multi-container orchestration

---

## Core Components

### 1. Flask Application (app.py)

The main application server handling HTTP requests and orchestrating the analysis workflow.

**Key Responsibilities:**
- Route handling (`/`, `/analyze`, `/download-report/<filename>`, `/api/last-search`, `/healthz`)
- Session management for last searches (IP-based)
- CORS configuration
- Error handling and logging
- Request/response formatting
- Integration between analysis and PDF generation

**Important Functions:**

- **`nominatim_headers()`** (app.py:42): Builds User-Agent headers for Nominatim API compliance
- **`get_location_name(lat, lon)`** (app.py:99): Reverse geocodes coordinates to human-readable location names
- **`analyze()`** (app.py:177): Main analysis endpoint that coordinates data extraction and report generation
- **`_to_json_safe(obj)`** (app.py:53): Converts numpy types to JSON-serializable primitives

### 2. OSM Analysis Engine (foot_traffic_analysis.py)

Extracts and processes OpenStreetMap data to calculate foot traffic indicators.

**Key Responsibilities:**
- Configure OSMnx with resilient settings
- Manage Overpass API endpoint failover
- Extract POI (Points of Interest) data
- Analyze street network topology
- Calculate 12 foot traffic indicators
- Retry logic with exponential backoff

**Important Functions:**

- **`extract_osm_foot_traffic_indicators(lat, lon, radius_m=300, max_retries=3)`** (foot_traffic_analysis.py:105): Main analysis function
- **`get_working_endpoint()`** (foot_traffic_analysis.py:86): Finds responsive Overpass API endpoint
- **`test_overpass_endpoint(endpoint)`** (foot_traffic_analysis.py:77): Tests endpoint availability
- **`collect_places(pois_df, key, values=None)`** (foot_traffic_analysis.py:263): Collects and formats place details
- **`get_detailed_place_info(row)`** (foot_traffic_analysis.py:199): Extracts detailed information including coordinates and addresses

**Indicators Collected:**

1. **Restaurants and Cafes** - Food establishments (restaurants, cafes, bars, food courts)
2. **Schools/Universities** - Educational institutions
3. **Hospitals/Clinics** - Healthcare facilities
4. **Markets** - Marketplaces
5. **Places of Worship** - Religious establishments
6. **Tourist Sites** - Tourist attractions and leisure facilities
7. **Shops** - Retail establishments
8. **Transport Hubs** - Bus stops and public transport
9. **Pedestrian Crossings** - Pedestrian infrastructure
10. **Intersection Count** - Road network density
11. **Office Buildings** - Commercial and office spaces
12. **Parking Lots** - Parking facilities

### 3. PDF Report Generator (pdf_report_generator.py)

Generates professional PDF viability reports with detailed analysis.

**Key Responsibilities:**
- Calculate weighted scores for each indicator
- Determine overall viability rating
- Generate executive summaries
- Create detailed tables of indicators and places
- Format PDF with ReportLab

**Important Classes & Methods:**

- **`LocationViabilityReportGenerator`** (pdf_report_generator.py:15): Main report generator class
- **`calculate_indicator_scores(analysis_data)`** (pdf_report_generator.py:69): Scores each indicator against thresholds
- **`calculate_overall_viability(scores)`** (pdf_report_generator.py:118): Computes overall viability percentage and rating
- **`generate_report(analysis_data, location_name, lat, lon, radius, output_path)`** (pdf_report_generator.py:252): Orchestrates PDF generation
- **`create_places_table(indicator_name, places_data)`** (pdf_report_generator.py:215): Creates detailed place listings with coordinates

**Scoring Criteria:**

Each indicator has:
- **Threshold**: Minimum count to meet criteria
- **Weight**: Contribution to overall score (0-1, sum = 1.0)
- **Description**: Business rationale

Example:
```python
'shops': {
    'threshold': 8,
    'weight': 0.17,  # 17% of total score
    'description': 'Retail establishments are primary foot traffic generators'
}
```

**Viability Ratings:**

- **BEST** (98%+): Ideal for premium retail and flagship stores
- **OUTSTANDING** (95-97%): Exceptional foot traffic potential
- **EXCELLENT** (85-94%): Highly suitable for foot traffic-dependent businesses
- **GOOD** (80-89%): Suitable for most commercial activities
- **MODERATE** (70-79%): Requires careful business planning
- **POOR** (<70%): Limited foot traffic potential

### 4. Frontend (templates/index.html)

Single-page application providing interactive map and results display.

**Key Features:**
- Leaflet map integration with OpenStreetMap tiles
- Location search via Nominatim API
- Adjustable radius control (100-2000m)
- Visual radius circle overlay
- Real-time analysis status
- Detailed results table with expandable place lists
- PDF download integration
- Last search restoration

**Important JavaScript Functions:**

- **`analyzeLocation(lat, lng)`** (index.html:597): Initiates analysis request
- **`displayResults(data)`** (index.html:855): Renders analysis results
- **`setupSearch()`** (index.html:409): Configures location search functionality
- **`getLocationName(lat, lng)`** (index.html:841): Fetches location name via reverse geocoding
- **`loadLastSearch()`** (index.html:351): Restores previous search from session

---

## Data Flow

### Analysis Request Flow

```
1. USER INTERACTION
   │
   ├─→ User clicks map or searches location
   │   └─→ Marker placed, radius circle displayed
   │
   └─→ User clicks marker to start analysis
       └─→ Confirmation dialog

2. FRONTEND (JavaScript)
   │
   ├─→ Collect coordinates and radius
   ├─→ Test network connectivity
   ├─→ Send POST /analyze request
   │   Body: { lat: float, lon: float, radius: int }
   └─→ Show loading state

3. BACKEND (app.py)
   │
   ├─→ Parse request data
   ├─→ Store search in session (IP-based)
   ├─→ Call extract_osm_foot_traffic_indicators()
   │
   └─→ ANALYSIS ENGINE (foot_traffic_analysis.py)
       │
       ├─→ Find working Overpass endpoint
       ├─→ Fetch POIs via OSMnx
       │   └─→ Retry logic with exponential backoff
       ├─→ Fetch street network
       ├─→ Process and categorize data
       └─→ Return DataFrame + detailed analysis

4. REPORT GENERATION (pdf_report_generator.py)
   │
   ├─→ Calculate indicator scores
   ├─→ Determine viability rating
   ├─→ Generate PDF with tables and recommendations
   └─→ Save to reports/ directory

5. RESPONSE PREPARATION
   │
   ├─→ Save JSON to analyses_new/
   ├─→ Convert numpy types to JSON-safe
   ├─→ Include viability score and PDF filename
   └─→ Return comprehensive response

6. FRONTEND DISPLAY
   │
   ├─→ Update location info
   ├─→ Display viability summary
   ├─→ Populate indicators table
   ├─→ Enable PDF download link
   └─→ Show save confirmation
```

### Data Storage

**Analyses (analyses_new/):**
- Format: JSON
- Naming: `analysis_YYYYMMDD_HHMMSS_<location>_<radius>m.json`
- Contents:
  ```json
  {
    "timestamp": "ISO-8601",
    "location_name": "string",
    "latitude": float,
    "longitude": float,
    "radius_meters": int,
    "analysis": {
      "indicator_name": {
        "count": int,
        "places": ["string"],
        "detailed_places": [
          {
            "name": "string",
            "latitude": float,
            "longitude": float,
            "address": "string"
          }
        ]
      }
    }
  }
  ```

**Reports (reports/):**
- Format: PDF
- Naming: `viability_report_YYYYMMDD_HHMMSS_<location>_<radius>m.pdf`
- Sections:
  - Executive Summary
  - Overall Viability Score
  - Detailed Indicator Analysis (ranked)
  - Places Tables (with coordinates and addresses)
  - Conclusion & Recommendations

**Cache (cache/):**
- OSMnx cache for faster repeated queries
- Managed automatically by OSMnx

---

## API Endpoints

### GET /

**Description:** Serves the main HTML interface

**Response:** HTML page with embedded Leaflet map

### POST /analyze

**Description:** Analyzes foot traffic for a location

**Request Body:**
```json
{
  "lat": 14.5995,
  "lon": 120.9842,
  "radius": 300
}
```

**Response (200 OK):**
```json
{
  "lat": 14.5995,
  "lon": 120.9842,
  "radius_meters": 300,
  "saved_file": "analyses_new/analysis_20231118_123456_Location_300m.json",
  "pdf_report": "viability_report_20231118_123456_Location_300m.pdf",
  "viability_score": 87.5,
  "viability_rating": "EXCELLENT",
  "viability_summary": "<HTML summary>",
  "restaurants_and_cafes": {
    "count": 12,
    "places": ["Cafe A", "Restaurant B"],
    "detailed_places": [...]
  },
  "shops": {...},
  "intersection_count": 25,
  ...
}
```

**Error Response (400):**
```json
{
  "error": "Error message"
}
```

### GET /download-report/<filename>

**Description:** Downloads a generated PDF report

**Parameters:**
- `filename` - Name of the PDF file

**Response:** PDF file download

**Security:** Prevents directory traversal attacks

### GET /api/last-search

**Description:** Retrieves the last search for the current user (IP-based)

**Response (200 OK):**
```json
{
  "success": true,
  "lat": 14.5995,
  "lon": 120.9842,
  "radius": 300
}
```

**Response (404):**
```json
{
  "success": false,
  "message": "No previous search found"
}
```

### GET /healthz

**Description:** Health check endpoint for monitoring

**Response (200 OK):**
```json
{
  "status": "ok",
  "last_search_count": 5,
  "time": "2023-11-18T12:34:56.789"
}
```

---

## Frontend Implementation

### Map Initialization

The application uses Leaflet.js for interactive mapping:

```javascript
const map = L.map('map').setView([14.5995, 120.9842], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);
```

### Location Selection

Three methods:
1. **Map Click** - Click anywhere on the map
2. **Search Box** - Type location name (uses Nominatim)
3. **Last Search** - Automatically restored on page load

### Search Functionality

- Debounced input (200ms delay)
- Minimum 3 characters
- Shows top 5 results
- Includes Nominatim email parameter if configured
- Click result to center map and place marker

### Analysis Workflow

1. User places marker (map click or search)
2. Radius circle displayed
3. Instruction shown: "Click marker to start analysis"
4. User clicks marker → confirmation dialog
5. Analysis initiated with loading state
6. Results displayed in table format
7. PDF download link enabled

### Error Handling

- Network connectivity testing before analysis
- Detailed error messages with suggestions
- Timeout detection for Overpass API
- Graceful degradation if PDF generation fails

---

## Analysis Engine

### OSMnx Configuration

**Resilience Settings:**
```python
ox.settings.requests_timeout = 300  # 5 minutes
ox.settings.max_query_area_size = 50_000
ox.settings.overpass_memory = 1024 * 1024 * 1024  # 1GB
ox.settings.use_cache = True
ox.settings.cache_folder = 'cache'
ox.settings.overpass_rate_limit = False  # Avoid status probes
```

### Endpoint Failover

The application tests Overpass API endpoints in order:

1. Check `OVERPASS_URL` environment variable (if set)
2. Test endpoints from `OVERPASS_ENDPOINTS` (or defaults)
3. Use first responsive endpoint
4. Retry with next endpoint on failure

**Default Endpoints:**
- `https://overpass.kumi.systems/api`
- `https://overpass-api.de/api`

### POI Tags

The application queries OpenStreetMap using the following tags:

```python
poi_tags = {
    "amenity": ["restaurant", "cafe", "fast_food", "bar", "food_court",
                "school", "university", "college", "hospital", "clinic",
                "place_of_worship", "marketplace", "parking"],
    "shop": True,  # All shop types
    "leisure": True,  # All leisure types
    "tourism": True,  # All tourism types
    "public_transport": True,
    "highway": ["bus_stop", "crossing"],
    "building": ["office", "commercial"],
    "office": True  # All office types
}
```

### Retry Logic

**Exponential Backoff:**
- Attempt 1: Immediate
- Attempt 2: Wait 5 seconds
- Attempt 3: Wait 10 seconds

**Endpoint Rotation:**
- Cycles through available endpoints on failure
- Each attempt uses a different endpoint
- Normalizes endpoint URLs for OSMnx v1/v2 compatibility

### Data Processing

**Place Name Resolution:**

Priority order:
1. `name` tag
2. `name:en` tag
3. `brand` tag
4. `operator` tag
5. Type tag (`shop`, `amenity`, etc.)
6. "Unnamed" fallback

**Address Formatting:**
- Extracts `addr:street`, `addr:housenumber`, `addr:city`
- Combines into readable format
- Includes in detailed place info

---

## PDF Report Generation

### Scoring System

**Base Score Calculation:**
```python
if count >= threshold:
    base_score = 100
else:
    base_score = (count / threshold) * 100

# Bonus for exceeding threshold significantly
if count > threshold * 2:
    base_score = min(120, base_score + 20)
```

**Weighted Score:**
```python
weighted_score = base_score * weight
```

**Overall Viability:**
```python
viability_percentage = (sum(weighted_scores) / sum(max_scores)) * 100
```

### Report Structure

1. **Title Page**
   - "FOOT TRAFFIC VIABILITY ANALYSIS"

2. **Executive Summary**
   - Location details (name, coordinates, radius)
   - Overall viability score and rating
   - Criteria met count
   - Key findings (strongest/weakest indicators)
   - Recommendations

3. **Overall Score Display**
   - Large, color-coded viability percentage

4. **Detailed Indicator Analysis**
   - Table of all 12 indicators (ranked by score)
   - Individual indicator sections with:
     - Score and status (meets/below threshold)
     - Count, threshold, and weight
     - Business rationale
     - Detailed places table (name, lat/lon, address)

5. **Conclusion & Recommendations**
   - Overall assessment
   - Specific recommendations based on rating
   - Top 3 strengths
   - Top 2 areas for improvement

6. **Footer**
   - Timestamp
   - Data attribution
   - Tool credits

### Styling

- **Colors:** Dark blue headers, color-coded ratings (green/blue/orange/red)
- **Fonts:** Helvetica family
- **Page Size:** A4
- **Tables:** Alternating row colors, bordered cells
- **Sections:** Clear hierarchy with spacers

---

## Configuration

### Environment Variables

**Required:**
None (all have defaults)

**Recommended:**
- **`NOMINATIM_EMAIL`** - Contact email for Nominatim API (improves reliability)
  - Used in User-Agent headers
  - Appended to search requests
  - Example: `you@example.com`

**Optional:**

- **`PORT`** - HTTP port (default: 1010)
- **`SECRET_KEY`** - Flask session secret (default: random, set in production)
- **`ALLOWED_ORIGINS`** - CORS allowed origins, comma-separated (default: `*`)
  - Production example: `https://example.com,https://app.example.com`
- **`OVERPASS_URL`** - Force specific Overpass endpoint
  - Accepts base: `https://overpass.kumi.systems/api`
  - Or full: `https://overpass.kumi.systems/api/interpreter`
- **`OVERPASS_ENDPOINTS`** - Comma-separated endpoint list
  - Example: `https://overpass.kumi.systems/api,https://overpass-api.de/api`
- **`GUNICORN_WORKERS`** - Number of Gunicorn workers (default: 2)
- **`GUNICORN_TIMEOUT`** - Gunicorn timeout in seconds (default: 300)

### Configuration Files

**.env.example:**
Template for environment variables. Copy to `.env` and customize.

**docker-compose.yml:**
- Maps environment variables
- Configures volumes for persistence
- Sets DNS servers (8.8.8.8, 8.8.4.4)
- User/group mapping for file permissions

**Dockerfile:**
- Installs system dependencies (GDAL, GCC)
- Configures matplotlib cache directory
- Creates analysis/report directories
- Sets up Gunicorn as production server

---

## Deployment

### Docker Deployment (Recommended)

**Quick Start:**

1. Copy environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set `NOMINATIM_EMAIL`

3. Build and run:
   ```bash
   docker compose up --build
   ```

4. Access at http://localhost:1010

**Production Considerations:**

- Set `SECRET_KEY` to a strong random value
- Restrict `ALLOWED_ORIGINS` to your domain(s)
- Configure reverse proxy (nginx) for HTTPS
- Adjust `GUNICORN_WORKERS` based on CPU cores
- Monitor logs and health endpoint
- Set up volume backups for analyses and reports

### Python Virtual Environment

**Setup:**

1. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export PORT=1010
   export SECRET_KEY=change-me
   export NOMINATIM_EMAIL=you@example.com
   export ALLOWED_ORIGINS=*
   ```

4. Run application:
   ```bash
   python3 app.py
   ```

**For production:**
```bash
gunicorn -w 2 -t 300 -b 0.0.0.0:1010 app:app
```

### Scaling Considerations

**Horizontal Scaling:**
- Use load balancer (nginx, HAProxy)
- Share cache/analyses/reports via network storage (NFS, S3)
- Configure session storage (Redis, Memcached) instead of in-memory

**Vertical Scaling:**
- Increase Gunicorn workers (typically 2-4 per CPU core)
- Increase timeout for slow networks
- Allocate more memory for large radius queries

**Caching:**
- OSMnx cache reduces Overpass API calls
- Consider CDN for static assets
- Cache Nominatim reverse geocoding results

---

## Error Handling & Resilience

### Network Resilience

**Overpass API:**
- Automatic endpoint testing before queries
- Retry logic with exponential backoff (3 attempts)
- Endpoint rotation on failure
- Graceful error messages with suggestions

**Nominatim API:**
- Timeout configuration (20 seconds)
- User-Agent compliance for better reliability
- Fallback to "unknown_location" on error

### Error Types and Handling

**Client Errors (400):**
- Invalid coordinates
- Missing parameters
- JSON parsing errors
- Returned with clear error messages

**Server Errors (500):**
- Logged with full traceback
- Generic message to client (security)
- JSON response for API consumers

**OSM Data Errors:**
- Network timeouts
- Rate limiting
- Invalid area size
- Connection refused
- All logged with context

**PDF Generation Errors:**
- Non-blocking (analysis continues without PDF)
- Error logged, user informed
- Viability data still returned

### Logging

**Log Levels:**
- INFO: Normal operations (requests, analysis stages)
- ERROR: Exceptions, failures

**Log Destinations:**
- Console (stdout)
- File (app.log)

**Log Format:**
```
%(asctime)s - %(levelname)s - %(message)s
```

**Key Log Points:**
- Application startup
- Each request (IP address)
- Analysis stages (OSM fetch, PDF generation)
- Errors with stack traces

---

## File Structure

```
foot-traffic-analysis/
├── app.py                      # Main Flask application
├── foot_traffic_analysis.py    # OSM data extraction & analysis
├── pdf_report_generator.py     # PDF report generation
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker orchestration
├── Makefile                    # Build automation
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── .dockerignore               # Docker ignore rules
├── VERSION                     # Version number
│
├── templates/
│   └── index.html              # Frontend HTML/JS/CSS
│
├── scripts/
│   └── package.py              # Packaging script
│
├── analyses_new/               # JSON analysis results (gitignored)
├── reports/                    # PDF reports (gitignored)
├── cache/                      # OSMnx cache (gitignored)
├── __pycache__/                # Python cache (gitignored)
│
├── README.md                   # User documentation
├── DOCUMENTATION.md            # This file (technical docs)
├── ATTRIBUTION.md              # OSM attribution
├── EULA.md                     # End-user license
├── THIRD_PARTY_NOTICES.md      # Third-party licenses
├── RELEASE_CHECKLIST.md        # Release process
├── changelog.md                # Change history
├── tasks.md                    # Development tasks
└── foot-traffic-indicators.md  # Indicator documentation
```

---

## Development Guide

### Setting Up Development Environment

1. Clone repository
2. Create virtual environment: `python3 -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`
6. Run: `python3 app.py`

### Code Organization

**Separation of Concerns:**
- **app.py**: HTTP layer, routing, session management
- **foot_traffic_analysis.py**: Data extraction, OSM integration
- **pdf_report_generator.py**: Report formatting, PDF creation
- **templates/index.html**: UI, user interactions

### Adding New Indicators

1. **Update POI tags** in `foot_traffic_analysis.py`:
   ```python
   poi_tags = {
       "new_category": ["tag1", "tag2"],
       ...
   }
   ```

2. **Collect places** in `extract_osm_foot_traffic_indicators()`:
   ```python
   new_indicator = collect_places(pois, "new_category", ["tag1", "tag2"])
   ```

3. **Add to analysis dict**:
   ```python
   analysis = {
       ...
       "new_indicator": new_indicator
   }
   ```

4. **Update scoring criteria** in `pdf_report_generator.py`:
   ```python
   self.criteria = {
       ...
       'new_indicator': {
           'threshold': 5,
           'weight': 0.05,
           'description': 'Why this matters'
       }
   }
   ```

5. **Add frontend description** in `index.html`:
   ```javascript
   const indicatorDescriptions = {
       ...
       'new_indicator': 'User-friendly description'
   };
   ```

6. **Update weights** to sum to 1.0 across all indicators

### Testing

**Manual Testing:**
1. Start application
2. Select various locations (urban, rural, coastal)
3. Try different radii
4. Verify indicator counts
5. Check PDF report accuracy
6. Test error scenarios (invalid coords, network issues)

**Endpoint Testing:**
```bash
# Health check
curl http://localhost:1010/healthz

# Analysis
curl -X POST http://localhost:1010/analyze \
  -H "Content-Type: application/json" \
  -d '{"lat": 14.5995, "lon": 120.9842, "radius": 300}'
```

### Packaging for Distribution

**Create ZIP package:**
```bash
make package
# or
python3 scripts/package.py
```

**Output:**
- `dist/foot-traffic-analysis_vX.X.X_YYYYMMDD_HHMMSS.zip`

**Excluded from package:**
- `.git*` files
- `__pycache__`, `*.pyc`
- `venv`, `.venv`
- `cache`, `analyses*`, `reports`, `dist`
- `app.log`
- IDE files (`.idea`, `.vscode`)

**Package contents:**
- Source code
- Configuration templates
- Docker files
- Documentation (README, EULA, ATTRIBUTION, THIRD_PARTY_NOTICES)

### Version Management

Edit `VERSION` file:
```bash
echo "1.0.0" > VERSION
```

Used by packaging script for filename.

### Logging Best Practices

- Log at INFO level for normal flow
- Log at ERROR level for exceptions
- Include context (coordinates, radius, stage)
- Use structured logging for parsing
- Don't log sensitive data

### Performance Optimization

**OSMnx Caching:**
- Enabled by default (`cache/` directory)
- Reuses network graphs and POI data
- Significantly speeds up repeated queries

**Gunicorn Workers:**
- Default: 2 workers
- Recommendation: 2-4 × CPU cores
- Sync worker class (blocking I/O for OSM requests)

**Timeout Tuning:**
- Default: 300 seconds (5 minutes)
- Increase for slow networks or large radii
- Consider async workers for higher concurrency

**Database Integration:**
- Current: In-memory session storage
- Production: Use Redis or database for sessions
- Enables horizontal scaling

---

## Troubleshooting

### Common Issues

**1. Slow or Failed Analyses**

**Symptoms:** Timeouts, connection errors, partial data

**Solutions:**
- Overpass API may be rate-limited or down
- Try again later (5-10 minutes)
- Reduce analysis radius
- Set `OVERPASS_URL` to a different endpoint
- Check OSMnx cache is writable

**2. Reverse Geocoding Errors**

**Symptoms:** "unknown_location" in results

**Solutions:**
- Set `NOMINATIM_EMAIL` in `.env`
- Check internet connectivity
- Nominatim may be rate-limiting (1 req/second)

**3. CORS Errors**

**Symptoms:** Browser console shows CORS policy errors

**Solutions:**
- In development: `ALLOWED_ORIGINS=*`
- In production: Set specific origins
  ```bash
  ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  ```

**4. Docker Permission Errors**

**Symptoms:** Can't write to `analyses_new/` or `reports/`

**Solutions:**
- Check directory permissions (should be 777 or writable by container user)
- Adjust `user:` in docker-compose.yml
- Use UID/GID environment variables

**5. Matplotlib Cache Errors**

**Symptoms:** Permission denied writing to matplotlib cache

**Solutions:**
- Set `MPLCONFIGDIR=/app/.matplotlib_cache` (already in Dockerfile)
- Ensure directory is writable
- Create `.matplotlib_cache` in project root

**6. OSMnx UnboundLocalError**

**Symptoms:** Error during Overpass status check

**Solutions:**
- Already mitigated: `ox.settings.overpass_rate_limit = False`
- Set `OVERPASS_URL` to bypass status probes
- Update OSMnx to latest version

**7. Doubled /interpreter Path**

**Symptoms:** Connection refused to `.../api/interpreter/interpreter`

**Solutions:**
- Already handled: Endpoint normalization in `_normalize_overpass_urls()`
- Ensure `OVERPASS_URL` is base form or full form (not mixed)

---

## API Integration Examples

### Python

```python
import requests

# Analyze location
response = requests.post('http://localhost:1010/analyze', json={
    'lat': 14.5995,
    'lon': 120.9842,
    'radius': 300
})

data = response.json()
print(f"Viability Score: {data['viability_score']}%")
print(f"Rating: {data['viability_rating']}")
print(f"Restaurants: {data['restaurants_and_cafes']['count']}")

# Download PDF
if data['pdf_report']:
    pdf_url = f"http://localhost:1010/download-report/{data['pdf_report']}"
    pdf_response = requests.get(pdf_url)
    with open('report.pdf', 'wb') as f:
        f.write(pdf_response.content)
```

### JavaScript

```javascript
// Analyze location
const response = await fetch('http://localhost:1010/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        lat: 14.5995,
        lon: 120.9842,
        radius: 300
    })
});

const data = await response.json();
console.log(`Viability: ${data.viability_score}% (${data.viability_rating})`);

// Download PDF
if (data.pdf_report) {
    window.location.href = `/download-report/${data.pdf_report}`;
}
```

### cURL

```bash
# Analyze location
curl -X POST http://localhost:1010/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 14.5995,
    "lon": 120.9842,
    "radius": 300
  }' | jq '.'

# Download PDF (extract filename from above)
curl -O http://localhost:1010/download-report/viability_report_20231118_123456_Location_300m.pdf
```

---

## Contributing

### Code Style

- Follow PEP 8 for Python
- Use meaningful variable names
- Comment complex logic
- Keep functions focused and small
- Use type hints where helpful

### Git Workflow

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Commit with descriptive messages
5. Push and create pull request

### Release Checklist

See `RELEASE_CHECKLIST.md` for detailed steps:
1. Update VERSION file
2. Update changelog.md
3. Test all features
4. Build Docker image
5. Create package (`make package`)
6. Tag release in Git
7. Update documentation

---

## License & Attribution

### Data Attribution

**OpenStreetMap:**
- All geographic data © OpenStreetMap contributors
- Licensed under Open Data Commons Open Database License (ODbL)
- See `ATTRIBUTION.md` for details

### Third-Party Software

See `THIRD_PARTY_NOTICES.md` for complete list:
- Flask - BSD License
- OSMnx - MIT License
- Leaflet - BSD License
- ReportLab - BSD License
- And others...

### End-User License

See `EULA.md` for terms of use when distributing this software commercially.

---

## Support & Resources

### Documentation Files

- **README.md** - Quick start and user guide
- **DOCUMENTATION.md** - This comprehensive technical documentation
- **foot-traffic-indicators.md** - Detailed indicator descriptions
- **changelog.md** - Version history
- **RELEASE_CHECKLIST.md** - Release process

### External Resources

- **OpenStreetMap Wiki:** https://wiki.openstreetmap.org/
- **OSMnx Documentation:** https://osmnx.readthedocs.io/
- **Overpass API:** https://wiki.openstreetmap.org/wiki/Overpass_API
- **Nominatim Usage Policy:** https://operations.osmfoundation.org/policies/nominatim/
- **Flask Documentation:** https://flask.palletsprojects.com/
- **Leaflet Tutorials:** https://leafletjs.com/examples.html

### Contact

For issues with the OpenStreetMap data or APIs, refer to their respective communities. For application-specific issues, check the project repository or contact the maintainer.

---

**Last Updated:** 2025-11-18
**Version:** Based on repository analysis
**Maintained By:** Project Team
