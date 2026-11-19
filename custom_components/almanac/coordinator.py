"""Keep astronomy current even when no dashboard is open."""
from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .astronomy import snapshot
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AlmanacCoordinator(DataUpdateCoordinator):
    """Calculate one consistent snapshot for entities and the card."""

    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=60))

    async def _async_update_data(self):
        return await self.hass.async_add_executor_job(
            snapshot, dt_util.utcnow(), self.hass.config.latitude,
            self.hass.config.longitude, self.hass.config.time_zone,
        )
