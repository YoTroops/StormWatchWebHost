# STORMWATCH v0.9.2 — Radar alignment fix

2026-10-14

## Correctness fix

- NWS/MRMS ImageServer export requests explicitly use `adjustAspectRatio=false`.
- The PNG pixel dimensions now match each region's geographic bounding-box aspect ratio. With the old fixed `720x480` exports, ArcGIS could expand the requested bbox, causing geographic offset when the frontend assumed the original bounds. The mesh rendering already uses EPSG:4326 coordinates and now receives the matching image footprint.
- The radar overlay is cleared during refresh and suppressed when the provider feed is `STALE` (>30 minutes after service-window end). Unavailable feeds cannot draw old imagery.
- The radar UI says *radar echoes*, not rain falling at ground level. Warning explains virga and clutter and links to official NWS radar.
- Changed radar imagery URL query cache-buster so old misregistered PNGs are not reused.

## Limitations

- No live NOAA export or physical comparison with a weather radar app was possible in the offline build environment. Provider service timing is not identical to individual image acquisition timing.
- Reflectivity is NOT precipitation accumulation at ground level; compare with official weather radar for local decisions.
- Satellite, model, and other providers are unchanged. Historical mode still hides radar and satellite controls.

Official documentation: https://developers.arcgis.com/rest/services-reference/enterprise/export-image.htm
Official NWS radar: https://radar.weather.gov/

## Renderer performance

- Triangulated radar/satellite/map rasters now crop each draw to the source triangle's small rectangle rather than redrawing the full PNG per mesh triangle. This avoids significant redundant bitmap rasterization and keeps the map more responsive when multiple layers are enabled.

## Verification

- 106 Python tests passed, including region-specific geographic footprints, API response headers, and stale-map protections.
- Chromium isolated browser test passed for stale and available radar, archive hiding, and live restore, with zero JavaScript page errors.
- Browser test intentionally used synthetic radar pixels, not real weather conditions or verified NOAA production imagery.
