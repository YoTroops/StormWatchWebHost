import pytest
from datetime import datetime, timezone, timedelta
from stormwatch.science import kt_to_mph, mph_to_kt, hpa_to_inhg, hurricane_category, geo_coord, wrap_longitude, freshness, utc

@pytest.mark.parametrize('wind,expected',[(0,None),(34,None),(63,None),(64,1),(82,1),(83,2),(95,2),(96,3),(112,3),(113,4),(136,4),(137,5),(160,5)])
def test_category(wind,expected):assert hurricane_category(wind)==expected

def test_wind_conversions(): assert mph_to_kt(kt_to_mph(113))==pytest.approx(113)
def test_hpa():assert hpa_to_inhg(1013.25)==pytest.approx(29.921,abs=.01)
@pytest.mark.parametrize('coord,result',[('11.5N',11.5),('99.5W',-99.5),('33.3S',-33.3),('170E',170)])
def test_coord(coord,result): assert geo_coord(coord)==result
@pytest.mark.parametrize('coordinate',['181W','91N','-5N','100E0','nanN'])
def test_bad_coord(coordinate):
 with pytest.raises(ValueError):geo_coord(coordinate)
def test_wrap_longitude():assert wrap_longitude(181)==-179 and wrap_longitude(-181)==179

def test_utc_offset():assert utc('2024-10-07T05:00:00-04:00').isoformat()=='2024-10-07T09:00:00+00:00'
def test_utc_naive_rejected():
 with pytest.raises(ValueError):utc('2024-10-07T09:00:00')
def test_freshness():
 now=datetime(2026,10,14,15,0,tzinfo=timezone.utc)
 assert freshness(now,now)=='LIVE'
 assert freshness(now-timedelta(minutes=100),now)=='DELAYED'
 assert freshness(now-timedelta(hours=8),now)=='STALE'
 assert freshness(None,now)=='UNAVAILABLE'
 assert freshness(now+timedelta(hours=3),now)=='UNAVAILABLE'
