import time
from datetime import datetime as dt

from HardwareComponents.Reader.ReaderWiegand import ReaderWiegand
from Modes.ConfigModeCloud import ConfigModeCloud


class ConfigModeOffline(ConfigModeCloud):
    """
    Implements the operational logic for the system when in configuration mode. In this mode,
    administrators can add or remove access permissions for cards directly through reader interactions or using the web interface.
    """

    def __init__(self, *args, r1: ReaderWiegand, r2: ReaderWiegand, **kwargs):
        super().__init__(*args, **kwargs)
        self.r1: ReaderWiegand = r1
        self.r2: ReaderWiegand = r2
        self.mode_name: str = "ConfigModeOffline"
        self.sys_led.set_status("blue", "blink")
        self.easy_add = bool(int(self.db_controller.get_val("ConfigDU", "easy_add")))
        self.easy_remove = bool(
            int(self.db_controller.get_val("ConfigDU", "easy_remove"))
        )

    def _manage_cards(self, reader: ReaderWiegand) -> None:
        """
        Processes card reads from the specified reader to add or remove access permissions
        based on the card's current status in the local database.
        """
        # check if card has been read
        card_id = reader.read()
        if card_id:
            # if card has access - remove it
            if self.db_controller.card_access_local(card_id, reader.id, dt.now()):
                if self.easy_remove:
                    success = self.db_controller.remove_access(card_id, reader.id)
                    if success:
                        self.sys_led.set_status("red", "on")
                        time.sleep(2)
                        self.sys_led.set_status("blue", "blink")

            # if card not in the database - add it and grant access
            else:
                if self.easy_add:
                    args = [
                        card_id,
                        reader.id,
                        0,
                        1,
                        0,
                        "Added in ConfigMode",
                    ]
                    success = self.db_controller.grant_access(args)
                    if success:
                        self.sys_led.set_status("green", "on")
                        time.sleep(2)
                        self.sys_led.set_status("blue", "blink")

    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            self._init_threads()
            self._wifi_setup()
            time.sleep(1)

            while not self._exit:
                self._check_timeout()
                if self._config_btn_is_pressed == 1:
                    return 0
                self.curr_time = time.perf_counter_ns()
                self._manage_cards(self.r1)
                self._manage_cards(self.r2)
                time.sleep(1)
            return 0
        except Exception as e:
            self.logger.log(1, str(e))
        finally:
            self.wifi_controller.ap_off()
            self._stop()
