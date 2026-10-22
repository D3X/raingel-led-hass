"""Light entity for Raingel LED."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import RaingelConfigEntry
from .const import (
    DOMAIN,
    EFFECT_PALETTE,
    EFFECT_SPEED,
    EFFECTS,
    MUSIC_EFFECTS,
)
from .device import (
    RaingelDevice,
    cmd_brightness,
    cmd_color,
    cmd_mic,
    cmd_mode,
    cmd_power,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RaingelConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RaingelLight(entry.runtime_data, entry.title)])


class RaingelLight(LightEntity, RestoreEntity):
    """The controller only accepts writes, so state is assumed and restored."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = [*EFFECTS, *MUSIC_EFFECTS]

    def __init__(self, device: RaingelDevice, title: str) -> None:
        self._device = device
        self._attr_unique_id = device.address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.address)},
            connections={(dr.CONNECTION_BLUETOOTH, device.address)},
            name=title,
            manufacturer="DoHome (Raingel)",
            model="VC-BLELIGHT",
        )
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_effect = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is None:
            return
        self._attr_is_on = last.state == STATE_ON
        if (brightness := last.attributes.get(ATTR_BRIGHTNESS)) is not None:
            self._attr_brightness = brightness
        if (rgb := last.attributes.get(ATTR_RGB_COLOR)) is not None:
            self._attr_rgb_color = tuple(rgb)
        if last.attributes.get(ATTR_EFFECT) in self._attr_effect_list:
            self._attr_effect = last.attributes[ATTR_EFFECT]
        self._sync_music_mode()

    async def async_turn_on(self, **kwargs: Any) -> None:
        commands: list[bytes] = []
        if not self._attr_is_on:
            commands.append(cmd_power(True))

        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness)

        if kwargs.get(ATTR_EFFECT) in MUSIC_EFFECTS:
            self._attr_effect = kwargs[ATTR_EFFECT]
            commands.append(
                cmd_mic(
                    self._device.music_sensitivity, MUSIC_EFFECTS[self._attr_effect]
                )
            )
            if ATTR_BRIGHTNESS in kwargs:
                commands.append(cmd_brightness(round(brightness / 255 * 100)))
        elif ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] in EFFECTS:
            self._attr_effect = kwargs[ATTR_EFFECT]
            commands.append(self._effect_command(brightness))
        elif ATTR_RGB_COLOR in kwargs:
            self._attr_effect = None
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
            commands.append(cmd_color(*self._attr_rgb_color))
            commands.append(cmd_brightness(round(brightness / 255 * 100)))
        elif ATTR_BRIGHTNESS in kwargs:
            if self._attr_effect in MUSIC_EFFECTS:
                commands.append(cmd_brightness(round(brightness / 255 * 100)))
            elif self._attr_effect:
                # Effects carry their own brightness byte.
                commands.append(self._effect_command(brightness))
            else:
                commands.append(cmd_brightness(round(brightness / 255 * 100)))

        await self._device.send(*commands)
        self._attr_brightness = brightness
        self._attr_is_on = True
        self._sync_music_mode()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.send(cmd_power(False))
        self._attr_is_on = False
        self._sync_music_mode()
        self.async_write_ha_state()

    def _sync_music_mode(self) -> None:
        """Tell the sensitivity slider whether a music mode is running."""
        active = self._attr_is_on and self._attr_effect in MUSIC_EFFECTS
        self._device.music_mode = MUSIC_EFFECTS[self._attr_effect] if active else None

    def _effect_command(self, brightness: int) -> bytes:
        return cmd_mode(
            EFFECTS[self._attr_effect],
            EFFECT_SPEED,
            round(brightness / 255 * 100),
            EFFECT_PALETTE,
        )
