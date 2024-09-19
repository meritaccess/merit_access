import os
import mysql.connector
from getmac import get_mac_address
from enum import Enum


def get_syslog_server() -> str:
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
    """Returns a boolean to determine whether open and monitor pins are swaped with reader pins"""
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


def get_mac(interface: str = "eth0") -> str:
    """
    Retrieves the MAC address for the specified network interface.
    """
    eth_mac = get_mac_address(interface=interface)
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

# SYSTEM
MAC = get_mac()


# TIME PLANS
class Action(Enum):
    NONE = 0  # No time plan
    SILENT_OPEN = 1  # Permanent open without sound
    PULS = 2  # Gives pulse to open (default state)
    REVERSE = 3  # Switches output


# MODES
class Mode(Enum):
    CLOUD = 0
    OFFLINE = 1


class Config(Enum):
    NONE = 0
    CONFIG = 1
    CONNECT = 2
