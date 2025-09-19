from abc import ABC, abstractmethod
import time
from datetime import datetime
from typing import List

from constants import Status


class WsControllerABC(ABC):

    def __init__(self, ws_address: str) -> None:
        self.loading: bool = False
        self.last_access: float = time.time()
        self.ws_addr = ws_address

    @abstractmethod
    def load_all_cards(self) -> List:
        """
        Abstract method to load all cards from the web service.
        """
        pass

    @abstractmethod
    def open_door_online(self, card: str, reader: str) -> Status:
        """
        Abstract method to open the door online.
        """
        pass

    @abstractmethod
    def insert_to_access(
        self, card: str, reader: str, mytime: datetime, status: int = 700
    ) -> Status:
        """
        Abstract method to insert access details to the web service.
        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Abstract method to check the connection to the web service.
        """
        pass

    @abstractmethod
    def _format_time_str(self, mytime: datetime) -> str:
        """
        Abstract method to format the time string.
        """
        pass

    @abstractmethod
    def load_all_tplans(self) -> List:
        """
        Abstract method to load all time plans from the web service.
        """
        pass

    def _update_last_access(self) -> None:
        """
        Updates the last access time.
        """
        self.last_access = time.time()
