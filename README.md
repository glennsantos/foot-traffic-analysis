# Foot Traffic Analysis Tool

Web app for analyzing foot traffic indicators around any point using OpenStreetMap (OSM) data, with automatic PDF viability reports.

## Default Run (Docker)

1) Copy env and set your contact email (recommended for Nominatim reliability):
   ```bash
   cp .env.example .env
   # edit .env and set NOMINATIM_EMAIL=you@example.com
   ```
2) Start the app:
   ```bash
   docker compose up --build
   ```
3) Open http://localhost:1010

## Features

- Interactive map and global search (Leaflet + Nominatim)
- 12 indicators with weighted scoring and clear viability rating
- Detailed PDF report with executive summary and places tables
- Resilient Overpass endpoint selection and OSMnx caching
- JSON persistence, logging, and a health check endpoint

## Quickstart

Docker (recommended):

1) Copy `.env.example` to `.env` and edit as needed (set `NOMINATIM_EMAIL` for better reliability)

2) Build and run:
   ```bash
   docker compose up --build
   ```

3) Open http://localhost:1010

Python environment:

1) Install deps
   ```bash
   pip install -r requirements.txt
   ```

2) Set env (optional)
   ```bash
   export PORT=1010
   export SECRET_KEY=change-me
   export NOMINATIM_EMAIL=you@example.com
   export ALLOWED_ORIGINS=*
   ```

3) Run
   ```bash
   python3 app.py
   ```

4) Open http://localhost:1010

## Configuration

- `PORT`: HTTP port (default `1010`)
- `SECRET_KEY`: Flask secret key (set in production)
- `ALLOWED_ORIGINS`: CORS origins, comma-separated (default `*` for dev)
- `NOMINATIM_EMAIL`: Contact email included in User-Agent for Nominatim requests (recommended)
  - Reverse geocoding includes it in headers; the search box appends it as a query parameter if set.
- `OVERPASS_URL`: Force a specific Overpass endpoint. Accepts either base (`https://.../api`) or full (`https://.../api/interpreter`) — the app normalizes per OSMnx version.
- `OVERPASS_ENDPOINTS`: Comma-separated list of endpoints to try (left-to-right). Accepts base or full forms; defaults are `https://overpass.kumi.systems/api,https://overpass-api.de/api`.

## Using the App

- Click on the map or use the search box to select a location
- Adjust radius (100–2000 m; default 300 m)
- Click the marker to start analysis (1–5 minutes typical)
- View indicators, viability summary, and download the PDF report

## Viability Ratings

- Best (98%+): Ideal for premium retail and flagship stores
- Outstanding (95–97%): Exceptional foot traffic potential
- Excellent (85–94%): Highly suitable for foot traffic-dependent businesses
- Good (80–89%): Suitable for most commercial activities
- Moderate (70–79%): Requires careful business planning
- Poor (<70%): Limited foot traffic potential

## Packaging To Sell the Code

- Include `EULA.md` (update with your company/jurisdiction).
- Include `ATTRIBUTION.md` and `THIRD_PARTY_NOTICES.md` with deliveries.
- Distribute source or a Docker image; Dockerfile runs Gunicorn in production.
- Remove any local `venv/` and cached artifacts before packaging the repo.

### Create a ZIP package

- Using Makefile:
  ```bash
  make package
  # output in dist/foot-traffic-analysis_YYYYMMDD_HHMMSS.zip
  ```
- Or run directly:
  ```bash
  python3 scripts/package.py
  ```

## Attribution

- Data © OpenStreetMap contributors. See `ATTRIBUTION.md`.
- This tool uses OSMnx, Overpass API, Flask, and ReportLab.

## Troubleshooting

- Slow or failed analyses: Overpass can be rate-limited. Try again later or reduce radius. Caching is enabled (`cache/`).
- Reverse geocoding: Set `NOMINATIM_EMAIL` to comply with usage policy.
- CORS: Restrict `ALLOWED_ORIGINS` in production.
 - Gunicorn worker timeout or OSMnx `UnboundLocalError` during Overpass status check: the app disables OSMnx's `overpass_rate_limit` to avoid status probes that can fail under strict networks. You can also set `OVERPASS_URL` to a reachable mirror.
 - Connection refused to `.../api/interpreter/interpreter`: this indicates a doubled `interpreter` path. The app now normalizes endpoints for OSMnx v1/v2; ensure your `OVERPASS_URL`/`OVERPASS_ENDPOINTS` are either base (`.../api`) or full (`.../api/interpreter`).
- Matplotlib cache permission errors inside Docker: the image sets `MPLCONFIGDIR=/app/.matplotlib_cache` and creates the directory with write perms.
