# STORMWATCH v0.9.9 — Support & CONUS Radar Default

- Added Buy Me a Coffee support links to dashboard desktop navigation, mobile bottom navigation, About Us, and Tropical Briefing. Links open in a separate tab and use `rel="noopener noreferrer"`.
- Changed NWS Radar regional default from Gulf of Mexico to Continental US in the selected HTML option, initial map state, and default API image query.
- Preserved all radar geographic EPSG:4326 bounding boxes and reprojection code, ensuring existing map alignment behavior is unchanged.
- Restored and retained `pyproject.toml`, `requirements.txt` and Vercel deployment configuration.
