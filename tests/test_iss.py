"""Regression coverage for the visible portion of a known ISS pass."""
from datetime import datetime, timezone
import unittest

from sgp4.api import Satrec

from custom_components.almanac.astronomy import sun_at
from custom_components.almanac.iss import predict_passes


class ISSPassTests(unittest.TestCase):
    def test_saskatoon_visible_pass(self):
        satellite = Satrec.twoline2rv(
            "1 25544U 98067A   26324.49484039  .00009536  00000+0  17778-3 0  9993",
            "2 25544  51.6319 246.5768 0007409  46.6569 313.5036 15.49509114595987",
        )
        start = int(datetime(2026, 11, 21, tzinfo=timezone.utc).timestamp())
        latitude, longitude = 52.11, -106.63
        passes = predict_passes(satellite, start, start + 3600, latitude, longitude, 500)
        self.assertEqual(len(passes), 1)
        visible = passes[0]
        self.assertAlmostEqual(visible["start"] / 1000 - start, 2015, delta=3)
        self.assertGreater(visible["end"], visible["start"])
        self.assertLess(sun_at(visible["start"], latitude, longitude)["alt"], -6)
        self.assertTrue(all(10 <= alt <= 90 and 0 <= az < 360 for alt, az in visible["points"]))
