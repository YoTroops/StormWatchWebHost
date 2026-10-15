# Test report — 2026-10-14

**Executed locally in the STORMWATCH build container.**

## Python automated checks

Command: `cd stormwatch && pytest -q --disable-warnings`

Result: `71 passed in the final 0.5 validation run` (final run; test counts include parameterized cases).

Covered: NOAA GOES-19 official CDN filename UTC extraction, channel validation, stale image age, unavailable responses, scheduled source-change notifications, along with hurricane categories, meteorological conversions, hemispheric and invalid coordinates, longitude wrapping, UTC offsets, delayed/stale quality boundaries, HURDAT2 mixed storm/record formatting and missing values, verified Milton fixture, HDOB coordinate/mission parsing and invalid inputs, KMZ/KML cone/track geometries, restricted source hostname, active JSON storm schema and motion-speed units, FastAPI health/HTML/fixture routes, CSV upload validity and invalid coordinates.

## HTTP smoke check

Started: `PYTHONPATH=apps/api uvicorn stormwatch.main:app --host 127.0.0.1 --port 8000`

Observed over HTTP with curl:

- `GET /api/storms/historical`: **1 embedded archived storm** (Milton) before network sync.
- `GET /api/storms/historical/AL142024`: **10 archived NHC advisory observations**, derived knots populated.
- `GET /api/recon/fixture`: **20 dated HDOB rows**.
- `GET /api/health`: **200 OK**, UTC timestamp and per-provider health.

## Frontend browser check

Chromium launched via Playwright, with the HTML/CSS/JavaScript loaded inline and HTTP requests mocked with the same fixture schema. The local-HTTP browser-navigation policy in the build environment caused `net::ERR_BLOCKED_BY_ADMINISTRATOR`, so **a true browser-to-FastAPI E2E was not executable**. The isolated client check is useful but does not replace real network integration testing.

Observed in the new isolated Chromium 0.5 check (all external feeds mocked, local HTTP browser navigation remained blocked):

- Inline stylesheet applied as a CSS grid; LIVE cyclone appears; GOES satellite preview and enlarge action work.
- Archive replay and 2D view switching function; zero JavaScript page errors.

Original isolated Chromium baseline:

- Initial historical storm list shows Milton; map title and UTC selected timestamp render correctly.
- Forward action changes the displayed timestamp.
- Recon button opens an inspector with actual-style HDOB positions.
- 2D map toggle changes the active view control.
- **0 JavaScript page errors** captured in this isolated run.

The screenshot `docs/stormwatch_browser_mock.png` uses an HTTP-mocked test response and should not be described as a live NOAA feed or as a real browser/server integration test.

## Environment limitations

- Package registry / NOAA network DNS unavailable to the container. The live NHC and full HURDAT downloads could not be integration-tested against their real upstream servers here.
- No Docker binary available; Compose config was written but not exercised.
- No Windows machine available; BAT script and user instructions were inspected, but Windows deployment was not executed.
- No production runtime/graphics performance FPS benchmark has been run.

## v0.4 test baseline

`PYTHONPATH=apps/api pytest -q` — **71 passed**. `node --check apps/web/dist/app.js` — **passed**. `python scripts/ui_smoke_live.py` — **passed** isolated Chromium UI with mocked NOAA responses. NOAA/NESDIS live CDN and Windows runtime cannot be verified from this environment.

## v0.5 implementation verification

- `PYTHONPATH=apps/api pytest -q`: **71 passed**, including bounded NWS MRMS ImageServer URLs, valid JSON service time extents, requested UTC offsets, region and offset allowlists, PNG signature validation, nonexistent/failed source states, recon age and bulletin parser, and radar FastAPI routes using fixed mocked response bytes.
- `node --check apps/web/dist/app.js`: **passed**.
- `PYTHONPATH=apps/api python scripts/ui_smoke_live.py`: **passed** in isolated Chromium with mocked official-shaped data and clearly synthetic **UI-only radar raster**; verified region selection, time requests, opacity slider, LIVE/ARCHIVE transition, GOES display, 2D map, and no page errors.
- Screenshot: `docs/stormwatch_v05_browser_mock.png`; it is **not a live weather screenshot**.
- End-to-end direct NWS radar export, NOAA realtime flights, Docker startup and deployment on user Windows remain unverified by the build container.

