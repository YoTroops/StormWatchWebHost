"""Map space and truthful source freshness regression tests."""
from pathlib import Path
from bs4 import BeautifulSoup
import subprocess

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

def test_removed_timeline_and_mobile_replay():
    doc=BeautifulSoup((WEB/'index.html').read_text(),'html.parser')
    assert doc.select_one('.timeline') is None
    assert doc.select_one('#timelineRange') is None
    assert 'mobile-replay-toggle' not in (WEB/'mobile.js').read_text()
    assert 'hideReplay()' not in (WEB/'mobile.js').read_text()
    assert doc.select_one('#earthCanvas') is not None

def test_source_timestamp_age_and_archive_navigation():
    app=(WEB/'app.js').read_text()
    for token in ('function observationAge(', 'function advisoryQuality(', 'advisoryQuality(s.quality,s.time)', 'nextObservation', 'previousObservation', 'state.mode!==\'ARCHIVE\''):
        assert token in app
    assert 'function refreshTimeline()' not in app
    assert "$('timelineRange')" not in app
    assert 'setInterval(()=>{if(document.hidden' in app

def test_age_edge_cases_run_in_js():
    code=(WEB/'app.js').read_text()
    start=code.index('function observationAge(')
    end=code.index('function catLabel(',start)
    helpers=code[start:end]
    test='''
const esc=x=>String(x);
const now=Date.parse('2026-10-15T12:00:00Z');
if(observationAge('2026-10-15T10:00:00Z',now)!=='2 HR AGO')throw Error('2 hours');
if(observationAge('2026-10-15T11:40:00Z',now)!=='20 MIN AGO')throw Error('20 minutes');
if(observationAge('2026-10-13T12:00:00Z',now)!=='2 D AGO')throw Error('2 days');
if(observationAge(null,now)!=='AGE UNKNOWN')throw Error('missing');
if(observationAge('2026-10-15T13:00:00Z',now)!=='AGE UNKNOWN')throw Error('future');
if(advisoryQuality('DELAYED','2026-10-15T10:00:00Z').startsWith('DELAYED · ')===false)throw Error('badge');
'''
    subprocess.run(['node','--check',str(WEB/'app.js')],check=True)
    subprocess.run(['node','-e',helpers+test],check=True)
