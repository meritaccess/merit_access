from datetime import datetime as dt
import os
from typing import Any
from constants import LOG_DIR, LOG_FILE_SIZE


class Logger:
    """
    Class for logging messages with varying severity levels to a rotating log file system.
    """

    def __init__(
        self,
        min_severity: int = 3,
        log_dir: str = LOG_DIR,
        max_size_mb: int = LOG_FILE_SIZE,
    ) -> None:
        self._log_dir = log_dir
        self._log_file1: str = log_dir + "logfile" + "1" + ".log"
        self._log_file2: str = log_dir + "logfile" + "2" + ".log"
        self._max_size: int = max_size_mb * 1024 * 1024
        self._min_severity: int = min_severity

    def log(self, severity: int, content: Any) -> bool:
        """
        Logs a message with a given severity.
        """
        self._check_dir()
        file = self._select_file()
        if severity <= self._min_severity:
            try:
                curr_time = dt.now()
                log = (
                    f"{severity} {curr_time.strftime('%Y-%m-%d %H:%M:%S')} {content}\n"
                )
                if os.path.exists(file):
                    with open(file, "a") as f:
                        f.write(log)
                else:
                    with open(file, "w") as f:
                        f.write(log)
                print(log)
                return True
            except Exception as e:
                print(f"Can not write to {file} ", str(e))
                return False

    def _get_file_size(self, file: str) -> int:
        """
        Gets the file size in bytes.
        """
        if os.path.exists(file):
            # file size in bytes
            return os.stat(file).st_size
        return 0

    def _select_file(self) -> str:
        """
        Handles file rotation.
        """
        f1_size = self._get_file_size(self._log_file1)
        f2_size = self._get_file_size(self._log_file2)
        if f1_size < self._max_size:
            return self._log_file1
        elif f2_size < self._max_size:
            return self._log_file2
        else:
            os.remove(self._log_file1)
            os.rename(self._log_file2, self._log_file1)
            return self._log_file2

    def _check_dir(self):
        if not os.path.exists(LOG_DIR):
            os.mkdir(self._log_dir)
