import time
from datetime import datetime as dt
import threading
from queue import Queue

from HardwareComponents.Reader.ReaderWiegand import ReaderWiegand
from HardwareComponents.DoorUnit.DoorUnit import DoorUnit
from Modes.BaseModeABC import BaseModeABC
from HardwareComponents.Button.Button import Button
from DataControllers.MQTTController import MQTTController
from CommandParser.CommandParser import CommandParser


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
        self._mode_name: str = "OfflineMode"
        self._sys_led.set_status("magenta", "on")
        self._mqtt_enabled = bool(
            int(self._db_controller.get_val("ConfigDU", "mqttenabled"))
        )

    def _open_door(self, door_unit: DoorUnit) -> None:
        if door_unit.openning:
            door_unit.extra_time = True
        else:
            door_unit.open_door()

    def _reader_access(self, reader: ReaderWiegand, door_unit: DoorUnit) -> None:
        """
        Checks if a card has been read by the specified reader and grants access if appropriate.
        """
        card_id = reader.read()
        if card_id:
            if self._db_controller.check_card_access(card_id, reader.id, dt.now()):
                self._open_door(door_unit)
                self._db_controller.insert_to_access(card_id, reader.id, dt.now(), 701)
            else:
                self._db_controller.insert_to_access(card_id, reader.id, dt.now(), 716)
            self._db_controller.set_val(
                "running", f"R{reader.id}ReadCount", reader.read_count
            )
            self._mqtt_card_read(card_id, reader.id)

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks, such as logging start information and updating database values.
        """
        self._logger.log(3, self._mode_name)
        self._db_controller.set_val("running", "R1ReadCount", self._r1.read_count)
        self._db_controller.set_val("running", "R1ReadError", self._r1.read_err)
        self._db_controller.set_val("running", "R2ReadCount", self._r2.read_count)
        self._db_controller.set_val("running", "R2ReadError", self._r2.read_err)
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
        while not self._stop_event.is_set():
            if self._open_btn1.pressed():
                if not self._door_unit1.openning:
                    self._door_unit1.open_door()
                    self._logger.log(3, "Open button 1 pressed")
            if self._open_btn2.pressed():
                if not self._door_unit2.openning:
                    self._door_unit2.open_door()
                    self._logger.log(3, "Open button 2 pressed")

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
        while not self._stop_event.is_set():
            if self._monitor_btn1.pressed():
                self._door_unit1.monitor = not self._door_unit1.monitor
            if self._monitor_btn2.pressed():
                self._door_unit2.monitor = not self._door_unit2.monitor

    def _mqtt_check(self) -> None:
        t = threading.Thread(
            target=self._thread_mqtt_check, daemon=True, name="mqtt_check"
        )
        self._threads.append(t)
        t.start()

    def _thread_mqtt_check(self) -> None:
        command_parser = CommandParser(
            self._door_unit1,
            self._door_unit2,
            self._db_controller,
            self._mac,
            self._logger,
        )
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
        if self._mqtt_enabled:
            msg = f"{self._mac}|{card_id}*{reader_id}"
            print(msg)
            self._mqtt_controller.publish(msg)

    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            self._initial_setup()
            self._init_threads()
            while not self._exit:
                if self._config_btn_is_pressed == 1:
                    return 1
                # check readers
                self.curr_time = time.perf_counter_ns()
                self._reader_access(self._r1, self._door_unit1)
                self._reader_access(self._r2, self._door_unit2)
                time.sleep(1)
        except Exception as e:
            self._logger.log(1, str(e))
        finally:
            # wait for the reader to finish opening
            while self._door_unit1.openning or self._door_unit2.openning:
                time.sleep(1)
            self._stop()
