from abc import ABC, abstractmethod
import time
from datetime import datetime
from typing import List

from Logger import log
from .DatabaseController import DatabaseController


class WsControllerABC(ABC):

    def __init__(self, ws_address: str) -> None:
        self.loading: bool = False
        self.last_access = time.time()
        self.ws_addr = ws_address

    @abstractmethod
    def _thread_load_all_cards_from_ws(self, cards) -> None:
        pass

    @abstractmethod
    def load_all_cards(self) -> List:
        pass

    @abstractmethod
    def open_door_online(self, card: str, reader: str) -> int:
        pass

    @abstractmethod
    def insert_to_access(
        self, card: str, reader: str, mytime: datetime, status: int = 700
    ) -> bool:
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        pass

    @abstractmethod
    def _format_time_str(self, mytime: datetime) -> str:
        pass

    @abstractmethod
    def load_all_tplans(self) -> List:
        pass

    @abstractmethod
    def _thread_load_all_tplans(self, tplans) -> None:
        pass

    def _update_last_access(self) -> None:
        self.last_access = time.time()
