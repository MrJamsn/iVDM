DOMAIN = "ivdm"

KEYCLOAK_TOKEN_URL = (
    "https://login.ista.com/realms/vdm/protocol/openid-connect/token"
)
KEYCLOAK_CLIENT_ID = "vdm-frontend"
API_BASE_URL = "https://ista-vdm.at/api"

CONF_FLAT_ID = "flat_id"

SCAN_INTERVAL_HOURS = 24

OBIS_CODES = "8-0:1.9.0,9-0:1.9.0,6-0:1.9.0,4-0:1.9.0,1-1:1.9.0+P.01,1-1:2.9.0+G.01"

# OBIS code -> (sensor name, unit, device_class)
OBIS_META = {
    "8-0:1.9.0":       ("Waerme",      "kWh", "energy"),
    "9-0:1.9.0":       ("Kaltwasser",  "m3",  "water"),
    "6-0:1.9.0":       ("Warmwasser",  "m3",  "water"),
    "4-0:1.9.0":       ("Strom",       "kWh", "energy"),
    "1-1:1.9.0+P.01":  ("Gas",         "m3",  "gas"),
    "1-1:2.9.0+G.01":  ("Gas2",        "m3",  "gas"),
}
