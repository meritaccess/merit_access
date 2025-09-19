import os
import mysql.connector
from getmac import get_mac_address
from enum import Enum
import logging
from typing import Literal


def get_syslog_server() -> str:
    """
    Retrieves the syslog server address from the database.
    """
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cur = mydb.cursor()
        cur.execute("SELECT VALUE AS v FROM ConfigDU WHERE PROPERTY='syslogserver'")
        rows = cur.fetchone()
        cur.close()
        mydb.close()
        if len(rows) != 1:
            return ""
        return rows[0]
    except Exception as e:
        print(e)
        return ""


def get_swap_wie() -> bool:
    """
    Returns a boolean to determine whether open and monitor pins are swaped with reader pins
    """
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cur = mydb.cursor()
        cur.execute(
            "SELECT VALUE AS v FROM ConfigDU WHERE PROPERTY='swap_wiegand_pins'"
        )
        rows = cur.fetchone()
        cur.close()
        mydb.close()
        if len(rows) != 1:
            return False
        return bool(int(rows[0]))
    except Exception as e:
        print(e)
        return False


def get_log_level() -> Literal[0, 10, 20, 30, 40, 50]:
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cur = mydb.cursor()
        cur.execute("SELECT VALUE AS v FROM ConfigDU WHERE PROPERTY='log_level'")
        rows = cur.fetchone()
        cur.close()
        mydb.close()
        if len(rows) != 1:
            return logging.INFO
        if rows[0] not in {"debug", "info", "warn", "error", "critical"}:
            print(
                f'Incorrect log level use: {["debug", "info", "warn", "error", "critical"]}'
            )
            return logging.INFO
        return getattr(logging, rows[0].upper())
    except Exception as e:
        print(e)
        return logging.INFO


def get_mac(interface: str = "eth0") -> str:
    """
    Retrieves the MAC address for the specified network interface.
    """
    eth_mac = get_mac_address(interface=interface)
    if eth_mac is None:
        return "MDU"
    mac = "MDU" + eth_mac.replace(":", "")
    mac = mac.upper()
    return mac


# DATABASE
DB_HOST = "localhost"
DB_USER = "ma"
DB_PASS = "FrameWork5414*"
DB_NAME = "MeritAccessLocal"

# PINOUT
SYS_LED_RED = 0
SYS_LED_GREEN = 1
SYS_LED_BLUE = 2
CONFIG_BTN = 3
R1_RED_LED = 23
R1_GREEN_LED = 24
R1_BEEP = 25
RELAY1 = 18
R2_RED_LED = 16
R2_GREEN_LED = 20
R2_BEEP = 21
RELAY2 = 12


if not get_swap_wie():
    OPEN1 = 27
    MONITOR1 = 17
    OPEN2 = 13
    MONITOR2 = 6
else:
    OPEN1 = 5
    MONITOR1 = 22
    OPEN2 = 26
    MONITOR2 = 19


# ACCESS POINT
AP_PASS = "meritmerit"

# PATHS
LOG_DIR = "logs/"
READER_PATH = "/dev/wie"
APP_PATH = os.path.dirname(os.path.abspath(__file__))
SSH_CONFIG = "/etc/ssh/sshd_config"

# SETTINGS
LOG_FILE_SIZE = 10

# SYSLOGGER
SYSLOG_SERVER = get_syslog_server()
SYSLOG_PORT = 514
LOG_LEVEL = get_log_level()

# SYSTEM
MAC = get_mac()

# TIME SLEEP
MODE_SLEEP_TIME = 0.1  # do not go below 0.05s
OSDP_INIT_TIME = 1  # do not go below 1s
CARD_READ_TIME = 0.3
OPEN_BTN_TIME = 0.2
MONITOR_BTN_TIME = 0.2
EASY_ADD_REMOVE_TIME = 2
CONFIG_BTN_TIME = 0.1
CONFIG_BTN_LONG_PRESS_TIME = 5  # shorter than this value is considered a short press
WIE_READER_LED_TIME = 0.01
SYS_LED_BLINK = 1
SYS_LED_BLINK_FAST = 0.2


# TIME PLANS
class Action(Enum):
    NONE = 0  # No time plan
    SILENT_OPEN = 1  # Permanent open without sound
    PULS = 2  # Gives pulse to open (default state)
    REVERSE = 3  # Switches output


# MODES
class Mode(Enum):
    CLOUD = 0  # cloud mode (ws or ivar)
    OFFLINE = 1  # offline mode


class Config(Enum):
    NONE = 0  # no config mode
    CONFIG = 1  # config mode
    OSDP = 2  # osdp config (scan) mode


# STATUSES
class Status(Enum):
    ALLOW = 701
    ALLOW_TERM_NOT_FOUND = 702  # access allowed terminal not found
    ALLOW_CARD_NOT_FOUND = 703  # access allowed card not found
    ALLOW_DOOR_NOT_CLOSED = 704  # door not closed
    ALLOW_INSERT_FAILED = 711  # access allowed insert failed
    ALLOW_DOOR_NOT_CLOSED_INSERT_FAILED = 714  # door not closed insert failed

    DENY = 716
    DENY_TERM_NOT_FOUND = 717  # access denied terminal not found
    DENY_CARD_NOT_FOUND = 718  # access denied card not found
    DENY_INSERT_FAILED = 726  # access denied insert failed

    OPEN_WITH_BTN = 731  # opened with button
    OPEN_WITH_BTN_INSERT_FAILED = 741  # opened with button insert failed

    UNAUTHORIZED_ACCESS = 751  # unauthorized access
    UNAUTHORIZED_ACCESS_INSERT_FAILED = 761  # unauthorized access insert failed


# PROTOCOLS
class Protocol(Enum):
    WIEGAND = 0
    OSDP = 1


# OSDP
OSDP_ADDRESSES = 128  # osdp address range 0-127
OSDP_MAX_READERS = 4  # two with relay outputs and two with gpio outputs
OSDP_BATCH_SIZE = 4  # max supported number of osdp reader for one control panel
OSDP_PORT = "/dev/ttyAMA1"


def test_constants_values():
    """
    Tests the constants values.
    """
    assert (
        MODE_SLEEP_TIME >= 0.05
    ), f"MODE_SLEEP_TIME={MODE_SLEEP_TIME}, do not go below 0.05s"
    assert OSDP_INIT_TIME >= 1, f"OSDP_INIT_TIME={OSDP_INIT_TIME}, do not go below 1s"


test_constants_values()
