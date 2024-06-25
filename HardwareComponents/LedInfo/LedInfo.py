import threading
import time
from typing import Tuple, Dict
import pigpio
from constants import SYS_LED_BLUE, SYS_LED_GREEN, SYS_LED_RED


class LedInfo:
    """
    Represents an LED's information and control logic, including color and style settings.

    Attributes:
        _r (int): GPIO pin for the red component.
        _g (int): GPIO pin for the green component.
        _b (int): GPIO pin for the blue component.
        _style (str): Current style of the LED (off, on, blink, blink_fast).
        _rgb (Tuple[int, int, int]): Current color of the LED in RGB format.
    """

    def __init__(
        self,
        pi,
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
        self._stop_event = threading.Event()
        self._style_thread = None

        self._init_hw()
        self._run_style()

    def _init_hw(self) -> None:
        """Initializes the GPIO pins for LED control."""
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

        Parameters:
            color: The color to set (can be a hex string, hex int, RGB tuple, or color constant).
            style (str): The style to apply (off, on, blink, blink_fast).
        """
        self._set_color(color)
        self._set_style(style)

    def _set_color(self, color) -> None:
        """
        Sets the LED's color.

        Parameters:
            color: The color to set. Supports hex string, hex int, RGB tuple, or color constant.
            Color constants: red, green, blue, yellow, magenta, white, cyan.
        """
        if isinstance(color, str):
            if color in self.color_map.keys():
                rgb = self.color_map[color]
            else:
                rgb = self._hex_2_rgb(int(color, base=16))
        elif isinstance(color, int):
            rgb = self._hex_2_rgb(color)
        elif isinstance(color, tuple):
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

    def _run_style(self) -> None:
        """
        Starts the LED style control logic in a separate thread.
        """
        if self._style_thread is None:
            self._style_thread = threading.Thread(
                target=self._thread_run_style, daemon=True, name="led_info"
            )
            self._style_thread.start()

    def stop(self) -> None:
        """
        Stops the LED control thread and cleans up GPIO.
        """
        self._pi.set_PWM_dutycycle(self._r, 0)
        self._pi.set_PWM_dutycycle(self._g, 0)
        self._pi.set_PWM_dutycycle(self._b, 0)
        self._stop_event.set()
        if self._style_thread:
            self._style_thread.join()

    def _thread_run_style(self) -> None:
        """
        Continuously updates the LED based on the current style setting.
        """
        while not self._stop_event.is_set():
            if self._style == "off":
                self._set_rgb((0, 0, 0))
            elif self._style == "on":
                self._set_rgb(self._rgb)
            elif self._style == "blink":
                self._set_rgb((0, 0, 0))
                time.sleep(1)
                self._set_rgb(self._rgb)
                time.sleep(1)
            elif self._style == "blink_fast":
                self._set_rgb((0, 0, 0))
                time.sleep(0.2)
                self._set_rgb(self._rgb)
                time.sleep(0.2)

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
