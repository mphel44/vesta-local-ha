"""Alarm Control Panel for Vesta/Climax Local integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ALARM_MODE_TO_STATE,
    ALARM_STATE_TO_MODE,
    CID_DISARM_EVENTS,
    CID_TRIGGER_EVENTS,
    DOMAIN,
)
from .entity import VestaPanelEntity

if TYPE_CHECKING:
    from . import VestaConfigEntry
    from .coordinator import VestaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VestaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vesta alarm control panel from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    # Create alarm control panel for area 1 (main panel)
    async_add_entities([VestaAlarmControlPanel(coordinator, entry.entry_id)])

    _LOGGER.debug("Alarm control panel entity added")


class VestaAlarmControlPanel(VestaPanelEntity, AlarmControlPanelEntity):
    """Alarm control panel entity for Vesta/Climax panels.

    This entity provides arm/disarm/home functionality for the alarm panel.

    Attributes:
        _attr_name: The entity name shown in Home Assistant.
        _attr_supported_features: The supported alarm features.
    """

    _attr_name = "Alarm"
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    _attr_code_arm_required = False
    _attr_code_disarm_required = False

    def __init__(
        self,
        coordinator: VestaDataUpdateCoordinator,
        entry_id: str,
        area: int = 1,
    ) -> None:
        """Initialize the alarm control panel.

        Args:
            coordinator: The data update coordinator.
            entry_id: The config entry ID.
            area: The panel area. Default is 1.
        """
        super().__init__(coordinator, entry_id, area)

        # Override unique ID for alarm panel
        self._attr_unique_id = f"{entry_id}_alarm_area_{area}"

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state.

        Checks reported events first to detect TRIGGERED state, then falls
        back to the standard panel mode.

        Returns:
            The current AlarmControlPanelState or None if unknown.
        """
        if self.coordinator.data is None:
            return None

        # Check reported events for triggered state
        if self._is_triggered():
            return AlarmControlPanelState.TRIGGERED

        mode = self.coordinator.data.panel.mode
        state = ALARM_MODE_TO_STATE.get(mode)

        if state is None:
            _LOGGER.warning("Unknown alarm mode: %s", mode)
            return None

        return state

    def _is_triggered(self) -> bool:
        """Check if alarm is in triggered state based on reported events.

        The alarm is triggered if the most recent event (highest UID) has
        new_event == "Trigger" and cid_event in CID_TRIGGER_EVENTS.

        The triggered state is reset if the most recent event is:
        - A disarm event (cid_event in CID_DISARM_EVENTS)
        - A restore event (new_event == "Restore")

        Returns:
            True if the alarm is currently triggered, False otherwise.
        """
        if self.coordinator.data is None:
            return False

        reported_events = self.coordinator.data.reported_events
        if not reported_events:
            return False

        # Events are sorted by uid descending, so first event is most recent
        latest_event = reported_events[0]

        # Check if latest event is a trigger event
        if (
            latest_event.new_event == "Trigger"
            and latest_event.cid_event in CID_TRIGGER_EVENTS
        ):
            return True

        return False

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command.

        Args:
            code: The disarm code (not used for local API).
        """
        _LOGGER.info("Disarming alarm (area %d)", self._area)
        mode = ALARM_STATE_TO_MODE["disarm"]
        await self.coordinator.async_set_alarm_mode(mode, self._area)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command.

        Args:
            code: The arm code (not used for local API).
        """
        _LOGGER.info("Arming alarm in home mode (area %d)", self._area)
        mode = ALARM_STATE_TO_MODE["arm_home"]
        await self.coordinator.async_set_alarm_mode(mode, self._area)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command.

        Args:
            code: The arm code (not used for local API).
        """
        _LOGGER.info("Arming alarm in away mode (area %d)", self._area)
        mode = ALARM_STATE_TO_MODE["arm_away"]
        await self.coordinator.async_set_alarm_mode(mode, self._area)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command.

        Args:
            code: The arm code (not used for local API).
        """
        _LOGGER.info("Arming alarm in night mode (area %d)", self._area)
        mode = ALARM_STATE_TO_MODE["arm_night"]
        await self.coordinator.async_set_alarm_mode(mode, self._area)
