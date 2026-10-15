# STORMWATCH v0.9.5 — Performance Hotfix

- The detailed OSM street/town-label map is **OFF at startup**; it remains manually toggleable.
- Drag and mousewheel redraws are scheduled via requestAnimationFrame.
- High-DPI mobile canvas scaling capped at 1.5; desktop capped at 2.
- The in-memory tile cache is reduced from 170 to 100 tiles and visible tile cap from 36 to 28.
- Heavy satellite/radar/aircraft/recon initial requests start after the first map render.
- The five-minute update loop skips background work when the tab is hidden.
- Resize redraws coalesce and model-chart recomputation is debounced.
- What’s New still opens on each page load; About Us and v0.9.4 branding are preserved.
