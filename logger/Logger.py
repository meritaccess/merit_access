from .LoggerDB import get_logger
from .LoggerSys import get_sys_logger
from constants import SYSLOG_SERVER
import logging

if SYSLOG_SERVER:
    sys_logger = get_sys_logger()
logger = get_logger()


def log(severity: int, content: str) -> None:
    logger.log(severity, content)
    if SYSLOG_SERVER:
        sys_logger.log(severity, content)
