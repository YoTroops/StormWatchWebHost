# STORMWATCH v0.9 — UI organization and GOES image fix

**Released:** 2026-10-14

## Fixed

- GOES imagery could render at native 1250×750 size inside a narrow sidebar because no restrictive `.satellite-frame` / `#satelliteImage` styles were provided. The preview is now constrained by the panel width and a 200 px max-height 5:3 frame, with object-fit `contain` and clip containment. Hidden/unavailable states remain explicit.
- Enlarged satellite preview cannot exceed the browser viewport height or modal width.
- All added styles are included in inline CSS and external `style.css`, with a cache-busted link and application script query string so users upgrading on Windows don't see outdated layouts.

## Changed

- Left sidebar split into tabbed **STORMS / MODELS / WEATHER / LAYERS / RECON** workspaces while preserving the central map, timeline and right-hand inspector.
- Moved the model intensity/pressure chart from the permanent inspector to the Models tab.
- Added native collapsible Weather satellite/radar sections, and grouped live aircraft under Recon.
- Added Focus Storm map control.
- Improved sidebar spacing, narrow desktop responsiveness and keyboard tab navigation.
- Archive mode hides both Models and Weather tabs, satellite/radar UI and live ADS-B, while keeping a selectable archive/replay and HDOB fixture viewer.
- Backend version reported as 0.9.0; provider adapters and API routes unchanged.

## Tests and limitations

- 96 Python tests passed, JavaScript parsed successfully and isolated Chromium mock UI passed with no runtime errors. Verified a 1250×750 mock GOES image is bounded to <=200 px display height.
- **Not verified:** live provider access, Windows runtime, and browser-to-server end-to-end networking. Screenshots in `docs/` are based on mock responses.
