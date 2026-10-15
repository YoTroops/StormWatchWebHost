from fastapi.testclient import TestClient
from stormwatch.main import app

client=TestClient(app)

def test_health():
 r=client.get('/api/health');assert r.status_code==200 and r.json()['service']=='STORMWATCH'

def test_page():
 r=client.get('/');assert r.status_code==200 and 'STORMWATCH' in r.text

def test_storm_fixture():
 r=client.get('/api/storms/historical');assert r.status_code==200
 assert any(s['name']=='MILTON' and s['dataset']=='SELECTED_ADVISORY_SNAPSHOTS' for s in r.json()['storms'])
 r=client.get('/api/storms/historical/AL142024');assert len(r.json()['points'])==10

def test_recon_fixture_api():
 r=client.get('/api/recon/fixture');assert r.status_code==200 and len(r.json()['points'])==20

def test_no_fake_storm():
 r=client.get('/api/storms/historical/AL999999');assert r.status_code==404

def test_uas_upload():
 valid=b'time,lat,lon,wind_kt\n2024-10-10T00:00:00Z,25,-80,30\n'
 r=client.post('/api/uas/upload',files={'file':('flight.csv',valid,'text/csv')})
 assert r.status_code==200 and r.json()['points'][0]['wind_kt']==30
 assert r.json()['quality']=='USER_SUPPLIED'

def test_uas_bad_data():
 bad=b'time,lat,lon\n2024-10-10T00:00:00Z,195,-80\n'
 r=client.post('/api/uas/upload',files={'file':('bad.csv',bad,'text/csv')})
 assert r.status_code==422
