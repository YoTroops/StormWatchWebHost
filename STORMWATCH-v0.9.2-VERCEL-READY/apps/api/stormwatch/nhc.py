"""NHC real-time adapter; bounded HTTPS, TTL cache, and GIS KMZ parsing."""
import asyncio
import io
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from datetime import datetime, timezone
from typing import Any
import httpx
from .science import hurricane_category, freshness, utc
from .models import AID_ROOT

STORMS_URL = 'https://www.nhc.noaa.gov/CurrentStorms.json'
from .aircraft import AIRCRAFT_URL, CALLSIGN_ROOT
HDOB_URLS = {
  'USAF Atlantic': 'https://www.nhc.noaa.gov/text/URNT15-USAF.shtml',
  'NOAA Atlantic': 'https://www.nhc.noaa.gov/text/URNT15-NOAA.shtml',
  'USAF Pacific': 'https://www.nhc.noaa.gov/text/URPN15-USAF.shtml',
}

class Provider:
    def __init__(self):
        self.cache: dict[str,tuple[float,Any]]={}
        self.health: dict[str,dict]={}
        self.lock = asyncio.Lock()

    async def fetch(self, url: str, ttl: int, max_bytes: int = 12_000_000) -> bytes:
        host = urlsplit(url)
        if host.scheme!='https' or not (
            (host.hostname == 'api.adsb.lol' and (url == AIRCRAFT_URL or
              (host.path.startswith('/v2/callsign/TEAL') and re.fullmatch(r'/v2/callsign/TEAL[0-9]{1,3}',host.path) and not host.query))) or
            (host.hostname == 'www.nhc.noaa.gov') or
            (host.hostname == 'ftp.nhc.noaa.gov' and re.fullmatch(r'/atcf/aid_public/a(?:al|ep|cp)\d{2}20\d{2}\.dat\.gz',host.path) and not host.query) or
            (host.hostname == 'nowcoast.noaa.gov' and
             host.path in ('/arcgis/rest/services/nowcoast/sat_meteo_imagery_time/MapServer',
                           '/arcgis/rest/services/nowcoast/sat_meteo_imagery_time/MapServer/export') and
             (host.query == 'f=pjson' or (host.path.endswith('/export') and
               'f=image' in host.query and 'bboxSR=4326' in host.query and 'imageSR=4326' in host.query))) or
            (host.hostname == 'mapservices.weather.noaa.gov' and
             host.path in ('/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer',
                           '/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer/exportImage') and
             (host.query == 'f=pjson' or (host.path.endswith('/exportImage') and
              'f=image' in host.query and 'bboxSR=4326' in host.query))) or
            (host.hostname == 'www.star.nesdis.noaa.gov' and host.path == '/GOES/conus.php' and host.query == 'sat=G19')
        ):
            raise ValueError('Unapproved data provider')
        existing=self.cache.get(url)
        if existing and time.monotonic()-existing[0]<ttl: return existing[1]
        async with self.lock:
            existing=self.cache.get(url)
            if existing and time.monotonic()-existing[0]<ttl: return existing[1]
            try:
                last_error = None
                for attempt in range(3):
                    try:
                        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0),follow_redirects=False,
                            headers={'User-Agent':'STORMWATCH/0.8 (educational NOAA/NHC/NESDIS and ADSB.lol local client)'}) as client:
                            async with client.stream('GET',url) as response:
                                response.raise_for_status()
                                chunks=[];size=0
                                async for chunk in response.aiter_bytes():
                                    size+=len(chunk)
                                    if size>max_bytes: raise ValueError('Provider payload too large')
                                    chunks.append(chunk)
                        data=b''.join(chunks)
                        self.cache[url]=(time.monotonic(),data)
                        # AVAILABLE refers only to successful transport, not fresh observed weather.
                        self.health[url]={'quality':'AVAILABLE','last_success_utc':datetime.now(timezone.utc).isoformat(),'error':None}
                        return data
                    except httpx.HTTPStatusError as exc:
                        last_error=exc
                        if exc.response.status_code not in (429,500,502,503,504) or attempt==2:
                            break
                        await asyncio.sleep(.5 * 2**attempt)
                    except (httpx.ConnectError,httpx.TimeoutException) as exc:
                        last_error=exc
                        # DNS outages should fail promptly; retry slow/temporary timeouts only.
                        if isinstance(exc,httpx.ConnectError) or attempt==2:
                            break
                        await asyncio.sleep(.5 * 2**attempt)
                    except Exception as exc:
                        last_error=exc
                        break
                if last_error is not None: raise last_error
                raise RuntimeError('Data provider yielded no result')
            except Exception as exc:
                self.health[url]={'quality':'STALE' if existing else 'UNAVAILABLE',
                                  'last_success_utc':self.health.get(url,{}).get('last_success_utc'),
                                  'error':type(exc).__name__ + ': ' + str(exc)[:180]}
                if existing: return existing[1]
                raise

    async def live_storms(self):
        raw=await self.fetch(STORMS_URL,300,max_bytes=1_000_000)
        payload=__import__('json').loads(raw)
        if not isinstance(payload.get('activeStorms'),list): raise ValueError('Invalid NHC response')
        storms=[]
        for item in payload['activeStorms']:
            try:
                lat=float(item['latitudeNumeric']); lon=float(item['longitudeNumeric'])
                if not (-90<=lat<=90 and -180<=lon<=180):continue
                wind=int(item['intensity']) if item.get('intensity') else None
                press=int(item['pressure']) if item.get('pressure') else None
                issue=item.get('lastUpdate'); dt=utc(issue) if issue else None
                storm={'id':item['id'].upper(), 'name':item['name'], 'basin':'Atlantic' if item['id'].lower().startswith('al') else 'Eastern Pacific',
                    'classification':item.get('classification'),'wind_kt':wind,'pressure_hpa':press,
                    'category':hurricane_category(wind),'lat':lat,'lon':lon,'motion_deg':item.get('movementDir'),
                    'motion_mph':item.get('movementSpeed'), 'time':issue,'quality':freshness(dt),
                    'provider':'NOAA/NHC','source_url':item.get('publicAdvisory',{}).get('url'),
                    'forecast_url':item.get('forecastGraphics',{}).get('url'),
                    'cone_kmz':item.get('trackCone',{}).get('kmzFile') if item.get('trackCone') else None,
                    'track_kmz':item.get('forecastTrack',{}).get('kmzFile') if item.get('forecastTrack') else None}
                storms.append(storm)
            except (KeyError,TypeError,ValueError): continue
        return storms


