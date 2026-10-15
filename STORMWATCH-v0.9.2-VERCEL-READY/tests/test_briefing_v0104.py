from stormwatch import briefing
import pytest

@pytest.mark.asyncio
async def test_search_fallback_grounded(monkeypatch):
    async def feeds(**kwargs):
        return ([], [{'source':'rss','status':'unreachable','count':0}])
    async def ai(payload):
        assert payload['tools'][0]['type']=='web_search_preview'
        return {'output':[{'content':[{'type':'output_text','text':'A cited report.', 'annotations':[{'type':'url_citation','url':'https://www.nhc.noaa.gov/','title':'Official NHC'}]}]}]},None
    monkeypatch.setattr(briefing,'fetch_headlines',feeds)
    monkeypatch.setattr(briefing,'_openai_response',ai)
    monkeypatch.setenv('OPENAI_API_KEY','fake')
    briefing._cache.update(day=None,data=None)
    data=await briefing.daily_brief()
    assert data['summary_method']=='web_search_fallback'
    assert data['summary_status']=='available'
    assert data['headlines'][0]['url']=='https://www.nhc.noaa.gov/'

@pytest.mark.asyncio
async def test_uncited_ai_text_rejected(monkeypatch):
    async def ai(payload):
        return {'output':[{'content':[{'type':'output_text','text':'Unverified statement','annotations':[]}]}]},None
    monkeypatch.setattr(briefing,'_openai_response',ai)
    summary,links,error=await briefing.search_briefing()
    assert not summary and not links and 'source-cited' in error

def test_errors_safe_and_actionable():
    from types import SimpleNamespace
    assert 'quota' in briefing._ai_error(SimpleNamespace(status_code=429))
    assert 'API key' in briefing._ai_error(SimpleNamespace(status_code=401))
    assert 'web search' in briefing._ai_error(SimpleNamespace(status_code=400))
