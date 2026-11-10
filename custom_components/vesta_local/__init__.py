"""Vesta/Climax Local integration for Home Assistant.

This integration provides local control of Vesta/Climax alarm panels
via their HTTP CGI interface, without requiring cloud connectivity.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .client import (
    VestaAuthenticationError,
    VestaConnectionError,
    VestaLocalClient,
)
from .const import CONF_USE_SSL, DOMAIN, MANUFACTURER, PANEL_MODEL
from .coordinator import VestaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

type VestaConfigEntry = ConfigEntry[VestaDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VestaConfigEntry) -> bool:
    """Set up Vesta/Climax Local from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being set up.

    Returns:
        True if setup was successful.

    Raises:
        ConfigEntryAuthFailed: If authentication fails.
        ConfigEntryNotReady: If the panel is not reachable.
    """
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    use_ssl = entry.data.get(CONF_USE_SSL, False)

    _LOGGER.debug("Setting up Vesta Local integration for %s (SSL: %s)", host, use_ssl)

    # Create the API client
    client = VestaLocalClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False,
        use_ssl=use_ssl,
    )

    # Test the connection
    try:
        await client.authenticate()
    except VestaAuthenticationError as err:
        await client.close()
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except VestaConnectionError as err:
        await client.close()
        raise ConfigEntryNotReady(f"Cannot connect to panel: {err}") from err

    # Create the coordinator
    coordinator = VestaDataUpdateCoordinator(hass, client, entry)

    # Register the panel device up front so the zone devices created by the
    # platforms can point at it with via_device_id.
    panel_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Vesta Panel ({host})",
        manufacturer=MANUFACTURER,
        model=PANEL_MODEL,
    )
    coordinator.panel_device_id = panel_device.id

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator in the entry runtime data
    entry.runtime_data = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Vesta Local integration set up successfully for %s", host)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VestaConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being unloaded.

    Returns:
        True if unload was successful.
    """
    _LOGGER.debug("Unloading Vesta Local integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Close the client session
        coordinator: VestaDataUpdateCoordinator = entry.runtime_data
        await coordinator.client.close()
        _LOGGER.debug("Vesta Local integration unloaded successfully")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: VestaConfigEntry) -> None:
    """Reload a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being reloaded.
    """
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
