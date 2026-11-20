"""Sun and moon measurements and upcoming events."""
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass

from .astronomy import COMPASS_POINTS, PHASE_EVENTS, SOLAR_EVENTS
from .entity import AlmanacEntity


def measurement(key, name, unit, device_class=None, precision=1):
    return SensorEntityDescription(key=key, name=name, native_unit_of_measurement=unit,
                                   device_class=device_class, state_class=SensorStateClass.MEASUREMENT,
                                   suggested_display_precision=precision)


DESCRIPTIONS = (
    measurement("daylight_percentage", "Daylight percentage", "%"),
    measurement("solar_noon_elevation", "Solar noon elevation", "°"),
    *(SensorEntityDescription(key=f"{body}_direction", name=f"{body.title()} direction",
                              device_class=SensorDeviceClass.ENUM, options=COMPASS_POINTS)
      for body in ("sun", "moon")),
    *(SensorEntityDescription(key=f"today_{event}", name="Today " + event.replace("_", " "),
                              device_class=SensorDeviceClass.TIMESTAMP)
      for event in (*SOLAR_EVENTS, "moonrise", "moonset")),
    *(SensorEntityDescription(key=f"next_{event}", name="Next " + event.replace("_", " "),
                              device_class=SensorDeviceClass.TIMESTAMP)
      for event in PHASE_EVENTS),
    measurement("sun_elevation", "Sun elevation", "°"),
    measurement("sun_azimuth", "Sun azimuth", "°"),
    measurement("moon_elevation", "Moon elevation", "°"),
    measurement("moon_azimuth", "Moon azimuth", "°"),
    measurement("moon_illumination", "Moon illumination", "%"),
    measurement("moon_age", "Moon age", "d", SensorDeviceClass.DURATION),
    measurement("moon_distance", "Moon distance", "km", SensorDeviceClass.DISTANCE, 0),
    measurement("daylight_duration", "Daylight duration", "min", SensorDeviceClass.DURATION),
    measurement("daylight_change", "Daylight change", "s", SensorDeviceClass.DURATION, 0),
    SensorEntityDescription(key="sky_period", name="Sky period", device_class=SensorDeviceClass.ENUM,
                            options=["day", "golden", "twilight", "night"], icon="mdi:theme-light-dark"),
    SensorEntityDescription(key="moon_phase", name="Moon phase", device_class=SensorDeviceClass.ENUM,
                            options=["new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
                                     "full_moon", "waning_gibbous", "last_quarter", "waning_crescent"], icon="mdi:moon-waxing-crescent"),
    *(SensorEntityDescription(key=key, name=name, device_class=SensorDeviceClass.TIMESTAMP)
      for key, name in (
          ("dark_sky_window_start", "Dark sky window start"),
          ("dark_sky_window_end", "Dark sky window end"),
          ("next_iss_pass_start", "Next ISS pass start"),
          ("next_sunrise", "Next sunrise"), ("next_sunset", "Next sunset"),
          ("next_dawn", "Next dawn"), ("next_dusk", "Next dusk"),
          ("next_solar_noon", "Next solar noon"), ("next_golden_hour", "Next evening golden hour"),
          ("next_moonrise", "Next moonrise"), ("next_moonset", "Next moonset"),
      )),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(AlmanacSensor(entry.runtime_data, entry, d) for d in DESCRIPTIONS)


class AlmanacSensor(AlmanacEntity, SensorEntity):
    @property
    def native_value(self):
        value = self.coordinator.data["values"].get(self.entity_description.key)
        if value is not None and self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            return datetime.fromtimestamp(value / 1000, timezone.utc)
        return value
