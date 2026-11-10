"""Tests for the binary sensor state logic.

Covers the two behaviours that do not come from the panel's ``status``
field: idle devices reporting ``off`` on an empty status, and motion
sensors deriving their state from the event log.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.util import dt as dt_util

from custom_components.vesta_local.binary_sensor import VestaBinarySensor
from custom_components.vesta_local.const import LOG_MOTION_WINDOW

from .conftest import build_data, load_json, panel_time

ENTRY_ID = "entry-id"


def device_row(zone: int) -> dict:
    """Return a raw device row from the fixture."""
    return next(r for r in load_json("deviceListGet.json")["senrows"] if r["zone"] == zone)


def response_log(zone: int, age_seconds: float, area: str = "1") -> list[dict]:
    """Build an event log holding one "Response" entry of the given age."""
    when = dt_util.now() - timedelta(seconds=age_seconds)
    return [
        {
            "log_time": panel_time(when),
            "area": area,
            "mode": "Full Arm",
            "action": "Response",
            "user": "",
            "source": f"Zone{zone}(Comedor)",
            "device_type": "IR Camera",
            "msg": "Start Entry 1",
        }
    ]


def motion_sensor(coordinator, zone: int = 3) -> VestaBinarySensor:
    """Build the motion binary sensor of a zone, wired to the coordinator."""
    device = next(d for d in coordinator.data.devices if d.zone == zone)
    sensor = VestaBinarySensor(coordinator, device, ENTRY_ID)
    assert sensor.device_class == BinarySensorDeviceClass.MOTION
    return sensor


# --- motion derived from the event log --------------------------------------


def test_ir_camera_is_a_motion_sensor(coordinator) -> None:
    """"IR Camera" is the spelling HSGW-MAX panels use for a PIR camera."""
    device = next(d for d in coordinator.data.devices if d.type_f == "IR Camera")
    assert VestaBinarySensor(coordinator, device, ENTRY_ID).device_class == (
        BinarySensorDeviceClass.MOTION
    )


def test_recent_response_turns_motion_on(coordinator) -> None:
    """A "Response" entry inside the window means motion."""
    coordinator.data = build_data(event_log=response_log(zone=3, age_seconds=5))
    assert motion_sensor(coordinator).is_on is True


def test_old_response_leaves_motion_off(coordinator) -> None:
    """Past the window the sensor falls back to off."""
    coordinator.data = build_data(
        event_log=response_log(zone=3, age_seconds=LOG_MOTION_WINDOW + 60)
    )
    assert motion_sensor(coordinator).is_on is False


def test_response_of_another_zone_is_ignored(coordinator) -> None:
    """Zone 9's motion must not light up zone 3."""
    coordinator.data = build_data(event_log=response_log(zone=9, age_seconds=5))
    assert motion_sensor(coordinator).is_on is False


def test_response_of_another_area_is_ignored(coordinator) -> None:
    """Zone numbers restart per area, so the area has to match too."""
    coordinator.data = build_data(event_log=response_log(zone=3, age_seconds=5, area="2"))
    assert motion_sensor(coordinator).is_on is False


def test_clock_skew_ahead_still_counts(coordinator) -> None:
    """A panel clock slightly ahead of HA must not break detection."""
    coordinator.data = build_data(event_log=response_log(zone=3, age_seconds=-5))
    assert motion_sensor(coordinator).is_on is True


def test_other_actions_do_not_trigger_motion(coordinator) -> None:
    """Only "Response" entries count; "Mode Changed" must not."""
    log = response_log(zone=3, age_seconds=5)
    log[0]["action"] = "Mode Changed"
    coordinator.data = build_data(event_log=log)
    assert motion_sensor(coordinator).is_on is False


def test_empty_log_leaves_motion_off(coordinator) -> None:
    """No events at all is not motion."""
    coordinator.data = build_data(event_log=[])
    assert motion_sensor(coordinator).is_on is False


def test_motion_attributes_expose_the_last_entry(coordinator) -> None:
    """The last "Response" is surfaced even when outside the window, so a
    drifting panel clock stays diagnosable."""
    coordinator.data = build_data(
        event_log=response_log(zone=3, age_seconds=LOG_MOTION_WINDOW + 600)
    )
    sensor = motion_sensor(coordinator)
    assert sensor.is_on is False
    assert "last_log_motion" in sensor.extra_state_attributes
    assert sensor.extra_state_attributes["last_log_motion_msg"] == "Start Entry 1"


# --- the status path is untouched -------------------------------------------


def test_empty_status_on_a_non_motion_device_is_off(coordinator) -> None:
    """A keypad with an empty status reports off, never unknown."""
    device = next(d for d in coordinator.data.devices if d.type_f == "Keypad")
    sensor = VestaBinarySensor(coordinator, device, ENTRY_ID)
    assert device.status == ""
    assert sensor.is_on is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [("Door Open", True), ("Door Close", False), ("Wide Open", True)],
)
def test_status_strings_still_win(coordinator, status: str, expected: bool) -> None:
    """Devices that do report a status keep using it."""
    rows = [device_row(1) | {"type_f": "Door Contact", "status": status}]
    coordinator.data = build_data(devices=rows)
    device = coordinator.data.devices[0]
    assert VestaBinarySensor(coordinator, device, ENTRY_ID).is_on is expected
