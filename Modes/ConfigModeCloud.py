import time

from .ConfigModeABC import ConfigModeABC
from Logger import log
from constants import Config


class ConfigModeCloud(ConfigModeABC):
    """
    Extends ConfigModeABC to implement configuration logic specific to cloud mode.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _initial_setup(self) -> None:
        self._mode_name: str = "ConfigModeCloud"
        self._sys_led.set_status("blue", "blink")
        log(20, self._mode_name)

    def _apache_setup(self) -> None:
        self._apache_controller.start()

    def run(self) -> Config:
        """The main loop of the mode."""
        try:
            self._initial_setup()
            self._init_threads()
            self._wifi_setup()
            self._apache_setup()
            self._ssh_setup()
            time.sleep(1)

            while not self._exit:
                self._check_timeout()
                if self._config_btn_is_pressed == 1:
                    return Config.NONE
                elif self._config_btn_is_pressed == 2:
                    return Config.CONNECT
                time.sleep(1)
            return Config.NONE
        except Exception as e:
            log(40, str(e))
        finally:
            self._wifi_controller.ap_off()
            self._stop()
