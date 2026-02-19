"""Climate platform for Nordkapp Heater."""

from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    HEATING_STATES,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_START_STOP,
    TEMP_MAX,
    TEMP_MIN,
)
from .coordinator import NordkappHeaterCoordinator, NordkappHeaterData

PRESET_AUTO = "auto"
PRESET_MANUAL = "manual"
PRESET_START_STOP = "start_stop"

PRESET_TO_MODE = {
    PRESET_AUTO: MODE_AUTO,
    PRESET_MANUAL: MODE_MANUAL,
    PRESET_START_STOP: MODE_START_STOP,
}

MODE_TO_PRESET = {v: k for k, v in PRESET_TO_MODE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NordkappHeaterClimate(coordinator, entry)])


class NordkappHeaterClimate(
    CoordinatorEntity[NordkappHeaterCoordinator], ClimateEntity
):
    _attr_has_entity_name = True
    _attr_translation_key = "heater"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.FAN_ONLY]
    _attr_preset_modes = [PRESET_AUTO, PRESET_MANUAL, PRESET_START_STOP]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(
        self, coordinator: NordkappHeaterCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['address']}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["address"])},
            name=entry.title,
            manufacturer="Nordkapp",
            model="Diesel Heater",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.available

    @property
    def _data(self) -> NordkappHeaterData:
        return self.coordinator.data

    @property
    def current_temperature(self) -> float | None:
        return self._data.ambient_temp

    @property
    def target_temperature(self) -> float | None:
        return float(self._data.target_temp) if self._data.target_temp else None

    @property
    def hvac_mode(self) -> HVACMode:
        ms = self._data.machine_status
        if ms in HEATING_STATES:
            return HVACMode.HEAT
        if ms == 8:  # ventilation
            return HVACMode.FAN_ONLY
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        ms = self._data.machine_status
        if ms == 1:  # igniting
            return HVACAction.PREHEATING
        if ms in (2, 3, 9):  # running
            return HVACAction.HEATING
        if ms == 8:  # ventilation
            return HVACAction.FAN
        if ms == 4:  # residual burn
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def preset_mode(self) -> str | None:
        return MODE_TO_PRESET.get(self._data.run_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            ms = self._data.machine_status
            if ms not in HEATING_STATES:
                await self.coordinator.async_power_on()
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self.coordinator.async_ventilation()
        elif hvac_mode == HVACMode.OFF:
            ms = self._data.machine_status
            if ms != 5:  # not standby
                await self.coordinator.async_power_off()

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.async_set_temperature(int(temp))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = PRESET_TO_MODE.get(preset_mode)
        if mode is not None:
            await self.coordinator.async_set_mode(mode)
