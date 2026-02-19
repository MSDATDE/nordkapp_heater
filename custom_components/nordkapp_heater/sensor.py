"""Sensor platform for Nordkapp Heater."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfLength,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MACHINE_STATUS
from .coordinator import NordkappHeaterCoordinator, NordkappHeaterData


@dataclass(frozen=True, kw_only=True)
class NordkappSensorDescription(SensorEntityDescription):
    value_fn: Callable[[NordkappHeaterData], float | int | str | None]


SENSORS: tuple[NordkappSensorDescription, ...] = (
    NordkappSensorDescription(
        key="ambient_temp",
        translation_key="ambient_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.ambient_temp,
    ),
    NordkappSensorDescription(
        key="shell_temp",
        translation_key="shell_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.shell_temp,
    ),
    NordkappSensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.voltage,
    ),
    NordkappSensorDescription(
        key="fan_rpm",
        translation_key="fan_rpm",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda d: d.fan_rpm,
    ),
    NordkappSensorDescription(
        key="pump_freq",
        translation_key="pump_freq",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pump",
        value_fn=lambda d: d.pump_freq,
    ),
    NordkappSensorDescription(
        key="heater_state",
        translation_key="heater_state",
        icon="mdi:radiator",
        value_fn=lambda d: MACHINE_STATUS.get(d.machine_status, "unknown"),
    ),
    NordkappSensorDescription(
        key="error_code",
        translation_key="error_code",
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.error_code,
    ),
    NordkappSensorDescription(
        key="altitude",
        translation_key="altitude",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:altimeter",
        value_fn=lambda d: d.altitude,
    ),
    NordkappSensorDescription(
        key="target_temp",
        translation_key="target_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: float(d.target_temp) if d.target_temp else None,
    ),
    NordkappSensorDescription(
        key="gear_level",
        translation_key="gear_level",
        icon="mdi:speedometer",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.gear,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NordkappHeaterSensor(coordinator, entry, desc) for desc in SENSORS
    )


class NordkappHeaterSensor(
    CoordinatorEntity[NordkappHeaterCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    entity_description: NordkappSensorDescription

    def __init__(
        self,
        coordinator: NordkappHeaterCoordinator,
        entry: ConfigEntry,
        description: NordkappSensorDescription,
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
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data)
