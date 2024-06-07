import time
import socket
import fcntl
import struct
from getmac import get_mac_address
from abc import ABC, abstractmethod
import threading
from Logger.Logger import Logger
from LedInfo.LedInfo import LedInfo
from Reader.ReaderWiegand import ReaderWiegand
from Button.Button import Button
from DatabaseController.DatabaseController import DatabaseController
from WifiController.WifiController import WifiController


class BaseMode(ABC):
    """
    An abstract base class for defining operational modes within an access control system. It provides common
    attributes and methods that all modes should implement.
    """

    def __init__(
        self,
        default_mode: int,
        logger: Logger,
        sys_led: LedInfo,
        r1: ReaderWiegand,
        r2: ReaderWiegand,
        config_btn: Button,
        db_controller: DatabaseController,
        wifi_controller: WifiController,
    ) -> None:
        self.default_mode: int = default_mode
        self.mac: str = self._get_mac_addr()
        self.curr_time: int = time.perf_counter_ns()
        self.mode_name: str = "BaseMode"

        # objects
        self.logger: Logger = logger
        self.sys_led: LedInfo = sys_led
        self.r1: ReaderWiegand = r1
        self.r2: ReaderWiegand = r2
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

    def _get_mac_addr(self, interface="eth0") -> str:
        """
        Retrieves the MAC address for the specified network interface.
        """
        eth_mac = get_mac_address(interface=interface)
        mac = "MDU" + eth_mac.replace(":", "")
        mac = mac.upper()
        return mac

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
