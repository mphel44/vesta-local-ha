"""Binary Sensor platform for Vesta/Climax Local integration."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .client import parse_panel_time
from .const import (
    DEVICE_TYPE_TO_BINARY_SENSOR_CLASS,
    LOG_MOTION_ACTION,
    LOG_MOTION_WINDOW,
    SENSOR_STATUS_OFF,
    SENSOR_STATUS_ON,
)
from .entity import VestaDeviceEntity

if TYPE_CHECKING:
    from . import VestaConfigEntry
    from .client import DeviceStatus, EventLogEntry
    from .coordinator import VestaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Event log source of a zone: "Zone1(detecteur_salon)" or "Zone3"
_ZONE_RE = re.compile(r"Zone(\d+)\b")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VestaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vesta binary sensors from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[BinarySensorEntity] = []

    # Create binary sensor entities for supported device types
    if coordinator.data:
        for device in coordinator.data.devices:
            # Add main device sensor if supported
            if device.type_f in DEVICE_TYPE_TO_BINARY_SENSOR_CLASS:
                entities.append(
                    VestaBinarySensor(coordinator, device, entry.entry_id)
                )
                _LOGGER.debug(
                    "Adding binary sensor: %s (zone %d, type %s)",
                    device.name,
                    device.zone,
                    device.type_f,
                )

            # Add battery sensor for devices with battery monitoring
            # battery_ok field is present on all wireless devices
            entities.append(
                VestaBatteryBinarySensor(coordinator, device, entry.entry_id)
            )
            _LOGGER.debug(
                "Adding battery sensor for: %s (zone %d)",
                device.name,
                device.zone,
            )

            # Add condition (problem) and tamper sensors for every device.
            # cond_ok and tamper_ok are reported for all enrolled devices.
            entities.append(
                VestaConditionBinarySensor(coordinator, device, entry.entry_id)
            )
            entities.append(
                VestaTamperBinarySensor(coordinator, device, entry.entry_id)
            )
            _LOGGER.debug(
                "Adding condition and tamper sensors for: %s (zone %d)",
                device.name,
                device.zone,
            )

    async_add_entities(entities)
    _LOGGER.debug("Added %d binary sensor entities", len(entities))


class VestaBinarySensor(VestaDeviceEntity, BinarySensorEntity):
    """Binary sensor entity for Vesta devices.

    This entity represents door contacts, motion sensors, smoke detectors,
    and other binary devices connected to the alarm panel.

    Attributes:
        _attr_name: The entity name shown in Home Assistant.
    """

    _attr_name = None  # Use device name

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        device: DeviceStatus,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: The data update coordinator.
            device: The device status information.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, device, entry_id)

        # Set device class based on device type
        self._attr_device_class = DEVICE_TYPE_TO_BINARY_SENSOR_CLASS.get(
            device.type_f
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on.

        The sensor is considered "on" when:
        - Door contacts are open
        - Motion is detected
        - Smoke/CO/Water is detected

        An empty status string from the panel means the device is idle
        (no alarm), which is reported as "off".

        Returns:
            True if triggered/open, False if normal/closed, None if unknown.
        """
        device = self.device_data
        if device is None:
            return None

        status = device.status

        # Panel reports an empty status string for idle devices
        # (smoke detectors, water sensors, PIRs). Empty == no alarm == off.
        # Wired PIRs and PIR cameras never report a status at all, so for
        # motion sensors a recent "Response" entry for their zone in the
        # event log turns them on instead. The panel only logs those while
        # armed, unless the zone is set to always report.
        if not status or not status.strip():
            if self._attr_device_class == BinarySensorDeviceClass.MOTION:
                return self._last_log_motion(window=True) is not None
            return False

        # Check if status indicates "on" state
        if status in SENSOR_STATUS_ON:
            return True

        # Check if status indicates "off" state
        if status in SENSOR_STATUS_OFF:
            return False

        # Handle unknown status by checking common patterns
        status_lower = status.lower()
        if "open" in status_lower or "motion" in status_lower or "alarm" in status_lower:
            return True
        if "close" in status_lower or "normal" in status_lower or "ready" in status_lower:
            return False

        _LOGGER.debug("Unknown sensor status: %s for device %s", status, device.name)
        return None

    def _last_log_motion(self, window: bool = False) -> EventLogEntry | None:
        """Return the newest "Response" log entry for this device's zone.

        Args:
            window: Only accept entries newer than LOG_MOTION_WINDOW seconds.

        Returns:
            The matching EventLogEntry, or None if there is none.
        """
        if self.coordinator.data is None:
            return None

        now = dt_util.now()
        for event in self.coordinator.data.event_log:  # newest first
            if event.action != LOG_MOTION_ACTION:
                continue
            match = _ZONE_RE.match(event.source)
            if not match or int(match.group(1)) != self._zone:
                continue
            if event.area and event.area != str(self._area):
                continue
            if not window:
                return event

            when = parse_panel_time(event.log_time)
            if when is None:
                continue
            age = (now - when).total_seconds()
            # Small negative ages are clock skew between the panel and HA.
            if -LOG_MOTION_WINDOW <= age <= LOG_MOTION_WINDOW:
                return event
            if age > LOG_MOTION_WINDOW:
                return None  # the log is newest first, older entries follow

        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool] | None:
        """Return additional state attributes.

        Returns:
            Dictionary of extra attributes or None.
        """
        device = self.device_data
        if device is None:
            return None

        attributes: dict[str, str | int | bool] = {}
        if self._attr_device_class == BinarySensorDeviceClass.MOTION:
            # Surfaced even when outside the window, so a stale panel clock
            # (which silently stops motion detection) stays diagnosable.
            last = self._last_log_motion()
            if last is not None:
                attributes["last_log_motion"] = last.log_time
                attributes["last_log_motion_msg"] = last.msg

        return attributes | {
            "zone": device.zone,
            "area": device.area,
            "rssi": device.rssi,
            "battery_ok": device.battery_ok,
            "tamper_ok": device.tamper_ok,
            "raw_status": device.status,
        }


