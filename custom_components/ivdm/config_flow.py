from __future__ import annotations

import logging
import re
from urllib.parse import urlparse, parse_qs

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import (
    DOMAIN,
    CONF_FLAT_ID,
    CONF_REFRESH_TOKEN,
    KEYCLOAK_AUTH_URL,
    KEYCLOAK_TOKEN_URL,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REDIRECT_URI,
    API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


class IstaVdmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            result = await self._browser_login(username, password)
            if result["error"]:
                errors["base"] = result["error"]
            else:
                flat_id = result["flat_id"]
                await self.async_set_unique_id(flat_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"ista VDM ({flat_id})",
                    data={
                        CONF_FLAT_ID: flat_id,
                        CONF_REFRESH_TOKEN: result["refresh_token"],
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

    async def _browser_login(self, username: str, password: str) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: load the Keycloak login page
                params = {
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "response_type": "code",
                    "redirect_uri": KEYCLOAK_REDIRECT_URI,
                    "scope": "openid",
                }
                async with session.get(KEYCLOAK_AUTH_URL, params=params) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Login page failed (HTTP %s)", resp.status)
                        return {"error": "cannot_connect"}
                    html = await resp.text()

                # Step 2: extract the form POST action URL
                match = re.search(r'action="([^"]+)"', html)
                if not match:
                    _LOGGER.error("Could not find login form action in Keycloak page")
                    return {"error": "cannot_connect"}
                form_action = match.group(1).replace("&amp;", "&")

                # Step 3: POST credentials, catch the redirect without following it
                async with session.post(
                    form_action,
                    data={"username": username, "password": password},
                    allow_redirects=False,
                ) as resp:
                    if resp.status not in (301, 302, 303):
                        _LOGGER.error("Unexpected login response (HTTP %s)", resp.status)
                        return {"error": "invalid_auth"}
                    location = resp.headers.get("Location", "")

                # Step 4: extract auth code from redirect URL
                parsed = urlparse(location)
                qs = parse_qs(parsed.query)

                if "error" in qs:
                    _LOGGER.error("Keycloak login error: %s", qs.get("error_description"))
                    return {"error": "invalid_auth"}

                code = qs.get("code", [None])[0]
                if not code:
                    _LOGGER.error("No auth code in redirect: %s", location)
                    return {"error": "invalid_auth"}

                # Step 5: exchange code for tokens
                async with session.post(
                    KEYCLOAK_TOKEN_URL,
                    data={
                        "client_id": KEYCLOAK_CLIENT_ID,
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": KEYCLOAK_REDIRECT_URI,
                    },
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("Token exchange failed (HTTP %s): %s", resp.status, text)
                        return {"error": "cannot_connect"}
                    tokens = await resp.json()

                access_token = tokens["access_token"]
                refresh_token = tokens.get("refresh_token")

                # Step 6: fetch flat_id from /api/me
                headers = {"Authorization": f"Bearer {access_token}"}
                async with session.get(f"{API_BASE_URL}/me", headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("/api/me failed (HTTP %s): %s", resp.status, text)
                        return {"error": "cannot_connect"}
                    me_data = await resp.json()

                flat_id = self._extract_flat_id(me_data)
                if not flat_id:
                    _LOGGER.error("No flat_id in /api/me response: %s", me_data)
                    return {"error": "no_flat_found"}

                return {
                    "error": None,
                    "flat_id": str(flat_id),
                    "refresh_token": refresh_token,
                }

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error during login: %s", err)
            return {"error": "cannot_connect"}

    @staticmethod
    def _extract_flat_id(me_data: dict) -> str | None:
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
