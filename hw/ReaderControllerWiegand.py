import pigpio
from typing import List, Tuple
from queue import Queue
import time

from controllers.ThreadManager import ThreadManager
from constants import READER_PATH, R1_BEEP, R1_GREEN_LED, R1_RED_LED
from constants import R2_BEEP, R2_GREEN_LED, R2_RED_LED, WIE_READER_LED_TIME
from logger.Logger import log


class ReaderWiegand:
    """
    Manages interactions with a Wiegand reader, including reading card data, controlling LEDs, and beeping.
    """

    def __init__(
        self,
        r_id: int,
        green_led: int,
        red_led: int,
        beep: int,
        pi: pigpio.pi,
        device_path: str = READER_PATH,
    ) -> None:
        self.id = r_id
        self._temp_signal_on: bool = False
        self._green_led = green_led
        self._red_led = red_led
        self._beep = beep
        self._pi = pi
        self._device_path: str = device_path + str(self.id)
        self._init_hw()

    def _init_hw(self) -> None:
        """
        Initializes the hardware.
        """
        self._pi.set_mode(self._beep, pigpio.OUTPUT)
        self._pi.set_mode(self._green_led, pigpio.OUTPUT)
        self._pi.set_mode(self._red_led, pigpio.OUTPUT)
        self._set_pins_to_low()

    def _set_pins_to_low(self) -> None:
        """
        Sets all pins to low.
        """
        self._pi.write(self._beep, pigpio.LOW)
        self._pi.write(self._red_led, pigpio.LOW)
        self._pi.write(self._green_led, pigpio.LOW)

    def read(self) -> str:
        """
        Reads data from the reader data queue.
        """
        try:
            with open(self._device_path, "r") as device_file:
                data = device_file.read()
                if data:
                    return data
        except Exception as e:
            log(40, f"Error accessing device: {e}")
            return None

    def buzzer(self, on: bool) -> None:
        """
        Turns the buzzer on/off.
        """
        self._pi.write(self._beep, pigpio.HIGH if on else pigpio.LOW)

    def led(self, on: bool, color: str) -> None:
        """
        Turns the LED on. Color can be "green" or "red".
        """
        if color == "green":
            self._pi.write(self._green_led, pigpio.HIGH if on else pigpio.LOW)
        elif color == "red":
            self._pi.write(self._red_led, pigpio.HIGH if on else pigpio.LOW)

    def set_default_signal(self) -> None:
        """
        Sets the default LED and buzzer signal.
        """
        self.led(False, "green")
        self.led(False, "red")
        self.buzzer(False)

    def __str__(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return str(self.id)


class ReaderControllerWiegand:
    """
    Manages interactions with Wiegand readers, including reading card data, controlling LEDs, and beeping.
    """

    def __init__(self, pi: pigpio.pi) -> None:
        self._pi = pi
        self.readers = {
            1: ReaderWiegand(1, R1_GREEN_LED, R1_RED_LED, R1_BEEP, self._pi),
            2: ReaderWiegand(2, R2_GREEN_LED, R2_RED_LED, R2_BEEP, self._pi),
        }
        self._q: Queue = Queue()
        self._thread_manager: ThreadManager = ThreadManager()

    def _init_threads(self) -> None:
        """
        Initializes the reader data reading threads.
        """
        success = True
        for r in self.readers.values():
            success &= self._thread_manager.start_thread(
                self._thread_read, f"wie_read{r.id}", args=(r,)
            )
        assert success, f"Failed to start some threads in {self}"

    def _thread_read(self, reader: ReaderWiegand) -> None:
        """
        Thread to read data from the reader.
        """
        while not self._thread_manager.stop_event():
            data = reader.read()
            if data:
                self._q.put((reader.id, data))
            time.sleep(0.1)

    def read(self) -> Tuple[int, str]:
        """
        Reads data from the readers.
        """
        if not self._q.empty():
            return self._q.get()

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
        self._thread_manager.start_thread(
            self._thread_set_signal,
            args=(reader_id, color, buzzer, duration, on_time, off_time),
        )

    def set_default_signal(self, reader_id: int) -> None:
        """
        Set the default LED and buzzer signal for the reader.
        """
        r = self.readers[reader_id]
        r.set_default_signal()

    def _thread_set_signal(
        self,
        reader_id: int,
        color: str,
        buzzer: bool,
        duration: int = 0,
        on_time: int = 0,
        off_time: int = 0,
    ) -> None:
        """
        Thread to set the reader LED and buzzer signal.
        """
        r = self.readers[reader_id]
        while r._temp_signal_on:
            time.sleep(WIE_READER_LED_TIME)
        if duration:
            r._temp_signal_on = True
            r.led(True, color)
            if buzzer:
                r.buzzer(True)
            time.sleep(duration)
            r.set_default_signal()
            r._temp_signal_on = False
        else:
            r.set_default_signal()
            r.led(True, color)
            if buzzer:
                r.buzzer(True)

    def exit(self):
        self._thread_manager.stop_all()

    def __str__(self) -> str:
        return "ReaderControllerWiegand"

    def __repr__(self) -> str:
        return "ReaderControllerWiegand"
