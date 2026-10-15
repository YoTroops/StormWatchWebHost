"""Public ADS-B sightings of known NOAA hurricane-research airframes.

Aircraft positions DO NOT attest to an operational reconnaissance mission. Do not
infer routes from sparse sightings. ADSB.lol terms: ODbL; local educational use.
"""
import math
from datetime import datetime, timedelta, timezone

AIRCRAFT_URL = "https://api.adsb.lol/v2/reg/N42RF,N43RF,N49RF"
CALLSIGN_ROOT = "https://api.adsb.lol/v2/callsign/"
REGISTRY = {
    "N42RF": {"type": "NOAA WP-3D Orion", "label": "Kermit", "source": "https://www.omao.noaa.gov/aircraft-operations/noaa-hurricane-hunters"},
    "N43RF": {"type": "NOAA WP-3D Orion", "label": "Miss Piggy", "source": "https://www.omao.noaa.gov/aircraft-operations/noaa-hurricane-hunters"},
    "N49RF": {"type": "NOAA Gulfstream IV-SP", "label": "Gonzo", "source": "https://www.omao.noaa.gov/aircraft-operations/aircraft/gulfstream-iv-sp"},
}

def _numeric(value, minimum, maximum):
    # Booleans and sentinel strings cannot be coordinates or telemetry.
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) and minimum <= number <= maximum else None

def parse_aircraft_response(payload, now=None, filter_registration=True):
    """Parse v2 ADS-B response with timestamp based on server 'now' - seen_pos.

    The time of API polling is NOT the observed aircraft position time.
    Never include a record that lacks fresh coordinates and age metadata.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get('ac'), list):
        raise ValueError('Malformed aircraft provider response')
    received = _numeric(payload.get('now'), 0, 5_000_000_000_000)
    if received is None:
        raise ValueError('Missing ADS-B feed timestamp')
    provider_utc = datetime.fromtimestamp(received/1000, timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('UTC comparison time must include timezone')
    if abs((provider_utc-now).total_seconds()) > 360:
        raise ValueError('Aircraft feed timestamp is out of range')
    records = []
    seen_registrations = set()
    for item in payload['ac'][:500]:
        if not isinstance(item, dict):
            continue
        reg = str(item.get('r') or '').strip().upper()
        if filter_registration and reg not in REGISTRY:
            continue
        pos_age = _numeric(item.get('seen_pos'), 0, 3600)
        lat = _numeric(item.get('lat'), -90, 90)
        lon = _numeric(item.get('lon'), -180, 180)
        if pos_age is None or lat is None or lon is None:
            continue
        observed = provider_utc - timedelta(seconds=pos_age)
        age = (now-observed).total_seconds()
        if age < -30 or age > 600:
            continue  # do not show positions older than 10 minutes
        if reg in seen_registrations:
            continue
        if reg:
            seen_registrations.add(reg)
        quality = 'LIVE' if age <= 90 else 'DELAYED' if age <= 600 else 'STALE'
        identity = REGISTRY.get(reg)
        records.append({
            'registration': reg or 'UNCONFIRMED',
            'icao_hex': str(item.get('hex') or '')[:12],
            'callsign': str(item.get('flight') or '').strip()[:24] or None,
            'name': (identity or {}).get('label') or 'Unverified callsign match',
            'aircraft_type': (identity or {}).get('type') or str(item.get('t') or 'Unknown')[:40],
            'identity_verified': bool(identity),
            'mission_status': 'NOT VERIFIED',
            'lat': lat, 'lon': lon,
            'altitude_ft': _numeric(item.get('alt_baro'), -1500, 65000),
            'groundspeed_kt': _numeric(item.get('gs'), 0, 1400),
            'heading_deg': _numeric(item.get('track'), 0, 360),
            'observed_utc': observed.isoformat().replace('+00:00','Z'),
            'age_seconds': round(max(0, age), 1),
            'quality': quality,
            'source_url': AIRCRAFT_URL if filter_registration else CALLSIGN_ROOT + str(item.get('flight') or '').strip()[:20],
            'airframe_reference': (identity or {}).get('source'),
        })
    return records
