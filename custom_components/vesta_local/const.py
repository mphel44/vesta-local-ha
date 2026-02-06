"""Constants for the Vesta/Climax Local integration."""
from typing import Final

from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

# Integration identifiers
DOMAIN: Final = "vesta_local"
INTEGRATION_TITLE: Final = "Vesta/Climax Local"
MANUFACTURER: Final = "Climax Technology"

# Configuration keys
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_USE_SSL: Final = "use_ssl"

# API endpoints (local CGI)
ENDPOINT_LOGIN: Final = "login"
ENDPOINT_PANEL_STATUS: Final = "panelCondGet"
ENDPOINT_DEVICE_LIST: Final = "deviceListGet"
ENDPOINT_PANEL_SET: Final = "panelCondPost"
ENDPOINT_EVENT_LOG: Final = "logsGet"
ENDPOINT_REPORTED_EVENTS: Final = "reportEventListGet"

# Polling configuration
DEFAULT_SCAN_INTERVAL: Final = 5  # seconds

# Alarm mode mappings (Panel -> Home Assistant)
ALARM_MODE_TO_STATE: dict[str, AlarmControlPanelState] = {
    "Disarm": AlarmControlPanelState.DISARMED,
    "disarm": AlarmControlPanelState.DISARMED,
    "Full Arm": AlarmControlPanelState.ARMED_AWAY,
    "full arm": AlarmControlPanelState.ARMED_AWAY,
    "Home Arm 1": AlarmControlPanelState.ARMED_HOME,
    "home arm 1": AlarmControlPanelState.ARMED_HOME,
    "Night": AlarmControlPanelState.ARMED_NIGHT,
    "night": AlarmControlPanelState.ARMED_NIGHT,
}

# Alarm mode mappings (Home Assistant -> Panel POST value)
ALARM_STATE_TO_MODE: dict[str, int] = {
    "disarm": 0,
    "arm_away": 1,
    "arm_home": 2,
    "arm_night": 3,
}

# Device type mappings
DEVICE_TYPE_NAMES: dict[str, str] = {
    "Door Contact": "Door Contact",
    "IR": "Motion Detector",
    "PIR": "Motion Detector",
    "Smoke Detector": "Smoke Detector",
    "CO Detector": "CO Detector",
    "Water Sensor": "Water Leak Sensor",
    "Glass Break": "Glass Break Detector",
    "Keypad": "Keypad",
    "Remote": "Remote Controller",
    "Siren": "Siren",
}

# Device type icon mappings (Material Design Icons)
DEVICE_TYPE_ICONS: dict[str, str] = {
    "Door Contact": "mdi:door-sensor",
    "IR": "mdi:motion-sensor",
    "PIR": "mdi:motion-sensor",
    "Smoke Detector": "mdi:smoke-detector-variant",
    "CO Detector": "mdi:molecule-co",
    "Water Sensor": "mdi:water-alert",
    "Glass Break": "mdi:glass-fragile",
    "Keypad": "mdi:dialpad",
    "Remote": "mdi:remote",
    "Siren": "mdi:bullhorn",
    "SVGS": "mdi:vibrate",
}

# Binary sensor device class mappings
DEVICE_TYPE_TO_BINARY_SENSOR_CLASS: dict[str, BinarySensorDeviceClass] = {
    "Door Contact": BinarySensorDeviceClass.DOOR,
    "IR": BinarySensorDeviceClass.MOTION,
    "PIR": BinarySensorDeviceClass.MOTION,
    "Smoke Detector": BinarySensorDeviceClass.SMOKE,
    "CO Detector": BinarySensorDeviceClass.CO,
    "Water Sensor": BinarySensorDeviceClass.MOISTURE,
    "Glass Break": BinarySensorDeviceClass.VIBRATION,
}

# Sensor status mappings (status string -> is_on boolean)
SENSOR_STATUS_ON: set[str] = {
    "Door Open",
    "Open",
    "Triggered",
    "Motion",
    "Alarm",
    "Active",
    "Tamper",
    "Low Battery",
}

SENSOR_STATUS_OFF: set[str] = {
    "Door Close",
    "Close",
    "Closed",
    "Normal",
    "Ready",
    "Standby",
    "OK",
}

# Diagnostic entity keys
DIAG_BATTERY: Final = "battery"
DIAG_GSM_SIGNAL: Final = "sig_gsm"
DIAG_AC_FAILURE: Final = "ac_fail"

# Contact ID codes for triggered alarm detection
CID_TRIGGER_EVENTS: Final[set[str]] = {"130", "131", "132"}
CID_DISARM_EVENTS: Final[set[str]] = {"400", "401"}

# Default values
DEFAULT_PORT: Final = 80
DEFAULT_TIMEOUT: Final = 10  # seconds
