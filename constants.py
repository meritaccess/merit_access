import os

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
