import time
from datetime import datetime as dt
from Reader.ReaderWiegand import ReaderWiegand
from Modes.BaseMode import BaseMode


class ConfigMode(BaseMode):
    """
    Implements the operational logic for the system when in configuration mode. In this mode,
    administrators can add or remove access permissions for cards directly through reader interactions or using the web interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode_name: str = "ConfigMode"
        self.sys_led.set_status("blue", "on")
        self.easy_add = bool(int(self.db_controller.get_val("ConfigDU", "easy_add")))
        self.easy_remove = bool(int(self.db_controller.get_val("ConfigDU", "easy_remove")))
        

    def _wifi_setup(self) -> None:
        self.wifi_controller.turn_on()

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
                        self.sys_led.set_status("blue", "on")
            
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
                        self.sys_led.set_status("blue", "on")

    def run(self) -> int:
        """The main loop of the mode."""
        try:
            print("Mode: ", self)
            time.sleep(2)
            while True:
                if self.config_btn.pressed():
                    return self.default_mode
                self.curr_time = time.perf_counter_ns()
                self._manage_cards(self.r1)
                self._manage_cards(self.r2)
                time.sleep(1)
        except Exception as e:
            self.logger.log(1, str(e))
        finally:
            self.wifi_controller.turn_off()
            self.sys_led.set_status("black", "off")
