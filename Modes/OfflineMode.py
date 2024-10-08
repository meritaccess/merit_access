import time
from datetime import datetime as dt
import threading
from typing import Dict, Tuple
from datetime import datetime

from HardwareComponents import ReaderWiegand, DoorUnit, Button
from .BaseModeABC import BaseModeABC
from DataControllers import MQTTController
from CommandParser import CommandParser
from TimePlans import TimePlanController
from Logger import log
from constants import MAC, Action, Config, Status


class OfflineMode(BaseModeABC):
    """
    Implements the operational logic for the system when running in offline mode. In this mode, the system
    operates independently of external web services, relying on local database checks for access control.
    """

    def __init__(
        self,
        *args,
        r1: ReaderWiegand,
        r2: ReaderWiegand,
        du1: DoorUnit,
        du2: DoorUnit,
        open_btn1: Button,
        open_btn2: Button,
        monitor_btn1: Button,
        monitor_btn2: Button,
        mqtt_controller: MQTTController,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._r1 = r1
        self._r2 = r2
        self._door_unit1 = du1
        self._door_unit2 = du2
        self._open_btn1 = open_btn1
        self._open_btn2 = open_btn2
        self._monitor_btn1 = monitor_btn1
        self._monitor_btn2 = monitor_btn2
        self._mqtt_controller = mqtt_controller
        self._mqtt_enabled = bool(
            int(self._db_controller.get_val("ConfigDU", "mqttenabled"))
        )

        # Time Plans
        self._tplan_controller = TimePlanController()
        self._sys_action1: Action = Action.NONE
        self._sys_action2: Action = Action.NONE

    def _apache_setup(self) -> None:
        self._apache_controller.start()

    def _ssh_setup(self) -> None:
        enable_ssh_password = not bool(
            int(self._db_controller.get_val("ConfigDU", "disable_ssh_password"))
        )
        disable_ssh = bool(int(self._db_controller.get_val("ConfigDU", "disable_ssh")))
        self._ssh_controller.password_auth(enable_ssh_password)

        if disable_ssh:
            self._ssh_controller.stop()
        else:
            self._ssh_controller.start()

    def _open_door(self, door_unit: DoorUnit) -> None:
        if door_unit.openning:
            door_unit.extra_time = True
        else:
            door_unit.open_door()

    def _reverse(self, door_unit: DoorUnit) -> None:
        if door_unit.permanent_open:
            door_unit.close_door()
        else:
            door_unit.permanent_open_door()

    def _execute_action(self, action: Action, door_unit: DoorUnit) -> None:
        if door_unit.du_id == 1 and self._sys_action1 == Action.SILENT_OPEN:
            return
        if door_unit.du_id == 2 and self._sys_action2 == Action.SILENT_OPEN:
            return
        if action == Action.PULS:
            self._open_door(door_unit)
        elif action == Action.REVERSE:
            self._reverse(door_unit)

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
        status = self._db_controller.check_card_access(card_id, reader.id)
        if status == Status.ALLOW:
            self._execute_action(action, door_unit)
        self._db_controller.insert_to_access(card_id, reader.id, mytime, status)
        self._db_controller.set_val(
            "running", f"R{reader.id}ReadCount", reader.read_count
        )
        self._mqtt_card_read(card_id, reader.id)

    def _silent_open(
        self, last_sys_action1: Action, last_sys_action2: Action
    ) -> Tuple[Action, Action]:
        """
        Handles silent open actions based on system time plans.
        """
        sys_action1 = self._sys_action1
        sys_action2 = self._sys_action2
        if sys_action1 != last_sys_action1:
            if sys_action1 == Action.SILENT_OPEN:
                self._door_unit1.permanent_open_door()
            elif sys_action1 == Action.NONE:
                self._door_unit1.close_door()
        if sys_action2 != last_sys_action2:
            if sys_action2 == Action.SILENT_OPEN:
                self._door_unit2.permanent_open_door()
            elif sys_action2 == Action.NONE:
                self._door_unit2.close_door()

        return (sys_action1, sys_action2)

    def _check_sys_tplans(self) -> None:
        """
        Starts a thread to periodically check system time plans and update actions for door units.
        """
        t = threading.Thread(
            target=self._thread_check_sys_tplans, daemon=True, name="sys_tplans"
        )
        self._threads.append(t)
        t.start()

    def _thread_check_sys_tplans(self) -> None:
        """
        Thread function to periodically (every started minute) check system time plans and update actions.
        """
        last_minute = dt.now().minute
        sys_tplan_r1 = int(self._db_controller.get_val("ConfigDU", "SYSPLANREADER1"))
        sys_tplan_r2 = int(self._db_controller.get_val("ConfigDU", "SYSPLANREADER2"))
        self._sys_action1 = self._tplan_controller.get_action(sys_tplan_r1)
        self._sys_action2 = self._tplan_controller.get_action(sys_tplan_r2)
        while not self._stop_event.is_set():
            if last_minute != dt.now().minute:
                self._sys_action1 = self._tplan_controller.get_action(sys_tplan_r1)
                self._sys_action2 = self._tplan_controller.get_action(sys_tplan_r2)
            time.sleep(1)

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks, such as logging start information and updating database values.
        """
        self._mode_name: str = "OfflineMode"
        self._sys_led.set_status("magenta", "on")
        self._get_tplans()
        log(20, self._mode_name)
        self._db_controller.set_val("running", "R1ReadCount", self._r1.read_count)
        self._db_controller.set_val("running", "R2ReadCount", self._r2.read_count)
        time.sleep(1)

    def _init_threads(self) -> None:
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

    def _open_btns_check(self) -> None:
        """
        Checks if open buttons are pressed and opens the corresponding doors.
        """
        t = threading.Thread(
            target=self._thread_open_btns, daemon=True, name="open_btns"
        )
        self._threads.append(t)
        t.start()

    def _thread_open_btns(self) -> None:
        """
        Thread function to check if open buttons are pressed and opens the corresponding doors.
        """
        while not self._stop_event.is_set():
            if self._open_btn1.pressed():
                if not self._door_unit1.openning:
                    self._door_unit1.open_door()
                    log(20, "Open button 1 pressed")
            if self._open_btn2.pressed():
                if not self._door_unit2.openning:
                    self._door_unit2.open_door()
                    log(20, "Open button 2 pressed")
            time.sleep(0.2)

    def _monitor_btns_check(self) -> None:
        """
        Checks if monitor buttons are pressed and toggles monitor flag
        """
        t = threading.Thread(
            target=self._thread_monitor_btns, daemon=True, name="monitor_btns"
        )
        self._threads.append(t)
        t.start()

    def _thread_monitor_btns(self) -> None:
        """
        Thread function to check if monitor buttons are pressed and toggles the monitor flag.
        """
        while not self._stop_event.is_set():
            if self._monitor_btn1.pressed():
                self._door_unit1.monitor = not self._door_unit1.monitor
            if self._monitor_btn2.pressed():
                self._door_unit2.monitor = not self._door_unit2.monitor

    def _mqtt_check(self) -> None:
        """
        Starts a thread to check MQTT messages and process commands.
        """
        t = threading.Thread(
            target=self._thread_mqtt_check, daemon=True, name="mqtt_check"
        )
        self._threads.append(t)
        t.start()

    def _thread_mqtt_check(self) -> None:
        """
        Thread function to check MQTT messages and process commands.
        """
        command_parser = CommandParser(self._door_unit1, self._door_unit2)
        self._mqtt_controller.clear_queue()
        while not self._stop_event.is_set():
            if self._mqtt_controller.is_connected():
                msg = self._mqtt_controller.get_msg()
                if msg:
                    print(msg)
                    response = command_parser.parse_command(msg)
                    if response:
                        self._mqtt_controller.publish(response)

            else:
                self._mqtt_controller.clear_queue()
                self._mqtt_controller.connect()

    def _mqtt_card_read(self, card_id: str, reader_id: int) -> None:
        """
        Publishes a card read event to the MQTT topic if MQTT is enabled.
        """
        if self._mqtt_enabled:
            msg = f"{MAC}|{card_id}*{reader_id}"
            print(msg)
            self._mqtt_controller.publish(msg)

    def _get_tplans(self) -> None:
        """
        Retrieves and parses time plans from the database.
        """
        try:
            tplans = self._db_controller.get_tplans()
            for tplan in tplans:
                self._tplan_controller.parse_tplan(tplan)
        except Exception as e:
            log(40, f"Failed to get TimePlans. Error:{e}")

    def run(self) -> Config:
        """The main loop of the mode."""
        try:
            self._initial_setup()
            self._init_threads()
            self._apache_setup()
            self._ssh_setup()
            last_sys_action1 = Action.NONE
            last_sys_action2 = Action.NONE
            while not self._exit:
                if self._config_btn_is_pressed == 1:
                    return Config.CONFIG
                last_sys_action1, last_sys_action2 = self._silent_open(
                    last_sys_action1, last_sys_action2
                )
                self._reader_access(self._r1, self._door_unit1)
                self._reader_access(self._r2, self._door_unit2)
                time.sleep(1)
        except Exception as e:
            log(40, str(e))
        finally:
            # wait for the reader to finish opening
            while self._door_unit1.openning or self._door_unit2.openning:
                time.sleep(1)
            self._stop()
