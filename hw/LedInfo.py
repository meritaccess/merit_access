import time
from typing import Tuple, Dict
import pigpio

from controllers.ThreadManager import ThreadManager
from constants import (
    SYS_LED_BLUE,
    SYS_LED_GREEN,
    SYS_LED_RED,
    SYS_LED_BLINK,
    SYS_LED_BLINK_FAST,
)


class LedInfo:
    """
    Represents an LED's information and control logic, including color and style settings.
    """

    def __init__(
        self,
        pi: pigpio.pi,
        r: int = SYS_LED_RED,
        g: int = SYS_LED_GREEN,
        b: int = SYS_LED_BLUE,
    ) -> None:
        # Set pins
        self._r: int = r
        self._g: int = g
        self._b: int = b
        self._pi = pi

        # Color constants
        self.color_map: Dict[str, Tuple[int, int, int]] = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "magenta": (255, 0, 255),
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "cyan": (0, 255, 255),
            "yellow": (255, 100, 0),
        }

        # Default settings
        self._style: str = "off"
        self._rgb: Tuple[int, int, int] = self.color_map["black"]

        self._thread_manager: ThreadManager = ThreadManager()

        self._init_hw()
        self._init_threads()

    def _init_threads(self) -> None:
        """
        Initializes the threads.
        """
        success = True
        success &= self._thread_manager.start_thread(self._thread_run_style, "led_info")
        assert success, f"Failed to start some threads in {self}"

    def _init_hw(self) -> None:
        """
        Initializes the hardware.
        """
        self._pi.set_mode(self._r, pigpio.OUTPUT)
        self._pi.set_mode(self._g, pigpio.OUTPUT)
        self._pi.set_mode(self._b, pigpio.OUTPUT)

        self._pi.set_PWM_frequency(self._r, 1000)
        self._pi.set_PWM_frequency(self._g, 1000)
        self._pi.set_PWM_frequency(self._b, 1000)

        self._pi.set_PWM_dutycycle(self._r, 0)
        self._pi.set_PWM_dutycycle(self._g, 0)
        self._pi.set_PWM_dutycycle(self._b, 0)

    def set_status(self, color, style: str) -> None:
        """
        Sets the LED's color and style.
        """
        self._set_color(color)
        self._set_style(style)

    def _set_color(self, color) -> None:
        """
        Sets the LED's color.
        """
        if isinstance(color, str):
            if color in self.color_map.keys():
                rgb = self.color_map[color]
            else:
                rgb = self._hex_2_rgb(int(color, base=16))
        elif isinstance(color, int):
            rgb = self._hex_2_rgb(color)
        elif isinstance(color, tuple):
            if max(color) > 255 or min(color) < 0:
                raise ValueError("Invalid color value - must be between 0 and 255")
            rgb = color
        else:
            raise ValueError("Invalid color type")
        self._set_rgb(rgb)
        self._rgb = rgb

    def _set_rgb(self, rgb: Tuple[int, int, int]) -> None:
        """
        Sets the LED's color using RGB values.
        """
        self._pi.set_PWM_dutycycle(self._r, rgb[0] / 255 * 255)
        self._pi.set_PWM_dutycycle(self._g, rgb[1] / 255 * 255)
        self._pi.set_PWM_dutycycle(self._b, rgb[2] / 255 * 255)

    def _set_style(self, style: str) -> None:
        """
        Sets the LED's style.
        """
        if style == "off":
            self._style = "off"
        elif style == "on":
            self._style = "on"
        elif style == "blink":
            self._style = "blink"
        elif style == "blink_fast":
            self._style = "blink_fast"

    def exit(self) -> None:
        """
        Stops the LED control thread and cleans up GPIO.
        """
        self._pi.set_PWM_dutycycle(self._r, 0)
        self._pi.set_PWM_dutycycle(self._g, 0)
        self._pi.set_PWM_dutycycle(self._b, 0)
        self._thread_manager.stop_all()

    def _thread_run_style(self) -> None:
        """
        Continuously updates the LED based on the current style setting.
        """
        # while not self._stop_event.is_set():
        while not self._thread_manager.stop_event():
            if self._style == "off":
                self._set_rgb((0, 0, 0))
            elif self._style == "on":
                self._set_rgb(self._rgb)
            elif self._style == "blink":
                self._set_rgb((0, 0, 0))
                time.sleep(SYS_LED_BLINK)
                self._set_rgb(self._rgb)
                time.sleep(SYS_LED_BLINK)
            elif self._style == "blink_fast":
                self._set_rgb((0, 0, 0))
                time.sleep(SYS_LED_BLINK_FAST)
                self._set_rgb(self._rgb)
                time.sleep(SYS_LED_BLINK_FAST)

    def _hex_2_rgb(self, color) -> Tuple[int, int, int]:
        """
        Converts a hexadecimal color value to an RGB tuple.
        """
        rgb = []
        for _ in range(3):
            rgb.insert(0, (color & 0xFF))
            color >>= 8
        return tuple(rgb)

    def __str__(self) -> str:
        return "SystemLED"

    def __repr__(self) -> str:
        return "SystemLED"
