Release Checklist (Direct Code Sale)

1) Versioning
- Update `VERSION` with a semver tag (e.g., 1.0.1)
- Add a new entry to `changelog.md` describing changes

2) Compliance and Configuration
- Confirm `ATTRIBUTION.md` and `THIRD_PARTY_NOTICES.md` are present and accurate
- Confirm `EULA.md` is updated with your company/jurisdiction
- Set `NOMINATIM_EMAIL` in `.env` (or advise buyer to set theirs)

3) Packaging
- Clean local artifacts: `make clean` (optional)
- Create the package: `make package`
- Verify ZIP contents in `dist/` exclude `venv/`, caches, reports, and logs

4) Smoke Test (optional)
- Docker: `docker compose up --build` then open http://localhost:1010
- Python: `pip install -r requirements.txt && python3 app.py`
- Hit `/healthz` and run a quick analysis

5) Deliverables to Customer
- The ZIP from `dist/`
- A short email or README excerpt on setup (env vars, ports)
- Your support/updates policy and contact info

