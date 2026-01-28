"""Sensor platform for Vesta/Climax Local integration.

This module provides diagnostic sensors for the alarm panel including
battery status and GSM signal strength.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import VestaPanelEntity

if TYPE_CHECKING:
    from . import VestaConfigEntry
    from .client import VestaLocalClient
    from .coordinator import VestaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VestaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vesta sensors from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        VestaGsmSignalSensor(coordinator, entry.entry_id),
        VestaBatteryStatusSensor(coordinator, entry.entry_id),
        VestaAcStatusSensor(coordinator, entry.entry_id),
        VestaEventLogSensor(coordinator, entry.entry_id),
    ]

    async_add_entities(entities)
    _LOGGER.debug("Added %d diagnostic sensor entities", len(entities))


class VestaGsmSignalSensor(VestaPanelEntity, SensorEntity):
    """Sensor entity for GSM signal strength.

    This sensor reports the GSM signal strength of the panel's
    cellular modem.

    Attributes:
        _attr_name: The entity name.
        _attr_native_unit_of_measurement: The unit (percentage).
        _attr_device_class: Not applicable for signal strength.
        _attr_state_class: Measurement state class.
        _attr_entity_category: Diagnostic category.
    """

    _attr_name = "GSM Signal"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:signal"

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the GSM signal sensor.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_gsm_signal"

    @property
    def native_value(self) -> int | None:
        """Return the GSM signal strength.

        Returns:
            The signal strength as a percentage (0-100) or None.
        """
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.panel.gsm_signal


class VestaBatteryStatusSensor(VestaPanelEntity, SensorEntity):
    """Sensor entity for panel battery status.

    This sensor reports the battery status of the panel's
    backup battery.

    Attributes:
        _attr_name: The entity name.
        _attr_device_class: Not a standard device class.
        _attr_entity_category: Diagnostic category.
    """

    _attr_name = "Battery Status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery"

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the battery status sensor.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_battery_status"

    @property
    def native_value(self) -> str | None:
        """Return the battery status.

        Returns:
            The battery status string or None.
        """
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.panel.battery_status

    @property
    def icon(self) -> str:
        """Return the icon based on battery status.

        Returns:
            The appropriate battery icon.
        """
        if self.coordinator.data is None:
            return "mdi:battery-unknown"

        status = self.coordinator.data.panel.battery_status.lower()
        if "low" in status or "fail" in status:
            return "mdi:battery-alert"
        if "charging" in status:
            return "mdi:battery-charging"
        return "mdi:battery"


class VestaAcStatusSensor(VestaPanelEntity, SensorEntity):
    """Sensor entity for AC power status.

    This sensor reports whether AC power is available or if
    the panel is running on battery backup.

    Attributes:
        _attr_name: The entity name.
        _attr_device_class: Problem device class for AC failure.
        _attr_entity_category: Diagnostic category.
    """

    _attr_name = "AC Power"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:power-plug"

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the AC status sensor.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_ac_status"

    @property
    def native_value(self) -> str | None:
        """Return the AC power status.

        Returns:
            "OK" if AC power is present, "Failure" if not, None if unknown.
        """
        if self.coordinator.data is None:
            return None

        if self.coordinator.data.panel.ac_failure:
            return "Failure"
        return "OK"

    @property
    def icon(self) -> str:
        """Return the icon based on AC status.

        Returns:
            The appropriate power icon.
        """
        if self.coordinator.data is None:
            return "mdi:power-plug-off-outline"

        if self.coordinator.data.panel.ac_failure:
            return "mdi:power-plug-off"
        return "mdi:power-plug"


class VestaEventLogSensor(VestaPanelEntity, SensorEntity):
    """Sensor entity for the panel event log.

    This sensor displays the most recent event from the panel's
    event log and provides the full log in attributes.

    Attributes:
        _attr_name: The entity name.
        _attr_entity_category: Diagnostic category.
        _attr_icon: The icon for the sensor.
    """

    _attr_name = "Event Log"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:history"

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the event log sensor.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_event_log"
        self._event_log: list[dict[str, str]] = []
        self._last_event: str | None = None

    async def async_update(self) -> None:
        """Fetch the latest event log from the panel.

        This method is called periodically to refresh the event log data.
        """
        try:
            client: VestaLocalClient = self.coordinator.client
            events = await client.get_event_log(limit=50)
            self._event_log = [
                {
                    "time": event.time,
                    "event": event.event,
                    "zone": event.zone,
                    "area": event.area,
                    "user": event.user,
                }
                for event in events
            ]
            if events:
                latest = events[0]
                self._last_event = f"{latest.time}: {latest.event}"
            else:
                self._last_event = "No events"
        except Exception as err:
            _LOGGER.warning("Failed to fetch event log: %s", err)
            # Keep the previous state on error

    @property
    def native_value(self) -> str | None:
        """Return the most recent event.

        Returns:
            The most recent event as a string or None.
        """
        return self._last_event

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str]]] | None:
        """Return the full event log as attributes.

        Returns:
            Dictionary containing the full event log.
        """
        return {"events": self._event_log} if self._event_log else None
