"""Constants for the ScreenLine WISE integration."""

from datetime import timedelta

DOMAIN = "screenline_wise"
PLATFORMS = ["cover", "sensor"]

CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

API_ROOMS = "/api/plant/rooms?includeBlinds=true&includeGlasses=true"
API_POSITION = "/api/rooms/{room_id}/position"
API_MOVE = "/api/rooms/{room_id}/move"
API_TILT = "/api/rooms/{room_id}/tilt"

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

ATTR_COVERAGE_RECEIVED = "coverage_received"
ATTR_INCLINATION_RECEIVED = "inclination_received"
ATTR_COVERAGE_CONFIRMED = "coverage_confirmed"
ATTR_INCLINATION_CONFIRMED = "inclination_confirmed"
ATTR_SCREENLINE_COVERAGE = "screenline_coverage"
ATTR_SCREENLINE_INCLINATION = "screenline_inclination"
ATTR_HUB_COUNTER_MISALIGNED = "hub_counter_misaligned"

TILT_MIN = -75
TILT_MAX = 75
