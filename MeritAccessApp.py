import RPi.GPIO as GPIO
import time
import subprocess
from LedInfo.LedInfo import LedInfo
from Reader.ReaderWiegand import ReaderWiegand
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
)
from Logger.Logger import Logger
from DatabaseController.DatabaseController import DatabaseController
from DoorUnit.DoorUnit import DoorUnit
from Button.Button import Button
from Modes.ConfigMode import ConfigMode
from Modes.OfflineMode import OfflineMode
from Modes.CloudMode import CloudMode
from WifiController.WifiController import WifiController
from NetworkController.NetworkController import NetworkController


class MeritAccessApp:
    """
    The main application class for the Merit Access control system. This class initializes all necessary
    components of the access control system, selects operational modes based on configuration, and manages
    the system's main operation loop.
    """

    def __init__(self) -> None:
        GPIO.setmode(GPIO.BCM)
        # reader script
        self.reader_script_path = "/home/bantj/wiegand_driver/read.sh"
        subprocess.Popen(
            [self.reader_script_path],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # software objects
        self.logger: Logger = Logger()
        self.db_controller: DatabaseController = DatabaseController()
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
        self.open_btn1: Button = Button(pin=OPEN1)
        self.open_btn2: Button = Button(pin=OPEN2)
        self.config_btn: Button = Button(pin=CONFIG_BTN)

        # setup
        self.default_mode: int = int(self.db_controller.get_val("ConfigDU", "mode"))
        # 0 - cloud, 1 - offline, 2 - config
        self.mode: int = self.default_mode

    def run(self) -> None:
        """
        The main operation loop of the application. This loop selects and runs the operational mode based
        on the current system configuration, handling mode transitions as required.
        """
        # select and run different modes
        try:
            args = [
                self.default_mode,
                self.logger,
                self.sys_led,
                self.r1,
                self.r2,
                self.config_btn,
                self.db_controller,
                self.wifi_controller,
            ]
            while True:
                # CloudMode
                if self.mode == 0:
                    mode = CloudMode(
                        *args,
                        du1=self.door_unit1,
                        du2=self.door_unit2,
                        open_btn1=self.open_btn1,
                        open_btn2=self.open_btn2,
                        network_controller=self.network_controller,
                    )

                # OfflineMode
                elif self.mode == 1:
                    mode = OfflineMode(
                        *args,
                        du1=self.door_unit1,
                        du2=self.door_unit2,
                        open_btn1=self.open_btn1,
                        open_btn2=self.open_btn2,
                    )
                # ConfigMode
                elif self.mode == 2:
                    mode = ConfigMode(*args)
                new_mode = mode.run()
                if new_mode == 0 or new_mode == 1 or new_mode == 2:
                    self.mode = new_mode
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
