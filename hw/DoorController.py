import time
import pigpio

from controllers.ThreadManager import ThreadManager


class DoorController:
    """
    Manages door operations.
    """

    def __init__(
        self,
        du_id: str,
        relay: int,
        has_monitor: bool,
        monitor_default: bool,
        max_open_time: int,
        pi: pigpio.pi,
    ) -> None:
        self.opening: bool = False
        self.opening_start: float = None
        self.extra_time_count: int = 1
        self.extra_time: bool = False
        self.permanent_open: bool = False
        self.has_monitor = has_monitor
        self.monitor_default = monitor_default
        self.monitor: bool = monitor_default
        self.max_open_time = max_open_time
        self._relay = relay
        self.id = du_id
        self._pi = pi
        self._init_hw()
        self._thread_manager: ThreadManager = ThreadManager()

    def _init_hw(self) -> None:
        """
        Initializes the hardware.
        """
        self._pi.set_mode(self._relay, pigpio.OUTPUT)
        self._pi.write(self._relay, pigpio.LOW)

    def open_door(self, duration: int) -> None:
        """
        Open door for a given duration.
        """

        if not self.permanent_open:
            self.opening_start = time.time()
            self.extra_time_count = 1
            self._thread_manager.start_thread(
                self._thread_open_door, f"open_door{self.id}", args=(duration,)
            )

    def permanent_open_door(self) -> None:
        """
        Door remains silently open until close_door() is called.
        """
        self.permanent_open = True
        self._pi.write(self._relay, pigpio.HIGH)

    def close_door(self) -> None:
        """
        Close the door.
        """
        self._pi.write(self._relay, pigpio.LOW)
        self.permanent_open = False
        self.opening = False

    def _thread_open_door(self, duration: int) -> None:
        """
        Thread to open door for a given time.
        """
        self.opening = True
        self._pi.write(self._relay, pigpio.HIGH)
        time.sleep(duration)
        while self.extra_time:
            self.extra_time = False
            time.sleep(duration)
        self.opening = False
        if not self.permanent_open:
            self._pi.write(self._relay, pigpio.LOW)

    def __str__(self) -> str:
        return f"DoorController{self.id}"

    def __repr__(self) -> str:
        return f"DoorController{self.id}"
