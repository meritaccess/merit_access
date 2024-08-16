import time

from .BaseModeABC import BaseModeABC
from Network import WifiController
from Logger import log


class ConfigModeABC(BaseModeABC):
    """
    An abstract base class for ConfigModes.
    """

    def __init__(self, *args, wifi_controller: WifiController, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_runtime: int = 30 * 60  # in seconds
        self._start_time: float = time.time()
        self._wifi_controller: WifiController = wifi_controller

    def _wifi_setup(self) -> None:
        self._wifi_controller.ap_on()

    def _check_timeout(self) -> None:
        """
        Checks if the configuration mode has exceeded the maximum runtime and exits if it has.
        """
        if self._start_time + self._max_runtime < time.time():
            log(30, f"Exiting {self._mode_name} due to timeout")
            self.exit()
