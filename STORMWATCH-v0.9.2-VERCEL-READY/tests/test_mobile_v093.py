"""Mobile v0.9.3 regressions: source availability and accessibility scaffolding."""
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from stormwatch.main import app

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'apps/web/dist'

def test_mobile_assets_embedded_and_loaded():
    page=(WEB/'index.html').read_text()
    css=(WEB/'mobile.css').read_text()
    js=(WEB/'mobile.js').read_text()
    assert '<meta name="viewport" content="width=device-width,initial-scale=1"/>' in page
    assert '/static/mobile.css?v=093' in page
    assert '/static/mobile.js?v=093' in page
    assert '.mobile-nav-button' in page
    assert css in page
    assert "document.createElement('nav')" in js
    assert "requestAnimationFrame(render)" in js
    assert "touchAction='none'" in js

def test_original_controls_unchanged_and_mobile_archive_safe():
    html=BeautifulSoup((WEB/'index.html').read_text(),'html.parser')
    ids=[n['id'] for n in html.select('[id]')]
    assert len(ids)==len(set(ids))
    for id_ in ('earthCanvas','archiveMode','liveMode','stormList','timeline','timelineRange','modelCycle','satelliteImage','radarRegion','inspector','releaseDialogBackdrop'):
        assert html.select_one('#'+id_) is not None or (id_=='timeline' and html.select_one('.timeline') is not None)
    css=(WEB/'mobile.css').read_text()
    assert '.archive-mode .mobile-nav-button.mode-live-only' in css
    assert 'touch-action:none' in css
    assert '76dvh' in css

def test_static_assets_served_by_backend():
    with TestClient(app) as client:
        for asset in ('mobile.css','mobile.js'):
            result=client.get('/static/'+asset)
            assert result.status_code==200
            assert len(result.content)>1000
        assert client.get('/api/health').json()['version']=='0.9.3'
