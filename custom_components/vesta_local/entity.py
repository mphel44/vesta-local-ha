"""Base entity classes for Vesta/Climax Local integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import DeviceStatus
from .const import DEVICE_TYPE_NAMES, DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import VestaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class VestaEntity(CoordinatorEntity["VestaDataUpdateCoordinator"]):
    """Base entity for Vesta/Climax Local integration.

    This class provides common functionality for all Vesta entities,
    including coordinator integration and device info.

    Attributes:
        _attr_has_entity_name: Indicates the entity uses the device name.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the base entity.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator)
        self._entry_id = entry_id


class VestaDeviceEntity(VestaEntity):
    """Base entity for Vesta device/zone entities.

    This class represents entities that correspond to physical devices
    (sensors, contacts, etc.) on the alarm panel.

    Attributes:
        device_id: The unique device identifier.
    """

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        device: DeviceStatus,
        entry_id: str,
    ) -> None:
        """Initialize the device entity.

        Args:
            coordinator: The data update coordinator.
            device: The device status information.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator, entry_id)

        self._device_id = device.device_id
        self._zone = device.zone
        self._area = device.area

        # Set unique ID based on device
        self._attr_unique_id = f"{entry_id}_{device.device_id}"

        # Device info for Home Assistant device registry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{device.device_id}")},
            name=device.name,
            manufacturer=MANUFACTURER,
            model=DEVICE_TYPE_NAMES.get(device.type_f, device.type_f),
            serial_number=device.device_id,
            via_device=(DOMAIN, entry_id),
        )

    @property
    def device_data(self) -> DeviceStatus | None:
        """Get the current device data from the coordinator.

        Returns:
            The DeviceStatus for this device, or None if not found.
        """
        if self.coordinator.data is None:
            return None

        for device in self.coordinator.data.devices:
            if device.device_id == self._device_id:
                return device
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Returns:
            True if the coordinator has data and the device exists.
        """
        return super().available and self.device_data is not None


class VestaPanelEntity(VestaEntity):
    """Base entity for Vesta panel entities.

    This class represents entities that correspond to the alarm panel
    itself (alarm control, diagnostics, etc.).

    Attributes:
        area: The panel area number.
    """

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
        area: int = 1,
    ) -> None:
        """Initialize the panel entity.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
            area: The panel area number. Default is 1.
        """
        super().__init__(coordinator, entry_id)

        self._area = area

        # Set unique ID based on panel area
        self._attr_unique_id = f"{entry_id}_panel_area_{area}"

        # Device info for the main panel
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Vesta Panel ({coordinator.client.host})",
            manufacturer=MANUFACTURER,
            model="HSGW-MAX",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Returns:
            True if the coordinator has data.
        """
        return super().available and self.coordinator.data is not None
