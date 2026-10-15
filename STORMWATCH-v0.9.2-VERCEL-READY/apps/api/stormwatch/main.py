"""STORMWATCH local backend. Provider failures never masquerade as observations."""
import asyncio
import csv
import io
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup
from .nhc import Provider, STORMS_URL, HDOB_URLS, parse_kmz
from .hurdat import HURDAT_SOURCES, SHOWCASE_IDS, parse_hurdat, load_fixture
from .recon import parse_hdob
from .aircraft import AIRCRAFT_URL, CALLSIGN_ROOT, REGISTRY, parse_aircraft_response
from .satellite import SATELLITE_PAGE, CHANNELS, parse_satellite_page
from .satmap import METADATA_URL as SAT_MAP_METADATA, choose_layer, image_url as satmap_image_url, validate_satellite_image
from .radar import RADAR_METADATA, REGIONS, ALLOWED_OFFSETS, radar_metadata, radar_image_url, validate_radar_png
from .models import deck_url, decode_deck, parse_atcf, assemble, unavailable_catalog

ROOT = Path(__file__).resolve().parents[3]
DIST = ROOT / 'apps' / 'web' / 'dist'
DATA = ROOT / 'data'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger('stormwatch')
provider=Provider()
archive_memory={}
uas_memory={}
subscribers=set()
poll_state={'running':False,'interval_seconds':300,'last_cycle_utc':None,'NHC':None,'SATELLITE':None,'RADAR':None,'RECON':None,'AIRCRAFT':None}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


async def _notify_change(source, signature, availability):
    previous=poll_state.get(source) or {}
    changed=previous.get('signature') != signature or previous.get('availability') != availability
    poll_state[source]={'signature':signature,'availability':availability,'checked_utc':_utc_now()}
    if changed:
        event={'event':'source_update','source':source,'availability':availability,'checked_utc':_utc_now()}
        for queue in tuple(subscribers):
            if queue.full():
                try:queue.get_nowait()
                except asyncio.QueueEmpty:pass
            queue.put_nowait(event)


async def _poll_once():
    # Cached HTTPS fetches and bounded requests; provider failures never block the globe.
    try:
        storms=await provider.live_storms()
        health=provider.health.get(STORMS_URL,{})
        quality='STALE' if health.get('quality')=='STALE' else 'AVAILABLE'
        signature=tuple(sorted((s['id'],s['time'],s['lat'],s['lon']) for s in storms))
        await _notify_change('NHC',signature,quality)
    except Exception as exc:
        log.warning('Scheduled NHC refresh unavailable: %s',type(exc).__name__)
        await _notify_change('NHC',None,'UNAVAILABLE')
    try:
        raw=await provider.fetch(SATELLITE_PAGE,300,max_bytes=1_500_000)
        image=parse_satellite_page(raw.decode('utf-8','replace'),'GEOCOLOR')
        health=provider.health.get(SATELLITE_PAGE,{})
        quality='STALE' if health.get('quality')=='STALE' else image['quality']
        await _notify_change('SATELLITE',image['observed_utc'],quality)
    except Exception as exc:
        log.warning('Scheduled GOES refresh unavailable: %s',type(exc).__name__)
        await _notify_change('SATELLITE',None,'UNAVAILABLE')
    try:
        metadata=radar_metadata(await provider.fetch(RADAR_METADATA,300,max_bytes=250_000))
        quality='STALE' if provider.health.get(RADAR_METADATA,{}).get('quality')=='STALE' else metadata['quality']
        await _notify_change('RADAR',metadata['end_ms'],quality)
    except Exception as exc:
        log.warning('Scheduled NWS radar metadata refresh unavailable: %s',type(exc).__name__)
        await _notify_change('RADAR',None,'UNAVAILABLE')
    try:
        latest=await _latest_recon('USAF Atlantic')
        signature=(latest['mission'],latest['points'][-1]['time'])
        await _notify_change('RECON',signature,latest['quality'])
    except Exception as exc:
        log.debug('No recent public HDOB: %s',type(exc).__name__)
        await _notify_change('RECON',None,'UNAVAILABLE')
    try:
        response=await _noaa_aircraft()
        fingerprint=tuple((x['registration'],x['observed_utc'],x['lat'],x['lon']) for x in response['aircraft'])
        await _notify_change('AIRCRAFT',fingerprint,response['quality'])
    except Exception as exc:
        log.debug('No ADS-B position updates: %s',type(exc).__name__)
        await _notify_change('AIRCRAFT',None,'UNAVAILABLE')
    poll_state['last_cycle_utc']=_utc_now()


