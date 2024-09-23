import time
from datetime import datetime, timedelta
import threading
from random import randint

from HardwareComponents import ReaderWiegand, DoorUnit
from DataControllers import WebServicesController, IvarController, WsControllerABC
from .OfflineMode import OfflineMode
from Logger import log
from constants import MAC


class CloudMode(OfflineMode):
    """
    Extends the OfflineMode to add functionality for verifying access permissions and logging
    access attempts through cloud-based web services. This mode allows for real-time access control
    decisions based on both local and cloud data sources.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update: bool = False
        self._ws_controller = self._get_ws_controller()
        self._ws_ready: bool = self._ws_controller.check_connection()
        log(20, f"WS Ready: {self._ws_ready}")
        self._update_local_db()

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

    def _apache_setup(self) -> None:
        disable_web = bool(int(self._db_controller.get_val("ConfigDU", "disable_web")))
        if disable_web:
            self._apache_controller.stop()
        else:
            self._apache_controller.start()

    def _get_ws_controller(self) -> WsControllerABC:
        """
        Returns the web services controller for the mode.
        """
        enable_ivar = bool(int(self._db_controller.get_val("ConfigDU", "enable_ivar")))
        if enable_ivar:
            ws_address = self._db_controller.get_val("ConfigDU", "ivar_server")
            term1 = self._db_controller.get_val("ConfigDU", "ivar_term_name1")
            term2 = self._db_controller.get_val("ConfigDU", "ivar_term_name2")
            return IvarController(
                ws_address=ws_address, address_r1=term1, address_r2=term2
            )
        ws_address = self._db_controller.get_val("ConfigDU", "ws")
        return WebServicesController(ws_address)

    def _update_local_db(self) -> None:
        cards = self._ws_controller.load_all_cards()
        print(f"New cards: \n{cards}\n")
        self._db_controller.update_temp_cards(cards)
        print("Loading done. Setting tempKarty to active...")
        self._db_controller.activate_temp_cards()
        print()

        if not isinstance(self._ws_controller, IvarController):
            tplans = self._ws_controller.load_all_tplans()
            print(f"New time plans: \n{tplans}\n")
            self._db_controller.update_temp_tplans(tplans)
            print("Loading done. Setting tempCasovePlany to active...")
            self._db_controller.activate_temp_tplans()

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
        if not self._is_thread_running("sys_tplans"):
            self._check_sys_tplans()
        if not self._is_thread_running("check_ws"):
            self._check_ws(1)
        if not self._is_thread_running("update_db"):
            self._update_db()
        if not self._is_thread_running("sync_db"):
            self._sync_db()
        if not self._is_thread_running("sync_access"):
            self._sync_access()

    def _reader_access(self, reader: ReaderWiegand, door_unit: DoorUnit) -> None:
        """
        Checks if a card has been read by the specified reader and grants access if appropriate.
        """
        card_id = reader.read()
        mytime = datetime.now()
        if not card_id:
            return
        plan_id = self._db_controller.get_card_tplan(card_id, reader.id)
        action = self._tplan_controller.get_action(plan_id)
        print(action)
        status = 701
        success = False

        if self._db_controller.check_card_access(card_id, reader.id):
            self._execute_action(action, door_unit)
            success = self._ws_controller.insert_to_access(
                card_id, reader.id, mytime, status
            )
            if not success:
                status += 10
        else:
            access_online = self._ws_controller.open_door_online(card_id, reader.id)
            if access_online == 0:
                status = 716
            elif access_online == 1:
                self._execute_action(action, door_unit)
                self._update = True
            else:
                status = 726

        self._db_controller.insert_to_access(card_id, reader.id, mytime, status)
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
                self._update = False
                self._update_local_db()
            time.sleep(1)

    def _sync_db(self) -> None:
        sync_time = self._get_sync_time(0, 1)
        t = threading.Thread(
            target=self._thread_sync_db, daemon=True, name="sync_db", args=(sync_time,)
        )
        self._threads.append(t)
        t.start()

    def _get_sync_time(self, start: int, end: int) -> datetime:
        start = timedelta(hours=start)
        end = timedelta(hours=end)
        random_time_delta = start + timedelta(
            seconds=randint(0, int(end.total_seconds()))
        )
        random_time = (datetime.min + random_time_delta).time()
        log(20, f"DB sync time for unit {MAC} is {random_time}")
        return random_time

    def _thread_sync_db(self, sync_time):
        while not self._stop_event.is_set():
            curr_time = datetime.now()
            if (
                curr_time.hour == sync_time.hour
                and curr_time.minute == sync_time.minute
            ):
                self._update = True
                time.sleep(60)
            time.sleep(2)

    def _sync_access(self) -> None:
        t = threading.Thread(
            target=self._thread_sync_access, daemon=True, name="sync_access"
        )
        self._threads.append(t)
        t.start()

    def _thread_sync_access(self) -> None:
        while not self._stop_event.is_set():
            if self._ws_ready:
                records_711 = self._db_controller.filter_access_by_status(711)
                records_726 = self._db_controller.filter_access_by_status(726)
                all_records = records_711 + records_726
                for record in all_records:
                    success = self._ws_controller.insert_to_access(
                        record[2], record[3], record[5], record[6] - 10
                    )
                    if success:
                        self._db_controller.change_status(record[6] - 10, record[0])
            time.sleep(1)
