from pathlib import Path
import pytest
from stormwatch.recon import parse_hdob,decode_coord

def test_recon_fixture():
 text=(Path(__file__).resolve().parents[1]/'data/fixtures/hdob_usaf_20260910.txt').read_text()
 p=parse_hdob(text,'https://www.nhc.noaa.gov/text/URNT15-USAF.shtml')
 assert len(p['points'])==20
 assert p['points'][0]['lat']==pytest.approx(30+46/60)
 assert p['points'][0]['lon']==pytest.approx(-(89+25/60))
 assert p['points'][0]['wind_kt']==15
 assert p['points'][0]['time']=='2026-09-10T01:04:00Z'
 assert p['quality']=='ARCHIVED'

def test_recon_missing_header():
 with pytest.raises(ValueError): parse_hdob('garbage')

def test_coordinate_invalid_minutes():
 with pytest.raises(ValueError):decode_coord('3069N')
