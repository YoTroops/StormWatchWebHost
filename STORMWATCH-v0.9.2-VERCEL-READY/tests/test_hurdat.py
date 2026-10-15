import pytest
from pathlib import Path
from stormwatch.hurdat import parse_hurdat,load_fixture

SAMPLE='''AL142024,            MILTON,      3,
20241005, 1800,  , TD, 22.7N, 95.0W,  30, 1006, -999, -999
20241006, 0000,  , TS, 22.6N, 94.6W,  40, 1002, -999, -999
20241007, 1800,  , HU, 21.7N, 91.3W, 155, 905, -999, -999
EP012025,            ALVIN,      1,
20250529, 1200,  , TS, 12.1N, 102.0W,  35, 1007, -999, -999
'''

def test_parse_hurdat():
 result=parse_hurdat(SAMPLE)
 assert len(result)==2 and result[0]['points'][2]['category']==5
 assert result[0]['points'][0]['lon']==-95
 assert result[1]['basin']=='Eastern Pacific'
 assert result[0]['points'][0]['time']=='2024-10-05T18:00:00Z'

def test_select():assert [e['id'] for e in parse_hurdat(SAMPLE,{'EP012025'})]==['EP012025']
def test_missing_data():
 a=parse_hurdat('AL012024, TEST, 1,\n20240101,0000,,TD,12.0N,70.0W,-999,-999,\n')
 assert a[0]['points'][0]['wind_kt'] is None and a[0]['points'][0]['pressure_hpa'] is None

def test_truncated():
 with pytest.raises(ValueError):parse_hurdat('AL142024,MILTON,3,\n20241005,1800,,TD,22.7N,95.0W,30,1006')

def test_fixture_provenance():
 p=Path(__file__).resolve().parents[1]/'data/fixtures/milton_advisories.json'
 d=load_fixture(p)
 assert d['dataset']=='SELECTED_ADVISORY_SNAPSHOTS' and len(d['points'])==10
 assert d['points'][2]['pressure_hpa']==897
 assert d['points'][2]['wind_kt']>150
 assert all(x['source_url'].startswith('https://www.nhc.noaa.gov/archive/') for x in d['points'])
