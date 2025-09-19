import pigpio


class Button:
    """
    Represents a button connected to a GPIO pin.
    """

    def __init__(self, pin: int, btn_id: str, pi: pigpio.pi) -> None:
        self._id = btn_id
        self._pin = pin
        self._pi = pi
        self._init_hw()

    def _init_hw(self) -> None:
        """
        Initializes the hardware.
        """
        self._pi.set_mode(self._pin, pigpio.INPUT)
        self._pi.set_pull_up_down(self._pin, pigpio.PUD_UP)

    def pressed(self) -> bool:
        """
        Checks if the button is pressed.
        """
        pressed = self._pi.read(self._pin) == pigpio.LOW
        return pressed

    def __str__(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return self._id
