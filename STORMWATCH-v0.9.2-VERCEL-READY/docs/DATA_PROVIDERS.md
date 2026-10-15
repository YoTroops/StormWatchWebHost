# Provider verification and implementation matrix

Source evaluation: 14 October 2026. Source URLs were inspected against publicly available NOAA/NHC pages, but the build runtime cannot issue NOAA outbound HTTP requests due network/DNS restrictions; this limits end-to-end feed testing.

| Source | Official URL | Availability / timestamps | Status in this MVP |
|---|---|---|---|
| NHC active cyclone JSON | https://www.nhc.noaa.gov/CurrentStorms.json | Contains current active systems, advisory times, position, intensity and official product links; polled every 5 min locally | **Integrated.** Schema checked using public sample and tests; live network not accessible from build container |
| NHC forecast GIS | GIS KMZ URLs returned in `trackCone.kmzFile`, `forecastTrack.kmzFile` of current JSON | Advisory-valid forecast shapes; files may be unavailable during source churn | **Integrated basic KML/KMZ** via controlled fetch and GeoJSON geometry extraction, on demand. Not verified on an actual live storm KMZ in this environment |
| Atlantic HURDAT2 | https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2025-092326.txt | Updated Sep 23 2026; six-hourly best-track after post-analysis, 1851-2025 | **Integrated on-demand** parser, selected cyclone IDs; fetch not tested against NHC directly |
| East/Central Pacific HURDAT2 | https://www.nhc.noaa.gov/data/hurdat/hurdat2-nepac-1949-2025-092926.txt | Updated Sep 29 2026; 1949-2025 | **Integrated on-demand** parser for applicable selected storms; fetch not tested against NHC directly |
| NHC Milton official advisory archive | https://www.nhc.noaa.gov/archive/2024/al14/ | NHC official issued advisories 7-10 Oct 2024, non-regular sample times | **Bundled offline** 10 actual reported advisory snapshots, manually transcribed from official reports with row-level URLs |
| NHC USAF HDOB products | https://www.nhc.noaa.gov/text/URNT15-USAF.shtml | Public archive-like *most recently posted* bulletin; not an ADS-B feed | **Integrated conservative parser and new auto-status v0.5** plus 20-row fixture Sep 10 2026. Status is ARCHIVED when bulletin age exceeds 6 h; not ADS-B |
| NHC NOAA HDOB products | https://www.nhc.noaa.gov/text/URNT15-NOAA.shtml | Most recently posted bulletin, may be training or unrelated to active TC | **Limited endpoint**; current bulletin parser may not match all published HTML variations |
| GOES-19 satellite CONUS preview | https://www.star.nesdis.noaa.gov/GOES/conus.php?sat=G19 | Official CDN JPG links embed acquisition timestamp `YYYYDDDHHMM` UTC; feed intended for informational use | **Metadata and standalone image preview integrated** for GeoColor, IR B13 and WV B08. Upstream network not verified here; imagery is NOT georeferenced to globe |
| Weather radar (NOAA NWS/MRMS) | https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer | Public NWS time-enabled MRMS reflectivity, service window approximately four hours; image acquisition time not directly verified | **Integrated in v0.5.** NWS MRMS time-enabled image service: bounded PNG proxy, source window status, manually chosen recent time, georegistered overlay. Direct upstream PNG export not tested in container. |
| Numerical hurricane guidance (GFS, HAFS, ECMWF) | https://www.nhc.noaa.gov/modelsummary.shtml | Varies by provider and license | **Not integrated** |
| Public aircraft ADS-B | https://api.adsb.lol/docs | ODbL 1.0, public free API subject to provider limits; output observation time derived from provider `now - seen_pos` | **v0.6 implemented:** recent public sightings for verified NOAA registrations N42RF/N43RF/N49RF, and optional TEAL exact-callsign search. Outages and missing positions explicitly stated. Live provider unreachable in build environment; no mission verification. |

**Important:** NOAA products have distinct observation timestamps, issue timestamps, and fetch timestamps. The UI must not combine them as if equivalent.

## Source metadata and operational safety

- HTTP requests are restricted to approved `www.nhc.noaa.gov` HTTPS, exact NWS radar ImageServer metadata/export paths, the exact official `www.star.nesdis.noaa.gov/GOES/conus.php?sat=G19` metadata URL, and the fixed `api.adsb.lol` NOAA-registration query / strictly validated exact TEAL callsign paths. Browser images are restricted to expected `cdn.star.nesdis.noaa.gov` product paths. Redirects are not followed by the adapter.
- Background polling runs every 5 minutes by default; source-change events travel via WebSocket. Each HTTP adapter request has payload-size limits, timeouts and time-based caching. Provider failures are isolated to their feature; they do not crash the rest of the app.
- An *empty valid NHC active-storm array* is not the same as *NHC inaccessible*.
- An official advisory or GIS forecast is not a direct aircraft observation or verified best track.
- HURDAT2 historical intensity and position may differ from old contemporaneous advisories because it is post-analysis.
- Inspect each provider's dissemination policy and service terms before deploying for broader audiences.

