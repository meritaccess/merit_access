import time
from datetime import datetime as dt

from Modes.BaseModeABC import BaseModeABC


class ConfigModeABC(BaseModeABC):
    """
    Implements the operational logic for the system when in configuration mode. In this mode,
    administrators can add or remove access permissions for cards directly through reader interactions or using the web interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_runtime = 30 * 60  # 30 minutes
        self._start_time = time.time()

    def _wifi_setup(self) -> None:
        self.wifi_controller.ap_on()

    def _check_timeout(self) -> None:
        if self._start_time + self._max_runtime < time.time():
            print("Exiting ConfigMode due to timeout")
            self.exit()
