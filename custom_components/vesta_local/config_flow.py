"""Config flow for Vesta/Climax Local integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    VestaAuthenticationError,
    VestaConnectionError,
    VestaLocalClient,
)
from .const import DOMAIN, INTEGRATION_TITLE

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class VestaLocalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vesta/Climax Local.

    This config flow handles initial setup and re-authentication for the
    Vesta/Climax local integration.
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._reauth_entry: ConfigEntry | None = None
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery.

        This step is triggered when a Vesta/Climax panel is discovered
        via mDNS/Zeroconf on the local network.
        """
        host = discovery_info.host
        name = discovery_info.name.removesuffix("._http._tcp.local.")

        _LOGGER.debug("Discovered Vesta/Climax panel: %s at %s", name, host)

        # Check if this device is already configured
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        # Store discovered info for the confirmation step
        self._discovered_host = host
        self._discovered_name = name

        # Set the title for the discovery notification
        self.context["title_placeholders"] = {"name": name, "host": host}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery confirmation.

        This step collects credentials after a device is discovered.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._discovered_host is not None

            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            error = await self._test_connection(
                self._discovered_host, username, password
            )
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=f"{INTEGRATION_TITLE} ({self._discovered_name or self._discovered_host})",
                    data={
                        CONF_HOST: self._discovered_host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={
                "name": self._discovered_name or "Vesta/Climax Panel",
                "host": self._discovered_host or "",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        This step collects the host, username, and password from the user.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Check for duplicate entries
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            error = await self._test_connection(host, username, password)
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=f"{INTEGRATION_TITLE} ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication.

        This step is triggered when authentication fails for an existing entry.
        """
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication confirmation.

        This step collects new credentials for an existing entry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._host is not None
            assert self._reauth_entry is not None

            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            error = await self._test_connection(self._host, username, password)
            if error:
                errors["base"] = error
            else:
                # Update the existing entry with new credentials
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        CONF_HOST: self._host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
                await self.hass.config_entries.async_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                REAUTH_SCHEMA,
                {CONF_USERNAME: self._reauth_entry.data.get(CONF_USERNAME, "")}
                if self._reauth_entry
                else {},
            ),
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def _test_connection(
        self, host: str, username: str, password: str
    ) -> str | None:
        """Test the connection to the panel.

        Args:
            host: The hostname or IP address.
            username: The username.
            password: The password.

        Returns:
            Error string if connection fails, None if successful.
        """
        client = VestaLocalClient(
            host=host,
            username=username,
            password=password,
            verify_ssl=False,
        )

        try:
            await client.authenticate()
            return None

        except VestaAuthenticationError:
            _LOGGER.warning("Authentication failed for %s", host)
            return "invalid_auth"

        except VestaConnectionError as err:
            _LOGGER.warning("Connection failed for %s: %s", host, err)
            return "cannot_connect"

        except Exception as err:
            _LOGGER.exception("Unexpected error connecting to %s: %s", host, err)
            return "unknown"

        finally:
            await client.close()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> VestaLocalOptionsFlow:
        """Get the options flow for this handler."""
        return VestaLocalOptionsFlow(config_entry)


class VestaLocalOptionsFlow:
    """Handle options flow for Vesta/Climax Local.

    This allows users to reconfigure options after initial setup.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
