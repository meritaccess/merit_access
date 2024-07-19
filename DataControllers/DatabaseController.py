from datetime import datetime
from typing import Tuple, Any, List
import mysql.connector

from Logger import log
from constants import DB_HOST, DB_USER, DB_PASS, DB_NAME


class DatabaseController:
    """
    Handles database operations such as connecting to the database, reading, and writing data.
    """

    def __init__(
        self,
        host: str = DB_HOST,
        user: str = DB_USER,
        passwd: str = DB_PASS,
        name: str = DB_NAME,
    ) -> None:
        self._db_host = host
        self._db_user = user
        self._db_pass = passwd
        self._db_name = name

    def _connect(self) -> Tuple:
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
            log(40, f"Error connecting to database: {str(e)}")

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
            log(40, f"Error getting value from database: {str(e)}")
            return ""
        finally:
            cur.close()
            mydb.close()

    def set_val(self, table: str, prop: str, value: Any) -> bool:
        """
        Sets a value in the specified table and property.
        """
        mydb, cur = self._connect()
        try:
            tables = ["running", "ConfigDU"]
            if table not in tables:
                return False

            select_query = f"SELECT value FROM {table} WHERE property LIKE %s"
            running_update_query = (
                f"UPDATE {table} SET value = %s, lastchange = %s WHERE property LIKE %s"
            )
            update_query = f"UPDATE {table} SET value = %s WHERE property LIKE %s"
            insert_query = f"INSERT INTO {table} (property, value) VALUES (%s, %s)"

            cur.execute(select_query, (prop,))
            result = cur.fetchone()

            if result:
                if table == "running":
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur.execute(running_update_query, (value, current_time, prop))
                else:
                    cur.execute(update_query, (value, prop))
            else:
                cur.execute(insert_query, (prop, value))

            mydb.commit()
            cur.close()
            mydb.close()
            return True
        except Exception as e:
            log(40, f"Error setting value in database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

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
            log(40, f"Error removing access from database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

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
            log(40, f"Error granting access in database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

    def check_card_access(
        self, card: str, reader: str, time: datetime, state=10
    ) -> bool:
        """
        Determines if a card has access permissions at a given reader and time.
        """
        mydb, cur = self._connect()
        try:
            cur.execute(
                "SELECT COUNT(cardid) FROM Karty WHERE Karta = %s AND Ctecka = %s AND Povoleni = 1",
                (card, reader),
            )
            access_allowed = cur.fetchone()[0]
            return access_allowed > 0
        except Exception as e:
            log(40, f"Error checking card access in database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

    def insert_to_access(
        self, card: str, reader: str, time: datetime, status: int = 700
    ) -> bool:
        """
        Inserts an access attempt into the database.
        """
        mydb, cur = self._connect()
        try:
            cur.execute(
                "INSERT INTO Access (Adresa, Karta, Ctecka, Tlacitko, Kdy, StavZpracovani)"
                "VALUES ('localhost', %s, %s, 0, %s, %s)",
                (card, reader, time.strftime("%Y-%m-%d %H:%M:%S"), status),
            )
            mydb.commit()
            return True
        except Exception as e:
            log(40, f"Error inserting access into database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

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
            log(40, f"Error updating temporary cards in database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

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
            log(40, f"Error activating temporary cards in database: {str(e)}")
            return False
        finally:
            cur.close()
            mydb.close()

    def __str__(self) -> str:
        return "Database Controller"

    def __repr__(self) -> str:
        return "Database Controller"
