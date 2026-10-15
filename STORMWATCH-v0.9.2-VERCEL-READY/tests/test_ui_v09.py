"""Static build checks for the new UI and the bounded NOAA image renderer."""
from pathlib import Path
from bs4 import BeautifulSoup

WEB = Path(__file__).resolve().parents[1] / 'apps/web/dist'


def test_live_and_archive_workspaces_are_unique_and_addressable():
    page = BeautifulSoup((WEB / 'index.html').read_text(), 'html.parser')
    ids = [t['id'] for t in page.select('[id]')]
    assert len(ids) == len(set(ids)), 'Duplicate control IDs cause broken browser event handlers'
    for name in ('storms', 'models', 'weather', 'layers', 'recon'):
        tab = page.select_one(f'#tab-{name}')
        pane = page.select_one(f'#workspace-{name}')
        assert tab is not None and pane is not None
        assert tab['aria-controls'] == pane['id']
    assert not page.select_one('#workspace-storms').has_attr('hidden')
    assert all(page.select_one(f'#workspace-{n}').has_attr('hidden') for n in ('models', 'weather', 'layers', 'recon'))
    assert page.select_one('#tab-models').has_attr('class')
    assert 'mode-live-only' in page.select_one('#tab-models')['class']
    assert 'mode-live-only' in page.select_one('#tab-weather')['class']
    assert 'mode-live-only' in page.select_one('#liveImageryOptions')['class']


def test_satellite_css_is_embedded_and_bounded():
    page = (WEB / 'index.html').read_text()
    stylesheet = (WEB / 'style.css').read_text()
    for required in ('.satellite-frame #satelliteImage', 'max-height:200px', 'max-width:100%!important', '.satellite-large', 'max-height:62vh', '.workspace-pane[hidden]'):
        assert required in stylesheet
        assert required in page, 'Styles must work if a separate stylesheet fails to load on Windows'


def test_existing_data_controls_preserved():
    page = BeautifulSoup((WEB / 'index.html').read_text(), 'html.parser')
    for control in ('satelliteImage', 'satelliteExpand', 'satelliteStatus', 'mappedSatControls', 'radarRegion', 'modelsIntensityChart', 'modelMetric', 'stormList', 'stormCount', 'reconButton', 'aircraftList', 'focusSelected'):
        assert page.select_one(f'#{control}') is not None, control
