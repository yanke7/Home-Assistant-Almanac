"""Almanac sun and moon sensors with a bundled dashboard card."""
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import CARD_URL, DOMAIN
from .coordinator import AlmanacCoordinator
from .space_weather import SpaceWeather

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


@websocket_api.websocket_command({vol.Required("type"): "almanac/snapshot", vol.Optional("chart_key"): str})
@websocket_api.async_response
async def websocket_snapshot(hass, connection, msg):
    """Return the same read-only snapshot used by the entities."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries or not entries[0].runtime_data.last_update_success:
        connection.send_error(msg["id"], "not_loaded", "Set up Almanac in Devices & services")
        return
    data = entries[0].runtime_data.data
    location = data["location"]
    chart_key = f'{location["latitude"]},{location["longitude"]},{location["time_zone"]},{data["days"][1]["d0"]}'
    result = {**data, "chart_key": chart_key}
    if msg.get("chart_key") == chart_key:
        result.pop("days")
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "almanac/space_weather"})
@websocket_api.async_response
async def websocket_space_weather(hass, connection, msg):
    """Return NOAA observations and local aurora potential."""
    connection.send_result(msg["id"], await hass.data["almanac_space_weather"].snapshot())


async def async_setup(hass, config):
    """Register the local card and authenticated WebSocket command once."""
    await hass.http.async_register_static_paths([
        StaticPathConfig("/almanac/almanac-sky-card.js",
                         str(Path(__file__).parent / "www" / "almanac-sky-card.js"), False)
    ])
    hass.data["almanac_space_weather"] = SpaceWeather(hass)
    websocket_api.async_register_command(hass, websocket_space_weather)
    websocket_api.async_register_command(hass, websocket_snapshot)
    return True


async def async_setup_entry(hass, entry):
    """Set up the home location and its sensors."""
    coordinator = AlmanacCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_add_listener(lambda: None))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    frontend.add_extra_js_url(hass, CARD_URL)
    return True


async def async_unload_entry(hass, entry):
    """Unload entities and stop background updates."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    frontend.remove_extra_js_url(hass, CARD_URL)
    await entry.runtime_data.async_shutdown()
    return True
