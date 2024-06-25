import threading
from zeep import Client
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from datetime import datetime
import time

from Logger.Logger import Logger
from DataControllers.DatabaseController import DatabaseController


class WebServicesController:
    """
    Manages interactions with external web services for operations related to access control.
    """

    def __init__(self, mac: str, db_controller: DatabaseController) -> None:
        self.mac: str = mac
        self.loading: bool = False
        self.db_controller: DatabaseController = db_controller
        self.ws_addr: str = self.db_controller.get_val("ConfigDU", "ws")
        self.ws_logger: Logger = Logger()
        self.last_access = time.time()

    def _thread_load_all_cards_from_ws(self) -> None:
        """
        A threaded method to load all access card information from the web service
        and update the local database accordingly.
        """
        print("Starting thread for import card...")
        try:
            client = Client(self.ws_addr)
            result = client.service.GetAllCardsForTerminal(self.mac)
            print("New cards:")
            print(result)
            print()
            self._update_last_access()
            xml = ET.fromstring(result)
            args = []
            for child in xml.findall("card"):
                mkarta = " ".join(child.get("Karta").split())
                arg = (
                    mkarta,
                    child.get("Ctecka"),
                    child.get("CasPlan"),
                    child.get("Povoleni"),
                    child.get("Smazano"),
                    child.get("Pozn"),
                )
                args.append(arg)
            self.db_controller.update_temp_cards(args)
        except Exception as e:
            self.ws_logger.log(1, str(e))
        finally:
            print("Loading done")

        try:
            print("Setting tempKarty to active...")
            self.db_controller.activate_temp_cards()
            return True
        except Exception as e:
            self.ws_logger.log(1, str(e))
            return False
        finally:
            self.loading = False
            print("Finished thread for import card...")

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

    def open_door_online(self, card: str, reader: str, time: datetime) -> bool:
        """
        Validates online if a specific card has access rights at the given time.
        """
        print("Testing rights for opening online...")
        try:
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = (
                time.strftime("%Y-%m-%d %H:%M:%S") + ".000"
            )  # 2024-01-22 20:25:10.133
            if reader == 1:
                myterm = "MDA" + self.mac[3:]
            else:
                myterm = "MDB" + self.mac[3:]
            mcard = " ".join(card.split())
            result = client.service.OpenDoorOnline(myterm, mcard, reader, mytime)
            print("Povolen vstup: ", result)
        except Exception as e:
            self.ws_logger.log(1, str(e))
            result = 0
        finally:
            print("Finished rights for opening online...")
            if result == "1":
                return True
            return False

    def insert_to_access(self, card: str, reader: str, time: datetime) -> None:
        """Logs an access attempt to the web service."""
        print("Inserting to access online...")
        try:
            client = Client(self.ws_addr)
            self._update_last_access()
            mytime = (
                time.strftime("%Y-%m-%d %H:%M:%S") + ".000"
            )  # 2024-01-22 20:25:10.133
            if reader == 1:
                myterm = "MDA" + self.mac[3:]
            else:
                myterm = "MDB" + self.mac[3:]
            mcard = " ".join(card.split())
            result = client.service.InsertToAccess(myterm, mcard, reader, mytime)
        except Exception as e:
            self.ws_logger.log(1, str(e))
        finally:
            print("Finished insert online...")

    def _update_last_access(self) -> None:
        self.last_access = time.time()

    def check_connection(self) -> bool:
        """Checks if the web service is reachable."""
        result = False
        try:
            transport = Transport(timeout=3)
            client = Client(self.ws_addr, transport=transport)
            result = client.service.SQLReady()
            if result:
                self._update_last_access()
                return True
            return False
        except Exception as e:
            self.ws_logger.log(1, str(e))
            return False

    def __str__(self) -> str:
        return "Web Services Controller"

    def __repr__(self) -> str:
        return "Web Services Controller"
