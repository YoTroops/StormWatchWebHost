"""Meteorological transformations and observability states (no guessed values)."""
from datetime import datetime, timezone
import math


def kt_to_mph(kt: float) -> float:
    return kt * 1.150779448


def mph_to_kt(mph: float) -> float:
    return mph / 1.150779448


def hpa_to_inhg(hpa: float) -> float:
    return hpa * 0.0295299830714


def hurricane_category(wind_kt: float | None) -> int | None:
    if wind_kt is None or wind_kt < 64:
        return None
    # Saffir-Simpson using NHC wind thresholds in knots.
    if wind_kt >= 137: return 5
    if wind_kt >= 113: return 4
    if wind_kt >= 96: return 3
    if wind_kt >= 83: return 2
    return 1


def geo_coord(value: str) -> float:
    value = value.strip().upper()
    if len(value) < 2 or value[-1] not in 'NSEW':
        raise ValueError('Invalid hemispheric coordinate')
    n = float(value[:-1]); hemi = value[-1]
    if not math.isfinite(n) or n < 0 or n > (90 if hemi in 'NS' else 180):
        raise ValueError('Out-of-range coordinate')
    return -n if hemi in 'SW' else n


def wrap_longitude(value: float) -> float:
    if not math.isfinite(value): raise ValueError('Invalid longitude')
    return (value + 180) % 360 - 180


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None: raise ValueError('UTC offset required')
    return result.astimezone(timezone.utc)


def freshness(observed: datetime | None, now: datetime | None = None,
              live_minutes: int = 90, stale_minutes: int = 360) -> str:
    if observed is None: return 'UNAVAILABLE'
    now = now or datetime.now(timezone.utc)
    if observed > now.replace(microsecond=0) and (observed-now).total_seconds() > 300:
        return 'UNAVAILABLE'
    minutes = max(0, (now-observed).total_seconds() / 60)
    if minutes <= live_minutes: return 'LIVE'
    if minutes <= stale_minutes: return 'DELAYED'
    return 'STALE'
