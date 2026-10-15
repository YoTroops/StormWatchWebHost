"""Offline tests using NOAA-shaped metadata, not claims of a live NOAA response."""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from stormwatch.satellite import parse_satellite_page, parse_image_time, SATELLITE_PAGE
from stormwatch.nhc import STORMS_URL
from stormwatch import main

IMAGE = 'https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/GEOCOLOR/20262871440_GOES19-ABI-CONUS-GEOCOLOR-1250x750.jpg'
IR_IMAGE = 'https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/13/20262871440_GOES19-ABI-CONUS-13-1250x750.jpg'
WV_IMAGE = 'https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/08/20262871440_GOES19-ABI-CONUS-08-1250x750.jpg'
HTML = '<html><body>'+''.join(f'<a href="{u}">1250 x 750 px</a>' for u in (IMAGE,IR_IMAGE,WV_IMAGE))+'</body></html>'
OBS = datetime(2026,10,14,14,40,tzinfo=timezone.utc)


def test_goes_filename_utc():
    assert parse_image_time(IMAGE)==OBS
    for value in ('https://host/20263671440_GOES19-ABI-CONUS-x',
                  'https://host/20262872599_GOES19-ABI-CONUS-x',
                  'https://host/no-time.jpg'):
        with pytest.raises(ValueError): parse_image_time(value)


@pytest.mark.parametrize('channel,product', [('GEOCOLOR','GEOCOLOR'),('IR','13'),('WATER_VAPOR','08')])
def test_goes_channel_metadata(channel,product):
    response=parse_satellite_page(HTML,channel,OBS)
    assert response['channel']==channel
    assert f'/CONUS/{product}/' in response['image_url']
    assert response['observed_utc']=='2026-10-14T14:40:00Z'
    assert response['quality']=='LIVE'


def test_goes_stale_and_no_invented_image():
    response=parse_satellite_page(HTML,'GEOCOLOR',datetime(2026,10,14,17,40,tzinfo=timezone.utc))
    assert response['quality']=='STALE'
    with pytest.raises(ValueError,match='No timestamped'):
        parse_satellite_page('<a href="https://evil.example/GOES19/ABI/CONUS/GEOCOLOR/20262871440_GOES19-ABI-CONUS-GEOCOLOR-1250x750.jpg">fake</a>','GEOCOLOR',OBS)
    with pytest.raises(ValueError,match='Unsupported'): parse_satellite_page(HTML,'INVALID',OBS)


def test_satellite_api_offline_mock(monkeypatch):
    async def fake_fetch(url, ttl, max_bytes):
        assert url==SATELLITE_PAGE
        return HTML.encode()
    monkeypatch.setattr(main.provider,'fetch',fake_fetch)
    main.provider.health[SATELLITE_PAGE]={'quality':'AVAILABLE'}
    response=TestClient(main.app).get('/api/satellite/latest?channel=IR')
    assert response.status_code==200
    data=response.json()
    assert data['channel']=='IR'
    assert data['source_url']==SATELLITE_PAGE
    assert 'observed_utc' in data
    invalid=TestClient(main.app).get('/api/satellite/latest?channel=UNTRUSTED')
    assert invalid.status_code==400


def test_satellite_api_unavailable(monkeypatch):
    async def offline(url, ttl, max_bytes):
        raise RuntimeError('offline')
    monkeypatch.setattr(main.provider,'fetch',offline)
    response=TestClient(main.app).get('/api/satellite/latest')
    assert response.status_code==200
    assert response.json()['quality']=='UNAVAILABLE'
    assert 'image_url' not in response.json()


@pytest.mark.asyncio
async def test_scheduled_poller_notifies_new_data(monkeypatch):
    async def storms(): return [{'id':'AL012026','time':'2026-10-14T14:00:00Z','lat':27.,'lon':-80.}]
    async def fetch(url,ttl,max_bytes):
        from stormwatch.radar import RADAR_METADATA
        if url.endswith('URNT15-USAF.shtml'):
            return '<pre>NOT ISSUED</pre>'.encode()
        if url==RADAR_METADATA:
            return __import__('json').dumps({'timeInfo':{'timeExtent':[1770000000000,1792000000000]}}).encode()
        return HTML.encode()
    monkeypatch.setattr(main.provider,'live_storms',storms)
    monkeypatch.setattr(main.provider,'fetch',fetch)
    main.provider.health[STORMS_URL]={'quality':'AVAILABLE'}
    main.provider.health[SATELLITE_PAGE]={'quality':'AVAILABLE'}
    q=__import__('asyncio').Queue(maxsize=8)
    main.subscribers.add(q)
    try:
        main.poll_state['NHC']=None
        main.poll_state['SATELLITE']=None
        main.poll_state['RADAR']=None
        main.poll_state['RECON']=None
        main.poll_state['AIRCRAFT']=None
        await main._poll_once()
        events=[q.get_nowait(),q.get_nowait(),q.get_nowait(),q.get_nowait(),q.get_nowait()]
        assert {e['source'] for e in events}=={'NHC','SATELLITE','RADAR','RECON','AIRCRAFT'}
        await main._poll_once()
        assert q.empty() # unchanged data should not generate duplicate change alerts
    finally:
        main.subscribers.discard(q)
