# STORMWATCH v0.9.1 — Welcome and release history

**Release date:** 2026-10-14

## Added

- **First-open release dialog** shows installed build version, latest changes, and expandable history from earlier releases. The dialog is fully local and does not rely on NOAA, network access, or third-party services.
- The dialog appears **once per browser per version after dismissal**, using `localStorage`. A new version displays the popup again. If the browser blocks storage or a user clears site data, the popup can recur on page load.
- New **WHAT'S NEW v0.9.1** button in the top status bar reopens the dialog on demand.
- Close with **ENTER STORMWATCH**, X, Escape, or by clicking the backdrop. Keyboard focus is moved into the dialog, trapped during display, and restored upon close.
- Responsive styling included in both inlined CSS and external stylesheet for reliable Windows deployments.

## Unchanged

The v0.9 geospatial client, hurricane feeds, GOES preview, radar, reconnaissance, and forecast model integrations remain unchanged. No new live data provider or API key is required. Backend version is now `0.9.1`.

## Limitations

Release history is bundled with the application, not an automatic internet software-update checker. Features in historical changelogs may depend on external data-provider availability. Windows runtime and external NOAA/ADS-B connections still require on-device verification.
