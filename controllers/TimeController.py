import subprocess
from datetime import datetime

from logger.Logger import log


class TimeController:

    def set_time(self, new_time: str, last_change: datetime = None) -> None:
        if not new_time:
            return
        elif new_time == "auto":
            self._set_time_auto()
        else:
            try:
                new_time = datetime.strptime(new_time, "%Y-%m-%d %H:%M:%S")
                new_time = self._compute_time_diff(new_time, last_change)
                self._set_time_manual(new_time)
            except Exception as e:
                log(
                    40,
                    f"Enter time in YYYY-MM-DD HH:MM:SS or 'auto' for automatic time: {e}",
                )

    def _compute_time_diff(self, new_time: datetime, last_change: datetime) -> datetime:
        # add time difference due to reboot
        if last_change:
            return (datetime.now() - last_change) + new_time
        return new_time

    def _set_time_manual(self, new_time: datetime) -> None:
        try:
            res = subprocess.run(
                ["sudo", "timedatectl", "set-ntp", "false"], capture_output=True
            )
            if res.returncode != 0:
                log(40, f"Error turning off NTP: {res.stderr.decode()}")
                return
            new_time = new_time.strftime("%Y-%m-%d %H:%M:%S")
            res = subprocess.run(["sudo", "date", "-s", new_time], capture_output=True)
            if res.returncode == 0:
                log(20, f"Time set: {new_time}")
            else:
                log(40, f"Error setting time to {new_time}: {res.stderr.decode()}")
        except Exception as e:
            log(40, f"Error setting time to {new_time}: {e}")

    def _set_time_auto(self) -> None:
        try:
            res = subprocess.run(["sudo", "timedatectl", "set-ntp", "true"])
            if res.returncode == 0:
                log(20, "Time set automatically")
            else:
                log(40, f"Error setting time automatically: {res.stderr.decode()}")
        except Exception as e:
            log(40, f"Error setting time automatically: {e}")
