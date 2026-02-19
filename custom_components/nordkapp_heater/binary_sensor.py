"""Binary sensor platform for Nordkapp Heater."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, RUNNING_STATES
from .coordinator import NordkappHeaterCoordinator, NordkappHeaterData


@dataclass(frozen=True, kw_only=True)
class NordkappBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[NordkappHeaterData], bool]


BINARY_SENSORS: tuple[NordkappBinarySensorDescription, ...] = (
    NordkappBinarySensorDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.machine_status in RUNNING_STATES,
    ),
    NordkappBinarySensorDescription(
        key="error",
        translation_key="error_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.error_code != 0,
    ),
    NordkappBinarySensorDescription(
        key="glow_plug",
        translation_key="glow_plug",
        icon="mdi:lightning-bolt",
        value_fn=lambda d: d.glow_plug_active,
    ),
    NordkappBinarySensorDescription(
        key="pump",
        translation_key="pump_active",
        icon="mdi:pump",
        value_fn=lambda d: d.pump_active,
    ),
    NordkappBinarySensorDescription(
        key="fan",
        translation_key="fan_active",
        icon="mdi:fan",
        value_fn=lambda d: d.fan_active,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NordkappHeaterBinarySensor(coordinator, entry, desc)
        for desc in BINARY_SENSORS
    )


class NordkappHeaterBinarySensor(
    CoordinatorEntity[NordkappHeaterCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    entity_description: NordkappBinarySensorDescription

    def __init__(
        self,
        coordinator: NordkappHeaterCoordinator,
        entry: ConfigEntry,
        description: NordkappBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data['address']}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["address"])},
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.available

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)
