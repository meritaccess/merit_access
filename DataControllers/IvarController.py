import threading
from zeep import Client
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

from .WsControllerABC import WsControllerABC
from Logger import log


class IvarController(WsControllerABC):
    """Handles communication with the IVAR web service."""

    def __init__(self, *args, address_r1: str, address_r2: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._address_r1 = address_r1
        self._address_r2 = address_r2

    def load_all_cards(self) -> List:
        """
        Initiates the process of loading all card information from the web service in a separate thread.
        """
        if not self.loading:
            cards = []
            self.loading = True
            t = threading.Thread(
                target=self._thread_load_all_cards_from_ws,
                daemon=True,
                name="load_all_cards_from_ws",
                args=(cards,),
            )
            t.start()
            t.join()
            return cards

    def _thread_load_all_cards_from_ws(self, cards) -> None:
        """
        A threaded method to load all access card information from the web service
        and update the local database accordingly.
        """
        print("Starting thread for import card...")
        try:
            service = self._get_service()
            cards_r1 = self._get_cards(service, 1)
            cards_r2 = self._get_cards(service, 2)
            cards.extend(cards_r1 + cards_r2)
        except Exception as e:
            log(40, str(e))
        finally:
            self.loading = False
            print("Finished thread for import card...")

    def load_all_tplans(self) -> List:
        return []

    def _thread_load_all_tplans(self, tplans) -> None:
        pass

    def _select_address(self, reader: int) -> str:
        if reader == 1:
            return self._address_r1
        return self._address_r2

    def _format_time_str(self, mytime: datetime) -> str:
        # 2024-08-23T09:48:26.129
        return mytime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    def _get_cards(self, service: Client, reader: int) -> list:
        """Fetches the list of valid cards from the web service for the specified reader."""
        cards = []
        if service:
            address = self._select_address(reader)
            result = service.GetTermValidCard(address, reader)
            if result:
                self._update_last_access()
                xml = ET.fromstring(result)
                cards = [
                    (code.text, reader, 0, 1, 0, "") for code in xml.findall("Code")
                ]
        return cards

    def _get_service(self, transport: Transport = None) -> Client:
        """Creates and returns a web service client."""
        if transport:
            client = Client(self.ws_addr, transport=transport)
        else:
            client = Client(self.ws_addr)
        service = client.service
        service._binding_options["address"] = self.ws_addr
        return service

    def _format_status(self, status: int) -> int:
        """Converts a status code to the format expected by the web service."""
        if status == 701:
            return 1
        return 0

    def open_door_online(self, card: str, reader: str) -> bool:
        """
        Validates online if a specific card has access rights at the given time.
        """
        print("Testing rights for opening online...")
        try:
            service = self._get_service()
            mytime = self._format_time_str(datetime.now())
            button = 0
            address = self._select_address(reader)
            result = service.CheckCardM(address, card, reader, button, mytime).Result
            print("Povolen vstup: ", result)
        except Exception as e:
            log(40, str(e))
            result = -reader
        finally:
            print("Finished rights for opening online...")
            if result == 0:
                return True
            return False

    def insert_to_access(
        self, card: str, reader: str, mytime: datetime, status: int = 700
    ) -> None:
        """Inserts an access record for the given card and reader into the web service."""
        try:
            service = self._get_service()
            mytime = self._format_time_str(mytime)
            access = self._format_status(status)
            result = service.WriteRecord(
                self._select_address(reader), card, reader, 0, mytime, access
            )
        except Exception as e:
            log(40, str(e))
        finally:
            print(f"Finished insert online with return code: {result}")

    def check_connection(self) -> bool:
        """Checks if the web service is reachable."""
        try:
            transport = Transport(timeout=3)
            service = self._get_service(transport)
            if service:
                self._update_last_access()
                return True
            return False
        except Exception:
            return False

    def __str__(self) -> str:
        return "IVAR Controller"

    def __repr__(self) -> str:
        return "IVAR Controller"
