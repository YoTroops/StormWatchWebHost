"""NOAA/NESDIS STAR latest CONUS satellite image metadata.

Read the official published page; never guess a changing CDN filename or
represent HTTP fetch time as the image's acquisition time. This is an image
preview, not a geographic map overlay.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit
import re
from bs4 import BeautifulSoup

SATELLITE_PAGE = 'https://www.star.nesdis.noaa.gov/GOES/conus.php?sat=G19'
CHANNELS = {
    'GEOCOLOR': {'product': 'GEOCOLOR', 'label': 'GeoColor (day/night composite)'},
    'IR': {'product': '13', 'label': 'Band 13 longwave infrared (10.3 µm)'},
    'WATER_VAPOR': {'product': '08', 'label': 'Band 8 water vapor (6.2 µm)'},
}
# GOES filename prefix is YYYYDDDHHMM in UTC; e.g. 20262742246.
_FILENAME_TIME = re.compile(r'/(\d{4})(\d{3})(\d{2})(\d{2})_GOES19-ABI-CONUS-')


def parse_image_time(url: str) -> datetime:
    match = _FILENAME_TIME.search(url)
    if not match:
        raise ValueError('NOAA image URL does not contain an acquisition timestamp')
    year, julian_day, hour, minute = map(int, match.groups())
    if not 2020 <= year <= 2100:
        raise ValueError('Image year outside expected range')
    day0 = datetime(year, 1, 1, tzinfo=timezone.utc)
    dt = day0 + timedelta(days=julian_day-1, hours=hour, minutes=minute)
    if dt.year != year or julian_day < 1 or hour > 23 or minute > 59:
        raise ValueError('Invalid NOAA image acquisition timestamp')
    return dt


def parse_satellite_page(html: str, channel: str, now: datetime | None = None) -> dict:
    if channel not in CHANNELS:
        raise ValueError('Unsupported NOAA satellite channel')
    product = CHANNELS[channel]['product']
    soup = BeautifulSoup(html, 'html.parser')
    possible = []
    for anchor in soup.find_all('a', href=True):
        absolute = urljoin(SATELLITE_PAGE, anchor['href'])
        parsed = urlsplit(absolute)
        # Provider-controlled product paths only; never return arbitrary links.
        if (parsed.scheme != 'https' or parsed.hostname != 'cdn.star.nesdis.noaa.gov'
            or not parsed.path.startswith(f'/GOES19/ABI/CONUS/{product}/')
            or not parsed.path.endswith('-1250x750.jpg')):
            continue
        try:
            acquisition = parse_image_time(parsed.path)
        except ValueError:
            continue
        possible.append((acquisition, absolute))
    if not possible:
        raise ValueError('No timestamped 1250x750 GOES-19 image link found on the official page')
    observed, image = max(possible, key=lambda x: x[0])
    now = now or datetime.now(timezone.utc)
    age_min = (now-observed).total_seconds()/60
    if age_min < -10:
        raise ValueError('NOAA page image timestamp appears to be in the future')
    quality = 'LIVE' if age_min <= 20 else 'DELAYED' if age_min <= 60 else 'STALE'
    return {
        'satellite': 'GOES-19 (GOES-East)', 'sector': 'CONUS', 'channel': channel,
        'channel_label': CHANNELS[channel]['label'], 'image_url': image,
        'observed_utc': observed.isoformat().replace('+00:00','Z'),
        'quality': quality, 'source_url': SATELLITE_PAGE,
        'note': 'NOAA/NESDIS STAR image preview. NOT georeferenced onto STORMWATCH globe. '
                'Image acquisition UTC time is extracted from the NOAA-published filename. '
                'NOAA STAR imagery is informational and is not an operational decision authority.'
    }
