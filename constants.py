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


def get_mac(interface: str = "eth0") -> str:
    """
    Retrieves the MAC address for the specified network interface.
    """
    eth_mac = get_mac_address(interface=interface)
    mac = "MDU" + eth_mac.replace(":", "")
    mac = mac.upper()
    return mac


# PINOUT
SYS_LED_RED = 0
SYS_LED_GREEN = 1
SYS_LED_BLUE = 2
CONFIG_BTN = 3
R1_RED_LED = 23
R1_GREEN_LED = 24
R1_BEEP = 25
OPEN1 = 27
MONITOR1 = 17
RELAY1 = 18
R2_RED_LED = 16
R2_GREEN_LED = 20
R2_BEEP = 21
OPEN2 = 13
MONITOR2 = 6
RELAY2 = 12


# DATABASE
DB_HOST = "localhost"
DB_USER = "ma"
DB_PASS = "FrameWork5414*"
DB_NAME = "MeritAccessLocal"

# ACCESS POINT
AP_PASS = "meritmerit"

# PATHS
LOG_DIR = "logs/"
READER_PATH = "/dev/wie"
APP_PATH = os.path.dirname(os.path.abspath(__file__))

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
