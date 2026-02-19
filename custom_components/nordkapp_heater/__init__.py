"""Nordkapp Heater integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import NordkappHeaterCoordinator

_LOGGER = logging.getLogger(__name__)

type NordkappHeaterConfigEntry = ConfigEntry[NordkappHeaterCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: NordkappHeaterConfigEntry
) -> bool:
    """Set up Nordkapp Heater from a config entry."""
    coordinator = NordkappHeaterCoordinator(
        hass, entry.data["address"], entry
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: NordkappHeaterConfigEntry
) -> bool:
    """Unload Nordkapp Heater config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: NordkappHeaterCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
