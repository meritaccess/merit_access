import time
from datetime import datetime as dt

from Modes.ConfigModeABC import ConfigModeABC
from Logger import log


class ConfigModeCloud(ConfigModeABC):
    """
    Implements the operational logic for the system when in configuration mode. In this mode,
    administrators can add or remove access permissions for cards directly through reader interactions or using the web interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mode_name: str = "ConfigModeCloud"
        self._sys_led.set_status("blue", "blink")

    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            self._initial_setup()
            self._init_threads()
            self._wifi_setup()
            time.sleep(1)

            while not self._exit:
                self._check_timeout()
                if self._config_btn_is_pressed == 1:
                    return 0
                elif self._config_btn_is_pressed == 2:
                    return 2
                self.curr_time = time.perf_counter_ns()
                time.sleep(1)
            return 0
        except Exception as e:
            log(40, str(e))
        finally:
            self._wifi_controller.ap_off()
            self._stop()
