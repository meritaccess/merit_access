import time
from datetime import datetime as dt
import threading

from HardwareComponents.Reader.ReaderWiegand import ReaderWiegand
from DataControllers.WebServicesController import WebServicesController
from HardwareComponents.DoorUnit.DoorUnit import DoorUnit
from Modes.OfflineMode import OfflineMode


class CloudMode(OfflineMode):
    """
    Extends the OfflineMode to add functionality for verifying access permissions and logging
    access attempts through cloud-based web services. This mode allows for real-time access control
    decisions based on both local and cloud data sources.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update: bool = False
        self._ws_controller = WebServicesController(
            mac=self._mac, db_controller=self._db_controller
        )
        self._mode_name: str = "CloudMode"
        self._ws_ready: bool = self._ws_controller.check_connection()
        self._logger.log(3, f"WS Ready: {self._ws_ready}")
        self._set_sys_led()
        self._ws_controller.load_all_cards_from_ws()

    def _set_sys_led(self) -> None:
        if self._ws_ready:
            self._sys_led.set_status("yellow", "on")
        else:
            self._sys_led.set_status("yellow", "blink_fast")

    def _init_threads(self) -> None:
        if not self._is_thread_running("open_btns"):
            self._open_btns_check()
        if not self._is_thread_running("monitor_btns"):
            self._monitor_btns_check()
        if not self._is_thread_running("config_btn"):
            self._config_btn_check()
        if not self._is_thread_running("mqtt_check") and self._mqtt_enabled:
            self._mqtt_check()
        if not self._is_thread_running("check_ws"):
            self._check_ws(10)
        if not self._is_thread_running("update_db"):
            self._update_db()

    def _reader_access(self, reader: ReaderWiegand, door_unit: DoorUnit) -> None:
        """
        Checks if a card has been read by the specified reader and grants access if appropriate.
        """
        card_id = reader.read()
        if card_id:
            status = 701
            # check if card has access - local db
            if self._db_controller.check_card_access(card_id, reader.id, dt.now()):
                self._open_door(door_unit)
            # check if card has access - cloud
            elif self._ws_controller.open_door_online(card_id, reader.id, dt.now()):
                self._open_door(door_unit)
                self._update = True
            else:
                status = 716
            self._db_controller.insert_to_access(card_id, reader.id, dt.now(), status)
            self._ws_controller.insert_to_access(card_id, reader.id, dt.now(), status)
            self._db_controller.set_val(
                "running", f"R{reader.id}ReadCount", reader.read_count
            )

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
        ws_ready_old = self._ws_ready
        while not self._stop_event.is_set():
            if time.time() - self._ws_controller.last_access > time_period:
                self._ws_ready = self._ws_controller.check_connection()
                self._set_sys_led()
                if ws_ready_old != self._ws_ready:
                    self._logger.log(2, f"WS Ready: {self._ws_ready}")
                    ws_ready_old = self._ws_ready
                print(f"WS Ready: {self._ws_ready}")
            time.sleep(1)

    def _update_db(self) -> None:
        t = threading.Thread(
            target=self._thread_update_db, daemon=True, name="update_db"
        )
        self._threads.append(t)
        t.start()

    def _thread_update_db(self) -> None:
        while not self._stop_event.is_set():
            if self._update:
                self._ws_controller.load_all_cards_from_ws()
                self._update = False
            time.sleep(1)
