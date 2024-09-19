import subprocess
from Logger import log


class ApacheController:

    def start(self) -> None:
        try:
            if not self.is_active():
                subprocess.run(["sudo", "systemctl", "start", "apache2"], check=True)
                log(20, "Apache2 started")
            else:
                print("Apache2 is already active")
        except Exception as e:
            log(40, f"Failed to start Apache2 due to err: {e}")

    def stop(self) -> None:
        try:
            if self.is_active():
                subprocess.run(["sudo", "systemctl", "stop", "apache2"], check=True)
                log(20, "Apache2 stopped")
            else:
                print("Apache2 is already inactive")
        except Exception as e:
            log(40, f"Failed to stop Apache2 due to err: {e}")

    def is_active(self) -> bool:
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", "apache2"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == "active":
                return True
            return False
        except Exception as e:
            log(40, f"Failed to check Apache2 status due to err: {e}")
            return False

    def reload(self):
        try:
            subprocess.run(["sudo", "systemctl", "reload", "apache2"], check=True)
        except Exception as e:
            log(40, f"Failed to reload Apache2 due to err: {e}")

    def restart(self):
        try:
            subprocess.run(["sudo", "systemctl", "restart", "apache2"], check=True)
        except Exception as e:
            log(40, f"Failed to restart Apache2 due to err: {e}")

    def __str__(self):
        return "ApacheController"

    def __repr__(self):
        return "ApacheController"
