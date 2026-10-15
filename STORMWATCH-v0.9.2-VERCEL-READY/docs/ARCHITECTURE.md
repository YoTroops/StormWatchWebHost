# Architecture, data flows, and deferred engineering work

```text
BROWSER  ┌─────────────────────────────────────────────────────────┐
         │ CSS + JS + bundled vector continents                   │
         │ Canvas geographic globe / 2D map / timeline / inspector│
         └──────────────────┬──────────────────────────────────────┘
                            │ REST HTTPS/localhost + WS heartbeat
LOCAL    ┌──────────────────▼──────────────────────────────────────┐
SERVER   │ FastAPI /apps/api/stormwatch/main.py                    │
         │ NHC adapter / nhc.py — validated NHC HTTPS URLs         │
         │ HURDAT2 parser / hurdat.py — historical best tracks     │
         │ HDOB parser / recon.py — actual bulletin observation    │
         │ Scientific utilities / science.py — units, states, UTC  │
         │ Source caches in process / fixture data on disk        │
         └──────────────────┬──────────────────────────────────────┘
                            │ Outbound HTTPS if permitted
EXTERNAL NOAA/NHC CurrentStorms.json, GIS KMZ, HURDAT2, HDOB
```

## Trust zones

- Browser files are served from the same FastAPI origin; backend is the only actor fetching remote NOAA URLs.
- User CSV uploads require time/lat/lon and have row and byte limits, but are not persisted. They are inherently untrusted research data and must not be merged with official NOAA observations.
- Response quality classifications are attached to both the source and the record. `provider.fetch` returns an error instead of simulated data when no source exists.
- Only official NHC hosts pass the adapter's allowlist; raw user-provided URLs cannot trigger a remote GET.
- REST interface has explicit product meanings; history cannot be interpreted as forecast or live feed.

## Known next milestones

1. Migrate frontend to React/TypeScript/Vite and CesiumJS with a real ellipsoid/terrain, while preserving the offline globe fallback. Add frontend bundling/test pipeline.
2. Add production ingestion scheduler with PostGIS geometry, Redis TTLs, rate-limited worker queue, and a database schema for all source timestamps/quality.
3. Verify NHC GIS schema variations live; add forecast validity and watches/warnings, wind radii and official advisory points.
4. Integrate current HDOB/VDM/dropsonde parsing with a documented observational schema and flight-level wind treatment.
5. Add correctly georeferenced NOAA satellite/radar tiles with precise frame times and authorized service usage; provide per-layer data provenance.
6. Add HAFS/GFS and other licensed model guidance with matched cycle/init/valid times, verification charts, official vs guidance separation.
7. Add UAS NetCDF parser, calibration metadata, scientifically justified thermodynamic diagnostics, proper uncertainty propagation.
8. Add browser-server E2E, performance benchmarks, resilience/load testing, accessibility audit and secure authentication if deployment becomes multi-user.

## Security / implementation caveats

This MVP has no user authentication and does not implement global rate limiting or persistent storage. It is intended for a single trusted local user, bound to loopback by its Windows launch script. Do not expose to the public internet without a deployment security review.


## v0.4 live source refresh and NOAA GOES preview

FastAPI lifespan schedules `_background_poll` every five minutes (configured with `STORMWATCH_POLL_SECONDS`). Each source independently attempts a bounded, allowlisted HTTPS refresh through `Provider`; results update source health. Changes in NHC storm positions/advisory times or GOES image times publish `source_update` events through per-client bounded WebSocket queues. Browser also refreshes every five minutes and when the tab returns to the foreground. The WS heartbeat is not weather data.

`/api/satellite/latest?channel=GEOCOLOR|IR|WATER_VAPOR` reads the official NOAA NESDIS STAR GOES-19 CONUS page, selects an allowed 1250×750 JPG link from the requested channel and decodes its acquisition time from the NOAA-published image filename. The browser loads the official CDN image separately. This is deliberately **not** a georeferenced globe overlay; lack of acquisition time or provider failure gives an unavailable response rather than invented imagery.

## v0.5 radar pipeline

`radar.py` consumes NWS MRMS `ImageServer` metadata and validates time extent/regions. An allowlisted, bounded `exportImage` HTTPS request fetches `png32` images georeferenced in EPSG:4326; `/api/radar/image` verifies PNG header and dimensions and never passes a browser-supplied upstream URL. Canvas draws a piecewise affine geographic mesh through the same globe/flat projection used for markers. Browser cache and source health are independent from NHC and satellite adapters. Periodic WebSocket events indicate metadata changes only, not actual rainfall changes. The recon status uses timestamp-age quality classification and is never labeled ADS-B.
