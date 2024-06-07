import threading
import RPi.GPIO as GPIO
from typing import Optional
from queue import Queue
from constants import READER_PATH


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
        device_path: str = READER_PATH,
    ) -> None:
        self.id: int = r_id
        self.reader: int = 0
        self._green_led: int = green_led
        self._red_led: int = red_led
        self._beep: int = beep
        self._device_path: str = device_path + str(self.id)
        self._data_queue = Queue()
        self.read_count = 0
        self.read_err = 0
        self._init_hw()
        self._init_read()

    def _init_hw(self) -> None:
        """
        Initializes the hardware components, setting GPIO pin modes for input or output as appropriate and
        configuring pull-up resistors for the data lines.
        """
        GPIO.setup(self._beep, GPIO.OUT)
        GPIO.setup(self._green_led, GPIO.OUT)
        GPIO.setup(self._red_led, GPIO.OUT)
        self._set_pins_to_low()

    def _set_pins_to_low(self) -> None:
        GPIO.output(self._beep, GPIO.LOW)
        GPIO.output(self._red_led, GPIO.LOW)
        GPIO.output(self._green_led, GPIO.LOW)

    def read(self):
        if not self._data_queue.empty():
            self.read_count += 1
            data = self._data_queue.get()
            print(f"Reader: {self.id} CardID: {data}")
            return data

    def _init_read(self) -> None:
        t = threading.Thread(
            target=self._thread_read, daemon=True, name=f"reader{self.id}"
        )
        t.start()

    def _thread_read(self) -> None:
        try:
            with open(self._device_path, "r") as device_file:
                while True:
                    data = device_file.read()
                    if data:
                        self._data_queue.put(data)
        except IOError as e:
            print("Error accessing device:", e)

    def _check_pwm_range(self, intensity: int) -> int:
        """
        Ensures that the value is within the acceptable range (0-255).
        """
        if intensity > 255:
            return 255
        if intensity < 0:
            return 0
        return intensity

    def beep_on(self, intensity: Optional[int] = 255) -> None:
        intensity = self._check_pwm_range(intensity)
        GPIO.output(self._beep, GPIO.HIGH if intensity > 0 else GPIO.LOW)

    def beep_off(self) -> None:
        GPIO.output(self._beep, GPIO.LOW)

    def led_on(self, color: str, intensity: Optional[int] = 255) -> None:
        intensity = self._check_pwm_range(intensity)
        if color == "green":
            GPIO.output(self._green_led, GPIO.HIGH if intensity > 0 else GPIO.LOW)
        elif color == "red":
            GPIO.output(self._red_led, GPIO.HIGH if intensity > 0 else GPIO.LOW)

    def led_off(self, color: str) -> None:
        if color == "green":
            GPIO.output(self._green_led, GPIO.LOW)
        elif color == "red":
            GPIO.output(self._red_led, GPIO.LOW)

    def __str__(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return str(self.id)