async def _background_poll():
    poll_state['running']=True
    try:
        while True:
            await _poll_once()
            await asyncio.sleep(poll_state['interval_seconds'])
    finally:
        poll_state['running']=False

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('STORMWATCH startup; static files %s', DIST)
    task=None
    if os.getenv('STORMWATCH_BACKGROUND_POLL','0' if os.getenv('VERCEL') else '1') != '0':
        poll_state['interval_seconds']=max(120,min(1800,int(os.getenv('STORMWATCH_POLL_SECONDS','300'))))
        task=asyncio.create_task(_background_poll())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass

app = FastAPI(title='STORMWATCH API', version='0.9.2', lifespan=lifespan,
              description='Research visualization only. Refer to official NHC/NWS advisories for decisions.')

@app.get('/api/health')
async def health():
    return {'service':'STORMWATCH','status':'ok','utc':datetime.now(timezone.utc).isoformat(),
      'network_probe':'not performed','version':'0.9.2','providers':provider.health,'poller':poll_state,'websocket_listeners':len(subscribers)}

@app.get('/api/storms/live')
async def live():
    try:
        items=await provider.live_storms()
        if provider.health.get(STORMS_URL,{}).get('quality')=='STALE':
            items=[{**row,'quality':'STALE'} for row in items]
        return {'mode':'LIVE','provider':'NOAA/NHC','source_url':STORMS_URL,'storms':items,'availability':'STALE' if provider.health.get(STORMS_URL,{}).get('quality')=='STALE' else 'AVAILABLE',
            'checked_utc':datetime.now(timezone.utc).isoformat(), 'note':'LIVE quality is based on the official observation timestamp, not polling time.'}
    except Exception as e:
        log.warning('NHC live unavailable: %s',e)
        return {'mode':'LIVE','provider':'NOAA/NHC','source_url':STORMS_URL,'storms':[],
                'availability':'UNAVAILABLE','checked_utc':datetime.now(timezone.utc).isoformat(),
                'error':f'{type(e).__name__}: {str(e)[:160]}',
                'note':'Unable to check NHC; zero results DOES NOT mean zero active storms.'}

@app.get('/api/satellite/latest')
async def satellite_latest(channel: str=Query('GEOCOLOR')):
    if channel not in CHANNELS:
        raise HTTPException(400,'Unknown satellite channel. Use GEOCOLOR, IR, or WATER_VAPOR.')
    try:
        raw=await provider.fetch(SATELLITE_PAGE,300,max_bytes=1_500_000)
        obj=parse_satellite_page(raw.decode('utf-8','replace'),channel)
        if provider.health.get(SATELLITE_PAGE,{}).get('quality')=='STALE':
            obj['quality']='STALE'
            obj['note']+=' Satellite page fetch failed: using cached metadata, not confirmed current.'
        obj['checked_utc']=_utc_now()
        return obj
    except Exception as exc:
        log.warning('NOAA GOES imagery unavailable: %s',exc)
        return {'availability':'UNAVAILABLE','quality':'UNAVAILABLE', 'channel':channel,
                'checked_utc':_utc_now(), 'source_url':SATELLITE_PAGE,
                'error':f'{type(exc).__name__}: {str(exc)[:160]}',
                'note':'GOES source unavailable. Do not infer weather conditions from a missing image.'}


@app.get('/api/satellite/map/status')
async def satellite_map_status(channel: str=Query('IR')):
    if channel not in ('VISIBLE','IR','WATER_VAPOR'):
        raise HTTPException(400,'Invalid mapped satellite channel')
    try:
        layer = choose_layer(await provider.fetch(SAT_MAP_METADATA,300,max_bytes=2_500_000),channel)
        layer['quality'] = 'STALE' if provider.health.get(SAT_MAP_METADATA,{}).get('quality')=='STALE' else 'AVAILABLE'
        layer['checked_utc'] = _utc_now()
        layer['regions'] = list(REGIONS)
        return layer
    except Exception as exc:
        return {'quality':'UNAVAILABLE','channel':channel,'checked_utc':_utc_now(),
                'source_url':SAT_MAP_METADATA,'error':type(exc).__name__+': '+str(exc)[:130],
                'note':'NOAA nowCOAST map layer unavailable; no simulated satellite image.'}

