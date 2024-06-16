import RPi.GPIO as GPIO
import time
import os

from constants import (
    R1_BEEP,
    R1_RED_LED,
    R1_GREEN_LED,
    RELAY1,
    R2_BEEP,
    R2_RED_LED,
    R2_GREEN_LED,
    RELAY2,
    CONFIG_BTN,
    OPEN1,
    OPEN2,
    APP_PATH,
)
from LedInfo.LedInfo import LedInfo
from Reader.ReaderWiegand import ReaderWiegand
from Logger.LoggerDB import LoggerDB
from DatabaseController.DatabaseController import DatabaseController
from DoorUnit.DoorUnit import DoorUnit
from Button.Button import Button
from Modes.OfflineMode import OfflineMode
from Modes.CloudMode import CloudMode
from WifiController.WifiController import WifiController
from NetworkController.NetworkController import NetworkController
from Modes.ConfigModeOffline import ConfigModeOffline
from Modes.ConfigModeCloud import ConfigModeCloud
from Modes.ConfigModeConnect import ConfigModeConnect


class MeritAccessApp:
    """
    The main application class for the Merit Access control system. This class initializes all necessary
    components of the access control system, selects operational modes based on configuration, and manages
    the system's main operation loop.
    """

    def __init__(self) -> None:
        GPIO.setmode(GPIO.BCM)

        # software objects
        self.db_controller: DatabaseController = DatabaseController()
        self.logger: LoggerDB = LoggerDB(db_controller=self.db_controller)
        self.wifi_controller: WifiController = WifiController()
        self.network_controller: NetworkController = NetworkController()

        # hardware objects
        self.sys_led: LedInfo = LedInfo()
        self.r1: ReaderWiegand = ReaderWiegand(
            r_id=1,
            beep=R1_BEEP,
            green_led=R1_GREEN_LED,
            red_led=R1_RED_LED,
        )
        self.r2: ReaderWiegand = ReaderWiegand(
            r_id=2,
            beep=R2_BEEP,
            green_led=R2_GREEN_LED,
            red_led=R2_RED_LED,
        )
        self.door_unit1: DoorUnit = DoorUnit("DU1", reader=self.r1, relay=RELAY1)
        self.door_unit2: DoorUnit = DoorUnit("DU2", reader=self.r2, relay=RELAY2)
        self.open_btn1: Button = Button(pin=OPEN1, btn_id="OpenBtn1")
        self.open_btn2: Button = Button(pin=OPEN2, btn_id="OpenBtn2")
        self.config_btn: Button = Button(pin=CONFIG_BTN, btn_id="ConfigBtn")

        # setup
        # 0 - cloud, 1 - offline
        self._main_mode: int = int(self.db_controller.get_val("ConfigDU", "mode"))
        # 0 - None, 1 - ConfigModeOffline/ConfigModeOffline, 2 - ConfigModeConnect
        self._config_mode: int = 0
        self._check_version()

    def _check_version(self) -> None:
        version_db = self.db_controller.get_val("running", "Version")
        file = os.path.join(APP_PATH, "version.txt")
        if os.path.exists(file):
            with open(file, "r") as f:
                version = f.read().strip()
            if version != version_db:
                self.db_controller.set_val("running", "Version", version)

    def run(self) -> None:
        """
        The main operation loop of the application. This loop selects and runs the operational mode based
        on the current system configuration, handling mode transitions as required.
        """
        # select and run different modes
        try:
            args_base = [
                self.logger,
                self.sys_led,
                self.config_btn,
                self.db_controller,
                self.wifi_controller,
            ]
            args_main_mode = {
                "r1": self.r1,
                "r2": self.r2,
                "du1": self.door_unit1,
                "du2": self.door_unit2,
                "open_btn1": self.open_btn1,
                "open_btn2": self.open_btn2,
            }
            while True:
                # CloudMode
                if self._main_mode == 0 and self._config_mode == 0:
                    self._config_mode = CloudMode(
                        *args_base,
                        **args_main_mode,
                        network_controller=self.network_controller,
                    ).run()

                # OfflineMode
                elif self._main_mode == 1 and self._config_mode == 0:
                    self._config_mode = OfflineMode(*args_base, **args_main_mode).run()

                # ConfigMode
                if self._config_mode == 1:
                    if self._main_mode == 0:
                        self._config_mode = ConfigModeCloud(
                            *args_base,
                        ).run()
                    else:
                        self._config_mode = ConfigModeOffline(
                            *args_base,
                            r1=self.r1,
                            r2=self.r2,
                        ).run()
                if self._config_mode == 2:
                    self._config_mode = ConfigModeConnect(*args_base).run()

        except KeyboardInterrupt:
            print("Ending by keyboard request")
        except Exception as e:
            self.logger.log(1, str(e))
        finally:
            # wait for the reader to finish opening
            while self.door_unit1.openning or self.door_unit2.openning:
                time.sleep(1)
            self.sys_led.set_status("black", "off")
            self.sys_led.stop()
            GPIO.cleanup()
            self.logger.log(3, "Exitting app")

    def __str__(self) -> str:
        return "MeritAccessMainApp"

    def __repr__(self) -> str:
        return "MeritAccessMainApp"
