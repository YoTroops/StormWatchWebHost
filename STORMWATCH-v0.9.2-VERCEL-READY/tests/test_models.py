"""NHC ATCF is scientific source data; avoid inferred or synthetic forecasts."""
from datetime import datetime, timezone
import gzip
from fastapi.testclient import TestClient
from stormwatch.models import (
    deck_url, parse_position, parse_atcf, decode_deck, assemble, unavailable_catalog, MODEL_REGISTRY)
from stormwatch.main import app, provider
import pytest

STORM='AL092026'
DATA='''AL, 09, 2026101400, 03, HFSA, 000, 220N, 0730W, 60, 985, HU,
AL, 09, 2026101400, 03, HFSA, 024, 238N, 0750W, 80, 960, HU,
AL, 09, 2026101400, 03, HFSA, 048, 256N, 0770W, 95, 945, HU,
AL, 09, 2026101400, 03, HFSB, 000, 221N, 0730W, 62, 983, HU,
AL, 09, 2026101400, 03, HFSB, 024, 240N, 0750W, 88, 950, HU,
AL, 09, 2026101400, 03, AVNI, 000, 220N, 0730W, 55, 990, HU,
AL, 09, 2026101400, 03, AVNI, 024, 237N, 0760W, 75, 965, HU,
AL, 09, 2026101400, 03, EMXI, 000, 220N, 0730W, 59, 987, HU,
AL, 09, 2026101400, 03, EMXI, 024, 248N, 0730W, 83, 960, HU,
AL, 09, 2026101400, 03, GDMI, 000, 220N, 0730W, 53, 994, HU,
AL, 09, 2026101400, 03, GDMI, 024, 253N, 0790W, 90, 955, HU,
AL, 09, 2026101400, 03, EAII, 000, 220N, 0730W, 54, 992, HU,
AL, 09, 2026101400, 03, EAII, 024, 253N, 0810W, 93, 952, HU,
AL, 09, 2026101412, 03, HFSA, 000, 224N, 0740W, 66, 981, HU,
AL, 09, 2026101412, 03, HFSA, 024, 244N, 0750W, 84, 956, HU,
AL, 09, 2026101412, 03, GDMI, 000, 224N, 0740W, 63, 984, HU,
AL, 09, 2026101412, 03, GDMI, 024, 255N, 0790W, 99, 941, HU,
EP, 09, 2026101412, 03, HFSA, 000, 224N, 0740W, 66, 981, HU,
AL, 09, 2026101412, 03, HFSA, 024, 999N, 0750W, 84, 956, HU,
AL, 09, 2026101412, 03, HFSA, 024, 244N, 0750W, 84, 956, HU, 34, NEQ, 0, 0, 0, 0
'''

def test_storm_url_validation():
    assert deck_url('al092026').endswith('/aal092026.dat.gz')
    assert deck_url('EP202026').endswith('/aep202026.dat.gz')
    for invalid in ('AL0124','AB092026','AL092026/../../bad','ALAA2026','AL090926'):
        with pytest.raises(ValueError):deck_url(invalid)

def test_atcf_tenths_degrees_and_basin():
    assert parse_position('005S',True)==-.5
    assert parse_position('0750W',False)==-75.0
    with pytest.raises(ValueError):parse_position('1900W',False)
    with pytest.raises(ValueError):parse_position('0730W',True)
    data=parse_atcf(DATA,STORM)
    assert len(data['cycles'])==2
    assert data['invalid_rows']>0
    assert len(data['rows'])==17

def test_same_cycle_no_cross_contamination():
    result=assemble(parse_atcf(DATA,STORM),now=datetime(2026,10,14,18,tzinfo=timezone.utc))
    assert result['cycle_utc']=='2026-10-14T12:00:00Z'
    items={row['id']:row for row in result['models']}
    assert items['hafsa']['points'][-1]['wind_kt']==84
    assert items['google']['points'][-1]['wind_kt']==99
    assert items['ecmwf']['availability']=='UNAVAILABLE'  # older cycle never plotted as same cycle
    assert items['hafsai']['availability']=='UNAVAILABLE'
    assert not items['hafsai']['aids']
    previous=assemble(parse_atcf(DATA,STORM), '2026-10-14T00:00:00Z')
    assert next(x for x in previous['models'] if x['id']=='ecmwf')['points'][1]['lat']==24.8
    assert next(x for x in previous['models'] if x['id']=='hafsa')['points'][1]['wind_kt']==80

def test_duplicate_wind_radii_does_not_make_extra_positions():
    result=assemble(parse_atcf(DATA,STORM))
    assert len(next(x for x in result['models'] if x['id']=='hafsa')['points'])==2
    with pytest.raises(ValueError):assemble(parse_atcf(DATA,STORM),'2026-10-13T00:00:00Z')

def test_unavailable_does_not_fabricate():
    empty=unavailable_catalog('Unreachable')
    assert len(empty['models'])==len(MODEL_REGISTRY)
    assert all(not x['points'] for x in empty['models'])
    with pytest.raises(ValueError):decode_deck(b'not gzip')
    assert decode_deck(gzip.compress(DATA.encode()))==DATA
    assert parse_atcf('garbage',STORM)['cycles']==[]

def test_api_models_from_mocked_official_deck(monkeypatch):
    async def live():return [{'id':STORM}]
    async def fetch(url,ttl,max_bytes):
        assert url.endswith('aal092026.dat.gz')
        return gzip.compress(DATA.encode())
    monkeypatch.setattr(provider,'live_storms',live)
    monkeypatch.setattr(provider,'fetch',fetch)
    client=TestClient(app)
    resp=client.get('/api/models/AL092026')
    assert resp.status_code==200,resp.text
    data=resp.json()
    assert data['quality']=='AVAILABLE'
    assert data['available_models']>=2
    assert next(m for m in data['models'] if m['id']=='google')['availability']=='AVAILABLE'
    assert next(m for m in data['models'] if m['id']=='hafsai')['availability']=='UNAVAILABLE'
    resp=client.get('/api/models/AL092026?cycle=2026-10-13T00:00:00Z')
    assert resp.status_code==400
    resp=client.get('/api/models/AL092026?cycle=2026-10-14T00:00:00Z')
    assert resp.status_code==200
    assert next(x for x in resp.json()['models'] if x['id']=='ecmwf')['availability']=='AVAILABLE'

def test_api_models_fail_closed(monkeypatch):
    async def live():return [{'id':'AL122026'}]
    monkeypatch.setattr(provider,'live_storms',live)
    client=TestClient(app)
    assert client.get('/api/models/AL092026').status_code==404
    assert client.get('/api/models/ALX92026').status_code==400
    async def live_ok():return [{'id':STORM}]
    async def failed(url,ttl,max_bytes):raise ConnectionError('offline')
    monkeypatch.setattr(provider,'live_storms',live_ok)
    monkeypatch.setattr(provider,'fetch',failed)
    result=client.get('/api/models/AL092026').json()
    assert result['quality']=='UNAVAILABLE'
    assert not any(m['points'] for m in result['models'])
