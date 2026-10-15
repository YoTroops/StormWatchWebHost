"""NOAA/NHC HURDAT2 parsing. Six-hourly best-track values are post-analysis."""
import json
from pathlib import Path
from .science import geo_coord, hurricane_category, mph_to_kt

HURDAT_SOURCES = {
  'atlantic': 'https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2025-092326.txt',
  'pacific': 'https://www.nhc.noaa.gov/data/hurdat/hurdat2-nepac-1949-2025-092926.txt',
}
SHOWCASE_IDS = ('AL122005','AL142018','AL092022','AL102023','AL092024','AL142024')


def parse_hurdat(text: str, selected: set[str] | None = None) -> list[dict]:
    result, current, remaining = [], None, 0
    for raw in text.splitlines():
        cols = [s.strip() for s in raw.split(',')]
        if len(cols) >= 3 and cols[0][:2] in ('AL','EP','CP') and len(cols[0]) == 8 and cols[0][2:].isdigit():
            if current is not None and remaining != 0: raise ValueError('Truncated HURDAT2 block')
            sid, name = cols[:2]
            remaining = int(cols[2]); current = None
            if selected is None or sid in selected:
                current = {'id':sid,'name':name,'year':int(sid[4:]), 'basin':'Atlantic' if sid.startswith('AL') else 'Eastern Pacific',
                   'quality':'ARCHIVED','dataset':'HURDAT2_BEST_TRACK','provider':'NOAA/NHC','source_url': HURDAT_SOURCES['atlantic' if sid.startswith('AL') else 'pacific'], 'points':[]}
                result.append(current)
            continue
        if remaining <= 0: continue
        if len(cols) < 8: raise ValueError('Malformed HURDAT2 record')
        remaining -= 1
        if current is None: continue
        date, clock, record_id, status, lat, lon, wind, pressure = cols[:8]
        time = f'{date[:4]}-{date[4:6]}-{date[6:8]}T{clock[:2]}:{clock[2:]}:00Z'
        w = int(wind); p = int(pressure)
        point = {'time':time,'lat':geo_coord(lat),'lon':geo_coord(lon), 'status':status,
                 'record':record_id or None, 'wind_kt':w if w>=0 else None,
                 'pressure_hpa':p if p>0 else None}
        point['category'] = hurricane_category(point['wind_kt'])
        current['points'].append(point)
    if remaining != 0: raise ValueError('Truncated HURDAT2 final block')
    return result


def load_fixture(path: Path) -> dict:
    entry = json.loads(path.read_text(encoding='utf-8'))
    for point in entry['points']:
        point['wind_kt'] = round(mph_to_kt(point['wind_mph']),1)
        point['category'] = hurricane_category(point['wind_kt'])
    return entry
