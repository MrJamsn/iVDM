from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation

from .const import DOMAIN, KEYCLOAK_CLIENT_ID, KEYCLOAK_AUTH_URL, KEYCLOAK_TOKEN_URL


class IstaVdmOAuth2Implementation(LocalOAuth2Implementation):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            domain=DOMAIN,
            client_id=KEYCLOAK_CLIENT_ID,
            client_secret="",
            authorize_url=KEYCLOAK_AUTH_URL,
            token_url=KEYCLOAK_TOKEN_URL,
        )

    @property
    def name(self) -> str:
        return "ista VDM"
