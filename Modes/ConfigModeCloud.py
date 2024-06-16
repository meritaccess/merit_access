import time
from datetime import datetime as dt
from Modes.ConfigModeABC import ConfigModeABC


class ConfigModeCloud(ConfigModeABC):
    """
    Implements the operational logic for the system when in configuration mode. In this mode,
    administrators can add or remove access permissions for cards directly through reader interactions or using the web interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode_name: str = "ConfigModeCloud"
        self.sys_led.set_status("blue", "blink")

    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            self._init_threads()
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
            self.logger.log(1, str(e))
        finally:
            self.wifi_controller.turn_off()
            self._stop()
