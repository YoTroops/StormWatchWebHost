"""Regression checks for v0.9.1 changelog and version consistency."""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from stormwatch.main import app

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'apps/web/dist'


def test_release_dialog_structure_and_unique_ids():
    html = BeautifulSoup((WEB / 'index.html').read_text(encoding='utf-8'), 'html.parser')
    ids = [node.get('id') for node in html.select('[id]')]
    assert len(ids) == len(set(ids))
    popup = html.select_one('#releaseDialogBackdrop')
    assert popup is not None and popup.has_attr('hidden')
    dialog = popup.select_one('[role="dialog"]')
    assert dialog['aria-modal'] == 'true'
    assert dialog['aria-labelledby'] == 'releaseDialogTitle'
    for name in ('openReleaseNotes', 'releaseDialogClose', 'releaseEnter', 'releaseHistoryList', 'releaseLatestItems'):
        assert html.select_one('#' + name)
    assert len(html.select('script[src*="release-notes.js"]')) == 1
    assert html.select_one('#workspace-storms') and html.select_one('#workspace-weather')


def test_release_version_backend_and_browser_match():
    page = (WEB / 'index.html').read_text(encoding='utf-8')
    notes = (WEB / 'release-notes.js').read_text(encoding='utf-8')
    assert re.search(r"version:\s*'0\.9\.7'", notes)
    assert 'STORMWATCH v0.9.7' in page
    assert 'v0.9.7' in BeautifulSoup(page, 'html.parser').select_one('#openReleaseNotes').get_text()
    with TestClient(app) as client:
        result = client.get('/api/health')
    assert result.status_code == 200
    assert result.json()['version'] == '0.9.7'


def test_embedded_release_styles_even_without_external_css():
    page = (WEB / 'index.html').read_text(encoding='utf-8')
    css = (WEB / 'style.css').read_text(encoding='utf-8')
    for selector in ('.release-backdrop[hidden]', '.release-dialog', '.release-enter', '.release-history-list details'):
        assert selector in page
        assert selector in css


def test_version_scoped_storage_and_local_history():
    js = (WEB / 'release-notes.js').read_text(encoding='utf-8')
    assert "localStorage.getItem(STORAGE_KEY)" in js
    assert "localStorage.setItem(STORAGE_KEY, latest.version)" in js
    assert 'showReleaseNotes();' in js
    assert 'RELEASES.slice(1)' in js
    assert 'document.createElement' in js
    assert "event.key === 'Escape'" in js
    assert (ROOT / 'docs/CHANGELOG_v0.9.2.md').is_file()
