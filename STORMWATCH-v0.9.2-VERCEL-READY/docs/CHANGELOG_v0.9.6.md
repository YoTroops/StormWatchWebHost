# v0.9.6 — Deployment and alignment hotfix

- Restore root pyproject.toml, requirements.txt, and Vercel deployment instructions.
- Correct NOAA nowCOAST satellite export dimensions to match each EPSG:4326 bounding box; force adjustAspectRatio=false.
- Preserve NWS radar export coordinate bounds and reprojection; refine radar mesh resolution.
- Preserve inverse Web Mercator treatment of OSM tiles and native lon/lat storm positions.
