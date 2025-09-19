import time
from datetime import datetime, timedelta
from random import randint
from typing import List

from controllers.WebServicesController import WebServicesController
from controllers.IvarController import IvarController
from controllers.WsControllerABC import WsControllerABC
from .OfflineMode import OfflineMode
from logger.Logger import log
from constants import MAC, Status, Action


class CloudMode(OfflineMode):
    """
    Extends the OfflineMode to add functionality for verifying access permissions and logging
    access attempts through cloud-based web services. This mode allows for real-time access control
    decisions based on both local and cloud data sources.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update: bool = True
        self._ws_controller = self._get_ws_controller()
        self._ws_ready: bool = self._ws_controller.check_connection()
        log(20, f"WS Ready: {self._ws_ready}")

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks, such as logging start information and updating database values.
        """
        self._mode_name: str = "CloudMode"
        self._sys_led.set_status("yellow", "on")
        self._get_tplans()
        log(20, self._mode_name)

    def _apache_setup(self) -> None:
        """
        Starts or stops the Apache web server based on the configuration.
        """
        disable_web = bool(int(self._db_controller.get_prop("ConfigDU", "disable_web")))
        if disable_web:
            self._apache_controller.stop()
        else:
            self._apache_controller.start()

    def _get_ws_controller(self) -> WsControllerABC:
        """
        Returns the web services controller for the mode.
        """
        enable_ivar = bool(int(self._db_controller.get_prop("ConfigDU", "enable_ivar")))
        if enable_ivar:
            ws_address = self._db_controller.get_prop("ConfigDU", "ivar_server")
            term1 = self._db_controller.get_prop("ConfigDU", "ivar_term_name1")
            term2 = self._db_controller.get_prop("ConfigDU", "ivar_term_name2")
            return IvarController(
                ws_address=ws_address, address_r1=term1, address_r2=term2
            )
        ws_address = self._db_controller.get_prop("ConfigDU", "ws")
        return WebServicesController(ws_address)

    def _update_local_db(self) -> None:
        """
        Updates the local database with data from the web service.
        """

        def _update_cards() -> None:
            cards, success = self._ws_controller.load_all_cards()
            if success:
                log(10, f"New cards: \n{cards}\n")
                self._db_controller.update_temp_cards(cards)
                log(10, "Loading done. Setting tempKarty to active...")
                self._db_controller.activate_temp_cards()
            else:
                log(40, "Error loading cards, probably no connection")

        def _update_tplans() -> None:
            if not isinstance(self._ws_controller, IvarController):
                # ignore time plans overwrite if IVAR is enabled
                tplans, success = self._ws_controller.load_all_tplans()
                if success:
                    log(10, f"New time plans: \n{tplans}\n")
                    self._db_controller.update_temp_tplans(tplans)
                    log(10, "Loading done. Setting tempCasovePlany to active...")
                    self._db_controller.activate_temp_tplans()
                else:
                    log(40, "Error loading tplans, probably no connection")

        self._thread_manager.start_thread(_update_cards, "update_cards")
        self._thread_manager.start_thread(_update_tplans, "update_tplans")

    def _set_sys_led(self) -> None:
        """
        Sets the system LED status based on the web service connection status.
        """
        if self._ws_ready:
            self._sys_led.set_status("yellow", "on")
        else:
            self._sys_led.set_status("yellow", "blink_fast")

    def _insert_to_access(
        self, card_id: str, reader_id: int, mytime: datetime, status: Status
    ) -> None:
        """
        Insert access data to the database.
        """
        log(
            10,
            f"card: {card_id} | reader: {reader_id} | time: {mytime} | status: {status.name} ({status.value})",
        )
        if not isinstance(self._ws_controller, IvarController):
            # IVAR does not support Status.OPEN_WITH_BTN, Status.UNAUTHORIZED_ACCESS
            status = self._ws_controller.insert_to_access(
                card_id, reader_id, mytime, status
            )
        self._db_controller.insert_to_access(card_id, reader_id, mytime, status)

    def _init_threads(self) -> None:
        """
        Initializes all threads for the mode.
        """
        success = True
        success &= self._thread_manager.start_thread(
            self._thread_open_btns, "open_btns"
        )
        success &= self._thread_manager.start_thread(
            self._thread_monitor_btns, "monitor_btns"
        )
        success &= self._thread_manager.start_thread(
            self._thread_config_btn, "config_btn"
        )
        if self._mqtt_enabled:
            success &= self._thread_manager.start_thread(
                self._thread_mqtt_check, "mqtt_check"
            )
        success &= self._thread_manager.start_thread(
            self._thread_check_sys_tplans, "sys_tplans"
        )
        success &= self._thread_manager.start_thread(
            self._thread_check_ws, "check_ws", args=(1,)
        )
        success &= self._thread_manager.start_thread(
            self._thread_update_db, "update_db"
        )
        success &= self._thread_manager.start_thread(
            self._thread_sync_db, "sync_db", args=(self._get_sync_time(0, 1),)
        )
        success &= self._thread_manager.start_thread(
            self._thread_sync_access, "sync_access"
        )
        for i in range(self._du_controller.get_readers_count()):
            if self._du_controller.get_has_monitor(i + 1):
                success &= self._thread_manager.start_thread(
                    self._thread_check_unauthorized_access,
                    f"unauthorized_access{i+1}",
                    args=(i + 1,),
                )
        assert success is True, f"Failed to start some threads in {self}"

    def _thread_check_card_access(self, card_id: str, reader_id: int) -> None:
        """
        Thread function to check card access and execute the corresponding action.
        """
        mytime = datetime.now()
        plan_id = self._db_controller.get_card_tplan(card_id, reader_id)
        action = self._tplan_controller.get_action(plan_id)
        log(10, f"Action: {action}")
        status = self._db_controller.check_card_access(card_id, reader_id)
        if status == Status.ALLOW:
            self._execute_action(action, reader_id)
            if action == Action.PULS:
                pulse_time = self._du_controller.get_pulse_time(reader_id)
                # only if door has monitor
                if self._du_controller.get_has_monitor(reader_id):
                    # Check if door is not kept open
                    max_open_time = self._du_controller.get_max_open_time(reader_id)
                    status = self._door_opened_timer(
                        reader_id, max_open_time + pulse_time
                    )
            status = self._ws_controller.insert_to_access(
                card_id, reader_id, mytime, status
            )
        else:
            # open_door_online automaticaly logs access => do not manualy call insert to access
            status = self._ws_controller.open_door_online(card_id, reader_id)
            if status == Status.ALLOW:
                self._execute_action(action, reader_id)
                self._update = True
            else:
                self._du_controller.set_signal(reader_id, "red", True, 1, 1, 1)
        self._db_controller.insert_to_access(card_id, reader_id, mytime, status)
        self._mqtt_card_read(card_id, reader_id)
        log(
            10,
            f"card: {card_id} | reader: {reader_id} | time: {mytime} | status: {status.name} ({status.value})",
        )

    def _thread_check_ws(self, time_period: int) -> None:
        """
        A threaded method to periodically check the connection to the web service.
        """
        ws_ready_old = self._ws_ready
        while not self._thread_manager.stop_event():
            if time.time() - self._ws_controller.last_access > time_period:
                self._ws_ready = self._ws_controller.check_connection()
                self._set_sys_led()
                if ws_ready_old != self._ws_ready:
                    log(20, f"WS Ready: {self._ws_ready}")
                    ws_ready_old = self._ws_ready
            time.sleep(1)

    def _thread_update_db(self) -> None:
        """
        Thread function to update the local database with data from the web service.
        """
        while not self._thread_manager.stop_event():
            if self._update:
                self._update = False
                self._update_local_db()
            time.sleep(1)

    def _get_sync_time(self, start: int, end: int) -> datetime:
        """
        Returns a random time within the specified range (range is in hours 0, 1 = time between 00:00: 01:00).
        """
        start = timedelta(hours=start)
        end = timedelta(hours=end)
        random_time_delta = start + timedelta(
            seconds=randint(0, int(end.total_seconds()))
        )
        random_time = (datetime.min + random_time_delta).time()
        log(20, f"DB sync time for unit {MAC} is {random_time}")
        return random_time

    def _thread_sync_db(self, sync_time: datetime) -> None:
        """
        Thread function to periodically sync the local database with the web service.
        """
        while not self._thread_manager.stop_event():
            curr_time = datetime.now()
            if (
                curr_time.hour == sync_time.hour
                and curr_time.minute == sync_time.minute
            ):
                self._update = True
                time.sleep(60)
            time.sleep(2)

    def _get_failed_statuses(self) -> List:
        """
        Returns a list of all INSERT_FAILED statuses.
        """
        failed_allow = self._db_controller.filter_access_by_status(
            Status.ALLOW_INSERT_FAILED
        ) + self._db_controller.filter_access_by_status(
            Status.ALLOW_DOOR_NOT_CLOSED_INSERT_FAILED
        )
        failed_deny = self._db_controller.filter_access_by_status(
            Status.DENY_INSERT_FAILED
        )
        failed_unauth = self._db_controller.filter_access_by_status(
            Status.UNAUTHORIZED_ACCESS_INSERT_FAILED
        )
        failed_open_buttons = self._db_controller.filter_access_by_status(
            Status.OPEN_WITH_BTN_INSERT_FAILED
        )
        return failed_allow + failed_deny + failed_unauth + failed_open_buttons

    def _thread_sync_access(self) -> None:
        """
        Thread function to periodically sync access records with the web service.
        """
        while not self._thread_manager.stop_event():
            if self._ws_ready:
                all_records = self._get_failed_statuses()
                for record in all_records:
                    status = self._ws_controller.insert_to_access(
                        record[2], record[3], record[5], Status(record[6] - 10)
                    )
                    insert_failed = {
                        Status.ALLOW_INSERT_FAILED,
                        Status.ALLOW_DOOR_NOT_CLOSED_INSERT_FAILED,
                        Status.DENY_INSERT_FAILED,
                        Status.UNAUTHORIZED_ACCESS_INSERT_FAILED,
                        Status.OPEN_WITH_BTN_INSERT_FAILED,
                    }
                    if status not in insert_failed:
                        self._db_controller.change_status(status, record[0])
                        log(
                            10,
                            f"Access record updated: card: {record[2]} | reader: {record[3]} | time: {record[5]} | status: {status.name} ({status.value})",
                        )

            time.sleep(1)
