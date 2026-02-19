"""BLE coordinator for Nordkapp Heater."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import timedelta

from bleak import BleakClient, BleakError
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    BTN_CLEAR_ERROR,
    BTN_POWER_OFF,
    BTN_POWER_ON,
    BTN_VENTILATION,
    CMD_AUTO_UPDATA,
    CMD_BUTTON,
    CMD_SHORT_PARA,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    NOTIFY_CHAR_UUID,
    PARA_RUN_MODE,
    PARA_TARGET_GEAR,
    PARA_TARGET_TEMP,
    RESP_BIND_ACCEPTED,
    RESP_BIND_REQUEST,
    RESP_CMD_ACK,
    RESP_PARA,
    RESP_STATUS,
    SERVICE_CHANGED_UUID,
    STATUS_PACKET_MIN_LENGTH,
    WRITE_CHAR_UUID,
    build_bind_response,
    build_cmd,
    le16,
    le16s,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class NordkappHeaterData:
    """Parsed heater status data."""

    available: bool = False
    machine_status: int = 5  # standby
    run_mode: int = 0  # auto
    voltage: float = 0.0
    altitude: int = 0
    ambient_temp: float | None = None
    shell_temp: float | None = None
    pump_freq: float = 0.0
    ignition_power: float = 0.0
    fan_rpm: int = 0
    error_code: int = 0
    gear: int = 0
    target_temp: int = 0
    pump_active: bool = False
    fan_active: bool = False
    glow_plug_active: bool = False
    temp_unit_fahrenheit: bool = False


class NordkappHeaterCoordinator(DataUpdateCoordinator[NordkappHeaterData]):
    """Manages BLE connection, polling, and commands for Nordkapp Heater."""

    def __init__(
        self, hass: HomeAssistant, address: str, entry: ConfigEntry
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.address = address
        self.entry = entry
        self._client: BleakClient | None = None
        self._connected = False
        self._bound = False
        self._data = NordkappHeaterData()
        self._mac_bytes = [int(b, 16) for b in address.split(":")]
        self._connect_lock = asyncio.Lock()

    async def _async_update_data(self) -> NordkappHeaterData:
        """Connect or send keepalive, return current data."""
        try:
            if not self._connected:
                await self._connect()
            else:
                await self._send_keepalive()
        except Exception as err:
            _LOGGER.debug("Update error: %s", err)
            self._data.available = False
            await self._disconnect()
        return self._data

    async def _connect(self) -> None:
        """Establish BLE connection, subscribe, start polling, bind."""
        async with self._connect_lock:
            if self._connected:
                return

            device = async_ble_device_from_address(self.hass, self.address)

            try:
                self._client = BleakClient(
                    device if device else self.address,
                    timeout=30.0,
                    disconnected_callback=self._handle_disconnect,
                )
                await self._client.connect()
            except (BleakError, TimeoutError, OSError) as err:
                _LOGGER.debug("Cannot connect to %s: %s", self.address, err)
                self._client = None
                self._data.available = False
                return

            self._connected = True
            _LOGGER.info("Connected to Nordkapp Heater %s", self.address)

            try:
                await self._client.start_notify(
                    SERVICE_CHANGED_UUID, lambda _s, _d: None
                )
            except (BleakError, Exception):
                pass

            await self._client.start_notify(
                NOTIFY_CHAR_UUID, self._handle_notification
            )

            # Start status polling
            await self._write(build_cmd(CMD_AUTO_UPDATA, 2, 20, 99))
            await asyncio.sleep(2)

            # Proactive bind
            await self._send_bind()

    async def _disconnect(self) -> None:
        """Clean up BLE connection."""
        self._connected = False
        self._bound = False
        if self._client:
            try:
                await self._client.disconnect()
            except (BleakError, Exception):
                pass
            self._client = None

    def _handle_disconnect(self, _client: BleakClient) -> None:
        """Called by bleak when connection drops."""
        _LOGGER.info("Nordkapp Heater %s disconnected", self.address)
        self._connected = False
        self._bound = False
        self._data.available = False

    @callback
    def _handle_notification(self, _sender: int, raw: bytearray) -> None:
        """Process incoming BLE notification."""
        data = bytes(raw)
        if len(data) < 3 or data[0] != 0xAA:
            return

        cmd = data[2]

        if cmd == RESP_STATUS and len(data) >= STATUS_PACKET_MIN_LENGTH:
            self._parse_status(data)
            self.async_set_updated_data(self._data)
        elif cmd == RESP_BIND_REQUEST:
            _LOGGER.debug("Bind request from heater")
            self.hass.async_create_task(self._delayed_bind())
        elif cmd == RESP_BIND_ACCEPTED:
            _LOGGER.debug("Bind accepted")
            self._bound = True
        elif cmd == RESP_CMD_ACK:
            _LOGGER.debug("Command ACK: btn=%d", data[3] if len(data) > 3 else -1)
        elif cmd == RESP_PARA:
            _LOGGER.debug(
                "Para response: type=%d val=%d",
                data[3] if len(data) > 3 else -1,
                data[5] if len(data) > 5 else -1,
            )

    def _parse_status(self, data: bytes) -> None:
        """Parse 52-byte status broadcast into data fields."""
        d = self._data
        d.available = True

        raw_status = data[8]
        d.machine_status = raw_status & 0x0F

        running = data[9]
        d.run_mode = (running >> 5) & 3
        d.pump_active = (running & 0x03) != 0
        d.fan_active = bool((running >> 2) & 1)
        d.glow_plug_active = bool((running >> 3) & 1)
        d.temp_unit_fahrenheit = bool((running >> 4) & 1)

        d.voltage = le16(data, 10) / 10.0
        d.altitude = le16(data, 12)

        raw_ambient = le16(data, 14)
        d.ambient_temp = le16s(data, 14) / 10.0 if raw_ambient != 32760 else None

        raw_shell = le16(data, 16)
        d.shell_temp = le16s(data, 16) / 10.0 if raw_shell != 32760 else None

        d.pump_freq = le16(data, 18) / 10.0
        d.ignition_power = le16(data, 20) / 10.0
        d.fan_rpm = le16(data, 22)

        d.error_code = le16(data, 28)
        d.gear = data[40]
        d.target_temp = data[41]

    async def _delayed_bind(self) -> None:
        """Respond to bind request after 500ms delay (APK behavior)."""
        await asyncio.sleep(0.5)
        await self._send_bind()

    async def _send_bind(self) -> None:
        """Send 0x91 bind response."""
        if not self._connected or not self._client:
            return
        try:
            cmd = build_bind_response(self._mac_bytes)
            await self._write(cmd)
            _LOGGER.debug("Bind response sent")
        except (BleakError, Exception) as err:
            _LOGGER.debug("Bind failed: %s", err)

    async def _send_keepalive(self) -> None:
        """Send AUTO_UPDATA keepalive."""
        await self._write(build_cmd(CMD_AUTO_UPDATA, 2, 20, 99))

    async def _write(self, cmd: bytearray) -> None:
        """Write command via BLE (writeNoResponse)."""
        if not self._client or not self._connected:
            raise BleakError("Not connected")
        await self._client.write_gatt_char(WRITE_CHAR_UUID, cmd, response=False)

    # --- Public command methods ---

    async def async_power_on(self) -> None:
        """Send power ON command."""
        rnd = random.randint(0, 254)
        await self._write(build_cmd(CMD_BUTTON, BTN_POWER_ON, rnd, 0))

    async def async_power_off(self) -> None:
        """Send power OFF command."""
        rnd = random.randint(0, 254)
        await self._write(build_cmd(CMD_BUTTON, BTN_POWER_OFF, rnd, 0))

    async def async_set_temperature(self, temp: int) -> None:
        """Set target temperature in Celsius."""
        await self._write(build_cmd(CMD_SHORT_PARA, PARA_TARGET_TEMP, 0, temp))

    async def async_set_gear(self, gear: int) -> None:
        """Set gear level (1-10)."""
        await self._write(build_cmd(CMD_SHORT_PARA, PARA_TARGET_GEAR, 0, gear))

    async def async_set_mode(self, mode: int) -> None:
        """Set run mode (0=auto, 1=manual, 2=start-stop)."""
        await self._write(build_cmd(CMD_SHORT_PARA, PARA_RUN_MODE, 0, mode))

    async def async_clear_error(self) -> None:
        """Send clear error command."""
        rnd = random.randint(0, 254)
        await self._write(build_cmd(CMD_BUTTON, BTN_CLEAR_ERROR, rnd, 0))

    async def async_ventilation(self) -> None:
        """Send ventilation mode command."""
        rnd = random.randint(0, 254)
        await self._write(build_cmd(CMD_BUTTON, BTN_VENTILATION, rnd, 0))

    async def async_shutdown(self) -> None:
        """Disconnect on coordinator shutdown."""
        await self._disconnect()
        await super().async_shutdown()
