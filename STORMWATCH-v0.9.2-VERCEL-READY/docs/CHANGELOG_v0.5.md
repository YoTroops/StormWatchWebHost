# STORMWATCH v0.5 — release notes (2026-10-14)

**Added:** a NOAA/NWS MRMS radar mosaic data connector with published service-window metadata, a bounded PNG export endpoint, and a geographically placed canvas overlay in both orthographic and 2D maps. The viewer supports Gulf of Mexico, Southeast US, Caribbean, and CONUS bounds, recent requested times, adjustable opacity, focus control, automatic five-minute polling, WebSocket change notifications, and visible unavailable/stale states. Radar never appears during historical replay.

**Added:** background and on-demand reconnaissance bulletin status checks for latest USAF Atlantic HDOB. The date-dependent quality state distinguishes recent public observations from archived bulletins, and does not claim a live aircraft location. Fixed original HDOB bulletin regex that did not match URNT15 headers.

**Validated:** 71 passing Python tests, passing Node JavaScript syntax validation, isolated Chromium UI smoke run (mocked NOAA/NWS sources only), and local HTTP startup smoke checks with background polling disabled.

**Not implemented:** ADS-B live aircraft tracking; radar acquisition time on a per-pixel basis; GOES satellite image registration onto globe; automatic multi-frame radar animation; numerical forecast comparisons; NOAA live provider e2e test within build container; CesiumJS.

**Windows upgrade:** stop v0.4 with Ctrl+C, extract v0.5 ZIP over your existing folder (or to a new folder), start `start-windows.bat`, Ctrl+Shift+R in your browser. No API keys required; internet needed for official NOAA/NWS imagery and first-time dependencies.
