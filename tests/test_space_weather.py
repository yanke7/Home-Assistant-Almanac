"""NOAA observations must be fresh before the dashboard can use them."""
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from custom_components.almanac.space_weather import aurora_forecast, latest


class SpaceWeatherTests(unittest.TestCase):
    def test_latest_active_bz_ignores_stale_and_inactive_readings(self):
        now = datetime(2026, 11, 20, 22, tzinfo=timezone.utc)
        rows = [
            {"active": False, "bz_gsm": -12, "time_tag": "2026-11-20T22:00:00Z"},
            {"active": True, "bz_gsm": -7.5, "time_tag": "2026-11-20T21:58:00"},
            {"active": True, "bz_gsm": -4, "time_tag": "2026-11-20T21:30:00Z"},
        ]
        self.assertEqual(latest(rows, "bz_gsm", now, 20, active_only=True)["value"], -7.5)
        self.assertIsNone(latest(rows[-1:], "bz_gsm", now, 20, active_only=True))

    def test_local_aurora_requires_darkness_and_fresh_forecast(self):
        now = datetime(2026, 11, 20, 22, tzinfo=timezone.utc)
        payload = {
            "Observation Time": "2026-11-20T21:30:00Z",
            "Forecast Time": "2026-11-20T22:10:00Z",
            "coordinates": [[253, 52, 8], [253, 55, 30], [253, 60, 90]],
        }
        target = "custom_components.almanac.space_weather.sun_at"
        with patch(target, return_value={"alt": -12}):
            result = aurora_forecast(payload, now, 52.11, -106.63)
            self.assertTrue(result["possible"])
            self.assertEqual((result["local_index"], result["nearby_index"]), (8, 30))
        with patch(target, return_value={"alt": -1}):
            self.assertFalse(aurora_forecast(payload, now, 52.11, -106.63)["possible"])
        self.assertIsNone(aurora_forecast({**payload, "Forecast Time": "2026-11-20T20:00:00Z"}, now, 52.11, -106.63))
