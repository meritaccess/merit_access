import pigpio


class Button:
    def __init__(self, pin: int, btn_id, pi) -> None:
        self._id: str = btn_id
        self._pin: int = pin
        self._pi = pi
        self._init_hw()

    def _init_hw(self) -> None:
        self._pi.set_mode(self._pin, pigpio.INPUT)
        self._pi.set_pull_up_down(self._pin, pigpio.PUD_UP)

    def pressed(self) -> bool:
        pressed = self._pi.read(self._pin) == pigpio.LOW
        return pressed

    def __str__(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return self._id
