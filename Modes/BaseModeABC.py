import time
from abc import ABC, abstractmethod
import threading
from typing import List
from constants import Config

from HardwareComponents import LedInfo, Button
from DataControllers import DatabaseController


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
    ) -> None:

        self._mode_name: str = "BaseMode"
        self._exit: bool = False

        # 0 - Not pressed, 1 - short press, 2 - long press
        self._config_btn_is_pressed: int = 0

        # threading
        self._stop_event: threading.Event = threading.Event()
        self._threads: List = []

        # objects
        self._sys_led = sys_led
        self._config_btn = config_btn
        self._db_controller = db_controller

    def exit(self) -> None:
        """
        Sets the exit flag to True, indicating that the mode should exit.
        """
        self._exit = True

    def _init_threads(self) -> None:
        """
        Initializes all threads for the mode.
        """
        if not self._is_thread_running("config_btn"):
            self._config_btn_check()

    def _config_btn_check(self):
        """
        Starts a new thread to monitor the configuration button state.
        """
        t = threading.Thread(
            target=self._thread_config_btn, daemon=True, name="config_btn"
        )
        self._threads.append(t)
        t.start()

    def _thread_config_btn(self) -> None:
        """
        Thread function that monitors the configuration button state and sets the button press state.
        """

        while not self._stop_event.is_set():
            if self._config_btn.pressed():
                press_time = time.time()
                time.sleep(0.1)
                while self._config_btn.pressed():
                    continue
                if time.time() - press_time > 5:
                    self._config_btn_is_pressed = 2
                else:
                    self._config_btn_is_pressed = 1

    def _stop(self) -> None:
        """
        Stops all running threads by setting the stop event and joining all threads.
        """
        self._stop_event.set()
        for t in self._threads:
            t.join()

    def _is_thread_running(self, thread_name) -> bool:
        for thread in threading.enumerate():
            if thread.name == thread_name:
                return True
        return False

    @abstractmethod
    def _initial_setup(self) -> None:
        """Abstract method to setup the mode."""
        pass

    @abstractmethod
    def run(self) -> Config:
        """Abstract method to run the mode."""
        pass

    def __str__(self) -> str:
        return self._mode_name

    def __repr__(self) -> str:
        return self._mode_name
