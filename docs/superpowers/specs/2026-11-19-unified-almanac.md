# Unified Almanac

One Marketplace integration installs the existing dashboard card and local backend sensors. Home Assistant's configured location and time zone are the single source of location settings. No external APIs, credentials, or runtime astronomy dependencies. Preserve `custom:almanac-sky-card`, its visual design, and the user's existing dashboard and home link.

Port the card's approximate astronomy to Python and verify cross-language parity. A coordinator updates every minute without browsers. Sensors expose sun/moon altitude and azimuth, phase/illumination/age/distance, next rise/set, dawn/dusk, solar noon, evening golden hour, daylight and daily change, sky period; two binary sensors expose horizon status. Polar missing events are unknown, never fabricated. Timestamp entities are UTC aware. DST days follow actual local midnight boundaries.

Bundle and auto-load the card from the integration. The live view consumes backend snapshots; interactive previews retain the same astronomical formulas for smooth scrubbing. Show a local-calculation status when backend data is absent/stale. Single config entry, setup/unload/reload supported. Existing dashboard stays untouched; new users add the bundled card to a panel view.

Ship as 2.0.0 with migration instructions and integration-category HACS/hassfest checks. Change the existing catalog submission from plugin to integration. Preserve the old release and resource configuration for rollback. Install and verify sensors before removing the former standalone resource. Restart HA only if custom-component discovery needs it; preserve current dashboard settings throughout.
