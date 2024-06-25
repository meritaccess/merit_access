from datetime import datetime
from typing import Tuple, Any, List
import mysql.connector

from Logger.Logger import Logger
from constants import DB_HOST, DB_PASS, DB_USER, DB_NAME


class DatabaseController:
    """
    Handles database operations such as connecting to the database, reading, and writing data.
    """

    def __init__(self) -> None:
        self._db_host: str = DB_HOST
        self._db_user: str = DB_USER
        self._db_pass: str = DB_PASS
        self._db_name: str = DB_NAME
        self._db_logger: Logger = Logger()

    def _connect(self):
        """
        Establishes a connection to the database and returns both the connection and cursor objects.
        """
        try:
            mydb = mysql.connector.connect(
                host=self._db_host,
                user=self._db_user,
                password=self._db_pass,
                database=self._db_name,
            )
            cur = mydb.cursor()
            return (mydb, cur)
        except Exception as e:
            self._db_logger.log(1, str(e))

    def get_val(self, table: str, prop: str) -> str:
        """
        Retrieves a value from the specified table and property.
        """
        mydb, cur = self._connect()
        try:
            arg = (prop,)
            cur.execute(
                """SELECT VALUE AS v FROM """ + table + """ WHERE PROPERTY=%s""", arg
            )
            rows = cur.fetchone()
            cur.close()
            mydb.close()
            if len(rows) != 1:
                return ""
            return rows[0]
        except Exception as e:
            self._db_logger.log(1, str(e))
            return ""

    def set_val(self, table: str, prop: str, value: Any) -> bool:
        """
        Sets a value in the specified table and property.
        """
        mydb, cur = self._connect()
        try:
            arg = (table, prop, str(value))
            cur.callproc("SetVal", arg)
            mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def remove_access(self, card: str, reader: str) -> bool:
        """
        Removes access permissions (the card is deleted from db) for a given card and reader.
        """
        mydb, cur = self._connect()
        try:
            cur.execute(
                "DELETE FROM `Karty` WHERE `Karta`=%s AND `Ctecka`=%s;",
                (card, reader),
            )
            mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def grant_access(self, args: List) -> bool:
        """
        Adds card to the db and grants access for given reader.
        """
        mydb, cur = self._connect()
        try:
            cur.execute(
                """INSERT INTO `Karty` (`Karta`, `Ctecka`, `CasPlan`, `Povoleni`, `Smazano`, `Pozn`) VALUES (%s, %s, %s, %s, %s, %s);""",
                args,
            )
            mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def card_access_local(self, card: str, reader: str, time: datetime) -> bool:
        """
        Determines if a card has access permissions at a given reader and time.
        """
        mydb, cur = self._connect()
        try:
            # time format: '2023-09-27 13:15:40'
            arg = (
                card,
                reader,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                0,
            )
            res_args = cur.callproc("CanAccess", arg)
            mydb.commit()
            cur.close()
            mydb.close()
            if res_args[3] == 1:
                return True
            return False
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def update_temp_cards(self, args: List) -> bool:
        """
        Updates temporary cards in the database with the provided arguments.
        """
        mydb, cur = self._connect()
        try:
            cur.execute("""DELETE FROM `tempKarty`""")
            mydb.commit()
            for arg in args:
                cur.execute(
                    """INSERT INTO `tempKarty` (`Karta`, `Ctecka`, `CasPlan`, `Povoleni`, `Smazano`, `Pozn`) VALUES (%s, %s, %s, %s, %s, %s);""",
                    arg,
                )
                mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def activate_temp_cards(self) -> bool:
        """
        Activates temporary cards by calling a stored procedure designed for this purpose.
        """
        mydb, cur = self._connect()
        try:
            cur.callproc("ActivateTempCard")
            mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def add_log(self, severity: int, content: Any) -> bool:
        """
        Adds a log entry to the database.
        """
        mydb, cur = self._connect()
        try:
            arg = (severity, content)
            cur.execute(
                """INSERT INTO `logs` (`severity`, `message`) VALUES (%s, %s);""",
                arg,
            )
            mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            self._db_logger.log(1, str(e))
            return False

    def __str__(self) -> str:
        return "Database Controller"

    def __repr__(self) -> str:
        return "Database Controller"
