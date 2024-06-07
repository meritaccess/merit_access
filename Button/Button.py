import RPi.GPIO as GPIO

class Button:
    def __init__(self, pin: int) -> None:
        self._pin: int = pin
        self._init_hw()

    def _init_hw(self) -> None:
        GPIO.setup(self._pin, GPIO.IN)

    def pressed(self) -> bool:
        pressed = GPIO.input(self._pin) == GPIO.LOW
        return pressed
