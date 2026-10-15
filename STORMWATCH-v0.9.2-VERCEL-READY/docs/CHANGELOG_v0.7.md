# STORMWATCH v0.7 — Enhanced map detail / experimental NOAA satellite-map overlay

## Included

1. Native-scale online OpenStreetMap settlement/place labels and roads rendered on globe and 2D Canvas. Longitude wraps correctly; Web Mercator tiles use a geographic mesh to avoid stretching. Offline coastline fallback retained. Viewport-only request queue, bounded in-memory image cache, visible OSM attribution, manual DETAIL ON/OFF.
2. Increased interactive zoom range to reveal finer towns and local features at higher tile zooms.
3. Optional NOAA nowCOAST projected satellite map service (visible / longwave infrared / water vapor), with bounded host/region/channel allowlists and PNG validation. Region, channel and opacity controls. The static NOAA CONUS JPG remains an independent preview. NOAA nowCOAST may not be accessible: the UI shows UNAVAILABLE, never made-up satellite observations.
4. Mapped satellite viewer, satellite preview, radar and aircraft controls disappear in ARCHIVE. The detailed cartographic basemap remains available for historical exploration; NOAA current satellite pixels are never overlaid onto archived storms.
5. Backend version + documentation updated, eight-six automated Python tests, isolated Chromium test with explicitly mocked OSM/NOAA imagery.

## Boundaries

- This is an OSM raster detail system on the existing Canvas globe, **not CesiumJS**. High-detail tiles require a network connection and the public tile server has usage restrictions (no offline downloading, scraping or bulk prefetch).
- NOAA nowCOAST live availability could not be verified here. Missing source imagery remains unavailable. No fabricated times or cloud data.
- Browser tests use mock tiles and NOAA satellite image; they are not a live-provider test. Windows startup and Docker still require local verification.