@app.get('/api/satellite/map/image')
async def satellite_map_image(channel: str=Query('IR'),region: str=Query('gulf')):
    if channel not in ('VISIBLE','IR','WATER_VAPOR') or region not in REGIONS:
        raise HTTPException(400,'Invalid mapped satellite channel or region')
    try:
        layer = choose_layer(await provider.fetch(SAT_MAP_METADATA,300,max_bytes=2_500_000),channel)
        raw = await provider.fetch(satmap_image_url(layer['layer_id'],region),300,max_bytes=6_000_000)
        validate_satellite_image(raw)
        return Response(raw,media_type='image/png',headers={
            'Cache-Control':'private, max-age=180','X-Content-Type-Options':'nosniff',
            'X-STORMWATCH-Source':'NOAA nowCOAST projected satellite map (EPSG:4326)',
            'X-STORMWATCH-Acquisition-Time':'NOT VERIFIED'})
    except Exception as exc:
        log.warning('Mapped satellite image unavailable: %s',type(exc).__name__)
        raise HTTPException(503,'NOAA satellite map imagery unavailable: '+type(exc).__name__)


async def _radar_metadata():
    raw=await provider.fetch(RADAR_METADATA,300,max_bytes=250_000)
    result=radar_metadata(raw)
    if provider.health.get(RADAR_METADATA,{}).get('quality')=='STALE':
        result['quality']='STALE'
        result['note']+=' Service metadata was served from cache after a failed refresh.'
    return result

@app.get('/api/radar/status')
async def radar_status():
    try:
        result=await _radar_metadata()
        return {**result, 'regions':REGIONS, 'available_offsets_minutes':ALLOWED_OFFSETS,
                'checked_utc':_utc_now()}
    except Exception as exc:
        return {'quality':'UNAVAILABLE','provider':'NOAA/NWS MRMS',
                'source_url':RADAR_METADATA, 'regions':REGIONS,'checked_utc':_utc_now(),
                'error':type(exc).__name__ + ': '+str(exc)[:150],
                'note':'No radar data verified. No simulated radar is shown.'}

@app.get('/api/radar/image')
async def radar_image(region: str=Query('gulf'), minutes_ago: int=Query(0)):
    if region not in REGIONS or minutes_ago not in ALLOWED_OFFSETS:
        raise HTTPException(400,'Invalid radar region or time offset')
    try:
        status=await _radar_metadata()
        if status['quality']=='UNAVAILABLE':raise ValueError('Radar metadata has invalid future time')
        url,requested=radar_image_url(region,minutes_ago,status)
        raw=await provider.fetch(url,240,max_bytes=5_000_000)
        validate_radar_png(raw)
        return Response(raw,media_type='image/png',headers={
            'Cache-Control':'private, max-age=120',
            'X-STORMWATCH-Requested-UTC':datetime.fromtimestamp(requested/1000,timezone.utc).isoformat(),
            'X-STORMWATCH-Source':'NOAA-NWS-MRMS',
            'X-STORMWATCH-Projection':'EPSG:4326; adjustAspectRatio=false',
            'X-STORMWATCH-Region-Bounds':','.join(str(x) for x in REGIONS[region]['bbox']),
            'X-Content-Type-Options':'nosniff'})
    except Exception as exc:
        log.warning('Radar image fetch failed: %s',type(exc).__name__)
        raise HTTPException(503,'Official radar image unavailable: '+type(exc).__name__)

async def _noaa_aircraft():
    """NOAA registration lookup. No inferred mission status or flight paths."""
    raw=await provider.fetch(AIRCRAFT_URL,300,max_bytes=500_000)
    records=parse_aircraft_response(json.loads(raw))
    quality='STALE' if provider.health.get(AIRCRAFT_URL,{}).get('quality')=='STALE' else 'AVAILABLE'
    # If the cached source could not be verified, do not label sightings LIVE.
    if quality=='STALE':
        records=[{**item,'quality':'STALE'} for item in records]
    return {'quality':quality,'source':'ADSB.lol','source_url':'https://www.adsb.lol/docs/open-data/api/',
      'license':'ODbL 1.0','checked_utc':_utc_now(), 'aircraft':records,
      'tracked_registrations':list(REGISTRY),
      'note':'Public ADS-B sightings only. No sighting does not mean no flight. Location does not verify a hurricane mission.'}

