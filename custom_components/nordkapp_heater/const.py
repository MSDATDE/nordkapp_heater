"""Constants for Nordkapp Heater integration."""

from homeassistant.const import Platform

DOMAIN = "nordkapp_heater"

PLATFORMS = [
    Platform.CLIMATE,
    Platform.FAN,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

# BLE UUIDs
SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "00003a00-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "00003a01-0000-1000-8000-00805f9b34fb"
SERVICE_CHANGED_UUID = "00002a05-0000-1000-8000-00805f9b34fb"

# CRC16 lookup table (from APK)
CRC16_TABLE = [
    0, 4129, 8258, 12387, 16516, 20645, 24774, 28903,
    33032, 37161, 41290, 45419, 49548, 53677, 57806, 61935,
]

# Command IDs (app -> heater)
CMD_BUTTON = 0x61
CMD_MANUAL_PUMP = 0x62
CMD_GET_REG_ADDR = 0x63
CMD_GET_REG_VAL = 0x64
CMD_AUTO_UPDATA = 0x65
CMD_SHORT_PARA = 0x66
CMD_BIND = 0x91

# Button codes for CMD_BUTTON (0x61 arg0)
BTN_POWER_ON = 1
BTN_POWER_OFF = 2
BTN_UP = 3
BTN_DOWN = 4
BTN_CLEAR_ERROR = 5
BTN_RF_PAIR = 6
BTN_OK = 7
BTN_SWITCH_TEMP_FC = 8
BTN_VENTILATION = 9
BTN_SWITCH_TEMP_CF = 10

# SHORT_PARA types for CMD_SHORT_PARA (0x66 arg0)
PARA_RUN_MODE = 0
PARA_TARGET_TEMP = 1
PARA_TARGET_GEAR = 2
PARA_TIMER = 3
PARA_TEMP_DIFF = 4

# Run modes
MODE_AUTO = 0
MODE_MANUAL = 1
MODE_START_STOP = 2

# Response command IDs (heater -> app)
RESP_BIND_REQUEST = 0x20
RESP_BIND_ACCEPTED = 0x21
RESP_BIND_REJECTED = 0x22
RESP_CMD_ACK = 0x41
RESP_REG_ADDR = 0x43
RESP_WRITE_ACK = 0x44
RESP_PARA = 0x46
RESP_STATUS = 0xFF

# Machine states
MACHINE_STATUS = {
    0: "booting",
    1: "igniting",
    2: "auto_run",
    3: "manual_run",
    4: "residual_burn",
    5: "standby",
    6: "error",
    7: "manual_pump",
    8: "ventilation",
    9: "start_stop_run",
    10: "setting_start_stop",
}

# States considered "running" (heater is on)
RUNNING_STATES = {0, 1, 2, 3, 7, 8, 9, 10}

# States considered "heating"
HEATING_STATES = {0, 1, 2, 3, 9, 10}

# Temperature limits
TEMP_MIN = 8
TEMP_MAX = 36

# Gear limits
GEAR_MIN = 1
GEAR_MAX = 10

# Polling
DEFAULT_POLL_INTERVAL = 15  # seconds
STATUS_PACKET_MIN_LENGTH = 50
BIND_DELAY = 0.5  # seconds

# N/A sensor value
SENSOR_NA_VALUE = 32760  # 0x7FF8


def crc16(data: list[int] | bytearray | bytes, length: int) -> int:
    """Calculate CRC16 checksum (from APK source)."""
    crc = 0
    for i in range(length):
        a = (crc >> 12) & 0xFFFF
        crc = (crc << 4) & 0xFFFF
        crc ^= CRC16_TABLE[((a & 0xFFFF) ^ (data[i] >> 4)) & 0x0F]
        a = (crc & 0xFFFF) >> 12
        crc = (crc << 4) & 0xFFFF
        crc ^= CRC16_TABLE[((a & 0xFFFF) ^ (data[i] & 0x0F)) & 0x0F]
    return crc & 0xFFFF


def build_cmd(cmd_id: int, arg0: int = 0, arg1: int = 0, arg2: int = 0) -> bytearray:
    """Build 8-byte command packet with CRC16."""
    pkt = [0xAA, 0x00, cmd_id, arg0, arg1, arg2, 0, 0]
    c = crc16(pkt, 6)
    pkt[6] = (c >> 8) & 0xFF
    pkt[7] = c & 0xFF
    return bytearray(pkt)


def build_bind_response(mac_bytes: list[int]) -> bytearray:
    """Build 12-byte bind response (0x91) from MAC bytes."""
    pkt = [0xAA, 0x00, CMD_BIND, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for i in range(6):
        pkt[3 + i] = mac_bytes[5 - i]
    pkt[9] = mac_bytes[5]  # magic byte = last byte of MAC
    c = crc16(pkt, 10)
    pkt[10] = (c >> 8) & 0xFF
    pkt[11] = c & 0xFF
    return bytearray(pkt)


def le16(data: bytes, offset: int) -> int:
    """Read 16-bit little-endian unsigned value."""
    return (data[offset + 1] << 8) | data[offset]


def le16s(data: bytes, offset: int) -> int:
    """Read 16-bit little-endian signed value."""
    v = le16(data, offset)
    return -(65536 - v) if v > 32767 else v
