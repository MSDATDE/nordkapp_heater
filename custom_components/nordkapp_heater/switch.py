"""Switch platform for Nordkapp Heater (power control)."""

from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, RUNNING_STATES
from .coordinator import NordkappHeaterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NordkappHeaterSwitch(coordinator, entry)])


class NordkappHeaterSwitch(
    CoordinatorEntity[NordkappHeaterCoordinator], SwitchEntity
):
    _attr_has_entity_name = True
    _attr_translation_key = "power"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self, coordinator: NordkappHeaterCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['address']}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["address"])},
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.available

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.machine_status in RUNNING_STATES

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_power_on()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_power_off()
