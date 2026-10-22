"""Music sensitivity slider for Raingel LED."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RaingelConfigEntry
from .const import DOMAIN
from .device import RaingelDevice, cmd_mic


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RaingelConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RaingelMusicSensitivity(entry.runtime_data, entry.title)])


class RaingelMusicSensitivity(RestoreNumber):
    """How strongly the lamp's microphone reacts in the music modes."""

    _attr_has_entity_name = True
    _attr_translation_key = "music_sensitivity"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:microphone"

    def __init__(self, device: RaingelDevice, title: str) -> None:
        self._device = device
        self._attr_unique_id = f"{device.address}_music_sensitivity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.address)},
            connections={(dr.CONNECTION_BLUETOOTH, device.address)},
            name=title,
        )

    @property
    def native_value(self) -> float:
        return self._device.music_sensitivity

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None:
            if last.native_value is not None:
                self._device.music_sensitivity = int(last.native_value)

    async def async_set_native_value(self, value: float) -> None:
        self._device.music_sensitivity = int(value)
        if (mode := self._device.music_mode) is not None:
            await self._device.send(cmd_mic(self._device.music_sensitivity, mode))
        self.async_write_ha_state()
