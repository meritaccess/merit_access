import time

from .ConfigModeABC import ConfigModeABC
from GeneratorID import GeneratorID
from Logger import log
from constants import Config


class ConfigModeConnect(ConfigModeABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uid_generator: GeneratorID = GeneratorID()

    def _initial_setup(self) -> None:
        self._mode_name: str = "ConfigModeConnect"
        self._sys_led.set_status("white", "blink_fast")
        log(20, self._mode_name)

    def _wifi_setup(self) -> None:
        pass

    def run(self) -> Config:
        """The main loop of the mode."""
        try:
            self._initial_setup()
            self._init_threads()
            time.sleep(1)

            while not self._exit:
                self._check_timeout()
                uid = self._uid_generator.generate_uid()
                print(uid)
                if self._config_btn_is_pressed == 1:
                    return Config.CONFIG
                time.sleep(1)
            return Config.NONE
        except Exception as e:
            log(40, str(e))
        finally:
            self._stop()
