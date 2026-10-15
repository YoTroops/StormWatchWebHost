# STORMWATCH v0.9.3 — Mobile operations interface

- Phone-first orthographic globe layout; left workspace and right inspector become accessible slide-up panels instead of stacking above the map.
- Bottom navigation for Map, Storms, Models, Weather, Layers, Recon, and Info.
- Hidden current radar/satellite/model tabs in archive mode, preserving historical research tools.
- Compact optional replay timeline, horizontally scrollable map actions and large touch targets.
- Added pinch-to-zoom handling and mobile-fit default globe zoom; original desktop controls remain.
- Mobile responsive styles embedded in HTML and shipped as a separate CSS asset for compatibility with offline/local launches.
- Version-aware launch changelog updated to v0.9.3.

Testing: Python tests and isolated Chromium UI tests at four viewports. Mobile weather and tiles in the browser test were mocked. Real NOAA, real mobile devices and all provider endpoints remain unverified in this environment.
