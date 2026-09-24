"""Constants for the MrSteam (iSteamX) integration."""

from __future__ import annotations

DOMAIN = "mrsteam"

# ---------------------------------------------------------------------------
# AWS backend constants (global for every MrSteam iSteamX account).
# Extracted from the com.estone.mrsteam.app bundle and verified live.
# ---------------------------------------------------------------------------
REGION = "us-east-2"
USER_POOL_ID = "us-east-2_mqB0IdHVw"
APP_CLIENT_ID = "3j8tuk3vdmqvn6nehrq0lg6rh0"  # public client, no secret
IDENTITY_POOL_ID = "us-east-2:c7dc2adc-d39d-4aab-abd6-23df3f362a3f"
LOGIN_PROVIDER = f"cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"

REST_BASE = "https://hn0d2u7uek.execute-api.us-east-2.amazonaws.com/latest"
IOT_ENDPOINT = "amfewofqcj9vf-ats.iot.us-east-2.amazonaws.com"

# ---------------------------------------------------------------------------
# Config / options
# ---------------------------------------------------------------------------
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_MODEL_NUMBER = "model_number"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_MODEL_NUMBER = "SU-70"
# Each poll briefly bumps the wall unit off the cloud (steam operation is
# unaffected). Keep the default conservative to minimise that churn.
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 20

# ---------------------------------------------------------------------------
# Shadow field names (reported.devices.*) and control (desired.steam.*)
# ---------------------------------------------------------------------------
DESIRED_STEAM = "steam"
KEY_APP_STEAM_STATUS = "appSteamStatus"  # bool: True=start, False=stop
KEY_APP_PROGRAM = "appProgram"  # program name, e.g. "default", "25@45"

R_STEAM_STATUS = "deviceSteamStatus"  # hex str; "0001"=on, "0000"=off
R_STEAM_TIME = "deviceSteamTime"  # hex str minutes (session length)
R_STEAM_REMAIN = "deviceSteamRemainTime"  # hex str minutes remaining
R_STEAM_TEMP = "deviceSteamTemp"  # int, tenths of a degree
R_ROOM_TEMP = "deviceRoomTemp"  # hex str, tenths of a degree
R_STEAM_H20 = "deviceSteamH20"  # bool: water present
R_AROMA = "deviceAromaStatus"  # int
R_TEMP_UNIT = "deviceTempUnit"  # 1=Fahrenheit, 2=Celsius
R_STEAM_MAX_TEMP = "steamMaxTemp"  # hex str
R_HUB_VERSION = "deviceHubVersion"  # str firmware
R_LIGHT_STATUS = "deviceLightStatus"  # bool
R_PROGRAM_LIST = "deviceProgramList"  # [{program_name, ...}]
R_MEMBER_LIST = "deviceMemberList"

# --- optional accessories (present only when the matching *Connected flag is true) ---
R_SHOWER_CONNECTED = "deviceShowerConnected"
R_SHOWER_STATUS = "deviceShowerStatus"  # hex str; "0000" off
R_SHOWER_TEMP = "deviceShowerTemp"  # target temp, encoding best-effort
R_SHOWER_CURRENT_TEMP = "deviceShowerCurrentTemp"
R_SHOWER_TIME = "deviceShowerTime"  # seconds (1200 = 20 min)
R_CHROMA_CONNECTED = "deviceChromaConnected"
R_RELAY_CONNECTED = "deviceRelayBoxConnected"
R_RELAY_STATUS = "deviceRelayBoxStatus"  # [{id, name, isOpen, ...}]

SHOWER_OFF = "0000"

STEAM_ON = "0001"
STEAM_OFF = "0000"

DEFAULT_PROGRAM = "default"
