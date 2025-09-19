from zeep import Client
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Tuple

from .WsControllerABC import WsControllerABC
from constants import MAC, Status
from logger.Logger import log


class WebServicesController(WsControllerABC):
    """
    Manages interactions with external web services for operations related to access control.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def load_all_cards(self) -> Tuple[List, bool]:
        """
        Initiates the process of loading all card information from the web service in a separate thread.
        """
        log(10, "Loading cards...")
        if not self.loading:
            success = False
            self.loading = True
            cards = []
            try:
                client = Client(self.ws_addr)
                self._update_last_access()
                new_cards, success = self._get_cards(client)
                cards.extend(new_cards)
            except Exception as e:
                log(10, f"Error loading cards, probably no connection: {e}")
            finally:
                self.loading = False
                return cards, success

    def load_all_tplans(self) -> Tuple[List, bool]:
        """
        Initiates the process of loading all time plans from the web service in a separate thread.
        """
        log(10, "Loading time plans...")
        tplans = []
        success = False
        try:
            client = Client(self.ws_addr)
            result = client.service.GetTimeZonesForTerminal(MAC)
            if result:
                self._update_last_access()
                xml = ET.fromstring(result)
                timezones = xml.findall("TimeZone")
                if timezones:
                    for timezone in timezones:
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
                        success = True
                else:
                    success = True
        except Exception as e:
            log(10, f"Error getting time plans, probably no connection: {e}")
        finally:
            return tplans, success

    def _get_cards(self, client: Client) -> Tuple[List, bool]:
        """
        Fetches the list of valid cards from the web service for the specified reader.
        """
        success = False
        cards = []
        try:
            result = client.service.GetAllCardsForTerminal(MAC)
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
                success = True
        except Exception as e:
            log(10, f"Error getting time plans, probably no connection: {e}")
        finally:
            return cards, success

    def _format_time_str(self, mytime: datetime) -> str:
        """
        Formats the given datetime object to a string in the format 2024-01-22 20:25:10.133
        """
        return mytime.strftime("%Y-%m-%d %H:%M:%S") + ".000"

    def _select_terminal(self, reader: int) -> str:
        """
        Selects the terminal based on the reader number.
        """
        if reader == 1:
            return "MDA" + MAC[3:]
        return "MDB" + MAC[3:]

    def _format_action(self, action) -> int:
        """
        Formats the action string to a number.
        """
        if action == "automatic":
            return 1
        if action == "impulse":
            return 2
        if action == "toggle":
            return 3

    def open_door_online(self, card: str, reader: str) -> Status:
        """
        Validates online if a specific card has access rights at the given time.
        """
        log(10, "Testing rights for opening online...")
        try:
            result = "2"
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = self._format_time_str(datetime.now())
            terminal = self._select_terminal(reader)
            result = client.service.OpenDoorOnline(terminal, card, reader, mytime)
            log(10, f"Povolen vstup: {result}")
            log(10, "Finished testing rights for opening online...")
            if result == "0":
                return Status.DENY_CARD_NOT_FOUND
            elif result == "1":
                return Status.ALLOW
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
        log(10, "Inserting to access online...")
        try:
            result = "Failed"
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = self._format_time_str(mytime)
            terminal = self._select_terminal(reader)
            result = client.service.InsertToAccess(
                terminal, card, reader, mytime, status.value
            )
            if result == "OK":
                return status
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
            client = Client(self.ws_addr, transport=transport)
            if client:
                self._update_last_access()
                return True
            return False
        except Exception as e:
            return False

    def __str__(self) -> str:
        return "WebServicesController"

    def __repr__(self) -> str:
        return "WebServicesController"
