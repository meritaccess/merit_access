import pigpio
import time
import subprocess
import os
from getmac import get_mac_address
import threading

from constants import R1_BEEP, R1_RED_LED, R1_GREEN_LED, RELAY1, R2_BEEP, R2_RED_LED
from constants import R2_GREEN_LED, RELAY2, CONFIG_BTN, OPEN1, OPEN2, APP_PATH, AP_PASS
from HardwareComponents.LedInfo.LedInfo import LedInfo
from HardwareComponents.Reader.ReaderWiegand import ReaderWiegand
from Logger.LoggerDB import LoggerDB
from DataControllers.DatabaseController import DatabaseController
from HardwareComponents.DoorUnit.DoorUnit import DoorUnit
from HardwareComponents.Button.Button import Button
from Modes.OfflineMode import OfflineMode
from Modes.CloudMode import CloudMode
from Network.WifiController import WifiController
from Network.NetworkController import NetworkController
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
        self._pi = pigpio.pi()
        self._mac: str = self._get_mac_addr()

        # software objects
        self._db_controller: DatabaseController = DatabaseController()
        self._logger: LoggerDB = LoggerDB(db_controller=self._db_controller)
        self._wifi_controller: WifiController = self._get_wifi_controller()
        self._network_controller: NetworkController = NetworkController(self._logger)
        self._network_settings()

        # hardware objects
        self._sys_led: LedInfo = LedInfo(pi=self._pi)
        self._r1: ReaderWiegand = ReaderWiegand(
            r_id=1,
            beep=R1_BEEP,
            green_led=R1_GREEN_LED,
            red_led=R1_RED_LED,
            pi=self._pi,
        )
        self._r2: ReaderWiegand = ReaderWiegand(
            r_id=2,
            beep=R2_BEEP,
            green_led=R2_GREEN_LED,
            red_led=R2_RED_LED,
            pi=self._pi,
        )
        self._door_unit1: DoorUnit = DoorUnit(
            "DU1", reader=self._r1, relay=RELAY1, pi=self._pi
        )
        self._door_unit2: DoorUnit = DoorUnit(
            "DU2", reader=self._r2, relay=RELAY2, pi=self._pi
        )
        self._open_btn1: Button = Button(pin=OPEN1, btn_id="OpenBtn1", pi=self._pi)
        self._open_btn2: Button = Button(pin=OPEN2, btn_id="OpenBtn2", pi=self._pi)
        self._config_btn: Button = Button(
            pin=CONFIG_BTN, btn_id="ConfigBtn", pi=self._pi
        )

        # setup
        # 0 - cloud, 1 - offline
        self._main_mode: int = int(self._db_controller.get_val("ConfigDU", "mode"))
        # 0 - None, 1 - ConfigModeOffline/ConfigModeOffline, 2 - ConfigModeConnect
        self._config_mode: int = 0
        self._runnig_mode = None
        self._pending_reboot = False
        self._exit = False
        self._stop_event = threading.Event()

        # threading
        self._threads = []
        self._run_all_checks()

    def _run_all_checks(self) -> None:
        self._check_version()
        self._check_pending_reboot()
        self._check_ip()

    def _get_mac_addr(self, interface="eth0") -> str:
        """
        Retrieves the MAC address for the specified network interface.
        """
        eth_mac = get_mac_address(interface=interface)
        mac = "MDU" + eth_mac.replace(":", "")
        mac = mac.upper()
        return mac

    def _get_wifi_controller(self) -> WifiController:
        wifi_ssid = self._db_controller.get_val("ConfigDU", "ssid")
        wifi_pass = self._db_controller.get_val("ConfigDU", "wifipass")
        ap_ssid = self._mac
        ap_pass = AP_PASS
        return WifiController(wifi_ssid, wifi_pass, ap_ssid, ap_pass, self._logger)

    def _network_settings(self) -> None:
        """
        Configures the network settings for the system.
        """
        self._set_interface()
        use_dhcp = bool(int(self._db_controller.get_val("ConfigDU", "dhcp")))
        if use_dhcp:
            self._network_controller.set_dhcp()
        else:
            ip = self._db_controller.get_val("ConfigDU", "ip")
            subnet = self._db_controller.get_val("ConfigDU", "mask")
            gateway = self._db_controller.get_val("ConfigDU", "dg")
            dns = self._db_controller.get_val("ConfigDU", "dns1")
            self._network_controller.set_static_ip(ip, subnet, gateway, dns)

    def _set_interface(self) -> None:
        wifi_enable = bool(int(self._db_controller.get_val("ConfigDU", "enablewifi")))
        if wifi_enable:
            self._wifi_controller.wifi_connect()
            interface = "wlan0"
        else:
            interface = "eth0"
        self._network_controller.set_interface(interface)

    def _check_version(self) -> None:
        version_db = self._db_controller.get_val("running", "Version")
        file = os.path.join(APP_PATH, "version.txt")
        if os.path.exists(file):
            with open(file, "r") as f:
                version = f.read().strip()
            if version != version_db:
                self._db_controller.set_val("running", "Version", version)

    def _check_ip(self) -> None:
        t = threading.Thread(
            target=self._thread_update_ip, daemon=True, name="update_ip"
        )
        self._threads.append(t)
        t.start()

    def _thread_update_ip(self) -> None:
        while not self._stop_event.is_set():
            current_ip = self._network_controller.get_ip_address()
            if not current_ip:
                time.sleep(1)
                continue
            old_ip = self._db_controller.get_val("running", "MyIP")
            if not self._config_mode == 0:
                time.sleep(1)
                continue
            if current_ip != old_ip:
                self._db_controller.set_val("running", "MyIP", current_ip)
            time.sleep(1)

    def _check_pending_reboot(self) -> None:
        t = threading.Thread(
            target=self._thread_pending_reboot, daemon=True, name="pending_reboot"
        )
        self._threads.append(t)
        t.start()

    def _thread_pending_reboot(self) -> None:
        while not self._stop_event.is_set():
            if not self._pending_reboot:
                self._pending_reboot = bool(
                    int(self._db_controller.get_val("running", "restart"))
                )
            if self._pending_reboot:
                self._db_controller.set_val("running", "restart", "0")
                if self._runnig_mode:
                    self._runnig_mode.exit()
                self.exit()
            time.sleep(1)

    def exit(self) -> None:
        self._exit = True

    def _stop(self) -> None:
        self._pi.stop()
        self._stop_event.set()
        for t in self._threads:
            t.join()

    def _check_reboot(self) -> None:
        if self._pending_reboot:
            self._logger.log(2, "System reboot")
            try:
                subprocess.run(["sudo", "reboot"], check=True)
            except subprocess.CalledProcessError as e:
                err = f"Error: {e}"
                self._logger.log(1, err)

    def run(self) -> None:
        """
        The main operation loop of the application. This loop selects and runs the operational mode based
        on the current system configuration, handling mode transitions as required.
        """
        # select and run different modes
        try:
            args_base = [
                self._mac,
                self._logger,
                self._sys_led,
                self._config_btn,
                self._db_controller,
                self._wifi_controller,
            ]
            args_main_mode = {
                "r1": self._r1,
                "r2": self._r2,
                "du1": self._door_unit1,
                "du2": self._door_unit2,
                "open_btn1": self._open_btn1,
                "open_btn2": self._open_btn2,
            }

            while not self._exit:
                # CloudMode
                if self._main_mode == 0 and self._config_mode == 0:
                    self._runnig_mode = CloudMode(*args_base, **args_main_mode)
                    self._config_mode = self._runnig_mode.run()

                # OfflineMode
                elif self._main_mode == 1 and self._config_mode == 0:
                    self._runnig_mode = OfflineMode(*args_base, **args_main_mode)
                    self._config_mode = self._runnig_mode.run()

                # ConfigMode
                if self._config_mode == 1:
                    if self._main_mode == 0:
                        self._runnig_mode = ConfigModeCloud(
                            *args_base,
                        )
                        self._config_mode = self._runnig_mode.run()
                    else:
                        self._runnig_mode = ConfigModeOffline(
                            *args_base,
                            r1=self._r1,
                            r2=self._r2,
                        )
                        self._config_mode = self._runnig_mode.run()
                if self._config_mode == 2:
                    self._runnig_mode = ConfigModeConnect(*args_base)
                    self._config_mode = self._runnig_mode.run()

        except KeyboardInterrupt:
            print("Ending by keyboard request")
        except Exception as e:
            self._logger.log(1, str(e))
        finally:
            # wait for the reader to finish opening
            while self._door_unit1.openning or self._door_unit2.openning:
                time.sleep(1)
            self._sys_led.set_status("white", "on")
            time.sleep(1)
            self._sys_led.stop()
            self._logger.log(3, "Exitting app")
            self._stop()
            time.sleep(1)
            self._check_reboot()

    def __str__(self) -> str:
        return "MeritAccessMainApp"

    def __repr__(self) -> str:
        return "MeritAccessMainApp"
