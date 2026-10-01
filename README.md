# Retail Location Viability Analyzer

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
- PDF report generated on download, with executive summary and places tables
- Completed-analysis caching shared across local workers, with optional Redis for multiple hosts
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
- `SECRET_KEY`: Flask secret key. Set the same strong secret on every worker/instance so signed report downloads work across requests and deployments.
  - Local workers share an automatically generated key in `cache/report-secret` when unset. Vercel and deployments across hosts require an explicit shared key.
- `ALLOWED_ORIGINS`: CORS origins, comma-separated (default `*` for dev)
- `NOMINATIM_EMAIL`: Contact email included in User-Agent for Nominatim requests (recommended)
  - Reverse geocoding includes it in headers; the search box appends it as a query parameter if set.
- `OVERPASS_URL`: Force a reachable Overpass endpoint. Accepts either base (`https://.../api`) or full (`https://.../api/interpreter`); the app normalizes it for OSMnx 1.9.4.
- `OVERPASS_ENDPOINTS`: Comma-separated list of endpoints to try (left-to-right). Accepts base or full forms; defaults are `https://overpass.private.coffee/api,https://overpass-api.de/api,https://maps.mail.ru/osm/tools/overpass/api`.
- The analyzer uses a 180-second deadline for Overpass work and returns `503` with `code: "analysis_timeout"` when it is reached. Failed POI or street network fetches return `503` with `code: "analysis_upstream_unavailable"`. Vercel function logs record elapsed time for POI, street network, geocoding, and PDF stages.
- `GOOGLE_MAPS_API_KEY`: One supported credential for `POST /api/places-insights`. Enable billing and the Places Aggregate API in the Google Cloud project that owns this key. Google's current API reference documents the `cloud-platform` OAuth scope; `GOOGLE_PLACES_INSIGHTS_ACCESS_TOKEN` can be used instead for OAuth/service-account authentication.
- `PLACES_INSIGHTS_CACHE_TTL_SECONDS`: In-memory Google-count cache duration, default `900`. This lowers repeated-call latency and billable requests; it is per-process and should not be treated as a distributed cache.
- `PLACES_INSIGHTS_CACHE_MAX_ENTRIES`: Maximum cached count queries per process, default `512`; oldest entries are evicted when full.
- `ANALYSIS_CACHE_TTL_SECONDS`: Completed OSM result freshness, default `3600`. Cache entries use exact coordinates, radius, and analysis version. Only successful extraction is cached.
- `ANALYSIS_CACHE_PATH`: SQLite cache path, default `cache/analyses.sqlite3` locally or `/tmp/cache/analyses.sqlite3` on Vercel. Workers on the same host share it.
- `ANALYSIS_CACHE_MAX_ENTRIES`: SQLite entry limit, default `512`. For Redis, configure memory limits and eviction on the Redis service.
- `REDIS_URL`: Optional Redis connection URL for completed results shared across hosts and serverless instances. Cache outages fall back to live analysis. Use `rediss://` for TLS.
- `REPORT_TOKEN_TTL_SECONDS`: Signed report snapshot lifetime, default `86400`. Expired snapshots require another analysis.

## Vercel deployment

Production URL: https://retailanalyzer.glennsantos.com

The repository includes `vercel.json` for the Flask function. The map and OpenStreetMap analysis use the existing `/analyze` route; they do not require a Google key. The separate `/api/places-insights` route requires `GOOGLE_MAPS_API_KEY` or `GOOGLE_PLACES_INSIGHTS_ACCESS_TOKEN` if you choose to use it.

On Vercel, `/analyze` writes temporary results and local cache files to `/tmp`. Set `REDIS_URL` for caching across instances. Analysis returns a signed, compressed report snapshot instead of generating a PDF. The browser posts it to `/api/report` when Download PDF is clicked. That endpoint builds the PDF in memory, so downloading does not depend on the original instance or saved JSON file. All instances must have the same `SECRET_KEY`. Saved JSON results and the last-search history are not durable across instances.

The OpenStreetMap analysis depends on public Overpass servers. If those servers are unreachable from Vercel, `/analyze` cannot produce a report. For reliable production analysis, run the Flask worker with an Overpass endpoint that is reachable from its host, or use a dedicated Overpass instance.

An uncached analysis remains synchronous and can still fail during an Overpass outage. PDF generation happens in a separate download request. Sustained analyses that need more than Vercel's function duration require a durable job queue and persistent result storage.

`POST /analyze` accepts optional `location_name` from address search, avoiding a second geocoding request, and `refresh: true` to bypass the completed-result cache. Refresh recomputes the analysis but may reuse OSMnx's existing download cache. Responses include `cache.hit`, `cache.analyzed_at`, and `cache.ttl_seconds`. The UI identifies cached analyses. The legacy `/download-report/<filename>` route still serves previously saved PDFs; new downloads use `/api/report` with `report_token` from the analysis response.

## Places Insights site-screening API

`POST /api/places-insights` returns live Google aggregate place counts for franchise site screening without pretending that POI counts are measured pedestrian traffic. The legacy `/analyze` endpoint remains unchanged.

```json
{
  "location": {"latitude": 14.5995, "longitude": 120.9842},
  "radius_meters": 500,
  "place_type": "restaurant"
}
```

It accepts legacy `lat`/`lon` and `radius` aliases. Radius is 40–50,000 m. `place_type` is deliberately limited to this verified franchise-oriented set: `bakery`, `bar`, `cafe`, `car_wash`, `clothing_store`, `convenience_store`, `dentist`, `drugstore`, `gas_station`, `grocery_store`, `gym`, `hair_salon`, `hotel`, `laundry`, `pharmacy`, `pet_store`, `restaurant`, `shopping_mall`, `spa`, and `supermarket`; `coffee_shop`, `fast_food`, `fitness_center`, `quick_service_restaurant`, and `qsr` are mapped to their supported equivalents.

The response contains separate, non-additive counts for demand generators, direct competitors (Google primary type only), and supporting categories that exclude the selected competitor type. It deliberately has no automated GO/NO-GO recommendation. It includes caveats and concrete evidence to collect before a site decision. `radius_meters` must be an integer; decimal values are rejected rather than rounded.

Live data failures are structured and truthful: missing credentials return `503` with `error.code: "places_insights_not_configured"`, rejected credentials/requests return non-retryable `502` errors, and only network/rate-limit/5xx failures are retryable `503` responses with `retry_after_seconds`. The endpoint accepts either `GOOGLE_MAPS_API_KEY`, `GOOGLE_PLACES_INSIGHTS_ACCESS_TOKEN`, or both; the API never substitutes demo data for a live result.

## Using the App

- Click on the map or use the search box to select a location
- Adjust radius (100–2000 m; default 300 m)
- Select Analyze location to start. Elapsed time and site-visit prompts appear while the service works.
- Review the indicator counts and expandable places lists, then download the matching PDF report. The score is a screening model, not a measured pedestrian count.

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