@app.get('/api/aircraft/noaa')
async def aircraft_noaa():
    try:
        return await _noaa_aircraft()
    except Exception as exc:
        log.warning('NOAA airframe ADS-B feed unavailable: %s',type(exc).__name__)
        return {'quality':'UNAVAILABLE','aircraft':[], 'tracked_registrations':list(REGISTRY),
          'checked_utc':_utc_now(),'source':'ADSB.lol',
          'error':type(exc).__name__+': '+str(exc)[:120],
          'note':'Aircraft data unavailable; this does not mean the aircraft are not flying.'}

@app.get('/api/aircraft/teal')
async def aircraft_teal(callsign: str=Query(...,min_length=5,max_length=7)):
    """Manual USAF TEAL callsign lookup. It is not a verified mission roster."""
    code=callsign.strip().upper()
    if not re.fullmatch(r'TEAL[0-9]{1,3}',code):
        raise HTTPException(400,'Enter an exact TEAL callsign, e.g. TEAL21.')
    try:
        raw=await provider.fetch(CALLSIGN_ROOT+code,300,max_bytes=500_000)
        records=parse_aircraft_response(json.loads(raw),filter_registration=False)
        records=[{**row,'mission_status':'NOT VERIFIED', 'identity_verified':False,
                  'name':'USAF callsign candidate (unconfirmed)',
                  'quality':'STALE' if provider.health.get(CALLSIGN_ROOT+code,{}).get('quality')=='STALE' else row['quality']}
                 for row in records if row['callsign']==code]
        return {'quality':'AVAILABLE','callsign':code,'aircraft':records,'checked_utc':_utc_now(),
          'note':'TEAL is an associated callsign family, not evidence of an active hurricane mission. Identity and tasking UNVERIFIED.'}
    except Exception as exc:
        return {'quality':'UNAVAILABLE','callsign':code,'aircraft':[], 'checked_utc':_utc_now(),
                'error':type(exc).__name__+': '+str(exc)[:120]}

@app.get('/api/models/{storm_id}')
async def forecast_models(storm_id:str, cycle:str|None=Query(None,max_length=20)):
    """NHC ATCF guidance; never substitute forecast images or inferred AI positions."""
    try: url=deck_url(storm_id)
    except ValueError: raise HTTPException(400,'Invalid tropical cyclone identifier')
    # Only offer forecasts of systems confirmed active by the current NHC feed.
    try:
        storms=await provider.live_storms()
        if not any(item['id']==storm_id.upper() for item in storms):
            raise HTTPException(404,'System is not currently in the NHC active-storm feed')
    except HTTPException: raise
    except Exception as exc:
        return {'storm_id':storm_id.upper(),'source_url':url,'quality':'UNAVAILABLE','checked_utc':_utc_now(),
                'error':'Current active-storm status could not be confirmed: '+type(exc).__name__,
                **unavailable_catalog('Active-storm feed unavailable. Model guidance cannot be verified.')}
    try:
        data=await provider.fetch(url,300,max_bytes=5_000_000)
        parsed=parse_atcf(decode_deck(data),storm_id)
        try: product=assemble(parsed,cycle)
        except ValueError:raise HTTPException(400,'Requested forecast cycle is not in this public deck')
        quality='STALE' if product['cycle_age_hours'] is not None and product['cycle_age_hours']>24 or provider.health.get(url,{}).get('quality')=='STALE' else ('AVAILABLE' if product['available_models'] else 'UNAVAILABLE')
        return {'storm_id':storm_id.upper(), 'source_url':url, 'quality':quality,
                'checked_utc':_utc_now(), 'provider':'NHC public ATCF forecast-aid A-deck',**product}
    except HTTPException:raise
    except Exception as exc:
        log.warning('ATCF forecast guidance unavailable: %s',type(exc).__name__)
        return {'storm_id':storm_id.upper(),'source_url':url,'quality':'UNAVAILABLE','checked_utc':_utc_now(),
                'error':type(exc).__name__+': '+str(exc)[:130],
                **unavailable_catalog('NHC public A-deck unavailable or invalid. No forecast lines shown.')}

