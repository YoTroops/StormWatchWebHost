# STORMWATCH daily briefing setup

1. Upload the contents of this ZIP to the repository root, preserving `pyproject.toml`, `requirements.txt`, and `apps/`.
2. In Vercel > Project > Settings > Environment Variables, set `OPENAI_API_KEY` (server-side only). Optionally set `STORMWATCH_OPENAI_MODEL` (default `gpt-4.1-mini`). Redeploy.
3. Open `/news.html`. The `/api/news/daily` endpoint fetches source-linked recent tropical news headlines from Google News RSS and requests a grounded 110–170 word summary from OpenAI Responses API. Never expose your API key in JavaScript.

**Operating notes**
- No API key: page still presents available headlines, with an explicit summary-unavailable message.
- Briefings are generated on first visit each UTC day, then kept in a per-process in-memory cache. Vercel instances do not share memory or promise daily persistence, so multiple instances/restarts can make extra requests. The CDN cache also reduces repeats. For one exactly scheduled persistent briefing, add a real datastore and secured scheduler later.
- Google News feed access can be unavailable/rate-limited; feeds are independent of official NHC observations. Summaries see headlines only, not article text. This is informational and never replaces NHC advisories.
- OpenAI API usage requires a separately billed API account. A ChatGPT subscription does not provide an API key or free API usage.
- For compliance with news source terms, review the source provider requirements before public launch.