class VestaBatteryBinarySensor(VestaDeviceEntity, BinarySensorEntity):
    """Binary sensor entity for device battery status.

    This entity represents the battery state of wireless devices.
    When is_on is True, the battery is low and needs replacement.

    Attributes:
        _attr_device_class: Battery device class.
        _attr_entity_category: Diagnostic category.
    """

    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        device: DeviceStatus,
        entry_id: str,
    ) -> None:
        """Initialize the battery binary sensor.

        Args:
            coordinator: The data update coordinator.
            device: The device status information.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, device, entry_id)

        # Override unique ID to distinguish from the main sensor
        self._attr_unique_id = f"{entry_id}_{device.device_id}_battery"
        self._attr_name = "Battery"

    @property
    def is_on(self) -> bool | None:
        """Return True if the battery is low.

        The BinarySensorDeviceClass.BATTERY follows the convention:
        - True (on) = Low battery / Problem
        - False (off) = Battery OK / Normal

        Returns:
            True if battery is low, False if OK, None if unknown.
        """
        device = self.device_data
        if device is None:
            return None

        # battery_ok is True when battery is OK, so we invert it
        # battery_ok = True -> is_on = False (battery OK)
        # battery_ok = False -> is_on = True (low battery alert)
        return not device.battery_ok


class VestaConditionBinarySensor(VestaDeviceEntity, BinarySensorEntity):
    """Binary sensor entity for device condition.

    This entity reports the panel's condition flag for a device. The panel
    raises a condition when a supervised device stops checking in or reports
    another problem, so this is the closest thing to a liveness indicator.
    When is_on is True, the panel reports a problem with the device.

    Attributes:
        _attr_device_class: Problem device class.
        _attr_entity_category: Diagnostic category.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        device: DeviceStatus,
        entry_id: str,
    ) -> None:
        """Initialize the condition binary sensor.

        Args:
            coordinator: The data update coordinator.
            device: The device status information.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, device, entry_id)

        # Override unique ID to distinguish from the main sensor
        self._attr_unique_id = f"{entry_id}_{device.device_id}_condition"
        self._attr_name = "Condition"

    @property
    def is_on(self) -> bool | None:
        """Return True if the panel reports a problem with the device.

        The BinarySensorDeviceClass.PROBLEM follows the convention:
        - True (on) = Problem detected
        - False (off) = OK / Normal

        Returns:
            True if the panel reports a problem, False if OK, None if unknown.
        """
        device = self.device_data
        if device is None:
            return None

        # condition_ok is True when the panel reports no problem, so we invert it
        return not device.condition_ok

    @property
    def extra_state_attributes(self) -> dict[str, str | bool] | None:
        """Return additional state attributes.

        Returns:
            Dictionary of extra attributes or None.
        """
        device = self.device_data
        if device is None:
            return None

        return {
            "condition": device.condition,
            "bypassed": device.bypassed,
            "supervised": device.supervised,
        }


class VestaTamperBinarySensor(VestaDeviceEntity, BinarySensorEntity):
    """Binary sensor entity for device tamper status.

    This entity represents the tamper switch state of a device.
    When is_on is True, the device reports tampering.

    Attributes:
        _attr_device_class: Tamper device class.
        _attr_entity_category: Diagnostic category.
    """

    _attr_device_class = BinarySensorDeviceClass.TAMPER
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        device: DeviceStatus,
        entry_id: str,
    ) -> None:
        """Initialize the tamper binary sensor.

        Args:
            coordinator: The data update coordinator.
            device: The device status information.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, device, entry_id)

        # Override unique ID to distinguish from the main sensor
        self._attr_unique_id = f"{entry_id}_{device.device_id}_tamper"
        self._attr_name = "Tamper"

    @property
    def is_on(self) -> bool | None:
        """Return True if the device reports tampering.

        The BinarySensorDeviceClass.TAMPER follows the convention:
        - True (on) = Tampering detected
        - False (off) = Clear

        Returns:
            True if tampered, False if clear, None if unknown.
        """
        device = self.device_data
        if device is None:
            return None

        # tamper_ok is True when the tamper switch is OK, so we invert it
        return not device.tamper_ok
