import threading
from zeep import Client
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from datetime import datetime

from .WsControllerABC import WsControllerABC
from constants import MAC
from Logger import log


class WebServicesController(WsControllerABC):
    """
    Manages interactions with external web services for operations related to access control.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ws_addr: str = self._db_controller.get_val("ConfigDU", "ws")

    def _thread_load_all_cards_from_ws(self) -> None:
        """
        A threaded method to load all access card information from the web service
        and update the local database accordingly.
        """
        print("Starting thread for import card...")
        try:
            client = Client(self.ws_addr)
            self._update_last_access()
            cards = self._get_cards(client)
            self._update_db(cards)
        except Exception as e:
            log(40, str(e))
        finally:
            self.loading = False
            print("Finished thread for import card...")

    def _get_cards(self, client: Client) -> list:
        """Fetches the list of valid cards from the web service."""
        result = client.service.GetAllCardsForTerminal(MAC)
        cards = []
        if result:
            xml = ET.fromstring(result)
            for child in xml.findall("card"):
                arg = (
                    child.get("Karta").strip(),
                    child.get("Ctecka").strip(),
                    child.get("CasPlan").strip(),
                    child.get("Povoleni").strip(),
                    child.get("Smazano").strip(),
                    child.get("Pozn").strip(),
                )
                cards.append(arg)
        return cards

    def _format_time_str(self, mytime: datetime) -> str:
        # 2024-01-22 20:25:10.133
        return mytime.strftime("%Y-%m-%d %H:%M:%S") + ".000"

    def _select_terminal(self, reader: int) -> str:
        if reader == 1:
            return "MDA" + MAC[3:]
        return "MDB" + MAC[3:]

    def load_all_cards_from_ws(self) -> None:
        """
        Initiates the process of loading all card information from the web service in a separate thread.
        """
        if not self.loading:
            self.loading = True
            t = threading.Thread(
                target=self._thread_load_all_cards_from_ws,
                daemon=True,
                name="load_all_cards_from_ws",
            )
            t.start()

    def open_door_online(self, card: str, reader: str) -> bool:
        """
        Validates online if a specific card has access rights at the given time.
        """
        print("Testing rights for opening online...")
        try:
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = self._format_time_str(datetime.now())
            terminal = self._select_terminal(reader)
            result = client.service.OpenDoorOnline(terminal, card, reader, mytime)
            print("Povolen vstup: ", result)
        except Exception as e:
            log(40, str(e))
            result = 0
        finally:
            print("Finished rights for opening online...")
            if result == "1":
                return True
            return False

    def insert_to_access(self, card: str, reader: str, status: int = 700) -> None:
        """Inserts an access record for the given card and reader into the web service."""
        print("Inserting to access online...")
        try:
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = self._format_time_str(datetime.now())
            terminal = self._select_terminal(reader)
            result = client.service.InsertToAccess(
                terminal, card, reader, mytime, status
            )
        except Exception as e:
            log(40, str(e))
        finally:
            print(f"Finished insert online with return code: {result}")

    def check_connection(self) -> bool:
        """Checks if the web service is reachable."""
        try:
            transport = Transport(timeout=3)
            client = Client(self.ws_addr, transport=transport)
            if client:
                self._update_last_access()
                return True
            return False
        except Exception:
            return False

    def __str__(self) -> str:
        return "Web Services Controller"

    def __repr__(self) -> str:
        return "Web Services Controller"
