import time
from datetime import datetime as dt
import threading
from Reader.ReaderWiegand import ReaderWiegand
from WebServicesController.WebServicesController import WebServicesController
from DoorUnit.DoorUnit import DoorUnit
from Modes.OfflineMode import OfflineMode
from NetworkController import NetworkController


class CloudMode(OfflineMode):
    """
    Extends the OfflineMode to add functionality for verifying access permissions and logging
    access attempts through cloud-based web services. This mode allows for real-time access control
    decisions based on both local and cloud data sources.
    """

    def __init__(self, *args, network_controller: NetworkController, **kwargs):
        super().__init__(*args, **kwargs)
        self.network_controller: NetworkController = network_controller
        self.update: bool = False
        self.ws_controller = WebServicesController(
            mac=self.mac, db_controller=self.db_controller
        )
        self.sys_led.set_status("yellow", "on")
        self.mode_name: str = "CloudMode"

        self.ws_controller.load_all_cards_from_ws()
        self.ws_ready: bool = self.ws_controller.check_connection()
        print(f"WS Ready: {self.ws_ready}")
        self._check_ws(600)

    def _reader_access(self, reader: ReaderWiegand, door_unit: DoorUnit) -> None:
        """
        Checks if a card has been read by the specified reader and grants access if appropriate.
        """
        card_id = reader.read()
        if card_id:
            # check if card has access - local db
            if self.db_controller.card_access_local(card_id, reader.id, dt.now()):
                self._open_door(door_unit)
            # check if card has access - cloud
            elif self.ws_controller.open_door_online(card_id, reader.id, dt.now()):
                self._open_door(door_unit)
                self.update = True
            self.ws_controller.insert_to_access(card_id, reader.id, dt.now())

    def _network_setup(self) -> None:
        """
        Configures the network settings for the system.
        """
        use_dhcp = bool(int(self.db_controller.get_val("ConfigDU", "dhcp")))
        if use_dhcp:
            self.network_controller.set_dhcp()
        else:
            ip = self.db_controller.get_val("ConfigDU", "ip")
            subnet = self.db_controller.get_val("ConfigDU", "mask")
            gateway = self.db_controller.get_val("ConfigDU", "dg")
            dns = self.db_controller.get_val("ConfigDU", "dns1")
            self.network_controller.set_static_ip(ip, subnet, gateway, dns)

    def _check_ws(self, time_period: int) -> None:
        t = threading.Thread(
            target=self._thread_check_ws, args=(time_period,), daemon=True
        )
        t.start()

    def _thread_check_ws(self, time_period: int) -> None:
        """
        A threaded method to periodically check the connection to the web service.
        """
        while True:
            if time.time() - self.ws_controller.last_access > time_period:
                self.ws_ready = self.ws_controller.check_connection()
                print(f"WS Ready: {self.ws_ready}")
            time.sleep(time_period + 1)
