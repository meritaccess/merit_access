import subprocess

from .ServiceControllerABC import ServiceControllerABC
from logger.Logger import log
from constants import SSH_CONFIG


class SSHController(ServiceControllerABC):
    """
    Manages the SSH service.
    """

    def start(self) -> None:
        """
        Starts the SSH service.
        """
        try:
            if not self.is_active():
                subprocess.run(["sudo", "systemctl", "start", "ssh"], check=True)
                log(20, f"SSH started")
            else:
                log(10, "SSH is already active")
        except Exception as e:
            log(40, f"Failed to start SSH due to err: {e}")

    def stop(self) -> None:
        """
        Stops the SSH service.
        """
        try:
            if self.is_active():
                subprocess.run(["sudo", "systemctl", "stop", "ssh"], check=True)
                log(20, f"SSH stopped")
            else:
                log(10, "SSH is already inactive")
        except Exception as e:
            log(40, f"Failed to stop SSH due to err: {e}")

    def is_active(self) -> bool:
        """
        Checks if the SSH service is active.
        """
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", "ssh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == "active":
                return True
            return False
        except Exception as e:
            log(40, f"Failed to check ssh status due to err: {e}")
            return False

    def reload(self):
        """
        Reloads the SSH service.
        """
        try:
            subprocess.run(["sudo", "systemctl", "reload", "ssh"], check=True)
        except Exception as e:
            log(40, f"Failed to reload ssh due to err: {e}")

    def restart(self) -> None:
        """
        Restarts the SSH service.
        """
        try:
            subprocess.run(["sudo", "systemctl", "restart", "ssh"], check=True)
        except Exception as e:
            log(40, f"Failed to reload SSH due to err: {e}")

    def password_auth(self, enable: bool) -> None:
        """
        Enables or disables password authentication for SSH.
        """
        try:
            if enable:
                val = "yes"
            else:
                val = "no"

            subprocess.run(
                [
                    "sudo",
                    "sed",
                    "-i",
                    f"s/^#*PasswordAuthentication.*/PasswordAuthentication {val}/",
                    SSH_CONFIG,
                ],
                check=True,
            )
            self.restart()
            log(20, f"SSH password auth enabled: {enable}")
        except Exception as e:
            log(40, f"Failed to modify SSH configuration due to err: {e}")

    def __str__(self) -> str:
        return "SSHController"

    def __repr__(self) -> str:
        return "SSHController"
