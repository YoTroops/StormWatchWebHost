from pathlib import Path
from bs4 import BeautifulSoup
from stormwatch import briefing

def test_xml_parsing_without_lxml(monkeypatch):
    from datetime import datetime,timezone
    xml=b'<rss><channel><item><title>Test NHC update</title><link>https://www.nhc.noaa.gov/</link><pubDate>Thu, 15 Oct 2026 03:00:00 GMT</pubDate></item></channel></rss>'
    assert briefing.parse_feed(xml,'NHC',datetime(2026,10,15,4,tzinfo=timezone.utc))[0]['title']=='Test NHC update'

def test_navigation_and_source_reporting():
    root=Path(__file__).resolve().parents[1]/'apps/web/dist'
    page=BeautifulSoup((root/'index.html').read_text(),'html.parser')
    assert page.select_one('.site-menu summary')
    assert page.select_one('#openReleaseNotes')
    assert page.select_one('#liveMode') and page.select_one('#archiveMode')
    assert page.select_one('[data-open-testers].header-feedback')
    assert page.select_one('.site-menu-list a[href="/news.html"]')
    assert page.select_one('.site-menu-list a[href="/about.html"]')
    assert page.select_one('.site-menu-list a[href^="https://buymeacoffee.com"]')
    assert 'feed_status' in (root/'news.js').read_text()
