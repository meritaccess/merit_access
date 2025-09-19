import time
from typing import Dict, Tuple, List
from datetime import datetime
import copy

from hw.DoorUnitController import DoorUnitController
from hw.Button import Button
from .BaseModeABC import BaseModeABC
from controllers.MQTTController import MQTTController
from controllers.MQTTController import CommandParser
from controllers.TimePlanController import TimePlanController
from logger.Logger import log
from constants import (
    MAC,
    Action,
    Config,
    Status,
    MODE_SLEEP_TIME,
    OPEN_BTN_TIME,
    MONITOR_BTN_TIME,
)


class OfflineMode(BaseModeABC):
    """
    Implements the operational logic for the system when running in offline mode. In this mode, the system
    operates independently of external web services, relying on local database checks for access control.
    """

    def __init__(
        self,
        *args,
        du_controller: DoorUnitController,
        open_btn1: Button,
        open_btn2: Button,
        monitor_btn1: Button,
        monitor_btn2: Button,
        mqtt_controller: MQTTController,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._du_controller = du_controller
        self._open_btn1 = open_btn1
        self._open_btn2 = open_btn2
        self._monitor_btn1 = monitor_btn1
        self._monitor_btn2 = monitor_btn2
        self._mqtt_controller = mqtt_controller
        self._mqtt_enabled: bool = bool(
            int(self._db_controller.get_prop("ConfigDU", "mqttenabled"))
        )

        # Time Plans
        self._tplan_controller: TimePlanController = TimePlanController()
        self._sys_actions: Dict = {}

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks, such as logging start information and updating database values.
        """
        self._mode_name: str = "OfflineMode"
        self._sys_led.set_status("magenta", "on")
        self._get_tplans()
        log(20, self._mode_name)

    def _apache_setup(self) -> None:
        """
        Set the Apache web server.
        """
        self._apache_controller.start()

    def _ssh_setup(self) -> None:
        """
        Set the SSH server.
        """
        enable_ssh_password = not bool(
            int(self._db_controller.get_prop("ConfigDU", "disable_ssh_password"))
        )
        disable_ssh = bool(int(self._db_controller.get_prop("ConfigDU", "disable_ssh")))
        self._ssh_controller.password_auth(enable_ssh_password)

        if disable_ssh:
            self._ssh_controller.stop()
        else:
            self._ssh_controller.start()

    def _execute_action(self, action: Action, reader_id: int) -> None:
        """
        Executes an action for a reader (associated door).
        """
        if reader_id in self._sys_actions.keys():
            if self._sys_actions[reader_id] == Action.SILENT_OPEN:
                return
        if action == Action.PULS:
            self._du_controller.open_door(reader_id)
        elif action == Action.REVERSE:
            self._du_controller.reverse_door(reader_id)

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
        self._db_controller.insert_to_access(card_id, reader_id, mytime, status)

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
                # only if door has monitor
                if self._du_controller.get_has_monitor(reader_id):
                    # Check if door is not kept open
                    pulse_time = self._du_controller.get_pulse_time(reader_id)
                    max_open_time = self._du_controller.get_max_open_time(reader_id)
                    status = self._door_opened_timer(
                        reader_id, max_open_time + pulse_time
                    )
        else:
            self._du_controller.set_signal(reader_id, "red", True, 1, 1, 1)
        self._db_controller.insert_to_access(card_id, reader_id, mytime, status)
        self._mqtt_card_read(card_id, reader_id)
        log(
            10,
            f"card: {card_id} | reader: {reader_id} | time: {mytime} | status: {status.name} ({status.value})",
        )

    def _door_opened_timer(self, reader_id: int, duration: int) -> Status:
        """
        Check if door is closed after a given duration
        """
        closed = self._du_controller.is_monitor(
            reader_id
        ) == self._du_controller.get_monitor_default(reader_id)
        # wait until door opens
        while closed:
            closed = self._du_controller.is_monitor(
                reader_id
            ) == self._du_controller.get_monitor_default(reader_id)
            time.sleep(MONITOR_BTN_TIME)

        # start timer
        start = time.time()
        while time.time() - start < duration:
            closed = self._du_controller.is_monitor(
                reader_id
            ) == self._du_controller.get_monitor_default(reader_id)
            if closed:
                return Status.ALLOW
            time.sleep(MONITOR_BTN_TIME)
        return Status.ALLOW_DOOR_NOT_CLOSED

    def _card_access(self, access_details: Tuple[int, str]) -> None:
        """
        Check if card has access
        """
        if not access_details:
            return
        reader_id = access_details[0]
        card_id = access_details[1]
        log(10, f"Reader: {reader_id} CardID: {card_id}")
        self._thread_manager.start_thread(
            self._thread_check_card_access, args=(card_id, reader_id)
        )

    def _silent_open(self, last_sys_actions: Dict) -> Dict:
        """
        Handles silent open actions based on system time plans.
        """
        sys_actions = copy.deepcopy(self._sys_actions)
        for i, action in sys_actions.items():
            if i in last_sys_actions.keys():
                if action != last_sys_actions[i]:
                    tplan = self._du_controller.get_reader_info(i, "sys_plan")
                    if action == Action.SILENT_OPEN:
                        log(20, f"Activating sys_plan {tplan}")
                        self._du_controller.permanent_open_door(i)
                    elif action == Action.NONE:
                        log(20, f"Deactivating sys_plan {tplan}")
                        self._du_controller.close_door(i)
        return sys_actions

    def _mqtt_card_read(self, card_id: str, reader_id: int) -> None:
        """
        Publishes a card read event to the MQTT topic if MQTT is enabled.
        """
        if self._mqtt_enabled:
            msg = f"{MAC}|{card_id}*{reader_id}"
            log(10, f"MQTT message: {msg}")
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
        for i in range(self._du_controller.get_readers_count()):
            if self._du_controller.get_has_monitor(i + 1):
                success &= self._thread_manager.start_thread(
                    self._thread_check_unauthorized_access,
                    f"unauthorized_access{i+1}",
                    args=(i + 1,),
                )
        assert success is True, f"Failed to start some threads in {self}"

    def _thread_open_btns(self) -> None:
        """
        Thread function to check if open buttons are pressed and opens the corresponding doors.
        """
        while not self._thread_manager.stop_event():
            if self._open_btn1.pressed():
                if not self._du_controller.is_opening(1):
                    self._du_controller.open_door(1)
                    self._insert_to_access(
                        "00000 0000000", 1, datetime.now(), Status.OPEN_WITH_BTN
                    )
            if self._open_btn2.pressed():
                if not self._du_controller.is_opening(2):
                    self._du_controller.open_door(2)
                    self._insert_to_access(
                        "00000 0000000", 1, datetime.now(), Status.OPEN_WITH_BTN
                    )

            time.sleep(OPEN_BTN_TIME)

    def _thread_monitor_btns(self) -> None:
        """
        Thread to update monitor status
        """
        self._du_controller.init_monitor(1, self._monitor_btn1.pressed())
        self._du_controller.init_monitor(2, self._monitor_btn2.pressed())
        time.sleep(MONITOR_BTN_TIME)
        while not self._thread_manager.stop_event():
            self._du_controller.set_monitor(1, self._monitor_btn1.pressed())
            self._du_controller.set_monitor(2, self._monitor_btn2.pressed())
            time.sleep(MONITOR_BTN_TIME)

    def _thread_mqtt_check(self) -> None:
        """
        Thread function to check MQTT messages and process commands.
        """
        command_parser = CommandParser(self._du_controller, self._db_controller)
        self._mqtt_controller.clear_queue()
        while not self._thread_manager.stop_event():
            if self._mqtt_controller.is_connected():
                msg = self._mqtt_controller.get_msg()
                if msg:
                    log(10, f"MQTT message: {msg}")
                    response = command_parser.parse_command(msg)
                    if response:
                        self._mqtt_controller.publish(response)

            else:
                self._mqtt_controller.clear_queue()
                self._mqtt_controller.connect()

    def _thread_check_sys_tplans(self) -> None:
        """
        Thread function to periodically (every started minute) check system time plans and update actions.
        """
        last_minute = datetime.now().minute
        sys_tplans = self._du_controller.get_sys_tplans()
        for i, sys_tplan in enumerate(sys_tplans):
            self._sys_actions[i + 1] = self._tplan_controller.get_action(sys_tplan)
        while not self._thread_manager.stop_event():
            if last_minute != datetime.now().minute:
                for i, sys_tplan in enumerate(sys_tplans):
                    self._sys_actions[i + 1] = self._tplan_controller.get_action(
                        sys_tplan
                    )
            time.sleep(1)

    def _thread_check_unauthorized_access(self, reader_id: int) -> None:
        """
        Thread method to check unauthorized access (door opened without card)
        """
        monitor_default = self._du_controller.get_monitor_default(reader_id)
        while not self._thread_manager.stop_event():
            door_opened = monitor_default != self._du_controller.is_monitor(reader_id)
            if door_opened:
                # authorized access (opened with card)
                if self._du_controller.is_opening(reader_id):
                    # wait until door is closed
                    while monitor_default != self._du_controller.is_monitor(reader_id):
                        time.sleep(MONITOR_BTN_TIME)
                else:
                    # unauthorized access (opened without card)
                    self._insert_to_access(
                        "00000 0000000",
                        reader_id,
                        datetime.now(),
                        Status.UNAUTHORIZED_ACCESS,
                    )
                    # wait until door is closed
                    while monitor_default != self._du_controller.is_monitor(reader_id):
                        time.sleep(MONITOR_BTN_TIME)
            time.sleep(MONITOR_BTN_TIME)

    def run(self) -> Config:
        """
        The main loop of the mode.
        """
        try:
            self._initial_setup()
            self._du_controller.load_active_readers()
            self._init_threads()
            self._apache_setup()
            self._ssh_setup()

            last_sys_actions = {}
            for i in range(len(self._sys_actions.values())):
                last_sys_actions[i + 1] = Action.NONE

            self._du_controller.init_read()
            while not self._exit:
                access_details = self._du_controller.read_readers()
                if access_details:
                    self._card_access(access_details)
                if self._config_btn_is_pressed == 1:
                    return Config.CONFIG
                elif self._config_btn_is_pressed == 2:
                    return Config.OSDP
                last_sys_actions = self._silent_open(last_sys_actions)
                # To avoid system overload. Do not go below 0.05s
                time.sleep(MODE_SLEEP_TIME)
        except Exception as e:
            log(40, str(e))
        finally:
            self.exit()
