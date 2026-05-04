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
    """Koordinator fuer ista VDM Verbrauchsdaten."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        flat_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
        )
        self._username = username
        self._password = password
        self.flat_id = flat_id
        self._access_token: str | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    async def _fetch_token(self, session: aiohttp.ClientSession) -> str:
        """Keycloak Resource-Owner-Password-Credentials Flow."""
        payload = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "username": self._username,
            "password": self._password,
            "grant_type": "password",
            "scope": "openid",
        }
        async with session.post(KEYCLOAK_TOKEN_URL, data=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise UpdateFailed(f"Login fehlgeschlagen ({resp.status}): {text}")
            data = await resp.json()
            return data["access_token"]

    # ------------------------------------------------------------------
    # Data fetch
    # ------------------------------------------------------------------
    async def _async_update_data(self) -> dict:
        """Verbrauchsdaten fuer den aktuellen und den Vormonat holen."""
        today = date.today()
        # Aktueller Monat
        current_from = today.replace(day=1)
        next_month = (current_from + timedelta(days=32)).replace(day=1)
        current_to = next_month - timedelta(days=1)

        # Vormonat
        prev_to = current_from - timedelta(days=1)
        prev_from = prev_to.replace(day=1)

        async with aiohttp.ClientSession() as session:
            self._access_token = await self._fetch_token(session)
            headers = {"Authorization": f"Bearer {self._access_token}"}

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

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------
    @staticmethod
    def _parse(records: list | dict) -> dict:
        """Gibt {obis_code: value} zurueck."""
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
