import io
import zipfile
import pytest
from stormwatch.nhc import parse_kmz,Provider

KML=b'''<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>Forecast cone</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-90,20 -89,20 -89,21 -90,20</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark><Placemark><name>forecast track</name><LineString><coordinates>-90,20 -89,21</coordinates></LineString></Placemark></Document></kml>'''

def test_cone_parser():
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as f:f.writestr('doc.kml',KML)
 obj=parse_kmz(b.getvalue())
 assert len(obj['features'])==2
 assert obj['features'][0]['geometry']['type']=='Polygon'
 assert obj['features'][1]['properties']['data_kind']=='FORECAST'

def test_bad_kmz():
 with pytest.raises(zipfile.BadZipFile):parse_kmz(b'not a zip')

@pytest.mark.asyncio
async def test_reject_unapproved_provider():
 p=Provider()
 with pytest.raises(ValueError):await p.fetch('https://example.org/anything',60)

@pytest.mark.asyncio
async def test_active_schema_and_movement_units():
 import json
 p=Provider()
 async def fake_fetch(url,ttl,max_bytes=0):
  return json.dumps({'activeStorms':[{'id':'ep212026','name':'Trudy','classification':'TS',
    'intensity':'50','pressure':'998','latitudeNumeric':11.5,'longitudeNumeric':-99.5,
    'movementDir':290,'movementSpeed':13,'lastUpdate':'2026-10-14T15:00:00.000Z',
    'publicAdvisory':{'url':'https://www.nhc.noaa.gov/text/MIATCPEP1.shtml'}}]}).encode()
 p.fetch=fake_fetch
 storms=await p.live_storms()
 assert len(storms)==1 and storms[0]['wind_kt']==50 and storms[0]['motion_mph']==13
 assert storms[0]['lon']==-99.5
