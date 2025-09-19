from typing import List, Dict, Tuple
import pigpio
import time

from .ReaderControllerWiegand import ReaderControllerWiegand
from .ReaderControllerOSDP import ReaderControllerOSDP
from .DoorController import DoorController
from controllers.DatabaseController import DatabaseController
from constants import Protocol, RELAY1, RELAY2
from logger.Logger import log


class DoorUnitController:

    def __init__(self, db_controller: DatabaseController, pi: pigpio.pi) -> None:
        self._pi = pi
        self._db_controller = db_controller
        self._osdp_controller: ReaderControllerOSDP = ReaderControllerOSDP(
            bool(int(self._db_controller.get_prop("ConfigDU", "use_secure_channel")))
        )
        self._wiegand_controller: ReaderControllerWiegand = ReaderControllerWiegand(
            self._pi
        )
        self._door_controllers: Dict = self._init_door_controllers()
        self._readers_info: Dict = dict()
        self.protocol: Protocol = Protocol.WIEGAND

    def _init_door_controllers(self) -> Dict:
        relays = [RELAY1, RELAY2]
        door_controllers = {}
        for i in range(2):
            door_controllers[i + 1] = DoorController(
                i + 1,
                relays[i],
                self._db_controller.get_has_monitor(i + 1),
                self._db_controller.get_default_monitor(i + 1),
                self._db_controller.get_max_open_time(i + 1) / 1000,
                self._pi,
            )
        return door_controllers

    def read_readers(self) -> Tuple[int, str]:
        """
        Read the card ID for each reader.
        """
        if self.protocol == Protocol.OSDP:
            return self._osdp_controller.read()
        elif self.protocol == Protocol.WIEGAND:
            return self._wiegand_controller.read()

    def init_read(self) -> None:
        """
        Initialize the reader for reading.
        """
        if self.protocol == Protocol.OSDP:
            self._osdp_controller._init_threads()
        elif self.protocol == Protocol.WIEGAND:
            self._wiegand_controller._init_threads()
        self.set_all_default()

    def set_signal(
        self,
        reader_id: int,
        color: str,
        buzzer: bool,
        duration: int = 0,
        on_time: int = 0,
        off_time: int = 0,
    ) -> None:
        """
        Set reader LED and buzzer signal.
        """
        if self.protocol == Protocol.OSDP:
            self._osdp_controller.set_signal(
                reader_id, color, buzzer, duration, on_time, off_time
            )
        elif self.protocol == Protocol.WIEGAND:
            self._wiegand_controller.set_signal(
                reader_id, color, buzzer, duration, on_time, off_time
            )

    def set_default_signal(self, reader_id: int) -> None:
        """
        Set the default LED and buzzer signal for the reader.
        """
        if self.protocol == Protocol.OSDP:
            self._osdp_controller.set_default_signal(reader_id)
        elif self.protocol == Protocol.WIEGAND:
            self._wiegand_controller.set_default_signal(reader_id)

    def set_all_default(self) -> None:
        """
        Set the default LED and buzzer signal for all readers.
        """
        for reader_id in self._readers_info.keys():
            self.set_default_signal(reader_id)

    def open_door(self, reader_id: int, duration: int = None) -> None:
        """
        Open the door associated with a reader for a specified duration.
        """
        OSDP_SYNC = 0.3
        if not duration:
            if reader_id in self._readers_info.keys():
                duration = self._readers_info[reader_id]["pulse_time"]
            else:
                duration = 3
        if self.is_opening(reader_id):
            self.add_extra_time(reader_id)
        else:
            self._door_controllers[reader_id].open_door(duration)

        if self.protocol == Protocol.OSDP:
            # syncs OSDP signal with door opening
            total_duration = duration * self.get_extra_time_count(reader_id)
            elapsed = time.time() - self.get_open_start(reader_id)
            signal_duration = total_duration - elapsed - OSDP_SYNC
        elif self.protocol == Protocol.WIEGAND:
            signal_duration = duration

        self.set_signal(reader_id, "green", True, signal_duration)

    def get_open_start(self, reader_id: int) -> float:
        """
        Get the start time of the door opening.
        """
        return self._door_controllers[reader_id].opening_start

    def get_extra_time_count(self, reader_id: int) -> int:
        """
        Get the extra time count for the door opening.
        """
        return self._door_controllers[reader_id].extra_time_count

    def permanent_open_door(self, reader_id: int) -> None:
        """
        Open the door associated with a reader permanently - silent open.
        """
        self._door_controllers[reader_id].permanent_open_door()
        self.set_signal(reader_id, "green", False)

    def close_door(self, reader_id: int) -> None:
        """
        Close the door associated with a reader.
        """
        self._door_controllers[reader_id].close_door()
        self.set_default_signal(reader_id)

    def reverse_door(self, reader_id: int) -> None:
        """
        Reverse the door state associated with a reader - close if open, open if closed.
        """
        if self.is_permanent_open(reader_id):
            self.close_door(reader_id)
        else:
            self.permanent_open_door(reader_id)

    def is_permanent_open(self, reader_id: int) -> bool:
        """
        Check if the door associated with a reader is permanently open.
        """
        return self._door_controllers[reader_id].permanent_open

    def is_opening(self, reader_id: int) -> bool:
        """
        Check if the door associated with a reader is opening.
        """
        return self._door_controllers[reader_id].opening

    def get_has_monitor(self, reader_id: int) -> bool:
        """
        Get has_monitor value for the door associated with a reader.
        """
        return self._door_controllers[reader_id].has_monitor

    def is_monitor(self, reader_id: int) -> bool:
        """
        Check if the door associated with monitor status.
        """
        return self._door_controllers[reader_id].monitor

    def get_monitor_default(self, reader_id: int) -> bool:
        """
        Get the default monitor status for the door associated with a reader.
        """
        return self._door_controllers[reader_id].monitor_default

    def set_monitor(self, reader_id: int, monitor: bool) -> None:
        """
        Set the monitor status for the door associated with a reader.
        """
        monitor_old = self._door_controllers[reader_id].monitor
        if monitor_old != monitor:
            self._door_controllers[reader_id].monitor = monitor
            self._db_controller.set_monitor(reader_id, monitor)

    def init_monitor(self, reader_id: int, monitor: bool) -> None:
        """
        Initialize the monitor status for the door associated with a reader.
        """
        self._door_controllers[reader_id].monitor = monitor
        self._db_controller.set_monitor(reader_id, monitor)

    def add_extra_time(self, reader_id: int) -> None:
        """
        Add extra opening time to the door associated with a reader (2 or more card taps within opening period).
        """
        self._door_controllers[reader_id].extra_time_count += 1
        self._door_controllers[reader_id].extra_time = True

    def inverse_monitor(self, reader_id: int) -> None:
        """
        Inverse the monitor status of the door associated with a reader.
        """
        self._door_controllers[reader_id].monitor = not self._door_controllers[
            reader_id
        ].monitor

    def get_pulse_time(self, reader_id: int) -> int:
        """
        Get the pulse time for the door associated with a reader.
        """
        return self._readers_info[reader_id]["pulse_time"]

    def get_max_open_time(self, reader_id: int) -> int:
        """
        Get the maximum open time for the door associated with a reader.
        """
        return self._door_controllers[reader_id].max_open_time

    def scan(self) -> None:
        """
        Scan for OSDP readers and load active readers.
        """
        self._db_controller.deactivate_readers()
        log(20, "OSDP enabled, starting scan...")
        self._osdp_controller.scan()
        osdp_dev = self._osdp_controller.detected_addresses
        if len(osdp_dev) >= 1:
            log(20, f"OSDP readers {osdp_dev} detected")
            self.protocol = Protocol.OSDP
            log(20, f"Generating keys...")
            keys = self._osdp_controller.generate_scbk()
            for i, address in enumerate(osdp_dev):
                self._db_controller.activate_reader(
                    i + 1, Protocol.OSDP, address, keys[i]
                )
            log(20, f"Loading readers...")
            self.load_active_readers()
            secure_channel = bool(
                int(self._db_controller.get_prop("ConfigDU", "use_secure_channel"))
            )
            if secure_channel:
                text = "OSDP readers successfully loaded. Please switch readers to secure mode"
            else:
                text = "OSDP readers successfully loaded."
            log(20, text)
        else:
            log(30, "No OSDP readers detected. Readers must be in install mode")

    def load_active_readers(self) -> None:
        """
        Load active readers from the database.
        """
        enable_osdp = bool(int(self._db_controller.get_prop("ConfigDU", "enable_osdp")))
        active_readers = self._db_controller.get_active_readers()
        print(active_readers)
        if enable_osdp:
            if self._validate_readers(active_readers, Protocol.OSDP):
                self._osdp_controller.set_active_readers(active_readers)
                self.protocol = Protocol.OSDP
                self._load_readers_info(active_readers)
                print(self._readers_info)
            else:
                self._set_for_wiegand(active_readers)
        else:
            self._set_for_wiegand(active_readers)

    def _set_for_wiegand(self, active_readers: List[Tuple]) -> None:
        """
        Set the system for Wiegand protocol.
        """
        self.protocol = Protocol.WIEGAND
        if not self._validate_readers(active_readers, Protocol.WIEGAND):
            self._db_controller.deactivate_readers()
            self._db_controller.activate_reader(1, Protocol.WIEGAND)
            self._db_controller.activate_reader(2, Protocol.WIEGAND)
            active_readers = self._db_controller.get_active_readers()
        self._load_readers_info(active_readers)

    def _load_readers_info(self, active_readers: List[Tuple]) -> None:
        """
        Load readers info from active_readers to a dict.
        """
        self._readers_info = {
            r[0]: {
                "protocol": r[1],
                "output": r[5],
                "pulse_time": r[6] / 1000,
                "sys_plan": r[7],
            }
            for r in active_readers
        }

    def get_reader_info(self, reader_id: int, key: str) -> int:
        """
        Retrieve reader info from the readers_info dict.
        """
        if reader_id in self._readers_info.keys():
            info = self._readers_info[reader_id]
            if key in info.keys():
                return info[key]
        return None

    def _validate_readers(
        self, active_readers: List[Tuple], protocol: Protocol
    ) -> bool:
        """
        Validate the active readers from database for a given protocol.
        """
        if not active_readers:
            return False
        if protocol == Protocol.OSDP:
            protocol = "osdp"
        if protocol == Protocol.WIEGAND:
            protocol = "wiegand"
        for r in active_readers:
            if r[1] != protocol:
                return False
        return True

    def get_readers_count(self) -> int:
        """
        Get the number of active readers.
        """
        return len(self._readers_info)

    def get_sys_tplans(self) -> List:
        """
        Get the system time plans.
        """
        return [r["sys_plan"] for r in self._readers_info.values()]

    def exit(self) -> None:
        """
        Exit the OSDP controller - ControlPanel teardown.
        """
        self._osdp_controller.exit()
        self._wiegand_controller.exit()
