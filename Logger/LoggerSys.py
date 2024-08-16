import logging
import logging.handlers
from syslog_rfc5424_formatter import RFC5424Formatter
import threading

from constants import SYSLOG_SERVER, SYSLOG_PORT, MAC


class CustomFormatter(logging.Formatter):
    """
    Custom logging formatter that includes the hostname in log records.
    """

    def __init__(self, fmt=None, datefmt=None, style="%", hostname: str = MAC):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.hostname = hostname

    def format(self, record):
        record.hostname = self.hostname
        return super().format(record)


class LoggerSys:
    """
    Singleton class for logging messages to a syslog server.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(
        cls, server_ip: str = SYSLOG_SERVER, port: int = SYSLOG_PORT, *args, **kwargs
    ):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._initialize(server_ip, port)
        return cls._instance

    def _initialize(self, server_ip: str, port: int) -> None:
        """
        Initializes the logger with syslog handler and custom formatter.
        """
        self.logger = logging.getLogger("syslog_logger")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.handlers.SysLogHandler(
            address=(server_ip, port),
            facility=logging.handlers.SysLogHandler.LOG_USER,
        )
        formatter = RFC5424Formatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_logger(self) -> logging.Logger:
        return self.logger

    def __str__(self) -> str:
        return "LoggerSys"

    def __repr__(self) -> str:
        return "LoggerSys"


def get_sys_logger() -> logging.Logger:
    return LoggerSys().get_logger()
