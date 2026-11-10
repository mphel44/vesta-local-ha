"""Tests for the API client: response decoding, timestamps and parsing."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from custom_components.vesta_local.client import (
    DeviceStatus,
    EventLogEntry,
    PanelStatus,
    ReportedEvent,
    _decode_json,
    parse_panel_time,
)

from .conftest import load_json


class FakeResponse:
    """Mimics httpx.Response.json(), which runs json.loads on raw bytes."""

    url = "http://panel/action/logsGet"

    def __init__(self, content: bytes) -> None:
        self.content = content

    def json(self):
        return json.loads(self.content)


# --- _decode_json -----------------------------------------------------------


def test_decode_json_plain_utf8() -> None:
    """A well-formed UTF-8 payload is parsed unchanged."""
    payload = '{"logrows":[{"user":"Entrée"}]}'.encode()
    assert _decode_json(FakeResponse(payload)) == {"logrows": [{"user": "Entrée"}]}


def test_decode_json_cp1252_recovers_accents() -> None:
    """A cp1252 payload breaks httpx but is decoded with its accents intact."""
    payload = '{"logrows":[{"user":"Café","action":"Disarm"}]}'.encode("cp1252")
    with pytest.raises(UnicodeDecodeError):
        FakeResponse(payload).json()
    assert _decode_json(FakeResponse(payload))["logrows"][0]["user"] == "Café"


def test_decode_json_undefined_byte_falls_back() -> None:
    """A byte that is undefined in cp1252 degrades instead of failing."""
    payload = b'{"logrows":[{"user":"A\x90\xc3B","action":"Arm"}]}'
    assert _decode_json(FakeResponse(payload))["logrows"][0]["action"] == "Arm"


def test_decode_json_rejects_non_json() -> None:
    """A non-JSON body still raises, so callers can turn it into VestaApiError."""
    with pytest.raises(ValueError):
        _decode_json(FakeResponse(b"<html>404</html>"))


# --- parse_panel_time -------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["2026/11/05 14:51:05", "2026-11-05 14:51:05"],
)
def test_parse_panel_time_accepts_both_separators(value: str) -> None:
    """The panel uses "/" in the event log and "-" elsewhere."""
    parsed = parse_panel_time(value)
    assert parsed is not None
    assert (parsed.year, parsed.month, parsed.day) == (2026, 11, 5)
    assert parsed.tzinfo is not None


@pytest.mark.parametrize("value", ["", "   ", "not a date", "1999/01/01 00:00:00"])
def test_parse_panel_time_rejects_unusable(value: str) -> None:
    """Empty, malformed and pre-2000 values (unset panel clock) are rejected."""
    assert parse_panel_time(value) is None


# --- model parsing against real panel answers -------------------------------


def test_device_list_fixture_parses() -> None:
    """Every row of a real deviceListGet answer validates."""
    rows = load_json("deviceListGet.json")["senrows"]
    devices = [DeviceStatus.model_validate(row) for row in rows]
    assert len(devices) == len(rows)
    assert {d.type_f for d in devices} == {"IR", "IR Camera", "Keypad"}


def test_binary_fields_accept_both_json_types() -> None:
    """The panel sends cond_ok as a string and su as an integer."""
    rows = {row["zone"]: row for row in load_json("deviceListGet.json")["senrows"]}
    assert rows[1]["cond_ok"] == "1" and rows[1]["su"] == 0
    assert rows[3]["su"] == 1

    not_supervised = DeviceStatus.model_validate(rows[1])
    supervised = DeviceStatus.model_validate(rows[3])
    assert not_supervised.supervised is False
    assert supervised.supervised is True
    assert not_supervised.condition_ok is True


def test_bypass_is_yes_no_text() -> None:
    """bypass is "No"/"Yes" text, not a 0/1 flag."""
    row = load_json("deviceListGet.json")["senrows"][0]
    assert row["bypass"] == "No"
    assert DeviceStatus.model_validate(row).bypassed is False
    assert DeviceStatus.model_validate(row | {"bypass": "Yes"}).bypassed is True


def test_device_without_a_name_is_accepted() -> None:
    """Zone 3 of the fixture has an empty name; it must not break parsing."""
    row = next(r for r in load_json("deviceListGet.json")["senrows"] if r["zone"] == 3)
    assert row["name"] == ""
    assert DeviceStatus.model_validate(row).name == ""


def test_panel_status_fixture_parses() -> None:
    """A real panelCondGet answer validates."""
    panel = PanelStatus.model_validate(load_json("panelCondGet.json")["updates"])
    assert panel.mode
    assert isinstance(panel.gsm_signal, int)


def test_event_log_and_reported_events_parse() -> None:
    """Real logsGet and reportEventListGet answers validate."""
    logs = [EventLogEntry.model_validate(r) for r in load_json("logsGet.json")["logrows"]]
    rpt = [ReportedEvent.model_validate(r) for r in load_json("reportEventListGet.json")["rptrows"]]
    assert logs and rpt
    assert all(isinstance(e.uid, int) for e in rpt)
    assert any(parse_panel_time(e.log_time) is not None for e in logs)
