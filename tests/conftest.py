"""Shared fixtures for the Vesta/Climax Local tests.

The JSON files in ``tests/fixtures`` are real answers from a Climax Hybrid
Panel Lite (VESTA-388), contributed by @B1oko and stripped of credentials.
They are the reference for what the panel actually sends, which differs from
the documentation in several places (``su`` is an integer while ``cond_ok``
is a string, ``bypass`` is "Yes"/"No", names can be empty).

The suite deliberately avoids spinning up a Home Assistant instance: the
integration only needs a handful of HA helpers, and testing the parsing and
state logic directly keeps the suite runnable on any Python the project
supports.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.vesta_local.client import (
    DeviceStatus,
    EventLogEntry,
    PanelStatus,
    ReportedEvent,
    VestaData,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str) -> dict[str, Any]:
    """Load a panel answer from tests/fixtures."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def panel_time(when) -> str:
    """Format a datetime the way the event log does."""
    return when.strftime("%Y/%m/%d %H:%M:%S")


def build_data(
    event_log: list[dict[str, Any]] | None = None,
    reported: list[dict[str, Any]] | None = None,
    devices: list[dict[str, Any]] | None = None,
) -> VestaData:
    """Build VestaData from the fixtures, optionally overriding parts of it."""
    rows = devices if devices is not None else load_json("deviceListGet.json")["senrows"]
    logs = event_log if event_log is not None else load_json("logsGet.json")["logrows"]
    rpt = reported if reported is not None else load_json("reportEventListGet.json")["rptrows"]
    return VestaData(
        panel=PanelStatus.model_validate(load_json("panelCondGet.json")["updates"]),
        devices=[DeviceStatus.model_validate(row) for row in rows],
        event_log=[EventLogEntry.model_validate(row) for row in logs],
        reported_events=sorted(
            (ReportedEvent.model_validate(row) for row in rpt),
            key=lambda e: e.uid,
            reverse=True,
        ),
    )


@pytest.fixture
def coordinator():
    """A coordinator stand-in carrying fixture data."""
    mock = MagicMock()
    mock.data = build_data()
    mock.panel_device_id = "panel-device-id"
    mock.client.host = "192.168.1.184"
    return mock
