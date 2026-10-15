"""NOAA nowCOAST map-projected satellite mosaics, when a service is available.

This is *not* a geolocation of the NOAA STAR static CONUS JPG; it requests
EPSG:4326 imagery from a registered NOAA GIS service. Provider time extent is
not treated as the observation time of individual pixels.
"""
import json
from urllib.parse import urlencode
from .radar import REGIONS, validate_radar_png

BASE = 'https://nowcoast.noaa.gov/arcgis/rest/services/nowcoast/sat_meteo_imagery_time/MapServer'
METADATA_URL = BASE + '?f=pjson'
CHANNEL_KEYWORDS = {
    'VISIBLE': ('visible',),
    'IR': ('longwave infrared', 'longwave', 'infrared'),
    'WATER_VAPOR': ('water vapor', 'water vapour'),
}

def choose_layer(raw: bytes, channel: str):
    """Select only a documented visible/IR/WV imagery layer by advertised name."""
    if channel not in CHANNEL_KEYWORDS:
        raise ValueError('Unknown satellite map channel')
    data = json.loads(raw)
    if not isinstance(data,dict) or 'error' in data:
        raise ValueError('Satellite service returned an error')
    layers = data.get('layers')
    if not isinstance(layers,list):
        raise ValueError('NOAA metadata has no layer list')
    scored=[]
    for layer in layers:
        if not isinstance(layer,dict) or not isinstance(layer.get('id'),int): continue
        name=str(layer.get('name','')).lower()
        # Exclude global layers where a named GOES composite is present.
        rank=next((len(CHANNEL_KEYWORDS[channel])-i for i,k in enumerate(CHANNEL_KEYWORDS[channel]) if k in name),0)
        if rank:
            rank+=3 if ('goes' in name or 'northern hemisphere' in name) else 0
            rank-=2 if ('global' in name and 'goes' not in name) else 0
            scored.append((rank,layer['id'],layer.get('name','')))
    if not scored: raise ValueError('No matching NOAA satellite layer advertised')
    scored.sort(key=lambda x:(-x[0],x[1]))
    _,layer_id,name=scored[0]
    return {'layer_id':layer_id,'layer_name':name,'channel':channel,
            'provider':'NOAA nowCOAST','source_url':BASE,
            'note':'Map-projected NOAA image. A service map time extent is NOT the acquisition time of each pixel.'}

def image_url(layer_id: int, region: str) -> str:
    if region not in REGIONS: raise ValueError('Unknown satellite map region')
    if not isinstance(layer_id,int) or layer_id<0 or layer_id>10000:
        raise ValueError('Invalid NOAA satellite layer ID')
    bbox = REGIONS[region]['bbox']
    # ArcGIS defaults to adjustAspectRatio=true and can expand the requested
    # geographic footprint if a fixed pixel aspect ratio differs. Ensure the
    # exported image exactly corresponds to the coordinates used by the client.
    height = 600
    width = round(height * (bbox[2] - bbox[0]) / (bbox[3] - bbox[1]))
    params={'bbox':','.join(str(x) for x in bbox),
            'bboxSR':'4326','imageSR':'4326','adjustAspectRatio':'false',
            'size':f'{width},{height}',
            'format':'png32','transparent':'true',
            'layers':f'show:{layer_id}','f':'image'}
    return BASE+'/export?'+urlencode(params)

def validate_satellite_image(raw: bytes):
    validate_radar_png(raw)
    # ArcGIS can return all-transparent PNGs when selected layers have no data;
    # this validator only validates format, not pixel-level coverage or time.
    if len(raw)>6_000_000:raise ValueError('Satellite overlay image exceeds size limit')
