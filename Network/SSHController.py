import subprocess
from Logger import log

from constants import SSH_CONFIG


class SSHController:

    def start(self) -> None:
        try:
            if not self.is_active():
                subprocess.run(["sudo", "systemctl", "start", "ssh"], check=True)
                log(20, f"SSH started")
            else:
                print("SSH is already active")
        except subprocess.CalledProcessError as e:
            log(40, f"Failed to start SSH due to err: {e}")

    def stop(self) -> None:
        try:
            if self.is_active():
                subprocess.run(["sudo", "systemctl", "stop", "ssh"], check=True)
                log(20, f"SSH stopped")
            else:
                print("SSH is already inactive")
        except subprocess.CalledProcessError as e:
            log(40, f"Failed to stop SSH due to err: {e}")

    def is_active(self) -> bool:
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
        try:
            subprocess.run(["sudo", "systemctl", "reload", "ssh"], check=True)
        except Exception as e:
            log(40, f"Failed to reload ssh due to err: {e}")

    def restart(self) -> None:
        try:
            subprocess.run(["sudo", "systemctl", "restart", "ssh"], check=True)
        except Exception as e:
            log(40, f"Failed to reload SSH due to err: {e}")

    def password_auth(self, enable: bool) -> None:
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
