import time
from abc import ABC, abstractmethod
from typing import List
from constants import Config, CONFIG_BTN_TIME, CONFIG_BTN_LONG_PRESS_TIME

from hw.Button import Button
from hw.LedInfo import LedInfo
from controllers.DatabaseController import DatabaseController
from controllers.SSHController import SSHController
from controllers.ApacheController import ApacheController
from controllers.ThreadManager import ThreadManager


class BaseModeABC(ABC):
    """
    An abstract base class for defining operational modes within an access control system. It provides common
    attributes and methods that all modes should implement.
    """

    def __init__(
        self,
        sys_led: LedInfo,
        config_btn: Button,
        db_controller: DatabaseController,
        ssh_controller: SSHController,
        apache_controller: ApacheController,
    ) -> None:

        self._mode_name: str = "BaseMode"
        self._exit: bool = False

        # 0 - Not pressed, 1 - short press, 2 - long press
        self._config_btn_is_pressed: int = 0

        # objects
        self._thread_manager: ThreadManager = ThreadManager()
        self._sys_led = sys_led
        self._config_btn = config_btn
        self._db_controller = db_controller
        self._ssh_controller = ssh_controller
        self._apache_controller = apache_controller

    def _init_threads(self) -> None:
        """
        Initializes all threads for the mode.
        """
        success = True
        success &= self._thread_manager.start_thread(
            self._thread_config_btn, "config_btn"
        )
        assert success is True, f"Failed to start some threads in {self}"

    def _thread_config_btn(self) -> None:
        """
        Thread function that monitors the configuration button state and sets the button press state.
        """

        while not self._thread_manager.stop_event():
            if self._config_btn.pressed():
                press_time = time.time()
                time.sleep(CONFIG_BTN_TIME)
                while self._config_btn.pressed():
                    continue
                if time.time() - press_time > CONFIG_BTN_LONG_PRESS_TIME:
                    self._config_btn_is_pressed = 2
                else:
                    self._config_btn_is_pressed = 1

    def exit(self) -> None:
        """
        Stops all running threads by setting the stop event and joining all threads.
        """
        self._exit = True
        self._thread_manager.stop_all()

    @abstractmethod
    def _initial_setup(self) -> None:
        """Abstract method to setup the mode."""
        pass

    @abstractmethod
    def run(self) -> Config:
        """Abstract method to run the mode."""
        pass

    def _apache_setup(self) -> None:
        """Abstract method to set Apache server"""
        pass

    def _ssh_setup(self) -> None:
        """Abstract method to set ssh"""
        pass

    def __str__(self) -> str:
        return self._mode_name

    def __repr__(self) -> str:
        return self._mode_name