@app.get('/api/storms/{storm_id}/forecast')
async def forecast(storm_id: str):
    if not (len(storm_id)==8 and storm_id[:2].upper() in ('AL','EP','CP') and storm_id[2:].isdigit()):
        raise HTTPException(status_code=400,detail='Invalid NHC storm ID')
    try:
        storms=await provider.live_storms()
        selected=next((s for s in storms if s['id']==storm_id.upper()),None)
        if not selected: raise HTTPException(404,'Not an active storm in the current NHC feed')
        overlay={}
        for kind in ('cone','track'):
            url=selected.get(kind+'_kmz')
            if not url: continue
            try:
                if urlsplit(url).path.startswith('/storm_graphics/api/'):
                    overlay[kind] = parse_kmz(await provider.fetch(url,900,max_bytes=6_000_000))
                else: overlay[kind]={'type':'FeatureCollection','features':[]}
            except Exception as e:
                overlay[kind]={'type':'FeatureCollection','features':[], 'error':str(e)[:160]}
        return {'storm_id':storm_id.upper(),'quality':selected['quality'],'source':'NHC official GIS KMZ',
                'forecast_issued_utc':selected['time'],'layers':overlay,
                'note':'These are NHC forecasts, not observed historical track positions.'}
    except HTTPException: raise
    except Exception as e: raise HTTPException(503,detail=f'NHC forecast unavailable: {type(e).__name__}')

async def _load_hurdat():
    # Source URLs are version-pinned; if fetch fails, fixture remains available.
    if archive_memory.get('loaded'):return
    entries=[]
    for basin,url in HURDAT_SOURCES.items():
        try:
            raw=await provider.fetch(url,86400,max_bytes=12_000_000)
            entries.extend(parse_hurdat(raw.decode('utf-8-sig'),set(SHOWCASE_IDS)))
        except Exception as e:
            log.warning('HURDAT %s unavailable: %s',basin,str(e)[:100])
    for row in entries:archive_memory[row['id']]=row
    archive_memory['loaded']=True

@app.get('/api/storms/historical')
async def historical(sync: bool=False):
    if sync: await _load_hurdat()
    fixture=load_fixture(DATA/'fixtures'/'milton_advisories.json')
    entries=[v for k,v in archive_memory.items() if k!='loaded']
    if not any(x['id']==fixture['id'] for x in entries):entries.append(fixture)
    return {'mode':'ARCHIVE','storms':[{'id':s['id'],'name':s['name'],'basin':s['basin'],'year':s['year'],
        'dataset':s['dataset'],'quality':'ARCHIVED','point_count':len(s['points']),
        'source_url':s['source_url']} for s in sorted(entries,key=lambda x:x['year'],reverse=True)],
        'note':'HURDAT2 downloaded from NHC if reachable; Milton offline fixture is explicitly advisory snapshots.'}

@app.get('/api/storms/historical/{storm_id}')
async def historic_detail(storm_id: str):
    if storm_id.upper() in archive_memory: return archive_memory[storm_id.upper()]
    fixture=load_fixture(DATA/'fixtures'/'milton_advisories.json')
    if storm_id.upper()==fixture['id']:return fixture
    raise HTTPException(404,'Historical dataset unavailable. Check internet access or try Milton.')

@app.get('/api/recon/fixture')
async def recon_fixture():
    text=(DATA/'fixtures'/'hdob_usaf_20260910.txt').read_text(encoding='utf8')
    obj=parse_hdob(text,'https://www.nhc.noaa.gov/text/URNT15-USAF.shtml')
    obj['note']+=' FIXTURE: Transcribed from NOAA/NHC September 10, 2026 product; this is not a live aircraft position.'
    return obj

async def _latest_recon(provider_name):
    url=HDOB_URLS[provider_name]
    raw=await provider.fetch(url,300,max_bytes=500_000)
    product=BeautifulSoup(raw,'html.parser').get_text('\n')
    matches=re.findall(r'(UR(?:NT|PN)15\s+\w+\s+\d+\s*\n\s*.+?\bHDOB\s+\d+\s+20\d{6}\s*\n.*?\$\$)',product,re.DOTALL)
    if not matches:raise ValueError('No current HDOB bulletin on official source page')
    obj=parse_hdob(matches[-1],url)
    latest=datetime.fromisoformat(obj['points'][-1]['time'].replace('Z','+00:00'))
    age=(datetime.now(timezone.utc)-latest).total_seconds()
    obj['quality']='LIVE' if 0<=age<1800 else 'DELAYED' if 0<=age<21600 else 'ARCHIVED'
    obj['note']+=' Latest public bulletin only; never inferred ADS-B location or mission activity.'
    return obj

