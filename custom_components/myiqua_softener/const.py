DOMAIN = "myiqua_softener"

PLATFORMS = ["sensor", "binary_sensor", "button", "switch"]

# How long the on-demand live WebSocket stays open before auto-closing (seconds).
LIVE_SECONDS = 300

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"
CONF_SERIAL = "serial_number"
CONF_NICKNAME = "nickname"

# How often we poll the MyIqua cloud. The legacy EcoWater API blocked accounts
# above ~1000 requests/day; 15 min keeps us far under that on any backend.
UPDATE_INTERVAL_MINUTES = 5
