import time

from .ConfigModeABC import ConfigModeABC
from hw.DoorUnitController import DoorUnitController
from logger.Logger import log
from constants import Config


class ConfigModeOSDP(ConfigModeABC):

    def __init__(self, *args, du_controller: DoorUnitController, **kwargs):
        super().__init__(*args, **kwargs)
        self._du_controller = du_controller

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks.
        """
        self._mode_name: str = "ConfigModeOSDP"
        self._sys_led.set_status("white", "blink_fast")
        log(20, self._mode_name)

    def run(self) -> Config:
        """
        The main loop of the mode.
        """
        try:
            self._initial_setup()
            self._init_threads()
            self._db_controller.set_prop("ConfigDU", "enable_osdp", 1)
            time.sleep(1)
            self._du_controller.scan()
            return Config.NONE
        except Exception as e:
            log(40, str(e))
        finally:
            self.exit()
