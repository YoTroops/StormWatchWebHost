"""Official GIS metadata is used to select a layer, never fabricated imagery."""
import json
import pytest
from fastapi.testclient import TestClient
from stormwatch.satmap import choose_layer, image_url, validate_satellite_image, METADATA_URL
from stormwatch.main import app, provider

def test_discover_layer_by_source_name():
    raw=json.dumps({'layers':[{'id':2,'name':'Global Visible Imagery Mosaic'},
       {'id':8,'name':'GOES Northern Hemisphere Longwave Infrared Imagery Composite'},
       {'id':4,'name':'GOES Northern Hemisphere Water Vapor Imagery Composite'},
       {'id':0,'name':'GOES Northern Hemisphere Visible Imagery Composite'}]}).encode()
    assert choose_layer(raw,'IR')['layer_id']==8
    assert choose_layer(raw,'WATER_VAPOR')['layer_id']==4
    assert choose_layer(raw,'VISIBLE')['layer_id']==0

def test_invalid_metadata_never_guesses_layer():
    with pytest.raises(ValueError):choose_layer(b'{"layers":[]}', 'IR')
    with pytest.raises(ValueError):choose_layer(b'{"error":{"message":"blocked"}}','VISIBLE')
    with pytest.raises(ValueError):choose_layer(b'{}', 'WATER_VAPOR')
    with pytest.raises(ValueError):choose_layer(b'{"layers":[]}', 'HACK')

def test_only_fixed_export_regions():
    url=image_url(8,'gulf')
    assert 'nowcoast.noaa.gov' in url and 'bboxSR=4326' in url and 'imageSR=4326' in url
    assert 'layers=show%3A8' in url and 'f=image' in url
    with pytest.raises(ValueError):image_url(2,'../../etc/passwd')
    with pytest.raises(ValueError):image_url(-1,'gulf')

def test_reject_fake_png():
    with pytest.raises(ValueError):validate_satellite_image(b'not-a-real-image')

@pytest.mark.asyncio
async def test_map_status_unavailable_not_simulated(monkeypatch):
    async def broken(*args, **kwargs):raise RuntimeError('offline')
    monkeypatch.setattr(provider,'fetch',broken)
    with TestClient(app) as client:
        bad=client.get('/api/satellite/map/status?channel=bogus')
        assert bad.status_code==400
        d=client.get('/api/satellite/map/status?channel=IR')
        assert d.status_code==200 and d.json()['quality']=='UNAVAILABLE'
        img=client.get('/api/satellite/map/image?channel=IR&region=gulf')
        assert img.status_code==503
        invalid=client.get('/api/satellite/map/image?channel=IR&region=moon')
        assert invalid.status_code==400
