"""Sensor platform for Vesta/Climax Local integration.

This module provides diagnostic sensors for the alarm panel including
battery status and GSM signal strength.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import DeviceStatus, EventLogEntry
from .entity import VestaDeviceEntity, VestaPanelEntity

if TYPE_CHECKING:
    from . import VestaConfigEntry
    from .coordinator import VestaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Maximum number of events to store in sensor attributes to avoid exceeding
# Home Assistant's 16384 byte state attribute limit
MAX_EVENTS_IN_ATTRIBUTES = 20


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

    if coordinator.data:
        for device in coordinator.data.devices:
            entities.append(
                VestaDeviceLastEventSensor(coordinator, device, entry.entry_id)
            )

    async_add_entities(entities)
    _LOGGER.debug("Added %d sensor entities", len(entities))


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
    Data is read from the coordinator (no independent API calls).

    Attributes:
        _attr_name: The entity name.
        _attr_entity_category: Diagnostic category.
        _attr_icon: The icon for the sensor.
    """

    _attr_name = "Event Log"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:history"

    _ZONE_RE = re.compile(r"Zone(\d+)")

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

    def _build_zone_map(self) -> dict[int, dict[str, str]]:
        """Build a mapping from zone number to device info.

        Returns:
            Dict mapping zone number to device_id and name.
        """
        if self.coordinator.data is None:
            return {}
        return {
            device.zone: {
                "device_id": device.device_id,
                "device_name": device.name,
            }
            for device in self.coordinator.data.devices
        }

    def _enrich_events(self) -> list[dict[str, str]]:
        """Build the enriched event list from coordinator data.

        Returns:
            List of event dicts with device_id/device_name when matched.
        """
        if self.coordinator.data is None:
            return []
        zone_map = self._build_zone_map()
        enriched = []
        for event in self.coordinator.data.event_log:
            entry: dict[str, str] = {
                "time": event.log_time,
                "area": event.area,
                "mode": event.mode,
                "action": event.action,
                "user": event.user,
                "source": event.source,
                "device_type": event.device_type,
                "msg": event.msg,
            }
            match = self._ZONE_RE.search(event.source)
            if match:
                zone_num = int(match.group(1))
                device_info = zone_map.get(zone_num)
                if device_info:
                    entry["device_id"] = device_info["device_id"]
                    entry["device_name"] = device_info["device_name"]
            enriched.append(entry)
        return enriched

    @property
    def native_value(self) -> str | None:
        """Return the most recent event.

        Returns:
            The most recent event as a string or None.
        """
        if self.coordinator.data is None or not self.coordinator.data.event_log:
            return None
        latest = self.coordinator.data.event_log[0]
        return f"{latest.log_time}: {latest.action}"

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str]]] | None:
        """Return the most recent events as attributes.

        Returns:
            Dictionary containing the most recent enriched events,
            limited to MAX_EVENTS_IN_ATTRIBUTES to avoid exceeding
            Home Assistant's state attribute size limit.
        """
        enriched = self._enrich_events()[:MAX_EVENTS_IN_ATTRIBUTES]
        return {"events": enriched} if enriched else None


class VestaDeviceLastEventSensor(VestaDeviceEntity, SensorEntity):
    """Sensor showing event log entries for a specific device/zone.

    This sensor displays the most recent event action as its state
    and provides all matching events in attributes.

    Attributes:
        _attr_name: The entity name.
        _attr_entity_category: Diagnostic category.
        _attr_icon: The icon for the sensor.
    """

    _attr_name = "Last Event"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:history"

    _ZONE_RE = re.compile(r"Zone(\d+)")

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        device: DeviceStatus,
        entry_id: str,
    ) -> None:
        """Initialize the device last event sensor.

        Args:
            coordinator: The data update coordinator.
            device: The device status information.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, device, entry_id)
        self._attr_unique_id = f"{entry_id}_{device.device_id}_last_event"

    def _find_device_events(self) -> list[EventLogEntry]:
        """Find all event log entries matching this device's zone.

        Returns:
            List of matching EventLogEntry objects, most recent first.
        """
        if self.coordinator.data is None:
            return []
        events = []
        for event in self.coordinator.data.event_log:
            match = self._ZONE_RE.search(event.source)
            if match and int(match.group(1)) == self._zone:
                events.append(event)
        return events

    @property
    def native_value(self) -> str | None:
        """Return the most recent event for this device.

        Includes the timestamp so HA detects a state change even when
        the same action occurs multiple times in a row.

        Returns:
            The timestamp and action string, or None if no events found.
        """
        events = self._find_device_events()
        if not events:
            return None
        return f"{events[0].log_time}: {events[0].action}"

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str]]] | None:
        """Return the most recent events for this device as attributes.

        Returns:
            Dictionary containing the list of events for this device,
            limited to MAX_EVENTS_IN_ATTRIBUTES to avoid exceeding
            Home Assistant's state attribute size limit.
        """
        events = self._find_device_events()[:MAX_EVENTS_IN_ATTRIBUTES]
        if not events:
            return None
        return {
            "events": [
                {
                    "time": event.log_time,
                    "area": event.area,
                    "mode": event.mode,
                    "action": event.action,
                    "user": event.user,
                    "source": event.source,
                    "device_type": event.device_type,
                    "msg": event.msg,
                }
                for event in events
            ]
        }