@app.get('/api/recon/status')
async def recon_status():
    try:
        obj=await _latest_recon('USAF Atlantic')
        return {'quality':obj['quality'], 'source_url':obj['source_url'],'mission':obj['mission'],
            'last_observation_utc':obj['points'][-1]['time'], 'point_count':len(obj['points']),
            'checked_utc':_utc_now(),
            'note':'USAF Atlantic public HDOB bulletin only; not a live flight-tracking feed.'}
    except Exception as exc:
        return {'quality':'UNAVAILABLE','source_url':HDOB_URLS['USAF Atlantic'],
            'checked_utc':_utc_now(), 'error':type(exc).__name__ + ': '+str(exc)[:120],
            'note':'No verified recent HDOB. This does not establish that no reconnaissance mission exists.'}

@app.get('/api/recon/latest')
async def recon_latest(provider_name: str=Query('USAF Atlantic')):
    if provider_name not in HDOB_URLS:raise HTTPException(400,'Unknown reconnaissance source')
    try:return await _latest_recon(provider_name)
    except Exception as exc:raise HTTPException(503,f'Reconnaissance bulletin unavailable: {type(exc).__name__}: {str(exc)[:150]}')

@app.post('/api/uas/upload')
async def upload_uas(file: UploadFile=File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(400,'CSV files only; NetCDF import not implemented')
    raw=await file.read(1_000_001)
    if len(raw)>1_000_000:raise HTTPException(413,'CSV maximum is 1 MB')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not {'time','lat','lon'}.issubset(reader.fieldnames or []):
            raise ValueError('CSV requires time, lat, lon headings (ISO UTC, degrees)')
        points=[]
        for record in reader:
            if len(points)>=5000:raise ValueError('Maximum 5000 rows')
            t=datetime.fromisoformat(record['time'].replace('Z','+00:00'))
            if t.tzinfo is None:raise ValueError('Timestamps must include UTC offset')
            lat,lon=float(record['lat']),float(record['lon'])
            if not (-90<=lat<=90 and -180<=lon<=180):raise ValueError('Bad coordinate')
            p={'time':t.astimezone(timezone.utc).isoformat().replace('+00:00','Z'),'lat':lat,'lon':lon}
            for key in ('wind_kt','temperature_c','pressure_hpa','altitude_m','rh_pct'):
                if record.get(key):p[key]=float(record[key])
            points.append(p)
        if not points:raise ValueError('CSV contains no rows')
    except (ValueError,UnicodeDecodeError) as exc:raise HTTPException(422,str(exc))
    id='uas-upload'
    uas_memory[id]={'id':id,'name':Path(file.filename).name[:120], 'points':points,'quality':'USER_SUPPLIED',
        'source':'Local user CSV upload','note':'User supplied observations; not certified NOAA or a live stream.'}
    return uas_memory[id]

@app.get('/api/uas/latest')
async def uas_last():
    if 'uas-upload' not in uas_memory:raise HTTPException(404,'No user CSV uploaded in current server session')
    return uas_memory['uas-upload']

@app.websocket('/ws')
async def ws(socket: WebSocket):
    await socket.accept()
    queue=asyncio.Queue(maxsize=8)
    subscribers.add(queue)
    try:
        await socket.send_json({'event':'connected','utc':_utc_now(),
                                'poll_interval_seconds':poll_state['interval_seconds']})
        while True:
            try:
                event=await asyncio.wait_for(queue.get(),timeout=30)
                await socket.send_json(event)
            except asyncio.TimeoutError:
                await socket.send_json({'event':'heartbeat','utc':_utc_now(),
                                        'poll_interval_seconds':poll_state['interval_seconds']})
    except (WebSocketDisconnect,RuntimeError):pass
    finally:subscribers.discard(queue)

app.mount('/static',StaticFiles(directory=DIST),name='static')

@app.get('/')
async def index():return FileResponse(DIST/'index.html')

@app.get('/{path:path}',include_in_schema=False)
async def page_fallback(path: str):
    if path.startswith('api/') or path=='ws': raise HTTPException(404)
    target=(DIST/path).resolve()
    if target.is_file() and target.is_relative_to(DIST.resolve()):return FileResponse(target)
    return FileResponse(DIST/'index.html')