## NHC original documentation

- Current-storm JSON and official product examples: https://www.nhc.noaa.gov/productexamples/
- NHC GIS index: https://www.nhc.noaa.gov/gis/
- NHC hurricane data archive: https://www.nhc.noaa.gov/data/
- HURDAT2 definition: https://www.nhc.noaa.gov/data/hurdat/hurdat2-format-nov2019.pdf
- HDOB bulletin description: https://www.nhc.noaa.gov/abouthdobs_2007.shtml
- HDOB format document: https://www.nhc.noaa.gov/pdf/HDOB-specification.pdf

- NOAA GOES-19 CONUS GeoColor and channels: https://www.star.nesdis.noaa.gov/GOES/conus.php?sat=G19
- NOAA GOES public disclaimer: satellite images on STAR are informational and may be delayed or unavailable.

## v0.5 official NWS radar service

- NWS weather radar service documentation: https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer
- NOAA NWS radar documentation: https://www.weather.gov/radarfaq/
- Official application: https://radar.weather.gov/
- `ImageServer?f=pjson` provides a `timeInfo.timeExtent` in milliseconds since epoch, UTC. Its boundaries represent the **available service window**, not a guaranteed imagery scan acquisition time; no such timestamp is represented as observed in STORMWATCH.
- `ImageServer/exportImage` requests an image of a fixed, allowlisted geographic region, limited image size and user-selectable time offset within the returned extent. Downloads are bounded and checked for PNG signature/dimensions.
- Ocean coverage is limited, and geographic projection has explicit distortions. Radar return/color intensity must not be interpreted as direct precipitation rate without scientific conversion.

## v0.6 aircraft documentation and licensing

- NOAA identifies its WP-3D aircraft as Kermit (`N42RF`) and Miss Piggy (`N43RF`): https://www.omao.noaa.gov/aircraft-operations/noaa-hurricane-hunters
- NOAA identifies Gulfstream IV-SP (`N49RF`): https://www.omao.noaa.gov/aircraft-operations/aircraft/gulfstream-iv-sp
- USAF 53rd WRS TEAL callsign reference: https://www.dvidshub.net/graphic/44487/air-force-reserve-hurricane-hunters-call-sign
- ADSB.lol public API: https://api.adsb.lol/docs and https://www.adsb.lol/docs/open-data/api/
- ADSB.lol data are licensed ODbL 1.0. Public API service can change, throttle or require contributor credentials in the future. This MVP polls no more frequently than five minutes by default. Contact ADSB.lol for production/public deployment and review ODbL obligations.
- **Not a verified real-time aircraft mission source.** Transponder coverage varies; no report does not mean no flight. Identity for NOAA aircraft comes from their known registration, but mission status is always unverified. Manually searched TEAL results are unverified candidates. No aircraft position is generated when the provider fails or data are too old.

## v0.8 official track and intensity objective forecast aids

- NHC public ATCF A-deck per active cyclone: `https://ftp.nhc.noaa.gov/atcf/aid_public/a{stormidlower}.dat.gz`. Read-only, no key; storm ID is validated on the server and must be listed in the NHC active-storm feed. NHC public directory: https://ftp.nhc.noaa.gov/atcf/aid_public/
- ATCF record reference: https://ftp.nhc.noaa.gov/atcf/docs/NRL_doc_ATCFdatabase.html
- NOAA/NHC current ATCF model summary and identifiers: https://www.nhc.noaa.gov/modelsummary.shtml
- NHC forecast models vs official advisory warning guidance: https://www.nhc.noaa.gov/verification/verify3.shtml
- ECMWF public IFS / AIFS forecasts: https://www.ecmwf.int/en/forecasts/datasets/open-data . Tropical cyclone track products use **BUFR**; v0.8 has not built a BUFR decoder and does not claim direct access.
- Google DeepMind experimental WeatherNext Cyclones: https://developers.google.com/weathernext/guides/weatherlab and https://deepmind.google.com/science/weatherlab . Real-time/experimental data carry distinct terms; current files are not scraped from the website.
- NASA/Google/unverified research runs are NOT represented as official NHC forecasts. HAFS physics models are not branded AI merely because their name includes HAFS.

### Scientific safeguards

- All aids plotted within a comparison use one **matching initialization UTC time** selected by the user. Values are valid forecast lead times (hours) and computed UTC valid times. No cross-cycle mixing.
- A model absent from the public A-deck remains unavailable, with no fake path or generated intensity series.
- Duplicated ATCF wind-radius records have their storm center merged by `(cycle, aid, lead_time)` instead of plotting duplicate dots.
- Gaps in model coverage, absent future positions, wind and pressure values remain unfilled. Displayed 'peak wind' means maximum of actually available forecast rows, not model's complete theoretical peak.
- Remote gz payloads bounded to 5 MB compressed / 32 MB decompressed, read via allowlisted HTTPS only, cached for 300 seconds.
