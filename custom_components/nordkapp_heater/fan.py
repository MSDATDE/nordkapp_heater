"""Fan platform for Nordkapp Heater (gear level control)."""

from __future__ import annotations

import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, GEAR_MAX, GEAR_MIN, MODE_AUTO, MODE_MANUAL, RUNNING_STATES
from .coordinator import NordkappHeaterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NordkappHeaterFan(coordinator, entry)])


class NordkappHeaterFan(
    CoordinatorEntity[NordkappHeaterCoordinator], FanEntity
):
    _attr_has_entity_name = True
    _attr_translation_key = "gear"
    _attr_speed_count = GEAR_MAX
    _attr_supported_features = FanEntityFeature.SET_SPEED

    def __init__(
        self, coordinator: NordkappHeaterCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['address']}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["address"])},
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.available

    @property
    def is_on(self) -> bool:
        d = self.coordinator.data
        return (
            d.machine_status in RUNNING_STATES
            and d.run_mode == MODE_MANUAL
        )

    @property
    def percentage(self) -> int | None:
        d = self.coordinator.data
        if d.machine_status not in RUNNING_STATES:
            return 0
        return min(d.gear * (100 // GEAR_MAX), 100)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.coordinator.async_set_mode(MODE_AUTO)
            return
        gear = max(GEAR_MIN, min(GEAR_MAX, math.ceil(percentage / (100 / GEAR_MAX))))
        await self.coordinator.async_set_gear(gear)

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs
    ) -> None:
        await self.coordinator.async_set_mode(MODE_MANUAL)
        if percentage is not None:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_mode(MODE_AUTO)
