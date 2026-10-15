from datetime import datetime, timezone
import pytest
from stormwatch import briefing

RSS=b'''<?xml version="1.0"?><rss><channel><item><title>NHC Tropical Weather Outlook</title><link>https://www.nhc.noaa.gov/gtwo.php</link><pubDate>Thu, 15 Oct 2026 03:00:00 GMT</pubDate></item></channel></rss>'''
ATOM=b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Tropical science update</title><link href="https://science.nasa.gov/update"/><updated>2026-10-15T03:00:00Z</updated></entry></feed>'''

def test_rss_and_atom():
    now=datetime(2026,10,15,6,tzinfo=timezone.utc)
    assert briefing.parse_feed(RSS,'NHC',now,2)[0]['channel']=='NHC'
    assert briefing.parse_feed(ATOM,'NASA',now,14)[0]['url']=='https://science.nasa.gov/update'

def test_stale_not_reported_as_current():
    now=datetime(2026,11,1,tzinfo=timezone.utc)
    assert not briefing.parse_feed(RSS,'NHC',now,2)

@pytest.mark.asyncio
async def test_feed_failover(monkeypatch):
    import httpx
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url):
            if 'google' in url:raise httpx.ConnectError('failed')
            return httpx.Response(200,content=RSS if 'nhc.noaa.gov' in url else ATOM,request=httpx.Request('GET',url))
    monkeypatch.setattr(briefing.httpx,'AsyncClient',FakeClient)
    articles,status=await briefing.fetch_headlines(with_status=True)
    assert articles and any(x['channel'].startswith('NHC') for x in articles)
    assert any(x['status']=='unreachable' for x in status)
    assert any(x['status']=='ok' for x in status)
