"""Tests for the device registry links and entity identities."""
from __future__ import annotations

from unittest.mock import patch

from custom_components.vesta_local import entity as entity_module
from custom_components.vesta_local.binary_sensor import VestaBinarySensor
from custom_components.vesta_local.const import DOMAIN

ENTRY_ID = "entry-id"


def build(coordinator, zone: int = 3) -> VestaBinarySensor:
    device = next(d for d in coordinator.data.devices if d.zone == zone)
    return VestaBinarySensor(coordinator, device, ENTRY_ID)


def test_links_with_via_device_id_when_supported(coordinator) -> None:
    """On HA versions that know via_device_id, the registry id is used."""
    with patch.object(entity_module, "_SUPPORTS_VIA_DEVICE_ID", True):
        info = build(coordinator)._attr_device_info
    assert info["via_device_id"] == "panel-device-id"
    assert "via_device" not in info


def test_falls_back_to_via_device_on_older_ha(coordinator) -> None:
    """Older HA versions only understand the identifier tuple."""
    with patch.object(entity_module, "_SUPPORTS_VIA_DEVICE_ID", False):
        info = build(coordinator)._attr_device_info
    assert info["via_device"] == (DOMAIN, ENTRY_ID)
    assert "via_device_id" not in info


def test_falls_back_when_the_panel_device_is_unknown(coordinator) -> None:
    """Without a registered panel the zone still links the old way, rather
    than ending up with no parent at all."""
    coordinator.panel_device_id = None
    with patch.object(entity_module, "_SUPPORTS_VIA_DEVICE_ID", True):
        info = build(coordinator)._attr_device_info
    assert info["via_device"] == (DOMAIN, ENTRY_ID)


def test_unique_ids_are_stable(coordinator) -> None:
    """Entity unique ids must not change: they are what keeps user history."""
    device = next(d for d in coordinator.data.devices if d.zone == 3)
    sensor = VestaBinarySensor(coordinator, device, ENTRY_ID)
    assert sensor.unique_id == f"{ENTRY_ID}_{device.device_id}"
    assert sensor._attr_device_info["identifiers"] == {
        (DOMAIN, f"{ENTRY_ID}_{device.device_id}")
    }
