import threading
import time
import pigpio
from Reader.ReaderWiegand import ReaderWiegand


class DoorUnit:
    """
    Manages door operations such as opening the door and controlling door hardware.
    """

    def __init__(self, du_id: str, reader: ReaderWiegand, relay: int, pi) -> None:
        self.openning: bool = False
        self.extra_time: bool = False
        self._relay: int = relay
        self._id: str = du_id
        self._reader: ReaderWiegand = reader
        self._pi = pi
        self._init_hw()

    def _init_hw(self) -> None:
        """
        Initializes the hardware components.
        """
        self._pi.set_mode(self._relay, pigpio.OUTPUT)
        self._pi.write(self._relay, pigpio.LOW)

    def open_door(self) -> None:
        print("Opening door: ", self._id)
        self.openning = True
        t = threading.Thread(
            target=self._thread_open_door, daemon=True, name=f"open_door{self._id}"
        )
        t.start()

    def _thread_open_door(self) -> None:
        """
        Thread to open door.
        """
        self._pi.write(self._relay, pigpio.HIGH)
        self._reader.beep_on()
        self._reader.led_on("green")
        time.sleep(3)
        while self.extra_time:
            self.extra_time = False
            time.sleep(3)
        self._pi.write(self._relay, pigpio.LOW)
        self._reader.beep_off()
        self._reader.led_off("green")
        self.openning = False

    def __str__(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return self._id
