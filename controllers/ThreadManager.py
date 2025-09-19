import threading
from typing import Dict, Tuple
from collections.abc import Callable

from logger.Logger import log


class ThreadManager:
    """
    A class for managing threads.
    """

    def __init__(self, max_threads: int = 20) -> None:
        self._threads: Dict = {}
        self.max_threads = max_threads
        self._stop_event: threading.Event = threading.Event()
        self.lock = threading.Lock()

    def start_thread(
        self,
        target_fn: Callable,
        name: str = None,
        daemon: bool = True,
        args: Tuple = tuple(),
    ) -> bool:
        """
        Starts a new thread with the given name and target function.
        Threads with name are tracked - use for threads with loops like check threads.
        return: True if thread started successfully (or already existing), False otherwise.
        """
        try:
            with self.lock:
                if len(self._threads) >= self.max_threads:
                    log(
                        30,
                        f"Max threads reached: {self.max_threads}. Skipping thread: {name}",
                    )
                    return False
                if self.is_alive(name):
                    return True

                if name:
                    thread = threading.Thread(
                        target=target_fn, name=name, args=args, daemon=daemon
                    )
                    self._threads[name] = thread
                else:
                    thread = threading.Thread(
                        target=target_fn, args=args, daemon=daemon
                    )
                thread.start()
                if self.is_alive(name):
                    return True
                return False

        except Exception as e:
            log(40, f"Error starting thread: {name}: {e}")
            return False

    def stop_all(self) -> None:
        """
        Stops all threads.
        """
        try:
            self._stop_event.set()
            for thread in self._threads.values():
                thread.join()
            self._threads = {}
        except Exception as e:
            log(40, f"Error stopping threads: {e}")

    def stop_event(self) -> bool:
        """
        Checks if the stop event is set.
        """
        return self._stop_event.is_set()

    def clear_stop_event(self) -> None:
        """
        Clears the stop event.
        """
        self._stop_event.clear()

    def is_alive(self, name: str) -> bool:
        """
        Checks if a thread is alive.
        """
        if name in self._threads:
            return self._threads[name].is_alive()
        return False

    def purge_dead(self) -> None:
        """
        Purges dead threads from the thread list.
        """
        to_remove = []
        with self.lock:
            for name, thread in self._threads.items():
                if not thread.is_alive():
                    to_remove.append(name)
            for thread in to_remove:
                del self._threads[name]
