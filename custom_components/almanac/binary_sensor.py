"""Whether the sun and moon are above the apparent horizon."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from .entity import AlmanacEntity

DESCRIPTIONS = (
    BinarySensorEntityDescription(key="moon_waxing", name="Moon waxing", icon="mdi:moon-waxing-crescent"),
    BinarySensorEntityDescription(key="sun_above_horizon", name="Sun above horizon", icon="mdi:white-balance-sunny"),
    BinarySensorEntityDescription(key="moon_above_horizon", name="Moon above horizon", icon="mdi:moon-waning-crescent"),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(AlmanacBinarySensor(entry.runtime_data, entry, d) for d in DESCRIPTIONS)


class AlmanacBinarySensor(AlmanacEntity, BinarySensorEntity):
    @property
    def is_on(self):
        return self.coordinator.data["values"][self.entity_description.key]
