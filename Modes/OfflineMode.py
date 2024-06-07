import time
from datetime import datetime as dt
import threading
from Reader.ReaderWiegand import ReaderWiegand
from DoorUnit.DoorUnit import DoorUnit
from Modes.BaseMode import BaseMode
from Button.Button import Button


class OfflineMode(BaseMode):
    """
    Implements the operational logic for the system when running in offline mode. In this mode, the system
    operates independently of external web services, relying on local database checks for access control.
    """

    def __init__(
        self,
        *args,
        du1: DoorUnit,
        du2: DoorUnit,
        open_btn1: Button,
        open_btn2: Button,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.door_unit1: DoorUnit = du1
        self.door_unit2: DoorUnit = du2
        self.open_btn1: Button = open_btn1
        self.open_btn2: Button = open_btn2
        self.mode_name: str = "OfflineMode"
        self.sys_led.set_status("magenta", "on")
        self._open_buttons_thread = None
        self._stop_event = threading.Event()

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
            if self.db_controller.card_access_local(card_id, reader.id, dt.now()):
                self._open_door(door_unit)

    def _network_setup(self) -> None:
        pass

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks, such as logging start information and updating database values.
        """
        self.logger.log(3, "Starting app...")
        self.logger.log(3, "Reading DU config from DB...")
        self.db_controller.set_val("running", "MyID", self.mac)
        self.logger.log(
            3, "DoorUnit ID: " + self.db_controller.get_val("running", "MyID")
        )
        self.db_controller.set_val("running", "LastStart", dt.now())
        self.db_controller.set_val("running", "R1ReadCount", self.r1.read_count)
        self.db_controller.set_val("running", "R1ReadError", self.r1.read_err)
        self.db_controller.set_val("running", "R2ReadCount", self.r2.read_count)
        self.db_controller.set_val("running", "R2ReadError", self.r2.read_err)
        self._network_setup()
        time.sleep(5)

    def _open_buttons(self) -> None:
        """
        Checks if open buttons are pressed and opens the corresponding doors.
        """
        self._open_buttons_thread = threading.Thread(target=self._thread_open_btns, daemon=True, name="open_btns")
        self._open_buttons_thread.start()

    def _thread_open_btns(self) -> None:
        while not self._stop_event.is_set():
            if self.open_btn1.pressed():
                if not self.door_unit1.openning:
                    self.door_unit1.open_door()
            if self.open_btn2.pressed():
                if not self.door_unit2.openning:
                    self.door_unit2.open_door()

    def _stop(self) -> None:
        self._stop_event.set()
        if self._open_buttons_thread:
            self._open_buttons_thread.join()


    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            self._initial_setup()
            # start button thread if not running
            if not self.is_thread_running("open_btns"):
                self._open_buttons()
            while True:
                # check if config button is pressed
                if self.config_btn.pressed():
                    return 2
                # check readers
                self.curr_time = time.perf_counter_ns()
                self._reader_access(self.r1, self.door_unit1)
                self._reader_access(self.r2, self.door_unit2)
                time.sleep(1)
        except Exception as e:
            self.logger.log(1, str(e))
        finally:
            while (
                self.door_unit1.openning or self.door_unit2.openning
            ):  # wait for the reader to finish opening
                time.sleep(1)
            self.sys_led.set_status("black", "off")
            self._stop()
