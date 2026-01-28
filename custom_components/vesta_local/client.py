"""Vesta/Climax Local API Client.

This module provides an async client for communicating with Vesta/Climax
alarm panels via their local HTTP CGI interface.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator

from .const import (
    DEFAULT_TIMEOUT,
    ENDPOINT_DEVICE_LIST,
    ENDPOINT_EVENT_LOG,
    ENDPOINT_LOGIN,
    ENDPOINT_PANEL_SET,
    ENDPOINT_PANEL_STATUS,
)

_LOGGER = logging.getLogger(__name__)


class DeviceStatus(BaseModel):
    """Represents a device/zone status from the panel.

    Attributes:
        area: The area number the device belongs to.
        zone: The zone number of the device.
        name: Human-readable name of the device.
        type_f: Device type (e.g., "Door Contact", "PIR").
        status: Current status string (e.g., "Door Open", "Door Close").
        battery_ok: True if battery is OK, False if low.
        tamper_ok: True if tamper switch is OK.
        rssi: Signal strength indicator.
        device_id: Unique identifier for the device.
    """

    area: int
    zone: int
    name: str
    type_f: str = Field(alias="type_f")
    status: str
    battery_ok: bool = Field(alias="battery_ok")
    tamper_ok: bool = Field(alias="tamper_ok")
    rssi: str
    device_id: str = Field(alias="id")

    model_config = {"populate_by_name": True}

    @field_validator("battery_ok", "tamper_ok", mode="before")
    @classmethod
    def parse_binary(cls, value: Any) -> bool:
        """Parse binary string values to boolean."""
        if isinstance(value, bool):
            return value
        return str(value) == "1"


class PanelStatus(BaseModel):
    """Represents the panel's current status.

    Attributes:
        mode: Current alarm mode (e.g., "Disarm", "Arm", "Home").
        battery_status: Battery status string.
        gsm_signal: GSM signal strength (0-100).
        ac_failure: True if AC power has failed.
    """

    mode: str = Field(alias="mode_a1")
    battery_status: str = Field(default="", alias="battery")
    gsm_signal: int = Field(default=0, alias="sig_gsm")
    ac_failure: bool = Field(default=False, alias="ac_fail")

    model_config = {"populate_by_name": True}

    @field_validator("ac_failure", mode="before")
    @classmethod
    def parse_ac_failure(cls, value: Any) -> bool:
        """Parse AC failure field to boolean."""
        if isinstance(value, bool):
            return value
        return str(value) == "1"

    @field_validator("gsm_signal", mode="before")
    @classmethod
    def parse_gsm_signal(cls, value: Any) -> int:
        """Parse GSM signal to integer."""
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0


class EventLogEntry(BaseModel):
    """Represents an event log entry from the panel.

    Attributes:
        time: Timestamp of the event.
        event: Event description.
        zone: Zone number (if applicable).
        area: Area number (if applicable).
        user: User name (if applicable).
    """

    time: str = Field(default="")
    event: str = Field(default="")
    zone: str = Field(default="")
    area: str = Field(default="")
    user: str = Field(default="")

    model_config = {"populate_by_name": True}


@dataclass
class VestaData:
    """Container for all data retrieved from the panel.

    Attributes:
        panel: The current panel status.
        devices: List of all device statuses.
    """

    panel: PanelStatus
    devices: list[DeviceStatus]


class VestaAuthenticationError(Exception):
    """Raised when authentication fails."""


class VestaConnectionError(Exception):
    """Raised when connection to panel fails."""


class VestaApiError(Exception):
    """Raised when API returns an error."""


class VestaLocalClient:
    """Async client for Vesta/Climax local API.

    This client handles all communication with the alarm panel's local
    HTTP interface using httpx with Digest Auth support.

    Attributes:
        host: The hostname or IP address of the panel.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        use_ssl: bool = False,
    ) -> None:
        """Initialize the Vesta Local Client.

        Args:
            host: Hostname or IP address of the panel.
            username: Username for authentication.
            password: Password for authentication.
            verify_ssl: Whether to verify SSL certificates. Default False for
                self-signed certs common on local panels.
            use_ssl: Whether to use HTTPS. Default False (use HTTP).
        """
        self._host = host
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._use_ssl = use_ssl
        self._client: httpx.AsyncClient | None = None

        protocol = "https" if use_ssl else "http"
        self._base_url = f"{protocol}://{host}/action"
        self._headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{protocol}://{host}/",
            "Accept": "application/json",
        }

    @property
    def host(self) -> str:
        """Return the host address."""
        return self._host

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client.

        Returns:
            The httpx AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            # Use Basic Auth for Vesta/Climax panels
            auth = httpx.BasicAuth(self._username, self._password)

            self._client = httpx.AsyncClient(
                auth=auth,
                headers=self._headers,
                timeout=httpx.Timeout(DEFAULT_TIMEOUT),
                verify=self._verify_ssl,
                follow_redirects=False,
            )

        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        retry_count: int = 2,
    ) -> dict[str, Any]:
        """Make an HTTP request to the panel.

        Args:
            method: HTTP method (GET, POST).
            endpoint: API endpoint (without /action/ prefix).
            data: Optional form data for POST requests.
            retry_count: Number of retries on failure.

        Returns:
            The JSON response as a dictionary.

        Raises:
            VestaAuthenticationError: If authentication fails (401).
            VestaConnectionError: If connection fails.
            VestaApiError: If the API returns an error.
        """
        url = f"{self._base_url}/{endpoint}"
        client = await self._get_client()

        last_error: Exception | None = None

        for attempt in range(retry_count + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(url, data=data)

                if response.status_code == 401:
                    raise VestaAuthenticationError(
                        f"Authentication failed for {self._host}"
                    )

                if response.status_code >= 400:
                    raise VestaApiError(
                        f"API error {response.status_code}: {response.text}"
                    )

                # Check if response is JSON
                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type and "text/json" not in content_type:
                    # Try to parse as JSON anyway (some panels don't set content-type correctly)
                    try:
                        return response.json()
                    except Exception:
                        raise VestaApiError(
                            f"Unexpected response type '{content_type}' from {url}: {response.text[:200]}"
                        )

                return response.json()

            except httpx.ConnectError as err:
                last_error = VestaConnectionError(
                    f"Connection to {self._host} failed: {err}"
                )
                if attempt < retry_count:
                    wait_time = 2**attempt
                    _LOGGER.debug(
                        "Request failed, retrying in %ds (attempt %d/%d): %s",
                        wait_time,
                        attempt + 1,
                        retry_count + 1,
                        err,
                    )
                    await asyncio.sleep(wait_time)
                continue

            except httpx.TimeoutException:
                last_error = VestaConnectionError(
                    f"Connection to {self._host} timed out"
                )
                if attempt < retry_count:
                    wait_time = 2**attempt
                    _LOGGER.debug(
                        "Request timed out, retrying in %ds (attempt %d/%d)",
                        wait_time,
                        attempt + 1,
                        retry_count + 1,
                    )
                    await asyncio.sleep(wait_time)
                continue

            except (VestaAuthenticationError, VestaApiError):
                raise

            except httpx.HTTPError as err:
                last_error = VestaConnectionError(
                    f"HTTP error for {self._host}: {err}"
                )
                if attempt < retry_count:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                continue

        if last_error:
            raise last_error

        raise VestaConnectionError(f"Failed to connect to {self._host}")

    async def authenticate(self) -> bool:
        """Test authentication with the panel.

        Returns:
            True if authentication succeeds.

        Raises:
            VestaAuthenticationError: If authentication fails.
            VestaConnectionError: If connection fails.
        """
        _LOGGER.debug("Testing authentication with %s", self._host)
        try:
            # Use panelCondGet to test auth (login endpoint returns HTML)
            await self._request("GET", ENDPOINT_PANEL_STATUS)
            _LOGGER.debug("Authentication successful for %s", self._host)
            return True
        except VestaAuthenticationError:
            _LOGGER.error("Authentication failed for %s", self._host)
            raise

    async def get_panel_status(self) -> PanelStatus:
        """Get the current panel status.

        Returns:
            PanelStatus object with current mode and diagnostics.

        Raises:
            VestaConnectionError: If connection fails.
            VestaApiError: If parsing fails.
        """
        _LOGGER.debug("Fetching panel status from %s", self._host)
        json_data = await self._request("GET", ENDPOINT_PANEL_STATUS)

        try:
            updates = json_data.get("updates", json_data)
            return PanelStatus.model_validate(updates)
        except Exception as err:
            _LOGGER.error("Failed to parse panel status: %s", err)
            raise VestaApiError(f"Failed to parse panel status: {err}") from err

    async def get_devices(self) -> list[DeviceStatus]:
        """Get the list of all devices/zones.

        Returns:
            List of DeviceStatus objects for each device.

        Raises:
            VestaConnectionError: If connection fails.
            VestaApiError: If parsing fails.
        """
        _LOGGER.debug("Fetching device list from %s", self._host)
        json_data = await self._request("GET", ENDPOINT_DEVICE_LIST)

        try:
            devices = []
            for device_data in json_data.get("senrows", []):
                try:
                    devices.append(DeviceStatus.model_validate(device_data))
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to parse device %s: %s",
                        device_data.get("id", "unknown"),
                        err,
                    )
            return devices
        except Exception as err:
            _LOGGER.error("Failed to parse device list: %s", err)
            raise VestaApiError(f"Failed to parse device list: {err}") from err

    async def get_all_data(self) -> VestaData:
        """Get all data from the panel in a single call.

        This method fetches both panel status and device list concurrently.

        Returns:
            VestaData object containing panel and device status.
        """
        _LOGGER.debug("Fetching all data from %s", self._host)
        panel_task = self.get_panel_status()
        devices_task = self.get_devices()

        panel, devices = await asyncio.gather(panel_task, devices_task)
        return VestaData(panel=panel, devices=devices)

    async def get_event_log(self, limit: int = 50) -> list[EventLogEntry]:
        """Get the event log from the panel.

        Args:
            limit: Maximum number of events to return. Default is 50.

        Returns:
            List of EventLogEntry objects, sorted by most recent first.

        Raises:
            VestaConnectionError: If connection fails.
            VestaApiError: If parsing fails.
        """
        _LOGGER.debug("Fetching event log from %s", self._host)
        json_data = await self._request("GET", ENDPOINT_EVENT_LOG)

        try:
            events = []
            # The API typically returns events in a "logrows" array
            event_rows = json_data.get("logrows", json_data.get("events", []))
            for event_data in event_rows[:limit]:
                try:
                    events.append(EventLogEntry.model_validate(event_data))
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to parse event log entry: %s",
                        err,
                    )
            return events
        except Exception as err:
            _LOGGER.error("Failed to parse event log: %s", err)
            raise VestaApiError(f"Failed to parse event log: {err}") from err

    async def set_alarm_mode(self, mode: int, area: int = 1) -> bool:
        """Set the alarm mode.

        Args:
            mode: The mode to set (0=Disarm, 1=Arm Away, 2=Arm Home, 3=Arm Night).
            area: The area number to set the mode for. Default is 1.

        Returns:
            True if the mode was set successfully.

        Raises:
            VestaConnectionError: If connection fails.
            VestaApiError: If the command fails.
        """
        _LOGGER.info(
            "Setting alarm mode to %d for area %d on %s",
            mode,
            area,
            self._host,
        )
        payload = {"area": str(area), "mode": str(mode)}
        response = await self._request("POST", ENDPOINT_PANEL_SET, data=payload)

        result = response.get("result")
        if result == 1 or result == "1":
            _LOGGER.debug("Alarm mode set successfully")
            return True

        _LOGGER.error("Failed to set alarm mode: %s", response)
        return False

    async def close(self) -> None:
        """Close the client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            _LOGGER.debug("Client session closed")
