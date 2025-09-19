import time

from .ConfigModeCloud import ConfigModeCloud
from logger.Logger import log
from constants import Config, Status, EASY_ADD_REMOVE_TIME, MODE_SLEEP_TIME


class ConfigModeOffline(ConfigModeCloud):
    """
    Extends ConfigModeCloud to implement configuration logic specific to offline mode.
    """

    def __init__(self, *args, du_controller, **kwargs):
        super().__init__(*args, **kwargs)
        self._du_controller = du_controller
        self._easy_add: bool = bool(
            int(self._db_controller.get_prop("ConfigDU", "easy_add"))
        )
        self._easy_remove: bool = bool(
            int(self._db_controller.get_prop("ConfigDU", "easy_remove"))
        )

    def _initial_setup(self) -> None:
        """
        Performs initial setup tasks
        """
        self._mode_name: str = "ConfigModeOffline"
        self._sys_led.set_status("blue", "blink")
        log(20, self._mode_name)

    def _manage_cards(self) -> None:
        """
        Processes card reads from the specified reader to add or remove access permissions
        based on the card's current status in the local database.
        """
        # check if card has been read
        access_details = self._du_controller.read_readers()
        if not access_details:
            return
        reader_id = access_details[0]
        card_id = access_details[1]
        log(10, f"Reader: {reader_id} CardID: {card_id}")
        status = self._db_controller.check_card_access(card_id, reader_id)
        # if card has access - remove it
        if status == Status.ALLOW:
            if not self._easy_remove:
                return
            success = self._db_controller.remove_access(card_id, reader_id)
            if success:
                self._sys_led.set_status("red", "on")
                time.sleep(EASY_ADD_REMOVE_TIME)
                self._sys_led.set_status("blue", "blink")
        # if card not in the database - add it and grant access
        else:
            if not self._easy_add:
                return
            args = [
                card_id,
                reader_id,
                0,
                1,
                0,
                "Added in ConfigMode",
            ]
            success = self._db_controller.grant_access(args)
            if success:
                self._sys_led.set_status("green", "on")
                time.sleep(EASY_ADD_REMOVE_TIME)
                self._sys_led.set_status("blue", "blink")

    def run(self) -> Config:
        """
        The main loop of the mode.
        """
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
                self._manage_cards()
                time.sleep(MODE_SLEEP_TIME)
            return Config.NONE
        except Exception as e:
            log(40, str(e))
        finally:
            self._wifi_controller.ap_off()
            self.exit()
