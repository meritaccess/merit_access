from abc import ABC, abstractmethod
import time
from datetime import datetime

from Logger import log
from .DatabaseController import DatabaseController


class WsControllerABC(ABC):

    def __init__(self, db_controller: DatabaseController) -> None:
        self.loading: bool = False
        self._db_controller: DatabaseController = db_controller
        self.last_access = time.time()

    @abstractmethod
    def _thread_load_all_cards_from_ws(self) -> None:
        pass

    @abstractmethod
    def load_all_cards_from_ws(self) -> None:
        pass

    @abstractmethod
    def open_door_online(self, card: str, reader: str) -> bool:
        pass

    @abstractmethod
    def insert_to_access(self, card: str, reader: str, status: int = 700) -> None:
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        pass

    @abstractmethod
    def _format_time_str(self, mytime: datetime) -> str:
        pass

    def _update_last_access(self) -> None:
        self.last_access = time.time()

    def _update_db(self, cards) -> None:
        try:
            if cards:
                print(f"New cards: \n{cards}\n")
                self._db_controller.update_temp_cards(cards)
                print("Loading done. Setting tempKarty to active...")
                self._db_controller.activate_temp_cards()
            else:
                print("No new cards")
        except Exception as e:
            log(40, str(e))
