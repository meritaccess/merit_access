import time
from datetime import datetime as dt

from Modes.ConfigModeABC import ConfigModeABC
from GeneratorID.GeneratorID import GeneratorID


class ConfigModeConnect(ConfigModeABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mode_name: str = "ConfigModeConnect"
        self._sys_led.set_status("white", "blink_fast")
        self._uid_generator: GeneratorID = GeneratorID()

    def _wifi_setup(self) -> None:
        pass

    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            self._initial_setup()
            self._init_threads()
            time.sleep(1)

            while not self._exit:
                self._check_timeout()
                uid = self._uid_generator.generate_uid()
                print(uid)
                if self._config_btn_is_pressed == 1:
                    return 1
                time.sleep(1)
            return 0
        except Exception as e:
            self._logger.log(1, str(e))
        finally:
            self._stop()
