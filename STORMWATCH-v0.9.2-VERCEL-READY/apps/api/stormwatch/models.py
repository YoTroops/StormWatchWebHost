"""NHC public ATCF A-deck objective forecast aids (not official NHC forecasts).

Only observed A-deck rows are surfaced; no synthetic tracks or intensity curves.
ATCF tracks and intensity techniques may have separate identifiers, merged by
storm, initialization, and forecast lead time. No interpolation is performed.
"""
from __future__ import annotations
import csv
import gzip
import io
import re
from datetime import datetime, timedelta, timezone

AID_ROOT = 'https://ftp.nhc.noaa.gov/atcf/aid_public/'
MODEL_REGISTRY = (
    dict(id='nhc', name='NHC Official', family='official', aids=('OFCL','OFCI'), source='NHC ATCF', url='https://www.nhc.noaa.gov/', note='Official forecast; A-deck records may be absent. NHC forecast cone is a separate product.'),
    dict(id='hafsa', name='HAFS-A', family='dynamical', aids=('HFSA','HFAI'), source='NOAA HAFS', url='https://www.emc.ncep.noaa.gov/hurricane/HFSA/', note='Physics-based HAFS configuration A; not an AI model.'),
    dict(id='hafsb', name='HAFS-B', family='dynamical', aids=('HFSB','HFBI'), source='NOAA HAFS', url='https://www.emc.ncep.noaa.gov/hurricane/HFSB/', note='Physics-based HAFS configuration B; not an AI model.'),
    dict(id='gfs', name='GFS', family='dynamical', aids=('AVNO','AVNI','GFSO','GFSI'), source='NOAA GFS', url='https://www.nhc.noaa.gov/modelsummary.shtml', note='GFS objective aid; model cycles must be compared at equal initialization times.'),
    dict(id='ecmwf', name='ECMWF IFS (Euro)', family='dynamical', aids=('EMXI','EMX','ECMF'), source='ECMWF via NHC', url='https://www.ecmwf.int/en/forecasts/datasets/open-data', note='ECMWF public NHC A-deck aids may be restricted or absent.'),
    dict(id='google', name='Google DeepMind', family='ai', aids=('GDMI','GDMN'), source='Google WeatherNext Cyclones via NHC', url='https://deepmind.google.com/science/weatherlab', note='Research/experimental cyclone ensemble aid when distributed publicly. No inference from Google website graphics.'),
    dict(id='gencast', name='Google GenCast', family='ai', aids=('GENI','GENC'), source='Google via NHC', url='https://deepmind.google.com/science/weatherlab', note='Experimental AI guidance, only displayed when an actual public ATCF aid exists.'),
    dict(id='aigfs', name='NOAA AI-GFS', family='ai', aids=('GAII','GAIO'), source='NOAA AI-GFS', url='https://www.noaa.gov/news-release/noaa-deploys-new-generation-of-ai-driven-global-weather-models', note='NOAA AI-based global guidance (not HAFS).'),
    dict(id='aigefs', name='NOAA AI-GEFS', family='ai', aids=('EGMI','EGMN'), source='NOAA AI-GEFS', url='https://www.noaa.gov/news-release/noaa-deploys-new-generation-of-ai-driven-global-weather-models', note='AI-based GEFS ensemble guidance.'),
    dict(id='aifs', name='ECMWF AIFS AI', family='ai', aids=('EAII','EAIO','EAMI','EAMN'), source='ECMWF AIFS via NHC', url='https://www.ecmwf.int/en/forecasts/datasets/open-data', note='May be restricted in the NHC public deck. Direct ECMWF BUFR decoding not implemented.'),
    dict(id='hafsai', name='HAFS-AI (requested)', family='ai', aids=(), source='No verified ATCF identifier', url='https://www.aoml.noaa.gov/hurricane-modeling-prediction/', note='HAFS-A and HAFS-B are physics-based. No distinct public HAFS-AI guidance feed has been verified; never substitute HAFS-A.'),
)
ALLOWED_BASINS={'AL','EP','CP'}

def deck_url(storm_id: str) -> str:
    if not re.fullmatch(r'(AL|EP|CP)\d{2}20\d{2}',storm_id.upper()):
        raise ValueError('Invalid NHC storm ID')
    return AID_ROOT + 'a' + storm_id.lower() + '.dat.gz'

def decode_deck(data: bytes) -> str:
    if len(data)>5_000_000:raise ValueError('Compressed A-deck too large')
    if not data.startswith(b'\x1f\x8b'):raise ValueError('Expected gzip-compressed official A-deck')
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        raw=stream.read(32_000_001)
    if len(raw)>32_000_000:raise ValueError('Expanded A-deck too large')
    return raw.decode('ascii','replace')

def parse_position(value: str, latitude:bool) -> float:
    """ATCF coordinates are tenths degrees, e.g. 223N, 0750W."""
    s=value.strip().upper()
    match=re.fullmatch(r'(\d{2,4})([NSWE])',s)
    if not match:raise ValueError('Invalid ATCF coordinate')
    hemi=match.group(2)
    if hemi not in ('NS' if latitude else 'EW'):raise ValueError('Invalid coordinate hemisphere')
    amount=int(match.group(1))/10
    if amount>(90 if latitude else 180):raise ValueError('Coordinate outside Earth')
    return -amount if hemi in 'SW' else amount

