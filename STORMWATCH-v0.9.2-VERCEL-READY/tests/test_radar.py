"""MRMS radar integration verification using representative service metadata and PNG fixture bytes."""
import json
from datetime import datetime,timezone
from io import BytesIO
from urllib.parse import urlparse, parse_qs
import pytest
from fastapi.testclient import TestClient
from stormwatch.radar import (RADAR_METADATA, REGIONS, ALLOWED_OFFSETS,
                              radar_metadata, radar_image_url, validate_radar_png)
from stormwatch import main

NOW=datetime(2026,10,14,20,0,tzinfo=timezone.utc)
END=int(datetime(2026,10,14,19,55,tzinfo=timezone.utc).timestamp()*1000)
START=END-2*3600*1000
META=json.dumps({'timeInfo':{'startTimeField':'idp_validtime','endTimeField':'idp_validendtime','timeExtent':[START,END]},'name':'radar/radar_base_reflectivity_time'}).encode()
# A complete minimal valid PNG (IHDR 1x1 and IDAT), not a meteorological image.
import base64
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qK0AAAAASUVORK5CYII=')


def test_radar_window_and_no_fabricated_observation():
    data=radar_metadata(META,NOW)
    assert data['quality']=='AVAILABLE'
    assert data['end_ms']==END
    assert 'coverage_window_end_utc' in data
    assert 'observed_utc' not in data
    assert 'verified pixel acquisition' in data['note']

@pytest.mark.parametrize('offset',[0,15,30,45,60,90,120])
def test_allowlisted_noaa_radar_url(offset):
    d=radar_metadata(META,NOW)
    url,sample=radar_image_url('gulf',offset,d)
    assert url.startswith('https://mapservices.weather.noaa.gov/')
    assert 'bboxSR=4326' in url
    assert 'imageSR=4326' in url
    assert 'format=png32' in url
    assert 'f=image' in url
    assert 'adjustAspectRatio=false' in url
    assert sample==END-offset*60000

@pytest.mark.parametrize('region,offset',[('bad',0),('gulf',20),('gulf',180)])
def test_disallow_bad_region_or_time(region,offset):
    with pytest.raises(ValueError):radar_image_url(region,offset,radar_metadata(META,NOW))

def test_bad_metadata_and_stale_quality():
    with pytest.raises(ValueError):radar_metadata(b'{}',NOW)
    with pytest.raises(ValueError):radar_metadata(json.dumps({'timeInfo':{'timeExtent':[1,1]}}).encode(),NOW)
    assert radar_metadata(META,datetime(2026,10,14,22,0,tzinfo=timezone.utc))['quality']=='STALE'

def test_validate_radar_image():
    validate_radar_png(PNG)
    with pytest.raises(ValueError):validate_radar_png(b'<html>error</html>')

def test_radar_api_metadata_and_image_mock(monkeypatch):
    async def fake_fetch(url,ttl,max_bytes):
        if url==RADAR_METADATA:return META
        assert '/exportImage?' in url
        return PNG
    monkeypatch.setattr(main.provider,'fetch',fake_fetch)
    main.provider.health[RADAR_METADATA]={'quality':'AVAILABLE'}
    with TestClient(main.app) as client:
        resp=client.get('/api/radar/status');assert resp.status_code==200
        result=resp.json()
        assert set(result['regions'])==set(REGIONS)
        assert set(result['available_offsets_minutes'])==set(ALLOWED_OFFSETS)
        image=client.get('/api/radar/image?region=gulf&minutes_ago=15')
        assert image.status_code==200
        assert image.headers['content-type'].startswith('image/png')
        assert image.content==PNG
        assert 'x-stormwatch-requested-utc' in image.headers
        assert client.get('/api/radar/image?region=evil').status_code==400
        assert client.get('/api/radar/image?minutes_ago=-1').status_code==400

def test_unavailable_returns_status_not_fake_png(monkeypatch):
    async def offline(url,ttl,max_bytes):raise RuntimeError('internet offline')
    monkeypatch.setattr(main.provider,'fetch',offline)
    with TestClient(main.app) as client:
        status=client.get('/api/radar/status')
        assert status.json()['quality']=='UNAVAILABLE'
        response=client.get('/api/radar/image')
        assert response.status_code==503
        assert 'image/png' not in response.headers['content-type']

def test_recon_status_offline_and_dated_bulletin(monkeypatch):
    from pathlib import Path
    fixture=Path(main.DATA/'fixtures'/'hdob_usaf_20260910.txt').read_text()
    async def bulletin(url,ttl,max_bytes):return ('<pre>'+fixture+'</pre>').encode()
    monkeypatch.setattr(main.provider,'fetch',bulletin)
    with TestClient(main.app) as client:
        d=client.get('/api/recon/status').json()
        assert d['quality']=='ARCHIVED'
        assert d['point_count']>0
        assert d['last_observation_utc'].startswith('2026-09-10')
        assert 'not a live' in d['note']
        raw=client.get('/api/recon/latest').json()
        assert raw['quality']=='ARCHIVED'
        assert raw['source_kind']=='NHC HDOB'

@pytest.mark.parametrize('region',list(REGIONS))
def test_each_radar_region_retains_geographic_footprint(region):
    """Regression: ArcGIS default adjusted bbox caused radar rain to shift into wrong towns."""
    url,_=radar_image_url(region,0,radar_metadata(META,NOW))
    params=parse_qs(urlparse(url).query)
    bbox=[float(x) for x in params['bbox'][0].split(',')]
    assert bbox==REGIONS[region]['bbox']
    assert params['adjustAspectRatio']==['false']
    assert params['imageSR']==['4326'] and params['bboxSR']==['4326']
    width,height=map(int,params['size'][0].split(','))
    assert height==480
    # The image aspect ratio matches the world-coordinate rectangle to <1px.
    actual_aspect=width/height
    footprint_aspect=(bbox[2]-bbox[0])/(bbox[3]-bbox[1])
    assert abs(actual_aspect-footprint_aspect)<1/height


def test_radar_api_returns_explicit_projection_and_boundaries(monkeypatch):
    async def fake_fetch(url,ttl,max_bytes):
        if url==RADAR_METADATA:return META
        assert 'adjustAspectRatio=false' in url
        return PNG
    monkeypatch.setattr(main.provider,'fetch',fake_fetch)
    main.provider.health[RADAR_METADATA]={'quality':'AVAILABLE'}
    with TestClient(main.app) as client:
        r=client.get('/api/radar/image?region=southeast')
    assert r.status_code==200
    assert r.headers['x-stormwatch-projection']=='EPSG:4326; adjustAspectRatio=false'
    assert r.headers['x-stormwatch-region-bounds']==','.join(str(x) for x in REGIONS['southeast']['bbox'])


def test_radar_display_disables_stale_without_synthetic_fallback():
    from pathlib import Path
    js=(Path(__file__).resolve().parents[1]/'apps/web/dist/app.js').read_text()
    assert "if(data.quality==='STALE')" in js
    assert 'STALE · HIDDEN' in js
    assert "['AVAILABLE','DELAYED'].includes(state.radar?.quality)" in js
    assert 'adjustAspectRatio' in (Path(__file__).resolve().parents[1]/'apps/api/stormwatch/radar.py').read_text()


def test_source_triangle_renderer_crops_bitmap_for_performance():
    from pathlib import Path
    js=(Path(__file__).resolve().parents[1]/'apps/web/dist/app.js').read_text()
    assert 'ctx.drawImage(img,x0,y0,x1-x0,y1-y0,x0,y0,x1-x0,y1-y0)' in js
    assert 'ctx.drawImage(img,0,0);ctx.restore()' not in js
