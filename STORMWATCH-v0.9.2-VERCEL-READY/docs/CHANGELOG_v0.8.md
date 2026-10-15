# STORMWATCH v0.8 — Objective forecast model guidance

Release date: 2026-10-14

## Implemented

- New NHC public ATCF A-deck HTTPS adapter with allowlisted FTP.NHC.NOAA.GOV URL pattern, 5-minute TTL and bounded gzip decompression.
- Same-cycle forecast-aid parser, strict ATCF latitude/longitude and time handling, 3-hour lead limits, storm basin/number filtering, duplicated wind radii de-duplication.
- LIVE storm-only `/api/models/{storm_id}` REST endpoint with optional `cycle`, explicit absent/unavailable entries and provider/source metadata.
- Model registries and availability for NHC official, HAFS-A/B, GFS, ECMWF IFS, Google DeepMind WeatherNext Cyclones, Google GenCast, NOAA AI-GFS and AI-GEFS, ECMWF AIFS. HAFS-AI stays unsupported pending verification.
- Selectable forecast tracks on the rotating globe and overhead map, 24h markers, click-to-inspect valid time/intensity, intensity/pressure chart and scientific CSV export.
- LIVE-to-ARCHIVE transition hides model panel and chart, maintaining prior v0.6 archive behavior.
- No user-provided model run is silently passed off as operational NHC guidance.

## Known limitations

- Live NHC/ATCF/ECMWF/Google host network requests not tested in this container (outbound DNS blocked).
- Google experimental and ECMWF forecast records only appear when NHC public A-deck actually includes them for the selected run. Direct Google Weather Lab downloads and ECMWF BUFR parsing have not yet been built.
- “HAFS-AI” is a requested label with no verified distinct authoritative public source, NOT an alias for HAFS-A.
- Existing globe remains orthographic canvas; Cesium 3D globe is future work.
- Forecast-aid positions are forecasts, not NHC observations or advisory issue times.
- Build's Chromium mock images are not actual current weather.

## Tests

- `PYTHONPATH=apps/api STORMWATCH_BACKGROUND_POLL=0 python -m pytest -q`: **93 passed**.
- `node --check apps/web/dist/app.js`: passed.
- `python scripts/ui_smoke_v08.py`: passed in isolated Chromium with source-shaped model fixtures and mock imagery, zero JS page errors; archive controls hidden.