def _valid_utc(value):
    if not re.fullmatch(r'20\d{8}',value):raise ValueError('Invalid ATCF cycle')
    return datetime.strptime(value,'%Y%m%d%H').replace(tzinfo=timezone.utc)

def parse_atcf(raw: str, storm_id: str) -> dict:
    """Extract compact technique/cycle/tau groups, no invented model records."""
    storm_id=storm_id.upper(); deck_url(storm_id)
    basin,number=storm_id[:2],int(storm_id[2:4])
    rows={}; cycles=set(); bad=0
    try: source=csv.reader(io.StringIO(raw),skipinitialspace=True)
    except Exception:raise ValueError('Unable to read A-deck CSV')
    for columns in source:
        if len(columns)<10: continue
        try:
            if columns[0].strip().upper()!=basin or int(columns[1])!=number:continue
            cycle=_valid_utc(columns[2].strip())
            aid=columns[4].strip().upper()
            if not re.fullmatch(r'[A-Z0-9]{3,5}',aid):continue
            tau=int(columns[5]);
            if tau<0 or tau>384 or tau%3:continue
            lat=parse_position(columns[6],True);lon=parse_position(columns[7],False)
            wind=int(columns[8]) if columns[8].strip() else None
            pressure=int(columns[9]) if columns[9].strip() else None
            if wind is not None and not 0<=wind<=250:continue
            if wind==0:wind=None  # zero is an ATCF missing-intensity placeholder, not a forecast of calm winds
            if pressure is not None and not 800<=pressure<=1100:pressure=None
            c=cycle.strftime('%Y-%m-%dT%H:%M:%SZ');cycles.add(c)
            row={'lat':lat,'lon':lon,'wind_kt':wind,'pressure_hpa':pressure,'tau_hours':tau,
                 'valid_utc':(cycle+timedelta(hours=tau)).strftime('%Y-%m-%dT%H:%M:%SZ'),'aid':aid}
            rows[(c,aid,tau)]=row  # overwrite repeated wind-radii rows, equivalent center values
        except (ValueError,TypeError,OverflowError):bad+=1
    return {'cycles':sorted(cycles,reverse=True),'rows':rows,'invalid_rows':bad}

def assemble(parsed:dict, cycle:str|None=None, now:datetime|None=None) -> dict:
    """One forecast initialization common to all displayed models."""
    now=now or datetime.now(timezone.utc)
    rows=parsed['rows']; cycles=parsed['cycles']
    latest=cycles[0] if cycles else None
    if cycle is not None and cycle not in cycles:raise ValueError('Unknown ATCF cycle')
    selected=cycle if cycle is not None else latest
    created=datetime.fromisoformat(selected.replace('Z','+00:00')) if selected else None
    age_hours=(now-created).total_seconds()/3600 if created else None
    results=[]
    for config in MODEL_REGISTRY:
        candidates=[]
        if selected:
            for rank, aid in enumerate(config['aids']):
                aidrows=[row for (cy,a,tau),row in rows.items() if cy==selected and a==aid]
                if aidrows:
                    aidsorted=sorted(aidrows,key=lambda p:p['tau_hours'])
                    candidates.append((rank,aid,aidsorted))
        tracks=[a for a in candidates if len(a[2])>=2]
        # choose technique with most usable forecast points; track aid with valid wind preferred for intensity
        chosen=min(tracks,key=lambda a:(-len(a[2]),-sum(p['wind_kt'] is not None for p in a[2]),a[0])) if tracks else None
        if chosen:
            points=[dict(p) for p in chosen[2]]
            # Additional technique may report intensity while track aid reports zeros/missing.
            for item in points:
                if item['wind_kt'] in (None,0):
                    for _,_,other in candidates:
                        hit=next((p for p in other if p['tau_hours']==item['tau_hours'] and p['wind_kt'] not in (None,0)),None)
                        if hit:
                            item['wind_kt']=hit['wind_kt'];item['wind_aid']=hit['aid'];break
        else: points=[]
        results.append({**config,'availability':'AVAILABLE' if chosen else 'UNAVAILABLE',
                        'quality':('STALE' if age_hours is not None and age_hours>24 else 'FORECAST') if chosen else 'UNAVAILABLE',
                        'aid_used':chosen[1] if chosen else None,'cycle_utc':selected if chosen else None,
                        'points':points,'max_wind_kt':max((p['wind_kt'] for p in points if p['wind_kt'] is not None),default=None)})
    return {'cycle_utc':selected,'available_cycles':cycles[:12], 'cycle_age_hours':round(age_hours,1) if age_hours is not None else None,
            'models':results,'available_models':sum(m['availability']=='AVAILABLE' for m in results),
            'note':'Objective model guidance, NOT NHC official forecast unless marked NHC Official. Tracks are grouped by the exact same initialization (UTC). No interpolation or fabricated points.'}

def unavailable_catalog(note:str) -> dict:
    return {'cycle_utc':None,'available_cycles':[],'cycle_age_hours':None,
            'models':[{**model,'availability':'UNAVAILABLE','quality':'UNAVAILABLE','aid_used':None,'cycle_utc':None,'points':[], 'max_wind_kt':None} for model in MODEL_REGISTRY],
            'available_models':0,'note':note}
