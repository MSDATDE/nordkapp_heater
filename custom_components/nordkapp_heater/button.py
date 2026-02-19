"""Button platform for Nordkapp Heater."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NordkappHeaterCoordinator


@dataclass(frozen=True, kw_only=True)
class NordkappButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[NordkappHeaterCoordinator], Coroutine[Any, Any, None]]


BUTTONS: tuple[NordkappButtonDescription, ...] = (
    NordkappButtonDescription(
        key="clear_error",
        translation_key="clear_error",
        icon="mdi:alert-remove",
        press_fn=lambda c: c.async_clear_error(),
    ),
    NordkappButtonDescription(
        key="ventilation",
        translation_key="ventilation",
        icon="mdi:air-filter",
        press_fn=lambda c: c.async_ventilation(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NordkappHeaterButton(coordinator, entry, desc) for desc in BUTTONS
    )


class NordkappHeaterButton(
    CoordinatorEntity[NordkappHeaterCoordinator], ButtonEntity
):
    _attr_has_entity_name = True
    entity_description: NordkappButtonDescription

    def __init__(
        self,
        coordinator: NordkappHeaterCoordinator,
        entry: ConfigEntry,
        description: NordkappButtonDescription,
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

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator)
