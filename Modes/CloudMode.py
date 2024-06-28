import time
from datetime import datetime as dt
import threading

from HardwareComponents.Reader.ReaderWiegand import ReaderWiegand
from DataControllers.WebServicesController import WebServicesController
from HardwareComponents.DoorUnit.DoorUnit import DoorUnit
from Modes.OfflineMode import OfflineMode
from Network import NetworkController


class CloudMode(OfflineMode):
    """
    Extends the OfflineMode to add functionality for verifying access permissions and logging
    access attempts through cloud-based web services. This mode allows for real-time access control
    decisions based on both local and cloud data sources.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update: bool = False
        self.ws_controller = WebServicesController(
            mac=self._mac, db_controller=self.db_controller
        )
        self.sys_led.set_status("yellow", "on")
        self.mode_name: str = "CloudMode"

        self.ws_controller.load_all_cards_from_ws()
        self.ws_ready: bool = self.ws_controller.check_connection()
        print(f"WS Ready: {self.ws_ready}")

    def _init_threads(self) -> None:
        if not self._is_thread_running("open_btns"):
            self._open_btns_check()
        if not self._is_thread_running("config_btn"):
            self._config_btn_check()
        if not self._is_thread_running("check_ws"):
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
            self.db_controller.set_val("running", f"R{reader.id}ReadCount", reader.read_count)

    def _check_ws(self, time_period: int) -> None:
        t = threading.Thread(
            target=self._thread_check_ws,
            args=(time_period,),
            daemon=True,
            name="check_ws",
        )
        self._threads.append(t)
        t.start()

    def _thread_check_ws(self, time_period: int) -> None:
        """
        A threaded method to periodically check the connection to the web service.
        """
        while not self._stop_event.is_set():
            if time.time() - self.ws_controller.last_access > time_period:
                self.ws_ready = self.ws_controller.check_connection()
                print(f"WS Ready: {self.ws_ready}")
            time.sleep(1)