## v0.6 verification (performed in build environment)

- `PYTHONPATH=apps/api STORMWATCH_BACKGROUND_POLL=0 python -m pytest -q` — **81 passed**. New tests cover timestamp derivation from ADS-B `now` and `seen_pos`, known NOAA aircraft registration allowlist, stale/invalid/missing geospatial coordinates, missing positions, invalid provider timestamps, telemetry sanity, masked/unverified TEAL callsigns, bounded provider URL allowlist, explicit outage behavior, and new aircraft API routes.
- `node --check apps/web/dist/app.js` — **passed**.
- `python scripts/ui_smoke_v06.py` — **passed** in **isolated Chromium with mocked public ADS-B and NOAA data**: LIVE panels visible, archive mode hides satellite/radar/aircraft controls and the LIVE HDOB button, Milton replay/step works, LIVE restores panels, aircraft detail inspector works, 2D selection works, and zero JavaScript exceptions. See `docs/stormwatch_v06_live_mock.png` and `docs/stormwatch_v06_archive_mock.png`. Screenshots use **mock responses**, not real aircraft positions.
- Local Uvicorn startup and HTTP smoke tested: `/`, `/api/health`, `/api/storms/historical`, `/api/storms/historical/AL142024` all returned HTTP 200.
- **Not verified:** live ADSB.lol upstream access, live NOAA sources, Windows-specific execution, Docker startup, full browser-to-FastAPI E2E under unrestricted networking.

## v0.7 verification (performed in build environment)

- `PYTHONPATH=apps/api STORMWATCH_BACKGROUND_POLL=0 pytest -q`: **86 passed**. Adds tests for NOAA nowCOAST metadata layer selection by advertised name, validation of map channel and fixed regions, georeferenced image URL generation, PNG safeguards, explicit unavailable handling, and endpoint failure behavior.
- `node --check apps/web/dist/app.js`: **passed**.
- `python scripts/ui_smoke_v07.py`: **passed**, isolated Chromium. Uses explicitly mock image tiles and projected-image response to verify: viewport tile requests, source attribution, map detail toggle, 2D selection, satellite-on-map controls and successful mock image load, ARCHIVE hiding live satellite/radar/aircraft controls, replay step, return to LIVE, and **zero JavaScript page errors**.
- No live OpenStreetMap or NOAA nowCOAST network call was possible from the test environment; source requests must be confirmed on user's Windows browser. No claim of NOAA map image acquisition times or production-grade map performance.

## v0.8 verification (performed in build environment)

- `PYTHONPATH=apps/api STORMWATCH_BACKGROUND_POLL=0 python -m pytest -q` **93 passed**. New tests validate ATCF basin/storm filtering, coordinate signs and bounds, duplicate wind radii, same-cycle comparison, Google and Euro aid recognition, missing HAFS-AI, gzip size/type validation, API successful parsing from a mocked gzip file, invalid cycles, inactive storms and offline errors.
- `node --check apps/web/dist/app.js` **passed**.
- `python scripts/ui_smoke_v08.py` **passed** in isolated Chromium using explicitly synthetic UI-only model tracks: active storm click, forecast cycle selection rendering, chart metric switch, source-model toggles, unavailable HAFS-AI status, mode switching, archive controls all hidden and historical replay working, with **0 JavaScript page errors**. Screenshots in `docs/stormwatch_v08_models_mock.png`, `docs/stormwatch_v08_live_mock.png`, `docs/stormwatch_v08_archive_mock.png`.
- Live NHC upstream gzip HTTP retrieval **not verified** from this environment (external DNS inaccessible), therefore production feed availability must be verified on Windows. Isolated interface mock is not a real hurricane forecast or real Google/ECMWF output.

