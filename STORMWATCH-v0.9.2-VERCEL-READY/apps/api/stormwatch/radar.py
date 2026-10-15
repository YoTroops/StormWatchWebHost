"""NOAA/NWS MRMS time-enabled ImageServer integration.

No estimated reflectivity, invented timestamps, or user-controlled upstream URLs.
Only provider-exposed temporal extent is treated as metadata, not individual scan time.
"""
import json
from datetime import datetime, timezone
from urllib.parse import urlencode

RADAR_BASE = ('https://mapservices.weather.noaa.gov/eventdriven/rest/services/'
              'radar/radar_base_reflectivity_time/ImageServer')
RADAR_METADATA = RADAR_BASE + '?f=pjson'
REGIONS = {
    'gulf': {'name':'Gulf of Mexico', 'bbox':[-100.0,14.0,-77.0,34.0], 'center':[-88.5,24.0]},
    'southeast': {'name':'Southeastern US', 'bbox':[-91.0,23.0,-73.0,39.0], 'center':[-82.0,31.0]},
    'caribbean': {'name':'Caribbean', 'bbox':[-88.0,10.0,-60.0,28.0], 'center':[-74.0,19.0]},
    'conus': {'name':'Continental US', 'bbox':[-125.0,23.0,-66.0,50.0], 'center':[-95.5,36.5]},
}
ALLOWED_OFFSETS = (0, 15, 30, 45, 60, 90, 120, 180)
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def radar_metadata(raw: bytes, now: datetime | None = None):
    """Provider metadata: timeExtent is coverage window, not an acquisition instant."""
    data = json.loads(raw)
    extent = (data.get('timeInfo') or {}).get('timeExtent')
    if not isinstance(extent,list) or len(extent)!=2 or not all(isinstance(x,(float,int)) for x in extent):
        raise ValueError('NWS radar service omitted valid time extent')
    start,end = extent
    if start<=0 or end<=start:
        raise ValueError('Invalid NWS radar service time extent')
    def iso(ts): return datetime.fromtimestamp(ts/1000,timezone.utc).isoformat().replace('+00:00','Z')
    now = now or datetime.now(timezone.utc)
    age = (now.timestamp()*1000-end)/60000
    quality = 'STALE' if age>30 else 'DELAYED' if age>12 else 'AVAILABLE'
    if age < -10: quality='UNAVAILABLE'  # impossible future service end
    return {'provider':'NOAA/NWS MRMS','product':'Quality-controlled radar base reflectivity',
            'source_url':RADAR_BASE, 'quality':quality, 'coverage_window_start_utc':iso(start),
            'coverage_window_end_utc':iso(end), 'start_ms':int(start),'end_ms':int(end),
            'coverage':'NWS/MRMS network only; no offshore ocean radar coverage guaranteed',
            'note':'Window bounds come from NWS service metadata; neither bound is a verified pixel acquisition time.'}


def radar_image_url(region: str, minutes_ago: int, metadata: dict) -> tuple[str,int]:
    if region not in REGIONS: raise ValueError('Unknown radar region')
    if minutes_ago not in ALLOWED_OFFSETS: raise ValueError('Unsupported radar time offset')
    # Offset relative to most recent published service extent, not current wall clock.
    sample = metadata['end_ms'] - minutes_ago*60_000
    if sample < metadata['start_ms']:
        raise ValueError('Requested radar time outside provider window')
    bbox = REGIONS[region]['bbox']
    # ArcGIS exportImage defaults adjustAspectRatio=true: when pixel dimensions
    # do not match bbox proportions, the server can silently EXPAND the bbox.
    # Previously all regions used 720x480, so the resulting raster was mapped
    # to coordinates different from its true footprint (false echoes over towns).
    # Match the request raster shape to the EPSG:4326 footprint as a second
    # defense in case an upstream server ignores adjustAspectRatio=false.
    pixel_height = 480
    pixel_width = round(pixel_height * (bbox[2] - bbox[0]) / (bbox[3] - bbox[1]))
    params={'bbox':','.join(str(x) for x in bbox),
            'bboxSR':'4326','imageSR':'4326',
            'adjustAspectRatio':'false',
            'size':f'{pixel_width},{pixel_height}',
            'format':'png32','transparent':'true','interpolation':'RSP_NearestNeighbor',
            'time':str(sample),'f':'image'}
    return RADAR_BASE+'/exportImage?'+urlencode(params),sample


def validate_radar_png(payload: bytes):
    if len(payload)<24 or not payload.startswith(PNG_SIGNATURE):
        raise ValueError('NWS did not return a PNG radar image')
    # Reject unexpected giant image dimensions even if upstream response is PNG.
    width=int.from_bytes(payload[16:20],'big');height=int.from_bytes(payload[20:24],'big')
    if not (1<=width<=2048 and 1<=height<=2048): raise ValueError('Invalid radar image dimensions')
