import subprocess
from logger.Logger import log
from .ServiceControllerABC import ServiceControllerABC


class ApacheController(ServiceControllerABC):
    """
    Manages the Apache2 service.
    """

    def start(self) -> None:
        """
        Starts the Apache2 service.d
        """
        try:
            if not self.is_active():
                subprocess.run(["sudo", "systemctl", "start", "apache2"], check=True)
                log(20, "Apache2 started")
            else:
                log(10, "Apache2 is already active")
        except Exception as e:
            log(40, f"Failed to start Apache2 due to err: {e}")

    def stop(self) -> None:
        """
        Stops the Apache2 service.
        """
        try:
            if self.is_active():
                subprocess.run(["sudo", "systemctl", "stop", "apache2"], check=True)
                log(20, "Apache2 stopped")
            else:
                log(10, "Apache2 is already inactive")

        except Exception as e:
            log(40, f"Failed to stop Apache2 due to err: {e}")

    def is_active(self) -> bool:
        """
        Checks if the Apache2 service is active.
        """
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

    def reload(self) -> None:
        """
        Reloads the Apache2 service.
        """
        try:
            subprocess.run(["sudo", "systemctl", "reload", "apache2"], check=True)
        except Exception as e:
            log(40, f"Failed to reload Apache2 due to err: {e}")

    def restart(self) -> None:
        """
        Restarts the Apache2 service.
        """
        try:
            subprocess.run(["sudo", "systemctl", "restart", "apache2"], check=True)
        except Exception as e:
            log(40, f"Failed to restart Apache2 due to err: {e}")

    def __str__(self) -> str:
        return "ApacheController"

    def __repr__(self) -> str:
        return "ApacheController"
