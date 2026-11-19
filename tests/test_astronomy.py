"""Astronomy contracts, including difficult local days and JS parity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('astronomy', ROOT / 'custom_components/almanac/astronomy.py')
astro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(astro)

class AstronomyTests(unittest.TestCase):
    def snap(self, at='2026-11-19T23:15:00+00:00', lat=52.13, lon=-106.67, tz='America/Regina'):
        return astro.snapshot(datetime.fromisoformat(at), lat, lon, tz)

    def test_js_parity(self):
        for at, lat, lon, tz in [('2026-11-19T23:15:00+00:00',52.13,-106.67,'America/Regina'), ('2026-06-21T12:00:00+00:00',-33.87,151.21,'Australia/Sydney')]:
            result=self.snap(at,lat,lon,tz)
            js=json.loads(subprocess.check_output(['node', str(ROOT/'tests/parity.cjs'), at,str(lat),str(lon),tz],text=True))
            for body in ['sun','moon','illumination']:
                for key in js[body]:
                    self.assertAlmostEqual(result[body][key],js[body][key],places=7)
            self.assertAlmostEqual(result['days'][1]['rise'],js['day']['rise'],delta=1)
            self.assertAlmostEqual(result['days'][1]['set'],js['day']['set'],delta=1)

    def test_dst_boundaries(self):
        for at,hours in [('2026-03-08T18:00:00+00:00',23),('2026-11-01T18:00:00+00:00',25)]:
            d=self.snap(at,41,-88,'America/Chicago')['days'][1]
            self.assertEqual(d['end']-d['d0'],hours*3600000)
            self.assertEqual(d['t'][-1],d['end'])
            self.assertEqual(len(d['t']),hours*30+1)

    def test_half_hour_zone(self):
        d=self.snap('2026-03-08T12:00:00+00:00',28.6,77.2,'Asia/Kolkata')['days'][1]
        self.assertEqual(datetime.fromtimestamp(d['d0']/1000,timezone.utc).isoformat(),'2026-03-07T18:30:00+00:00')

    def test_polar_day_and_night(self):
        for at,length in [('2026-06-21T12:00:00+00:00',86400000),('2026-12-21T12:00:00+00:00',0)]:
            data=self.snap(at,80,0,'UTC');d=data['days'][1]
            self.assertIsNone(d['rise']);self.assertIsNone(d['set']);self.assertEqual(d['len'],length)
            self.assertIsNone(data['values']['next_sunrise'])
            self.assertIsNone(data['values']['next_sunset'])

    def test_future_events_and_values(self):
        d=self.snap()
        for key in ['next_sunrise','next_sunset','next_moonrise','next_moonset','next_dawn','next_dusk']:
            self.assertGreater(d['values'][key],d['now'])
        self.assertEqual(d['values']['sky_period'],'golden')
        self.assertTrue(0<=d['values']['moon_illumination']<=100)
        self.assertTrue(0<=d['values']['moon_azimuth']<360)
        json.dumps(d,allow_nan=False)

    def test_invalid_location(self):
        for lat,lon in [(91,0),(0,181),(float('nan'),0)]:
            with self.assertRaises(ValueError): self.snap(lat=lat,lon=lon)

if __name__=='__main__': unittest.main()
