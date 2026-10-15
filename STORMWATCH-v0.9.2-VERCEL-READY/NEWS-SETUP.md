# STORMWATCH Tropical Briefing setup (v0.9.8)

1. Deploy the project root (the directory containing `pyproject.toml`) to Vercel.
2. In Vercel project Settings > Environment Variables, add a **Secret** named `OPENAI_API_KEY` containing your OpenAI Platform API key. Select Production and redeploy.
3. Open `/news.html` and inspect `/api/news/daily` if the briefing shows no recent coverage.
4. The `feed_status` array indicates which sources were unreachable versus available but with no recent dated items. `source_status` will be `available`, `sources_unreachable`, or `no_recent_items`.
5. The OpenAI API is only used if source headlines exist. Summaries are grounded in supplied titles, not full articles, and never replace NHC advisories.

Sources: Google News (7 days), NHC Atlantic / Eastern Pacific (2 days), NASA Hurricane Science (14 days). Sources and their coverage vary; empty results can be legitimate. The Vercel runtime must be able to reach the feeds.
