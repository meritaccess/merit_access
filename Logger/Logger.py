import os
from typing import Any
import threading
import logging
from logging.handlers import RotatingFileHandler
from typing import Tuple
import mysql.connector

from constants import LOG_DIR, LOG_FILE_SIZE, APP_PATH
from constants import DB_HOST, DB_NAME, DB_PASS, DB_USER


class DatabaseHandler(logging.Handler):
    def __init__(
        self,
        host: str = DB_HOST,
        user: str = DB_USER,
        passwd: str = DB_PASS,
        name: str = DB_NAME,
    ):
        super().__init__()
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
            print("Error connecting to database (logger): ", str(e))

    def emit(self, record: logging.LogRecord) -> None:
        """
        Adds a log entry to the database.
        """
        mydb, cur = self._connect()
        try:
            arg = (record.levelno, record.message)
            cur.execute(
                """INSERT INTO `logs` (`severity`, `message`) VALUES (%s, %s);""",
                arg,
            )
            mydb.commit()
            cur.close()
            mydb.close()
        except Exception as e:
            print("Error logging to database: ", str(e))

    def close(self):
        super().close()


class Logger:
    """
    Class for logging messages with varying severity levels to a rotating log file system.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize(*args, **kwargs)
        return cls._instance

    def _initialize(
        self,
        min_severity: int = 10,
        log_dir: str = LOG_DIR,
        max_size_mb: int = LOG_FILE_SIZE,
    ) -> None:
        self._log_dir = os.path.join(APP_PATH, log_dir)
        self._log_file = os.path.join(self._log_dir, "logfile.log")
        self._max_size: int = max_size_mb * 1024 * 1024
        self._min_severity: int = min_severity
        self._logger = self._init_logger()

    def _init_logger(self):
        self._check_dir()
        logger = logging.getLogger("custom_logger")
        logger.setLevel(self._min_severity)
        handler = logging.StreamHandler()
        handler.setLevel(self._min_severity)
        file_handler = RotatingFileHandler(
            self._log_file, maxBytes=self._max_size, backupCount=1
        )
        file_handler.setLevel(self._min_severity)
        db_handler = DatabaseHandler()
        db_handler.setLevel(self._min_severity)
        formatter = logging.Formatter(
            fmt="<%(levelno)s>%(asctime)s: %(message)s",
            datefmt="%b %d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        db_handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addHandler(file_handler)
        logger.addHandler(db_handler)
        return logger

    def log(self, severity: int, content: Any) -> bool:
        """
        Logs a message with a given severity.
        """
        self._check_dir()
        try:
            self._logger.log(severity, content)
            return True
        except Exception as e:
            print(f"Can not write to {self._log_file} ", str(e))
            return False

    def _check_dir(self) -> None:
        if not os.path.exists(self._log_dir):
            os.mkdir(self._log_dir)

    def __str__(self) -> str:
        return "Logger"

    def __repr__(self) -> str:
        return "Logger"


def get_logger():
    return Logger()
