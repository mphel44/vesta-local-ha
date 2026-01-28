"""DataUpdateCoordinator for Vesta/Climax Local integration.

This module manages data polling and state updates for the alarm panel.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    VestaApiError,
    VestaAuthenticationError,
    VestaConnectionError,
    VestaData,
    VestaLocalClient,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class VestaDataUpdateCoordinator(DataUpdateCoordinator[VestaData]):
    """Coordinator for managing Vesta panel data updates.

    This coordinator handles polling the panel at regular intervals and
    distributes the data to all entities that depend on it.

    Attributes:
        client: The VestaLocalClient instance for API communication.
        config_entry: The config entry for this coordinator.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: VestaLocalClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            client: The VestaLocalClient for API communication.
            config_entry: The config entry for this integration instance.
        """
        self.client = client
        self.config_entry = config_entry

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        _LOGGER.debug(
            "Coordinator initialized for %s with %ds interval",
            client.host,
            DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> VestaData:
        """Fetch data from the panel.

        This method is called by the coordinator at the configured interval
        to refresh all data from the panel.

        Returns:
            VestaData containing panel status and device list.

        Raises:
            UpdateFailed: If the update fails.
        """
        try:
            data = await self.client.get_all_data()
            _LOGGER.debug(
                "Updated data: mode=%s, devices=%d",
                data.panel.mode,
                len(data.devices),
            )
            return data

        except VestaAuthenticationError as err:
            _LOGGER.error("Authentication failed during update: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err

        except VestaConnectionError as err:
            _LOGGER.warning("Connection error during update: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err

        except VestaApiError as err:
            _LOGGER.error("API error during update: %s", err)
            raise UpdateFailed(f"API error: {err}") from err

        except Exception as err:
            _LOGGER.exception("Unexpected error during update: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_set_alarm_mode(self, mode: int, area: int = 1) -> bool:
        """Set the alarm mode and refresh data.

        Args:
            mode: The mode to set (0=Disarm, 1=Arm Away, 2=Arm Home).
            area: The area number. Default is 1.

        Returns:
            True if successful.
        """
        result = await self.client.set_alarm_mode(mode, area)
        if result:
            # Refresh data immediately after mode change
            await self.async_request_refresh()
        return result
