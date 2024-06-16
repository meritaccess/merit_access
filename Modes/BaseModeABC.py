import time
import socket
import fcntl
import struct
from getmac import get_mac_address
from abc import ABC, abstractmethod
import threading
from Logger.LoggerDB import LoggerDB
from LedInfo.LedInfo import LedInfo
from Reader.ReaderWiegand import ReaderWiegand
from Button.Button import Button
from DatabaseController.DatabaseController import DatabaseController
from WifiController.WifiController import WifiController


class BaseModeABC(ABC):
    """
    An abstract base class for defining operational modes within an access control system. It provides common
    attributes and methods that all modes should implement.
    """

    def __init__(
        self,
        logger: LoggerDB,
        sys_led: LedInfo,
        config_btn: Button,
        db_controller: DatabaseController,
        wifi_controller: WifiController,
    ) -> None:
        self.mac: str = self._get_mac_addr()
        self.mode_name: str = "BaseMode"
        self._exit: bool = False

        # 0 - Not pressed, 1 - short press, 2 - long press
        self._config_btn_is_pressed: int = 0

        # threading
        self._config_buttons_thread = None
        self._stop_event = threading.Event()

        # objects
        self.logger: LoggerDB = logger
        self.sys_led: LedInfo = sys_led
        self.config_btn: Button = config_btn
        self.db_controller: DatabaseController = db_controller
        self.wifi_controller: WifiController = wifi_controller
        self._wifi_setup()

    def _get_ip_address(self, ifname):
        """
        Retrieves the IP address for the specified network interface.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(), 0x8915, struct.pack("256s", ifname[:15])  # SIOCGIFADDR
            )[20:24]
        )

    def _wifi_setup(self) -> None:
        self.wifi_controller.turn_off()

    def exit(self) -> None:
        self._exit = True

    def _get_mac_addr(self, interface="eth0") -> str:
        """
        Retrieves the MAC address for the specified network interface.
        """
        eth_mac = get_mac_address(interface=interface)
        mac = "MDU" + eth_mac.replace(":", "")
        mac = mac.upper()
        return mac

    def _init_threads(self) -> None:
        if not self.is_thread_running("config_btn"):
            self._config_btn_check()

    def _config_btn_check(self):
        self._config_buttons_thread = threading.Thread(
            target=self._thread_config_btn, daemon=True, name="config_btn"
        )
        self._config_buttons_thread.start()

    def _thread_config_btn(self) -> None:
        while not self._stop_event.is_set():
            if self.config_btn.pressed():
                press_time = time.time()
                time.sleep(0.1)
                while self.config_btn.pressed():
                    continue
                if time.time() - press_time > 5:
                    self._config_btn_is_pressed = 2
                else:
                    self._config_btn_is_pressed = 1

    def _stop(self) -> None:
        self._stop_event.set()
        if self._config_buttons_thread:
            self._config_buttons_thread.join()

    def is_thread_running(self, thread_name) -> bool:
        for thread in threading.enumerate():
            if thread.name == thread_name:
                return True
        return False

    @abstractmethod
    def run(self) -> int:
        """Abstract method to run the mode."""
        pass

    def __str__(self) -> str:
        return self.mode_name

    def __repr__(self) -> str:
        return self.mode_name
