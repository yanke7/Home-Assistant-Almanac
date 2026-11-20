"""Exercise the integration against real Home Assistant classes."""
import asyncio
import importlib
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from types import MappingProxyType

class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        satellite_feed = patch("custom_components.almanac.iss.ISSPasses.next_pass", new_callable=AsyncMock, return_value=None)
        satellite_feed.start()
        self.addCleanup(satellite_feed.stop)
        self.temp=tempfile.TemporaryDirectory()
        self.hass=HomeAssistant(self.temp.name)
        self.hass.config_entries=ConfigEntries(self.hass,{})
        from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
        self.hass.data[DATA_EXTRA_MODULE_URL] = set()
        self.hass.config.latitude=52.13
        self.hass.config.longitude=-106.67
        self.hass.config.time_zone='America/Regina'

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def entry(self):
        return ConfigEntry(state=ConfigEntryState.SETUP_IN_PROGRESS, domain='almanac', title='Almanac', data={}, options={}, source='user', version=1, minor_version=1, unique_id=None, discovery_keys=MappingProxyType({}), subentries_data=[])

    async def test_setup_and_unload(self):
        integration=importlib.import_module('custom_components.almanac')
        entry=self.entry()
        self.hass.config_entries.async_forward_entry_setups=AsyncMock()
        self.hass.config_entries.async_unload_platforms=AsyncMock(return_value=True)
        self.assertTrue(await integration.async_setup_entry(self.hass,entry))
        from custom_components.almanac.const import CARD_URL
        from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
        self.assertIn(CARD_URL, self.hass.data[DATA_EXTRA_MODULE_URL])
        self.assertTrue(entry.runtime_data._listeners)
        self.assertGreater(entry.runtime_data.data['values']['moon_distance'],300000)
        self.hass.config_entries.async_forward_entry_setups.assert_awaited_once()
        self.assertTrue(await integration.async_unload_entry(self.hass,entry))
        self.hass.config_entries.async_unload_platforms.assert_awaited_once()
        self.assertNotIn(CARD_URL, self.hass.data[DATA_EXTRA_MODULE_URL])

    async def test_sensor_contracts(self):
        from custom_components.almanac.coordinator import AlmanacCoordinator
        from custom_components.almanac.sensor import AlmanacSensor, DESCRIPTIONS
        from custom_components.almanac.binary_sensor import AlmanacBinarySensor, DESCRIPTIONS as BINARY
        c=AlmanacCoordinator(self.hass,self.entry())
        await c.async_refresh()
        entry=self.entry()
        for description in DESCRIPTIONS:
            entity=AlmanacSensor(c,entry,description)
            self.assertIsNotNone(entity.unique_id)
            if description.key.startswith('next_') and entity.native_value:
                self.assertIsNotNone(entity.native_value.tzinfo)
        for description in BINARY:
            self.assertIsInstance(AlmanacBinarySensor(c,entry,description).is_on,bool)
        await c.async_shutdown()

    async def test_single_config_entry(self):
        from custom_components.almanac.config_flow import AlmanacConfigFlow
        flow=AlmanacConfigFlow();flow.hass=self.hass
        flow._async_current_entries=lambda: []
        form=await flow.async_step_user()
        self.assertEqual(form['type'],'form')
        created=await flow.async_step_user({})
        self.assertEqual(created['type'],'create_entry')
        flow._async_current_entries=lambda: [MagicMock()]
        duplicate=await flow.async_step_user({})
        self.assertEqual(duplicate['reason'],'single_instance_allowed')

if __name__=='__main__': unittest.main()
