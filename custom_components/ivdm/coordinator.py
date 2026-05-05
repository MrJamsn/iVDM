from __future__ import annotations

import logging
from datetime import timedelta, date

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    KEYCLOAK_TOKEN_URL,
    KEYCLOAK_CLIENT_ID,
    API_BASE_URL,
    OBIS_CODES,
    SCAN_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


class IstaVdmCoordinator(DataUpdateCoordinator):

    def __init__(
        self,
        hass: HomeAssistant,
        refresh_token: str,
        flat_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
        )
        self._refresh_token = refresh_token
        self.flat_id = flat_id

    async def _get_access_token(self, session: aiohttp.ClientSession) -> str:
        async with session.post(
            KEYCLOAK_TOKEN_URL,
            data={
                "client_id": KEYCLOAK_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise UpdateFailed(f"Token refresh failed ({resp.status}): {text}")
            tokens = await resp.json()
            self._refresh_token = tokens.get("refresh_token", self._refresh_token)
            return tokens["access_token"]

    async def _async_update_data(self) -> dict:
        today = date.today()
        current_from = today.replace(day=1)
        next_month = (current_from + timedelta(days=32)).replace(day=1)
        current_to = next_month - timedelta(days=1)
        prev_to = current_from - timedelta(days=1)
        prev_from = prev_to.replace(day=1)

        async with aiohttp.ClientSession() as session:
            access_token = await self._get_access_token(session)
            headers = {"Authorization": f"Bearer {access_token}"}

            async def fetch_month(from_d: date, to_d: date) -> list:
                url = (
                    f"{API_BASE_URL}/measurement-records"
                    f"?filter[from-date]={from_d}"
                    f"&filter[to-date]={to_d}"
                    f"&filter[obis_code]={OBIS_CODES}"
                    f"&filter[flat]={self.flat_id}"
                    f"&resolution=month"
                )
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise UpdateFailed(f"API-Fehler ({resp.status}): {text}")
                    return await resp.json()

            current_data = await fetch_month(current_from, current_to)
            prev_data = await fetch_month(prev_from, prev_to)

        return {
            "current": self._parse(current_data),
            "previous": self._parse(prev_data),
            "month": current_from.strftime("%B %Y"),
        }

    @staticmethod
    def _parse(records: list | dict) -> dict:
        result: dict = {}
        if isinstance(records, dict):
            records = records.get("data", [])
        if not isinstance(records, list):
            return result
        for rec in records:
            attrs = rec.get("attributes", rec)
            obis = attrs.get("obis_code") or rec.get("obis_code")
            value = attrs.get("value") or rec.get("value")
            if obis is not None and value is not None:
                try:
                    result[obis] = float(value)
                except (TypeError, ValueError):
                    result[obis] = None
        return result
