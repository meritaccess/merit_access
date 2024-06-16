from Logger.Logger import Logger
from DatabaseController.DatabaseController import DatabaseController
from typing import Any
from datetime import datetime as dt
import os


class LoggerDB(Logger):

    def __init__(self, *args, db_controller: DatabaseController, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_controller = db_controller

    def log(self, severity: int, content: Any) -> bool:
        """
        Logs a message with a given severity.
        """
        if severity <= self._min_severity:
            try:
                self.db_controller.add_log(severity, content)
            except Exception as e:
                print("Cannot log to database: ", e)
                return False
            if severity == 1:
                self._check_dir()
                file = self._select_file()
                try:
                    curr_time = dt.now()
                    log = f"{severity} {curr_time.strftime('%Y-%m-%d %H:%M:%S')} {content}\n"
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

    def __str__(self) -> str:
        return "LoggerDB"

    def __repr__(self) -> str:
        return "LoggerDB"
