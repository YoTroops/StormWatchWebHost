"""No real ADS-B endpoints are called by automated tests."""
import json
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from stormwatch.aircraft import AIRCRAFT_URL, CALLSIGN_ROOT, parse_aircraft_response
from stormwatch import main

NOW=datetime(2026,10,14,20,40,0,tzinfo=timezone.utc)
MS=int(NOW.timestamp()*1000)

def sample(**extra):
    ac=dict(r='N42RF',hex='a4fac3',flight='NOAA42  ',lat=28.5,lon=-84.3,
        alt_baro=12000,gs=220.4,track=267.0,seen_pos=5)
    ac.update(extra)
    return {'now':MS,'ac':[ac]}


def test_known_noaa_aircraft_position():
    results=parse_aircraft_response(sample(),NOW)
    assert len(results)==1
    row=results[0]
    assert row['registration']=='N42RF'
    assert row['name']=='Kermit'
    assert row['observed_utc']=='2026-10-14T20:39:55Z'
    assert row['age_seconds']==5
    assert row['quality']=='LIVE'
    assert row['groundspeed_kt']==220.4
    assert row['mission_status']=='NOT VERIFIED'
    assert row['identity_verified']


def test_delayed_and_old_positions_are_not_live():
    assert parse_aircraft_response(sample(seen_pos=130),NOW)[0]['quality']=='DELAYED'
    assert parse_aircraft_response(sample(seen_pos=700),NOW)==[]
    assert parse_aircraft_response(sample(seen_pos=3601),NOW)==[]


def test_invalid_geo_and_missing_position_are_skipped():
    for invalid in (dict(lat=91),dict(lon=-181),dict(lat='nan'),dict(lat=None),dict(seen_pos=None),dict(seen_pos=-1)):
        assert parse_aircraft_response(sample(**invalid),NOW)==[]


def test_registration_allowlist_enforced():
    assert parse_aircraft_response(sample(r='N123XX'),NOW)==[]
    assert parse_aircraft_response(sample(r='N49RF'),NOW)[0]['name']=='Gonzo'
    assert parse_aircraft_response(sample(r='N43RF'),NOW)[0]['name']=='Miss Piggy'
    assert parse_aircraft_response(sample(r='N123XX'),NOW,filter_registration=False)[0]['mission_status']=='NOT VERIFIED'


def test_payload_time_and_type_integrity():
    for bad in ({'ac':[]}, {'now':MS,'ac':{}}, {'now':'nan','ac':[]},
                {'now':MS+900000,'ac':[]}, {'now':MS,'ac':None}):
        with pytest.raises(ValueError):parse_aircraft_response(bad,NOW)


def test_metadata_enforces_bad_altitude_not_displayed():
    row=parse_aircraft_response(sample(alt_baro='ground',gs='nan',track=999),NOW)[0]
    assert row['altitude_ft'] is None
    assert row['groundspeed_kt'] is None
    assert row['heading_deg'] is None


def test_noaa_api_uses_only_expected_request(monkeypatch):
    async def fake_fetch(url,ttl,max_bytes):
        assert url==AIRCRAFT_URL and ttl==300 and max_bytes==500_000
        return json.dumps({'now':int(datetime.now(timezone.utc).timestamp()*1000),'ac':[]}).encode()
    monkeypatch.setattr(main.provider,'fetch',fake_fetch)
    response=TestClient(main.app).get('/api/aircraft/noaa')
    assert response.status_code==200
    assert response.json()['quality']=='AVAILABLE'
    assert response.json()['aircraft']==[]
    assert len(response.json()['tracked_registrations'])==3


def test_noaa_feed_failure_not_no_flights(monkeypatch):
    async def no_provider(url,ttl,max_bytes):
        raise RuntimeError('offline')
    monkeypatch.setattr(main.provider,'fetch',no_provider)
    r=TestClient(main.app).get('/api/aircraft/noaa')
    assert r.status_code==200
    assert r.json()['quality']=='UNAVAILABLE'
    assert 'not mean' in r.json()['note']


def test_usaf_teal_input_validation_and_no_mission_claim(monkeypatch):
    async def fetch(url,ttl,max_bytes):
        assert url==CALLSIGN_ROOT+'TEAL21'
        return json.dumps({'now':int(datetime.now(timezone.utc).timestamp()*1000),
                           'ac':[{'r':'','hex':'ae1234','flight':'TEAL21 ','lat':29.0,
                                  'lon':-89.0,'seen_pos':3,'gs':200}]}).encode()
    monkeypatch.setattr(main.provider,'fetch',fetch)
    cli=TestClient(main.app)
    for bad in ('TEAL', 'TEAL9999', 'N42RF', 'TEAL21/evil', 'TEAL2!'):
        assert cli.get('/api/aircraft/teal',params={'callsign':bad}).status_code in (400,422)
    obj=cli.get('/api/aircraft/teal',params={'callsign':'teal21'}).json()
    assert obj['quality']=='AVAILABLE'
    assert obj['aircraft'][0]['mission_status']=='NOT VERIFIED'
    assert obj['aircraft'][0]['identity_verified'] is False
    assert len(obj['aircraft'])==1


def test_provider_rejects_arbitrary_adsb_paths():
    import asyncio
    from stormwatch.nhc import Provider
    async def check():
        obj=Provider()
        for bad in ('https://api.adsb.lol/v2/mil/',
                    'https://api.adsb.lol/v2/callsign/TEAL21?extra=1',
                    'https://api.adsb.lol/v2/callsign/TEAL21/../../foo'):
            with pytest.raises(ValueError):await obj.fetch(bad,300)
    asyncio.run(check())
