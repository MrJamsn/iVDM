from __future__ import annotations

import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    CONF_FLAT_ID,
    KEYCLOAK_TOKEN_URL,
    KEYCLOAK_CLIENT_ID,
    API_BASE_URL,
)


class IstaVdmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurationsassistent fuer ista VDM."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            flat_id, error = await self._validate_credentials(username, password)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(flat_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"ista VDM ({flat_id})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_FLAT_ID: flat_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _validate_credentials(self, username: str, password: str):
        """Login testen und Flat-ID ermitteln."""
        try:
            async with aiohttp.ClientSession() as session:
                # Token holen
                payload = {
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "username": username,
                    "password": password,
                    "grant_type": "password",
                    "scope": "openid",
                }
                async with session.post(KEYCLOAK_TOKEN_URL, data=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("Token request failed (HTTP %s): %s", resp.status, text)
                        return None, "invalid_auth"
                    token_data = await resp.json()
                    token = token_data["access_token"]

                # /api/me aufrufen -> Flat-ID ermitteln
                headers = {"Authorization": f"Bearer {token}"}
                async with session.get(f"{API_BASE_URL}/me", headers=headers) as resp:
                    if resp.status != 200:
                        return None, "cannot_connect"
                    me_data = await resp.json()

                flat_id = self._extract_flat_id(me_data)
                if not flat_id:
                    return None, "no_flat_found"
                return str(flat_id), None

        except aiohttp.ClientError:
            return None, "cannot_connect"

    @staticmethod
    def _extract_flat_id(me_data: dict) -> str | None:
        """Flat-ID aus /api/me Response extrahieren."""
        for key in ("flat_id", "flatId", "flat"):
            if key in me_data:
                val = me_data[key]
                if isinstance(val, dict):
                    return val.get("id")
                return val
        data = me_data.get("data", {})
        if isinstance(data, dict):
            attrs = data.get("attributes", {})
            for key in ("flat_id", "flatId"):
                if key in attrs:
                    return attrs[key]
            rels = data.get("relationships", {})
            flat_rel = rels.get("flat") or rels.get("flats")
            if flat_rel:
                return flat_rel.get("data", {}).get("id")
        return None