def parse_kmz(data: bytes) -> dict:
    if len(data)>6_000_000: raise ValueError('KMZ too large')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        members=[x for x in z.infolist() if x.filename.lower().endswith('.kml')]
        if not members: raise ValueError('Missing KML')
        member=members[0]
        if member.file_size>8_000_000:raise ValueError('Expanded KML too large')
        xml=z.read(member)
    root=ET.fromstring(xml)
    features=[]
    for place in root.iter():
        if place.tag.split('}')[-1]!='Placemark':continue
        name=next((x.text for x in place if x.tag.split('}')[-1]=='name'),None)
        for geo in place.iter():
            kind=geo.tag.split('}')[-1]
            if kind not in ('Point','LineString','Polygon'):continue
            coords=[]
            for node in geo.iter():
                if node.tag.split('}')[-1]!='coordinates' or not node.text:continue
                for pair in node.text.strip().split():
                    parts=pair.split(',')
                    if len(parts)<2:continue
                    try:
                        lon,lat=map(float,parts[:2])
                        if -180<=lon<=180 and -90<=lat<=90:coords.append([lon,lat])
                    except ValueError: pass
            if not coords or len(coords)>12000:continue
            if kind=='Point': geometry={'type':'Point','coordinates':coords[0]}
            elif kind=='LineString':geometry={'type':'LineString','coordinates':coords}
            else:
                if coords[0]!=coords[-1]:coords.append(coords[0])
                geometry={'type':'Polygon','coordinates':[coords]}
            features.append({'type':'Feature','properties':{'name':name,'source':'NHC advisory forecast', 'data_kind':'FORECAST'}, 'geometry':geometry})
    return {'type':'FeatureCollection','features':features[:400]}
