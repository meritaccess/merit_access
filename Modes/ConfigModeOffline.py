import time
from datetime import datetime as dt

from HardwareComponents import ReaderWiegand
from .ConfigModeCloud import ConfigModeCloud
from Logger import log
from constants import Config


class ConfigModeOffline(ConfigModeCloud):
    """
    Extends ConfigModeCloud to implement configuration logic specific to offline mode.
    """

    def __init__(self, *args, r1: ReaderWiegand, r2: ReaderWiegand, **kwargs):
        super().__init__(*args, **kwargs)
        self._r1 = r1
        self._r2 = r2
        self._easy_add: bool = bool(
            int(self._db_controller.get_val("ConfigDU", "easy_add"))
        )
        self._easy_remove: bool = bool(
            int(self._db_controller.get_val("ConfigDU", "easy_remove"))
        )

    def _initial_setup(self) -> None:
        self._mode_name: str = "ConfigModeOffline"
        self._sys_led.set_status("blue", "blink")
        log(20, self._mode_name)

    def _manage_cards(self, reader: ReaderWiegand) -> None:
        """
        Processes card reads from the specified reader to add or remove access permissions
        based on the card's current status in the local database.
        """
        # check if card has been read
        card_id = reader.read()
        if card_id:
            # if card has access - remove it
            if self._db_controller.check_card_access(card_id, reader.id):
                if self._easy_remove:
                    success = self._db_controller.remove_access(card_id, reader.id)
                    if success:
                        self._sys_led.set_status("red", "on")
                        time.sleep(2)
                        self._sys_led.set_status("blue", "blink")

            # if card not in the database - add it and grant access
            else:
                if self._easy_add:
                    args = [
                        card_id,
                        reader.id,
                        0,
                        1,
                        0,
                        "Added in ConfigMode",
                    ]
                    success = self._db_controller.grant_access(args)
                    if success:
                        self._sys_led.set_status("green", "on")
                        time.sleep(2)
                        self._sys_led.set_status("blue", "blink")

    def run(self) -> Config:
        """The main loop of the mode."""
        try:
            self._initial_setup()
            self._init_threads()
            self._wifi_setup()
            time.sleep(1)

            while not self._exit:
                self._check_timeout()
                if self._config_btn_is_pressed == 1:
                    return Config.NONE
                self._manage_cards(self._r1)
                self._manage_cards(self._r2)
                time.sleep(1)
            return Config.NONE
        except Exception as e:
            log(40, str(e))
        finally:
            self._wifi_controller.ap_off()
            self._stop()
