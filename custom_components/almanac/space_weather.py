"""On-demand NOAA SWPC observations and OVATION forecast."""
import asyncio
from datetime import datetime, timedelta, timezone
from math import cos, isfinite, radians
from time import monotonic

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .astronomy import sun_at

BASE_URL = "https://services.swpc.noaa.gov/"
FEEDS = {
    "kp": "json/planetary_k_index_1m.json",
    "wind": "products/summary/solar-wind-speed.json",
    "bz": "json/rtsw/rtsw_mag_1m.json",
    "aurora": "json/ovation_aurora_latest.json",
}
UTC = timezone.utc


def instant(value):
    """Parse NOAA timestamps, which are UTC even when the suffix is omitted."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def latest(rows, field, now, max_minutes, *, active_only=False):
    """Select the newest valid observation even if feed rows arrive out of order."""
    best = None
    for row in rows:
        if not isinstance(row, dict) or (active_only and row.get("active") is not True):
            continue
        observed = instant(row.get("time_tag"))
        value = row.get(field)
        if type(value) not in (int, float) or not isfinite(value):
            continue
        if observed is None or not now - timedelta(minutes=max_minutes) <= observed <= now + timedelta(minutes=2):
            continue
        if best is None or observed > best[0]:
            best = observed, value
    return {"time": best[0].isoformat(), "value": best[1]} if best else None


def aurora_forecast(payload, now, lat, lon):
    """Estimate nearby aurora potential from the forecast grid and local Sun."""
    if not isinstance(payload, dict):
        return None
    observed = instant(payload.get("Observation Time"))
    forecast = instant(payload.get("Forecast Time"))
    if (observed is None or forecast is None
        or not now - timedelta(minutes=90) <= observed <= now + timedelta(minutes=2)
        or not now - timedelta(minutes=20) <= forecast <= now + timedelta(hours=2)):
        return None
    coordinates = payload.get("coordinates")
    if not isinstance(coordinates, list):
        return None
    latitude = radians(lat)
    nearest = None
    peak = 0
    radius = cos(500 / 6371)
    for point in coordinates:
        if not isinstance(point, list) or len(point) != 3 or any(type(v) not in (int, float) or not isfinite(v) for v in point):
            continue
        x, y, value = point
        if abs(y - lat) > 5 or not 0 <= value <= 100:
            continue
        # Great-circle distance handles the antimeridian and polar longitudes.
        similarity = cos(radians(y - lat)) - cos(latitude) * cos(radians(y)) * (1 - cos(radians(x - lon)))
        if nearest is None or similarity > nearest[0]:
            nearest = similarity, value
        if similarity >= radius:
            peak = max(peak, value)
    if nearest is None or nearest[0] < radius:
        return None
    evaluation = max(now, forecast)
    dark = sun_at(evaluation.timestamp() * 1000, lat, lon)["alt"] < -6
    return {
        "time": forecast.isoformat(), "local_index": nearest[1], "nearby_index": peak,
        "dark": dark, "possible": dark and peak >= 20,
    }


class SpaceWeather:
    """Share one NOAA poll across dashboards and keep network failures isolated."""

    def __init__(self, hass):
        self.hass = hass
        self.lock = asyncio.Lock()
        self.fetched = float("-inf")
        self.payloads = {}

    async def _fetch(self, path):
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(BASE_URL + path, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return None

    async def snapshot(self):
        async with self.lock:
            if monotonic() - self.fetched >= 300:
                payloads = await asyncio.gather(*(self._fetch(path) for path in FEEDS.values()))
                self.payloads.update((name, data) for name, data in zip(FEEDS, payloads) if data is not None)
                self.fetched = monotonic()
        now = datetime.now(UTC)

        def samples(name):
            payload = self.payloads.get(name)
            if isinstance(payload, dict):
                return [payload]
            return payload if isinstance(payload, list) else []

        forecast = await self.hass.async_add_executor_job(
            aurora_forecast, self.payloads.get("aurora"), now,
            self.hass.config.latitude, self.hass.config.longitude,
        )
        return {
            "kp": latest(samples("kp"), "estimated_kp", now, 20),
            "wind": latest(samples("wind"), "proton_speed", now, 20),
            "bz": latest(samples("bz"), "bz_gsm", now, 20, active_only=True),
            "aurora": forecast,
        }
