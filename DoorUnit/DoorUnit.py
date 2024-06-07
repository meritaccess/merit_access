import threading
import time
import RPi.GPIO as GPIO
from Reader.ReaderWiegand import ReaderWiegand


class DoorUnit:
    """
    Manages door operations such as opening the door and controlling door hardware.
    """

    def __init__(self, du_id: str, reader: ReaderWiegand, relay: int) -> None:
        self.openning: bool = False
        self.extra_time: bool = False
        self._relay: int = relay
        self._id: str = du_id
        self._reader: ReaderWiegand = reader
        self._init_hw()

    def _init_hw(self) -> None:
        """
        Initializes the hardware components.
        """
        GPIO.setup(self._relay, GPIO.OUT)
        GPIO.output(self._relay, GPIO.LOW)

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
        GPIO.output(self._relay, GPIO.HIGH)
        self._reader.beep_on()
        self._reader.led_on("green")
        time.sleep(3)
        while self.extra_time:
            self.extra_time = False
            time.sleep(3)
        GPIO.output(self._relay, GPIO.LOW)
        self._reader.beep_off()
        self._reader.led_off("green")
        self.openning = False

    def __str__(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return self._id
