"""Estimate visible ISS passes using public orbital elements and SGP4."""
from math import atan2, cos, degrees, hypot, radians, sin, sqrt
from time import monotonic

from aiohttp import ClientError, ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from sgp4.api import Satrec
from sgp4.propagation import gstime

from .astronomy import days, sun_coords, sun_at

TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"
EARTH_RADIUS = 6378.137
ECCENTRICITY_SQUARED = 0.00669437999
DAY_SECONDS = 86400


def predict_passes(satellite, start, end, latitude, longitude, elevation):
    """Return sunlit tracks above 10° while the observer is in civil darkness."""
    lat, lon = radians(latitude), radians(longitude)
    radius = EARTH_RADIUS / sqrt(1 - ECCENTRICITY_SQUARED * sin(lat) ** 2)
    height = elevation / 1000
    observer = (
        (radius + height) * cos(lat) * cos(lon),
        (radius + height) * cos(lat) * sin(lon),
        (radius * (1 - ECCENTRICITY_SQUARED) + height) * sin(lat),
    )

    def sample(time):
        day, fraction = divmod(time, DAY_SECONDS)
        jd = day + 2440587.5
        fraction /= DAY_SECONDS
        error, position, _ = satellite.sgp4(jd, fraction)
        if error:
            return None
        x, y, z = position
        rotation = gstime(jd + fraction)
        dx = x * cos(rotation) + y * sin(rotation) - observer[0]
        dy = -x * sin(rotation) + y * cos(rotation) - observer[1]
        dz = z - observer[2]
        east = -sin(lon) * dx + cos(lon) * dy
        north = -sin(lat) * (cos(lon) * dx + sin(lon) * dy) + cos(lat) * dz
        up = cos(lat) * (cos(lon) * dx + sin(lon) * dy) + sin(lat) * dz
        altitude = degrees(atan2(up, hypot(east, north)))
        if altitude < 10 or sun_at(time * 1000, latitude, longitude)["alt"] >= -6:
            return None
        sun = sun_coords(days(time * 1000))
        projection = (x * cos(sun["ra"]) + y * sin(sun["ra"])) * cos(sun["dec"]) + z * sin(sun["dec"])
        # Cylindrical Earth shadow is sufficient for an approximate viewing prediction.
        if projection < 0 and x*x + y*y + z*z - projection*projection < EARTH_RADIUS**2:
            return None
        return [altitude, degrees(atan2(east, north)) % 360]

    passes = []
    points = []
    first = None
    step = 10
    for time in range(start, end, step):
        point = sample(time)
        if point is not None:
            if first is None:
                first = next(t for t in range(max(start, time - step + 1), time + 1) if sample(t) is not None)
                points.append(sample(first))
            if time != first:
                points.append(point)
        elif first is not None:
            last = next(t for t in range(time - 1, time - step - 1, -1) if sample(t) is not None)
            if last - first >= 20:
                points.append(sample(last))
                passes.append({"start": first * 1000, "end": (last + 1) * 1000, "points": points})
            first, points = None, []
    return passes


class ISSPasses:
    """Refresh orbital elements and cache predicted tracks between updates."""

    def __init__(self, hass):
        self.hass = hass
        self.fetched = float("-inf")
        self.satellite = None
        self.cache_key = None
        self.passes = []

    async def next_pass(self, now):
        elapsed = monotonic() - self.fetched
        if elapsed >= (4 * 3600 if self.satellite else 600):
            self.fetched = monotonic()
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(TLE_URL, timeout=ClientTimeout(total=6)) as response:
                    response.raise_for_status()
                    lines = (await response.text()).splitlines()
                    line1 = next((line for line in lines if line.startswith("1 25544")), None)
                    line2 = next((line for line in lines if line.startswith("2 25544")), None)
                    if line1 and line2 and min(len(line1), len(line2)) >= 69:
                        self.satellite = Satrec.twoline2rv(line1, line2)
                        self.cache_key = None
            except (ClientError, TimeoutError, UnicodeError, ValueError):
                pass
        if self.satellite is None:
            return None
        timestamp = now.timestamp()
        epoch = (self.satellite.jdsatepoch + self.satellite.jdsatepochF - 2440587.5) * DAY_SECONDS
        if not -DAY_SECONDS <= timestamp - epoch <= 3 * DAY_SECONDS:
            return None
        config = self.hass.config
        location = (config.latitude, config.longitude, config.elevation or 0)
        anchor = int(timestamp // (6 * 3600)) * (6 * 3600)
        key = (anchor, *location)
        if self.cache_key != key:
            self.passes = await self.hass.async_add_executor_job(
                predict_passes, self.satellite, anchor - 3600, anchor + 5 * DAY_SECONDS, *location
            )
            self.cache_key = key
        return next((item for item in self.passes if item["end"] > timestamp * 1000), None)
