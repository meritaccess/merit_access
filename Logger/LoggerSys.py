import logging
import logging.handlers
import threading

from constants import SYSLOG_SERVER, SYSLOG_PORT, MAC


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style="%", hostname=MAC):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.hostname = hostname

    def format(self, record):
        record.hostname = self.hostname
        return super().format(record)


class LoggerSys:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, server_ip=SYSLOG_SERVER, port=SYSLOG_PORT, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._initialize(server_ip, port)
        return cls._instance

    def _initialize(self, server_ip, port):
        self.logger = logging.getLogger("syslog_logger")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.handlers.SysLogHandler(
            address=(server_ip, port),
            facility=logging.handlers.SysLogHandler.LOG_USER,
        )
        formatter = CustomFormatter(
            fmt="<%(levelno)s>%(asctime)s %(hostname)s %(name)s: %(message)s",
            datefmt="%b %d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger

    def __str__(self) -> str:
        return "LoggerSys"

    def __repr__(self) -> str:
        return "LoggerSys"


def get_sys_logger():
    return LoggerSys().get_logger()
