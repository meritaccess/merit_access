import threading
import time
import pigpio
from HardwareComponents.Reader.ReaderWiegand import ReaderWiegand


class DoorUnit:
    """
    Manages door operations such as opening the door and controlling door hardware.
    """

    def __init__(self, du_id: str, reader: ReaderWiegand, relay: int, pi) -> None:
        self.openning: bool = False
        self.extra_time: bool = False
        self.permanent_open: bool = False
        self.monitor: bool = False
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

    def open_door(self, open_time=3) -> None:
        print("Opening door: ", self._id)
        self.openning = True
        t = threading.Thread(
            target=self._thread_open_door,
            args=(open_time,),
            daemon=True,
            name=f"open_door{self._id}",
        )
        t.start()

    def permanent_open_door(self) -> None:
        self.permanent_open = True
        self._pi.write(self._relay, pigpio.HIGH)
        self._reader.led_on("green")

    def close_door(self) -> None:
        self._pi.write(self._relay, pigpio.LOW)
        self._reader.beep_off()
        self._reader.led_off("green")
        self.permanent_open = False

    def _thread_open_door(self, open_time) -> None:
        """
        Thread to open door.
        """
        if not self.permanent_open:
            self._pi.write(self._relay, pigpio.HIGH)
            self._reader.beep_on()
            self._reader.led_on("green")
            time.sleep(open_time)
            while self.extra_time:
                self.extra_time = False
                time.sleep(open_time)
            if not self.permanent_open:
                self._pi.write(self._relay, pigpio.LOW)
                self._reader.beep_off()
                self._reader.led_off("green")
                self.openning = False

    def __str__(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return self._id
