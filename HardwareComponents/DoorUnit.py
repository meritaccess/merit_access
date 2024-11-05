import threading
import time
import pigpio

from .ReaderWiegand import ReaderWiegand


class DoorUnit:
    """
    Manages door operations.
    """

    def __init__(self, du_id: str, reader: ReaderWiegand, relay: int, pi) -> None:
        self.openning: bool = False
        self.extra_time: bool = False
        self.permanent_open: bool = False
        self.monitor: bool = False
        self._relay: int = relay
        self.du_id: int = du_id
        self._reader: ReaderWiegand = reader
        self._pi = pi
        self._init_hw()

    def _init_hw(self) -> None:
        self._pi.set_mode(self._relay, pigpio.OUTPUT)
        self._pi.write(self._relay, pigpio.LOW)

    def open_door(self, open_time=3) -> None:
        t = threading.Thread(
            target=self._thread_open_door,
            args=(open_time,),
            daemon=True,
            name=f"open_door{self.du_id}",
        )
        t.start()

    def permanent_open_door(self) -> None:
        """
        Door remains silently open until closed() is called.
        """
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
        Thread to open door for a given time.
        """
        if not self.permanent_open:
            print("Opening door:", self.du_id)
            self.openning = True
            self._pi.write(self._relay, pigpio.HIGH)
            self._reader.beep_on()
            self._reader.led_on("green")
            time.sleep(open_time)
            while self.extra_time:
                self.extra_time = False
                time.sleep(open_time)
            if not self.permanent_open:
                self._pi.write(self._relay, pigpio.LOW)
                self._reader.led_off("green")
            self._reader.beep_off()
            self.openning = False

    def __str__(self) -> str:
        return self.du_id

    def __repr__(self) -> str:
        return self.du_id
