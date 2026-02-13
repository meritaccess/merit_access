import pigpio
import time
import subprocess
import os
from datetime import datetime
from typing import Any

from constants import CONFIG_BTN, OPEN1, OPEN2, APP_PATH, AP_PASS
from constants import MONITOR1, MONITOR2, MAC, Mode, Config
from hw.DoorUnitController import DoorUnitController
from hw.Button import Button
from hw.LedInfo import LedInfo
from controllers.TimeController import TimeController
from controllers.DatabaseController import DatabaseController
from controllers.MQTTController import MQTTController
from modes.OfflineMode import OfflineMode
from modes.CloudMode import CloudMode
from modes.ConfigModeOffline import ConfigModeOffline
from modes.ConfigModeCloud import ConfigModeCloud
from modes.ConfigModeOSDP import ConfigModeOSDP
from controllers.WifiController import WifiController
from controllers.NetworkController import NetworkController
from controllers.SSHController import SSHController
from controllers.ApacheController import ApacheController
from controllers.HealthCheck import HealthCheck
from controllers.ThreadManager import ThreadManager
from logger.Logger import log


class MeritAccessApp:
    """
    The main application class for the Merit Access control system. This class initializes all necessary
    components of the access control system, selects operational modes based on configuration, and manages
    the system's main operation loop.
    """

    def __init__(self) -> None:
        self._pi: pigpio.pi = pigpio.pi()
        # software objects
        self._thread_manager: ThreadManager = ThreadManager()
        self._db_controller: DatabaseController = DatabaseController()
        self._set_time()
        self._wifi_controller: WifiController = self._get_wifi_controller()
        self._network_controller: NetworkController = NetworkController()
        self._network_settings()
        self._mqtt_controller: MQTTController = self._get_mqtt_controller()
        self._ssh_controller: SSHController = SSHController()
        self._apache_controller: ApacheController = ApacheController()

        # hardware objects
        self._sys_led: LedInfo = LedInfo(pi=self._pi)
        self._du_controller: DoorUnitController = DoorUnitController(
            db_controller=self._db_controller, pi=self._pi
        )
        self._open_btn1: Button = Button(pin=OPEN1, btn_id="OpenBtn1", pi=self._pi)
        self._open_btn2: Button = Button(pin=OPEN2, btn_id="OpenBtn2", pi=self._pi)
        self._monitor_btn1: Button = Button(
            pin=MONITOR1, btn_id="MonitorBtn1", pi=self._pi
        )
        self._monitor_btn2: Button = Button(
            pin=MONITOR2, btn_id="MonitorBtn2", pi=self._pi
        )
        self._config_btn: Button = Button(
            pin=CONFIG_BTN, btn_id="ConfigBtn", pi=self._pi
        )

        # setup
        # 0 - cloud, 1 - offline
        self._main_mode: Mode = Mode(
            int(self._db_controller.get_prop("ConfigDU", "mode"))
        )
        self._config_mode: Config = Config.NONE
        self._in_config_mode = False
        self._running_mode = None
        self._pending_reboot = False
        self._exit = False
        self._init_threads()
        self._check_version()

    def _initial_setup(self) -> None:
        """
        Initial setup for the unit, logging startup details and updating the database.
        """
        version = self._db_controller.get_prop("running", "Version")
        text = f"Starting Unit: {MAC}, IP(interface={self._network_controller.get_interface()}): {self._network_controller.get_ip_address()}, {version}"
        log(20, text)
        self._db_controller.set_prop("running", "MyID", MAC)
        self._db_controller.set_prop("running", "LastStart", datetime.now())

    def _set_time(self) -> None:
        new_time = self._db_controller.get_prop("running", "change_time")
        last_change = self._db_controller.get_running_lastchange("change_time")
        time_controller: TimeController = TimeController()
        time_controller.set_time(new_time, last_change)
        self._db_controller.set_prop("running", "change_time", "")

    def _init_threads(self) -> None:
        """
        Run all necessary checks and tests for the system.
        """
        self._thread_manager.start_thread(
            self._thread_health_check, "health_check", args=(600,)
        )
        self._thread_manager.start_thread(self._thread_pending_reboot, "pending_reboot")
        self._thread_manager.start_thread(self._thread_update_ip, "update_ip")

    def _get_wifi_controller(self) -> WifiController:
        """
        Get the WifiController object based on the configuration in the database.
        """
        wifi_ssid = self._db_controller.get_prop("ConfigDU", "ssid")
        wifi_pass = self._db_controller.get_prop("ConfigDU", "wifipass")
        ap_ssid = MAC
        ap_pass = AP_PASS
        return WifiController(wifi_ssid, wifi_pass, ap_ssid, ap_pass)

    def _get_mqtt_controller(self) -> MQTTController:
        """
        Get the MQTTController object based on the configuration in the database.
        """
        broker = self._db_controller.get_prop("ConfigDU", "mqttserver")
        topic_root = self._db_controller.get_prop("ConfigDU", "mqtttopic")
        topic_sub = f"{topic_root}{MAC}"
        topic_pub = f"{topic_root}common"
        return MQTTController(broker, topic_pub, topic_sub)

    def _network_settings(self) -> None:
        """
        Configures the network settings for the system.
        """
        self._set_interface()
        use_dhcp = bool(int(self._db_controller.get_prop("ConfigDU", "dhcp")))
        if use_dhcp:
            self._network_controller.set_dhcp()
        else:
            ip = self._db_controller.get_prop("ConfigDU", "ip")
            subnet = self._db_controller.get_prop("ConfigDU", "mask")
            gateway = self._db_controller.get_prop("ConfigDU", "dg")
            dns = self._db_controller.get_prop("ConfigDU", "dns1")
            self._network_controller.set_static_ip(ip, subnet, gateway, dns)

    def _set_interface(self) -> None:
        """
        Set network interface according to database.
        """
        wifi_enable = bool(int(self._db_controller.get_prop("ConfigDU", "enablewifi")))
        if wifi_enable:
            self._wifi_controller.wifi_connect()
            interface = "wlan0"
        else:
            interface = "eth0"
            if self._wifi_controller.check_wifi_connection():
                self._wifi_controller.wifi_disconnect()
        self._network_controller.set_interface(interface)

    def _check_version(self) -> None:
        """
        Check and update the software version in the database.
        """
        version_db = self._db_controller.get_prop("running", "Version")
        file = os.path.join(APP_PATH, "version.txt")
        if os.path.exists(file):
            with open(file, "r") as f:
                version = f.read().strip()
            if version != version_db:
                self._db_controller.set_prop("running", "Version", version)

    def _thread_update_ip(self) -> None:
        """
        Thread to periodically check and update the IP address.
        """
        while not self._thread_manager.stop_event():
            current_ip = self._network_controller.get_ip_address()
            if not current_ip:
                time.sleep(1)
                continue
            old_ip = self._db_controller.get_prop("running", "MyIP")
            if not self._in_config_mode and current_ip != old_ip:
                self._db_controller.set_prop("running", "MyIP", current_ip)
            time.sleep(1)

    def _thread_pending_reboot(self) -> None:
        """
        Thread function to handle pending reboot requests.
        """
        while not self._thread_manager.stop_event():
            if not self._pending_reboot:
                self._pending_reboot = bool(
                    int(self._db_controller.get_prop("running", "restart"))
                )
            if self._pending_reboot:
                self._db_controller.set_prop("running", "restart", "0")
                if self._running_mode:
                    self._running_mode.exit()
                self.exit()
            time.sleep(1)

    def _thread_health_check(self, update_time: int) -> None:
        """
        Thread function to perform health checks at regular intervals.
        """
        last_update = time.time()
        health_check = HealthCheck()
        health_check.check_health()
        while not self._thread_manager.stop_event():
            if time.time() - last_update > update_time:
                last_update = time.time()
                health_check.check_health()
            time.sleep(0.5)

    def exit(self) -> None:
        """
        Set the exit flag to True, signaling the main loop to stop.
        """
        self._exit = True

    def _stop(self) -> None:
        """
        Stop all threads and clean up pigpio resources.
        """
        self._pi.stop()
        self._thread_manager.stop_all()

    def _check_reboot(self) -> None:
        """
        Reboot system if a reboot is pending.
        """
        if self._pending_reboot:
            try:
                text = "Scheduled system reboot due to setting changes"
                log(20, text)
                subprocess.run(["sudo", "reboot"], check=True)
            except subprocess.CalledProcessError as e:
                err = f"Error: {e}"
                log(40, err)

    def run(self) -> None:
        """
        The main operation loop of the application. This loop selects and runs the operational mode based
        on the current system configuration, handling mode transitions as required.
        """
        # select and run different modes
        self._initial_setup()
        try:
            args_base = [
                self._sys_led,
                self._config_btn,
                self._db_controller,
                self._ssh_controller,
                self._apache_controller,
            ]
            args_main_mode = {
                "du_controller": self._du_controller,
                "open_btn1": self._open_btn1,
                "open_btn2": self._open_btn2,
                "monitor_btn1": self._monitor_btn1,
                "monitor_btn2": self._monitor_btn2,
                "mqtt_controller": self._mqtt_controller,
            }

            while not self._exit:
                # CloudMode
                if self._main_mode == Mode.CLOUD and self._config_mode == Config.NONE:
                    self._running_mode = CloudMode(*args_base, **args_main_mode)
                    self._config_mode = self._running_mode.run()

                # OfflineMode
                elif (
                    self._main_mode == Mode.OFFLINE and self._config_mode == Config.NONE
                ):
                    self._running_mode = OfflineMode(*args_base, **args_main_mode)
                    self._config_mode = self._running_mode.run()
                # ConfigMode
                if self._config_mode == Config.CONFIG:
                    self._in_config_mode = True
                    if self._main_mode == Mode.CLOUD:
                        self._running_mode = ConfigModeCloud(
                            *args_base, wifi_controller=self._wifi_controller
                        )
                        self._config_mode = self._running_mode.run()
                    else:
                        self._running_mode = ConfigModeOffline(
                            *args_base,
                            wifi_controller=self._wifi_controller,
                            du_controller=self._du_controller,
                        )
                        self._config_mode = self._running_mode.run()
                # OSDP config mode
                if self._config_mode == Config.OSDP:
                    self._in_config_mode = True
                    self._running_mode = ConfigModeOSDP(
                        *args_base,
                        wifi_controller=self._wifi_controller,
                        du_controller=self._du_controller,
                    )
                    self._config_mode = self._running_mode.run()

                self._in_config_mode = False

        except KeyboardInterrupt:
            print("Ending by keyboard request")
        except Exception as e:
            log(40, str(e))
        finally:
            self._du_controller.exit()
            self._sys_led.set_status("white", "on")
            self._sys_led.exit()
            self._mqtt_controller.disconnect()
            log(20, f"Stopping Unit {MAC}")
            self._stop()
            self._check_reboot()

    def __str__(self) -> str:
        return "MeritAccessMainApp"

    def __repr__(self) -> str:
        return "MeritAccessMainApp"
