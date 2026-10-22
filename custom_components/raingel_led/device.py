"""BLE connection and command encoding for VC-BLELIGHT controllers."""

from __future__ import annotations

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

try:
    from dbus_fast import BusType, Message, MessageType, Variant
    from dbus_fast.aio import MessageBus
except ImportError:  # not on Linux/BlueZ
    MessageBus = None

from .const import (
    CHAR_WRITE,
    DISCONNECT_DELAY,
    MUSIC_SENSITIVITY,
    OP_BRIGHTNESS,
    OP_COLOR,
    OP_MIC,
    OP_MODE,
    OP_POWER,
)

_LOGGER = logging.getLogger(__name__)


def _byte(value: float, top: int = 255) -> int:
    return max(0, min(top, int(round(value))))


def cmd_power(on: bool) -> bytes:
    return bytes([OP_POWER, 1 if on else 0])


def cmd_brightness(level: int) -> bytes:
    """Global brightness, 0-255."""
    return bytes([OP_BRIGHTNESS, _byte(level)])


def cmd_color(r: int, g: int, b: int) -> bytes:
    """Static colour; cancels any running effect."""
    return bytes([OP_COLOR, _byte(r), _byte(g), _byte(b), 0, 0, 0])


def cmd_mic(sensitivity: int, mode: int) -> bytes:
    """Start a music mode using the lamp's microphone. Sensitivity is 0-100.

    The mode byte comes first, confirmed on hardware.
    """
    return bytes([OP_MIC, mode & 0x03, _byte(sensitivity, 100)])


def _palette(indices: tuple[int, ...]) -> bytes:
    nib = list(indices) + [0] * (8 - len(indices))
    packed = [(nib[i] << 4) | nib[i + 1] for i in range(0, 8, 2)]
    return bytes([len(indices), *packed])


def cmd_mode(
    mode_id: int, speed: int, brightness_pct: int, palette: tuple[int, ...]
) -> bytes:
    """Start a firmware effect. Speed and brightness run 0-100."""
    return bytes(
        [OP_MODE, mode_id & 0x1F, _byte(speed, 100), _byte(brightness_pct, 100)]
    ) + _palette(palette)


async def _prefer_le_bearer(ble_device: BLEDevice) -> None:
    """Make BlueZ connect over LE instead of BR/EDR.

    The controller advertises flags 0x0A, which don't mark BR/EDR as
    unsupported, so BlueZ treats it as dual-mode and tries a classic
    connection first, failing with "br-connection-profile-unavailable".
    PreferredBearer (BlueZ experimental, enabled on HA OS) overrides that.
    Proxies such as ESPHome don't have a D-Bus path and don't need this.
    """
    details = ble_device.details
    path = details.get("path") if isinstance(details, dict) else None
    if MessageBus is None or not path:
        return
    bus = None
    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        reply = await bus.call(
            Message(
                destination="org.bluez",
                path=path,
                interface="org.freedesktop.DBus.Properties",
                member="Set",
                signature="ssv",
                body=["org.bluez.Device1", "PreferredBearer", Variant("s", "le")],
            )
        )
        if reply.message_type == MessageType.ERROR:
            _LOGGER.warning(
                "Could not set PreferredBearer=le on %s (%s: %s); BlueZ may be"
                " too old, so the connection may fall back to BR/EDR",
                path,
                reply.error_name,
                reply.body,
            )
        else:
            _LOGGER.debug("Set PreferredBearer=le on %s", path)
    except Exception:  # noqa: BLE001 - best effort, connection may still work
        _LOGGER.debug("Failed to set PreferredBearer on %s", path, exc_info=True)
    finally:
        if bus:
            bus.disconnect()


class RaingelDevice:
    """Holds a lazily opened BLE connection to one light."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._disconnect_timer: asyncio.TimerHandle | None = None
        # Shared by the light and number entities.
        self.music_sensitivity = MUSIC_SENSITIVITY
        self.music_mode: int | None = None  # active music mode id, if any

    @property
    def address(self) -> str:
        return self._ble_device.address

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLEDevice (e.g. when a different proxy sees it)."""
        self._ble_device = ble_device

    async def send(self, *commands: bytes) -> None:
        async with self._lock:
            for attempt in range(2):
                try:
                    client = await self._ensure_connected()
                    for command in commands:
                        _LOGGER.debug("%s <- %s", self.address, command.hex(" "))
                        await client.write_gatt_char(
                            CHAR_WRITE, command, response=False
                        )
                    break
                except BleakError:
                    await self._disconnect()
                    if attempt:
                        raise
            self._schedule_disconnect()

    async def _ensure_connected(self) -> BleakClientWithServiceCache:
        if self._client and self._client.is_connected:
            return self._client
        await _prefer_le_bearer(self._ble_device)
        self._client = await establish_connection(
            BleakClientWithServiceCache,
            self._ble_device,
            self._ble_device.name or self.address,
            ble_device_callback=lambda: self._ble_device,
        )
        return self._client

    def _schedule_disconnect(self) -> None:
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        loop = asyncio.get_running_loop()
        self._disconnect_timer = loop.call_later(
            DISCONNECT_DELAY, lambda: loop.create_task(self._timed_disconnect())
        )

    async def _timed_disconnect(self) -> None:
        async with self._lock:
            await self._disconnect()

    async def _disconnect(self) -> None:
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None
        client, self._client = self._client, None
        if client and client.is_connected:
            try:
                await client.disconnect()
            except BleakError:
                _LOGGER.debug("Error disconnecting from %s", self.address)

    async def stop(self) -> None:
        async with self._lock:
            await self._disconnect()
