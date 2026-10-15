# v0.9.8 — Tropical Briefing Reliability

- Added NOAA National Hurricane Center Atlantic and Eastern Pacific XML feeds and NASA Hurricane Science as independent sources alongside Google News.
- Supports RSS and Atom, safe HTTPS links, and differentiated recency windows (2 days for NHC bulletins, 7 for Google News, and 14 for research).
- Reports per-source health and distinguishes unreachable sources from no recent coverage.
- Allows redirects, uses a more compatible user-agent, and prevents Vercel from caching empty headline results.
- Updated the briefing copy and preserved optional server-side OpenAI summaries.

Note: Source hosts may change feed formats or limit access. Live network reliability must be checked on deployed Vercel.
