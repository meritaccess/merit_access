import threading
from zeep import Client
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

from .WsControllerABC import WsControllerABC
from constants import MAC


class WebServicesController(WsControllerABC):
    """
    Manages interactions with external web services for operations related to access control.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def load_all_cards(self) -> None:
        """
        Initiates the process of loading all card information from the web service in a separate thread.
        """
        if not self.loading:
            self.loading = True
            cards = []
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
            client = Client(self.ws_addr)
            self._update_last_access()
            cards.extend(self._get_cards(client))
        except Exception as e:
            print(f"Error loading cards, probably no connection: {e}")
        finally:
            self.loading = False
            print("Finished thread for import card...")

    def load_all_tplans(self) -> List:
        tplans = []
        t = threading.Thread(
            target=self._thread_load_all_tplans,
            daemon=True,
            name="load_all_tplans",
            args=(tplans,),
        )
        t.start()
        t.join()
        return tplans

    def _thread_load_all_tplans(self, tplans) -> None:
        """
        A threaded method to load all time plans from the web service
        and update the local database accordingly.
        """
        print("Starting thread for import time plans...")
        try:
            client = Client(self.ws_addr)
            result = client.service.GetTimeZonesForTerminal(MAC)
            if result:
                self._update_last_access()
                xml = ET.fromstring(result)
                for timezone in xml.findall("TimeZone"):
                    plan_id = timezone.attrib["Cislo"]
                    name = timezone.attrib["Nazev"]
                    description = timezone.attrib["Popis"]
                    action = self._format_action(timezone.attrib["RezimOtevirani"])
                    times = []
                    for day in ["Po", "Ut", "St", "Ct", "Pa", "So", "Ne", "Svatky"]:
                        prvni_zacatek = timezone.attrib[f"{day}_PrvniZacatek"]
                        prvni_konec = timezone.attrib[f"{day}_PrvniKonec"]
                        druhy_zacatek = timezone.attrib[f"{day}_DruhyZacatek"]
                        druhy_konec = timezone.attrib[f"{day}_DruhyKonec"]
                        times.extend(
                            [prvni_zacatek, prvni_konec, druhy_zacatek, druhy_konec]
                        )
                    tplans.append((plan_id, name, description, action, *times))
        except Exception as e:
            print(f"Error getting time plans, probably no connection: {e}")
        finally:
            print("Finished thread for import time plans...")

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

    def _format_action(self, action):
        if action == "automatic":
            return 1
        if action == "impulse":
            return 2
        if action == "toggle":
            return 3

    def open_door_online(self, card: str, reader: str) -> int:
        """
        Validates online if a specific card has access rights at the given time.
        """
        print("Testing rights for opening online...")
        try:
            result = "2"
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = self._format_time_str(datetime.now())
            terminal = self._select_terminal(reader)
            result = client.service.OpenDoorOnline(terminal, card, reader, mytime)
            print("Povolen vstup: ", result)
            print("Finished rights for opening online...")
            if result == "0":
                return 0
            elif result == "1":
                return 1
            else:
                return 2
        except Exception as e:
            print(f"Error checking online access, probably no connection: {e}")
            return 2

    def insert_to_access(
        self, card: str, reader: str, mytime: datetime, status: int = 700
    ) -> bool:
        """Inserts an access record for the given card and reader into the web service."""
        print("Inserting to access online...")
        try:
            result = "Failed"
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = self._format_time_str(mytime)
            terminal = self._select_terminal(reader)
            result = client.service.InsertToAccess(
                terminal, card, reader, mytime, status
            )
            if result == "OK":
                return True
            return False
        except Exception as e:
            print(f"Error inserting to access, probably no connection: {e}")
            return False
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
