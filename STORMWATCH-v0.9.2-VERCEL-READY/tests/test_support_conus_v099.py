"""Regression coverage for v0.10.0 support links and CONUS radar defaults."""
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from stormwatch.main import app
from stormwatch.radar import REGIONS

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'
URL='https://buymeacoffee.com/stormwatchsite?new=1'

def test_desktop_and_secondary_pages_link_to_support():
    for name in ('index.html','about.html','news.html'):
        doc=BeautifulSoup((WEB/name).read_text(),'html.parser')
        links=[a for a in doc.select('a[href]') if a.get('href')==URL]
        assert len(links)==1, name
        link=links[0]
        assert link['target']=='_blank'
        assert {'noopener','noreferrer'}.issubset(set(link['rel']))
        assert 'support' in link.get_text().lower()
        assert link.get('aria-label')

def test_mobile_support_is_a_real_link_in_bottom_navigation():
    mobile=(WEB/'mobile.js').read_text()
    css=(WEB/'mobile.css').read_text()
    assert "support.href='"+URL+"'" in mobile
    assert "support.target='_blank'" in mobile
    assert "nav.append(support)" in mobile
    assert 'repeat(8,minmax(0,1fr))' in css
    assert 'repeat(6,minmax(0,1fr))' in css
    assert '.mobile-support-link' in (WEB/'design.css').read_text()

def test_radar_ui_and_image_api_default_to_conus():
    html=BeautifulSoup((WEB/'index.html').read_text(),'html.parser')
    select=html.select_one('#radarRegion')
    assert select is not None
    assert select.select_one('option[selected]')['value']=='conus'
    assert {o['value'] for o in select.select('option')} == set(REGIONS)
    js=(WEB/'app.js').read_text()
    assert 'radarRegion:"conus"' in js
    assert 'bboxSR' not in js or 'radarBoxes' in js  # retained render-time geographic transform
    with TestClient(app) as client:
        response=client.get('/openapi.json')
        assert response.status_code==200
        parameters=response.json()['paths']['/api/radar/image']['get']['parameters']
        region=next(p for p in parameters if p['name']=='region')
        assert region['schema']['default']=='conus'
        assert client.get('/api/health').json()['version']=='0.10.3'

def test_radar_bounds_unchanged():
    assert REGIONS['conus']['bbox']==[-125.,23.,-66.,50.]
    assert REGIONS['gulf']['bbox']==[-100.,14.,-77.,34.]
