"""Conservative subset decoder for NHC HDOB; no guessed aircraft altitude or pressure."""
import re
from datetime import datetime, timezone, timedelta
from .science import geo_coord

LINE = re.compile(r'^([0-2]\d[0-5]\d[0-5]\d)\s+(\d{4}[NS])\s+(\d{5}[EW])\s+(\S+)\s+(\S+)\s+(\S+)\s+([+-]\d{3}|////)\s+([+-]\d{3}|////)\s+(\S+)\s+(\S+)')
HEADER = re.compile(r'^(\S.{5,}?)\s+HDOB\s+(\d+)\s+(20\d{6})\s*$')


def decode_coord(text: str) -> float:
    hemisphere = text[-1]
    degrees = int(text[:-3]); minutes = int(text[-3:-1])
    # NOTE: this is specifically DDMM[N/S] or DDDMM[E/W].
    if minutes >= 60 or degrees > (90 if hemisphere in 'NS' else 180):
        raise ValueError('Invalid HDOB coordinate')
    val = degrees + minutes / 60
    return -val if hemisphere in 'SW' else val


def parse_hdob(text: str, url: str = '') -> dict:
    lines = text.splitlines()
    marker = next((HEADER.match(line.strip()) for line in lines if HEADER.match(line.strip())), None)
    if marker is None: raise ValueError('HDOB mission header missing')
    mission, obs_number, date = marker.groups()
    base = datetime.strptime(date, '%Y%m%d').replace(tzinfo=timezone.utc)
    observations = []
    previous = None
    for line in lines:
        match = LINE.match(line.strip())
        if not match: continue
        hhmmss, latcode, loncode, static_p, geo_height, temp_code, dew, other_temp, wind_code, other_wind = match.groups()
        try:
            latitude = decode_coord(latcode)
            longitude = decode_coord(loncode)
            hour, minute, second = int(hhmmss[:2]), int(hhmmss[2:4]), int(hhmmss[4:6])
            if hour > 23: continue
            when = base + timedelta(hours=hour,minutes=minute,seconds=second)
            # HDOB timestamp can cross midnight; handle sequence regressions with a 12h wrap threshold.
            if previous is not None and (previous-when).total_seconds() > 12*3600: when += timedelta(days=1)
            previous = when
            point = {'time': when.isoformat().replace('+00:00','Z'), 'lat':latitude,'lon':longitude,
                     'source_url': url, 'wind_kt': None,'pressure_hpa':None,'temperature_c':None,'altitude_m':None}
            # Source format encodes flight-level wind direction and speed as DDDSSS;
            # 3-digit wind speed is in knots. /// means missing.
            if len(wind_code)==6 and wind_code.isdigit():
                direction=int(wind_code[:3]); speed=int(wind_code[3:])
                if direction <= 360 and speed <= 300:
                    point['wind_dir_deg'] = direction
                    point['wind_kt'] = speed
            # Temperature encoding signed tenths of deg C.
            if re.fullmatch(r'[+-]\d{3}',dew):
                point['temperature_c'] = int(dew)/10
            observations.append(point)
        except (ValueError, OverflowError):
            continue
    if not observations: raise ValueError('No valid HDOB rows')
    return {'id':f'hdob-{date}-{obs_number}','mission':mission.strip(), 'observation_number':int(obs_number),
            'quality':'ARCHIVED', 'source_kind':'NHC HDOB', 'provider':'NOAA/NHC', 'source_url':url,
            'note':'Aircraft HDOB positions; wind is flight-level if decoded. Other fields intentionally unavailable until verified against the full HDOB specification.',
            'points':observations}
