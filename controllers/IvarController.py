from zeep import Client
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Tuple

from .WsControllerABC import WsControllerABC
from constants import Status
from logger.Logger import log


class IvarController(WsControllerABC):
    """
    Handles communication with the IVAR web service.
    """

    def __init__(self, *args, address_r1: str, address_r2: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._address_r1 = address_r1
        self._address_r2 = address_r2

    def load_all_cards(self) -> Tuple[List, bool]:
        """
        Initiates the process of loading all card information from the web service in a separate thread.
        """
        if not self.loading:
            cards = []
            self.loading = True
            success = False
            try:
                client = self._get_client()
                cards_r1, success_r1 = self._get_cards(client, 1)
                cards_r2, success_r2 = self._get_cards(client, 2)
                cards.extend(cards_r1 + cards_r2)
                success = success_r1 and success_r2
            except Exception as e:
                log(10, f"Error loading cards, probably no connection: {e}")
            finally:
                self.loading = False
                return cards, success

    def load_all_tplans(self) -> Tuple[List, bool]:
        """
        NOT IMPLEMENTED FOR IVAR - returns []. Initiates the process of loading all time plans from the web service in a separate thread.
        """
        return [], False

    def _select_address(self, reader: int) -> str:
        """
        Selects the address of the reader based on the reader number.
        """
        if reader == 1:
            return self._address_r1
        return self._address_r2

    def _format_time_str(self, mytime: datetime) -> str:
        """
        Formats the given datetime object to a string in the format 2024-08-23T09:48:26.129
        """
        return mytime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    def _get_cards(self, client: Client, reader: int) -> Tuple[List, bool]:
        """
        Fetches the list of valid cards from the web service for the specified reader.
        """
        success = False
        cards = []
        try:
            if client:
                address = self._select_address(reader)
                if address:
                    result = client.service.GetTermValidCard(address, reader)
                    if result:
                        self._update_last_access()
                        xml = ET.fromstring(result)
                        cards = [
                            (code.text, reader, 0, 1, 0, "")
                            for code in xml.findall("Code")
                        ]
                        success = True
                else:
                    log(10, f"Reader {reader} has no IVAR address")
                    success = True
        except Exception as e:
            log(10, f"Error loading cards, probably no connection: {e}")
        finally:
            return cards, success

    def _get_client(self, transport: Transport = None) -> Client:
        """
        Creates and returns a web service client.
        """
        if transport:
            client = Client(self.ws_addr, transport=transport)
        else:
            client = Client(self.ws_addr)
        client.service._binding_options["address"] = self.ws_addr
        return client

    def _format_status(self, status: int) -> int:
        """
        Converts a status code to the format (int) expected by the web service.
        """
        if status == Status.ALLOW:
            return 1
        if status == Status.ALLOW_DOOR_NOT_CLOSED:
            return 1
        return 0

    def open_door_online(self, card: str, reader: str) -> Status:
        """
        Validates online if a specific card has access rights at the given time.
        """
        print("Testing rights for opening online...")
        try:
            result = -1000
            service = self._get_client().service
            mytime = self._format_time_str(datetime.now())
            button = 0
            address = self._select_address(reader)
            result = service.CheckCardM(address, card, reader, button, mytime).Result
            log(10, f"Povolen vstup: {result}")
            log(10, "Finished testing rights for opening online...")
            if result == 0:
                return Status.ALLOW
            elif result == -1:
                return Status.DENY_TERM_NOT_FOUND
            elif result == -2:
                return Status.DENY_CARD_NOT_FOUND
            return Status.DENY_INSERT_FAILED
        except Exception as e:
            log(10, f"Error checking online access, probably no connection: {e}")
            return Status.DENY_INSERT_FAILED

    def insert_to_access(
        self, card: str, reader: str, mytime: datetime, status: Status
    ) -> Status:
        """
        Inserts an access record for the given card and reader into the web service.
        """
        try:
            result = -1000
            service = self._get_client().service
            mytime = self._format_time_str(mytime)
            access = self._format_status(status)
            result = service.WriteRecord(
                self._select_address(reader), card, reader, 0, mytime, access
            )
            if result == 0:
                return status
            elif result in {-1, -2} and status in {Status.ALLOW, Status.DENY}:
                return Status(status.value + abs(result))
            return Status(status.value + 10)

        except Exception as e:
            log(10, f"Error inserting to access, probably no connection: {e}")
            return Status(status.value + 10)
        finally:
            log(10, f"Finished insert online with return code: {result}")

    def check_connection(self) -> bool:
        """
        Checks if the web service is reachable.
        """
        try:
            transport = Transport(timeout=3)
            service = self._get_client(transport).service
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