## v0.9 verification (performed in build environment)

- `python -m pytest -q`: **96 passed**, covering prior parsers/API validations plus unique HTML control IDs, five workspace/link targets, live/archive tab classes, embedded satellite-size styles, and preservation of core controls.
- `node --check apps/web/dist/app.js`: **passed**.
- `python scripts/ui_smoke_v09.py`: **passed** in isolated Chromium with **mocked** NOAA, ATCF, NWS and OSM sources. The browser loaded a mocked native-size **1250 × 750** GOES image and verified it displayed within a sidebar frame **no taller than 200 px**; verified the enlarged image stayed within the viewport; all five workspaces opened; model/chart controls, radar disclosure and reconnaissance actions remained usable; archive mode hid live satellite/radar/model/aircraft controls while preserving replay; live mode restored tabs; tab arrow-key navigation worked; and **0 browser page errors** were recorded. Rechecked GOES image containment at 1280 px viewport.
- Screenshots `docs/stormwatch_v09_live_ui_mock.png`, `docs/stormwatch_v09_weather_ui_mock.png`, `docs/stormwatch_v09_models_ui_mock.png` and `docs/stormwatch_v09_archive_ui_mock.png` show **mock data, NOT live weather or actual forecast output**.
- **Not tested:** upstream NOAA/ADS-B CDN access from this environment, unrestricted browser-to-FastAPI network integration, Windows-specific launch, Docker, and operational map performance.


## v0.9.1 verification (performed in build environment)

- `PYTHONPATH=apps/api STORMWATCH_BACKGROUND_POLL=0 python -m pytest -q`: **100 passed**, including version coherence, popup markup/ARIA, local bundled changelog metadata, and embedded/external CSS parity.
- `node --check apps/web/dist/app.js` and `node --check apps/web/dist/release-notes.js`: **passed**.
- `python scripts/ui_smoke_v091.py`: **passed** in isolated Chromium with mocked data and an in-memory localStorage shim (the test environment restricts local HTTP browser navigation). Verified that first open shows the popup, older notes expand, dismissal remembers the new version, the header button reopens it, Escape closes and restores keyboard focus, a different stored version triggers the popup again, archive/live workspaces still toggle, and the dialog fits a narrow viewport. **0 JavaScript page errors**.
- Screenshot `docs/stormwatch_v091_welcome_mock.png` is a **mock-backed interface test**, not a live NOAA screenshot.
- Browser-to-server HTTP E2E and Windows-specific runtime **remain unverified** in this container. Version and release notes require no external API or network access.

## v0.9.2 geographic radar hotfix — 2026-10-14

- Verified by inspection against Esri `exportImage` documentation that `adjustAspectRatio` defaults true and may alter requested bounding boxes. The old fixed 720x480 exports could therefore be mislocated when drawn against different requested region bounds.
- Request now explicitly pins `adjustAspectRatio=false` and region-matched pixel dimensions; source EPSG:4326 coordinates and 2D/3D mesh logic remain shared.
- Radar is hidden if metadata quality is `STALE` (more than 30 minutes since latest NWS service-window end). UI explains that reflectivity echoes do not establish rain at the surface.
- 106 tests passed locally, including new regression tests for every region's `bbox`, `size`, `imageSR`, `bboxSR`, and export flags; API headers assert geographic metadata.
- Mocked Chromium browser radar smoke passed: stale feed skips image; available source renders mock image; archival mode hides radar; page errors 0. Additional release-dialog browser smoke passed.
- Verified only through a mocked browser and server tests: live NOAA radar download and pixel alignment against actual observed weather on the user's Windows device remain unverified.
