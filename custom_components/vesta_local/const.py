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

# API endpoints (local CGI)
ENDPOINT_LOGIN: Final = "login"
ENDPOINT_PANEL_STATUS: Final = "panelCondGet"
ENDPOINT_DEVICE_LIST: Final = "deviceListGet"
ENDPOINT_PANEL_SET: Final = "panelCondPost"
ENDPOINT_EVENT_LOG: Final = "eventLogGet"

# Polling configuration
DEFAULT_SCAN_INTERVAL: Final = 5  # seconds

# Alarm mode mappings (Panel -> Home Assistant)
ALARM_MODE_TO_STATE: dict[str, AlarmControlPanelState] = {
    "Disarm": AlarmControlPanelState.DISARMED,
    "disarm": AlarmControlPanelState.DISARMED,
    "Arm": AlarmControlPanelState.ARMED_AWAY,
    "arm": AlarmControlPanelState.ARMED_AWAY,
    "Home": AlarmControlPanelState.ARMED_HOME,
    "home": AlarmControlPanelState.ARMED_HOME,
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

# Default values
DEFAULT_PORT: Final = 80
DEFAULT_TIMEOUT: Final = 10  # seconds
