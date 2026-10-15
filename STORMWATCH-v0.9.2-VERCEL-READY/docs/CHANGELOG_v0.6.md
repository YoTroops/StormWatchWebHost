# STORMWATCH v0.6 — NOAA public aircraft sightings and archive UX

## Delivered

- Server-side whitelist-based ADSB.lol adapter for N42RF, N43RF, N49RF; optional exact TEAL callsign query, with clearly unverified USAF identity and mission status.
- Bounded five-minute cached requests and scheduled source status WebSocket update.
- Aircraft markers and inspector: reported lat/lon, true observed UTC (feed timestamp minus position age), altitude and speed only where reported, heading, source, and mission NOT VERIFIED.
- Explicit no-sightings and provider-failure states. No fabricated positions or flight history.
- Archive mode fully hides live satellite and radar options (including radar layer toggle), live aircraft controls, live HDOB button, and forecast cone toggle. Back to LIVE restores them.
- 81 backend tests passing, isolated Chromium archive and live smoke passing.

## Limitations

- Network access to ADSB.lol/NOAA and Windows install unverified here.
- USAF TEAL searches are manually initiated and cannot certify aircraft type or tasking. No continuous ADS-B history and no authorized operational mission list.
- No aligned GOES imagery or CesiumJS 3D engine yet.

## Windows upgrade

Stop the previous server with Ctrl+C, extract ZIP over the existing stormwatch folder (back up any modifications first), double-click start-windows.bat, open http://127.0.0.1:8000 and hard refresh Ctrl+Shift+R.
