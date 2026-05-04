from __future__ import annotations

import logging

import aiohttp

from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, CONF_FLAT_ID, API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class IstaVdmFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    async def async_oauth_create_entry(self, data: dict) -> dict:
        token = data["token"]["access_token"]
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                async with session.get(f"{API_BASE_URL}/me", headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("/api/me failed (HTTP %s): %s", resp.status, text)
                        return self.async_abort(reason="cannot_connect")
                    me_data = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            return self.async_abort(reason="cannot_connect")

        flat_id = self._extract_flat_id(me_data)
        if not flat_id:
            _LOGGER.error("No flat_id found in /api/me response: %s", me_data)
            return self.async_abort(reason="no_flat_found")

        await self.async_set_unique_id(str(flat_id))
        self._abort_if_unique_id_configured()
        data[CONF_FLAT_ID] = str(flat_id)
        return self.async_create_entry(title=f"ista VDM ({flat_id})", data=data)

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
