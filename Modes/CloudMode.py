import time
from datetime import datetime as dt
import threading

from HardwareComponents import ReaderWiegand, DoorUnit
from DataControllers import WebServicesController
from .OfflineMode import OfflineMode
from Logger import log


class CloudMode(OfflineMode):
    """
    Extends the OfflineMode to add functionality for verifying access permissions and logging
    access attempts through cloud-based web services. This mode allows for real-time access control
    decisions based on both local and cloud data sources.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update: bool = False
        self._ws_controller = WebServicesController(db_controller=self._db_controller)
        self._ws_ready: bool = self._ws_controller.check_connection()
        log(20, f"WS Ready: {self._ws_ready}")
        self._ws_controller.load_all_cards_from_ws()

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks, such as logging start information and updating database values.
        """
        self._mode_name: str = "CloudMode"
        self._sys_led.set_status("yellow", "on")
        self._get_tplans()
        log(20, self._mode_name)
        self._db_controller.set_val("running", "R1ReadCount", self._r1.read_count)
        self._db_controller.set_val("running", "R2ReadCount", self._r2.read_count)
        time.sleep(1)

    def _set_sys_led(self) -> None:
        """
        Sets the system LED status based on the web service connection status.
        """
        if self._ws_ready:
            self._sys_led.set_status("yellow", "on")
        else:
            self._sys_led.set_status("yellow", "blink_fast")

    def _init_threads(self) -> None:
        """
        Initializes all threads for the mode.
        """
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
            plan_id = self._db_controller.get_card_tplan(card_id, reader.id)
            action = self._tplan_controller.get_action(plan_id)
            print(action)
            status = 701
            if self._db_controller.check_card_access(card_id, reader.id):
                self._execute_action(action, door_unit)
            elif self._ws_controller.open_door_online(card_id, reader.id, dt.now()):
                self._execute_action(action, door_unit)
                self._update = True
            else:
                status = 716
            self._db_controller.insert_to_access(card_id, reader.id, dt.now(), status)
            self._ws_controller.insert_to_access(card_id, reader.id, dt.now(), status)
            self._db_controller.set_val(
                "running", f"R{reader.id}ReadCount", reader.read_count
            )
            self._mqtt_card_read(card_id, reader.id)

    def _check_ws(self, time_period: int) -> None:
        """
        Starts a thread to periodically check the connection to the web service.
        """
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
                    log(20, f"WS Ready: {self._ws_ready}")
                    ws_ready_old = self._ws_ready
            time.sleep(1)

    def _update_db(self) -> None:
        """
        Starts a thread to periodically update the local database with data from the web service.
        """
        t = threading.Thread(
            target=self._thread_update_db, daemon=True, name="update_db"
        )
        self._threads.append(t)
        t.start()

    def _thread_update_db(self) -> None:
        """
        Thread function to update the local database with data from the web service.
        """
        while not self._stop_event.is_set():
            if self._update:
                self._ws_controller.load_all_cards_from_ws()
                self._update = False
            time.sleep(1)
