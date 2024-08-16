import subprocess
from typing import List

from Logger import log


class WifiController:
    """A class to control the WiFi state on a Raspberry Pi using nmcli."""

    def __init__(
        self,
        wifi_ssid: str,
        wifi_pass: str,
        ap_ssid: str,
        ap_pass: str,
        interface: str = "wlan0",
    ) -> None:
        self._wifi_ssid = wifi_ssid
        self._wifi_pass = wifi_pass
        self._ap_ssid = ap_ssid
        self._ap_pass = ap_pass
        self._interface = interface

    def _wifi_on(self) -> None:
        try:
            subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"], check=True)
            print(f"WiFi {self._interface} turned on.")
        except subprocess.CalledProcessError as e:
            err = f"Error turning on WiFi for {self._interface}: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def _wifi_off(self) -> None:
        try:
            subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"], check=True)
            print(f"WiFi {self._interface} turned off.")
        except subprocess.CalledProcessError as e:
            err = f"Error turning off WiFi for {self._interface}: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def wifi_connect(self) -> None:
        try:
            if not self.check_wifi_status():
                self._wifi_on()
            ssid_list = self._get_available_wifi()
            if not self._wifi_ssid in ssid_list:
                log(
                    30,
                    f"WiFi {self._wifi_ssid} not found. Available networks: {', '.join(ssid_list)}",
                )
                return
            if not self.check_connection():
                subprocess.run(
                    [
                        "sudo",
                        "nmcli",
                        "device",
                        "wifi",
                        "connect",
                        self._wifi_ssid,
                        "password",
                        self._wifi_pass,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            if self.check_connection():
                text = f"Connected to WiFi {self._wifi_ssid}."
                log(20, text)
            else:
                log(
                    30,
                    f"Failed to connect to WiFi {self._wifi_ssid}, possibly wrong password.",
                )
        except subprocess.CalledProcessError as e:
            err = f"Error connecting to WiFi {self._wifi_ssid}: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def _get_available_wifi(self) -> List[str]:
        try:
            result = subprocess.run(
                ["nmcli", "-f", "SSID", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
            if not result:
                return []
            return [ssid.strip() for ssid in result.stdout.strip().splitlines()[1::]]
        except subprocess.CalledProcessError as e:
            err = f"Error getting available WiFi networks: {e.stderr.strip()}"
            log(40, err)
            return []
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)
            return []

    def wifi_disconnect(self) -> None:
        try:
            if self.check_connection():
                subprocess.run(
                    ["sudo", "nmcli", "device", "disconnect", self._interface]
                )
            if not self.check_connection():
                text = f"Disconnected from WiFi {self._wifi_ssid}."
                log(20, text)
        except subprocess.CalledProcessError as e:
            err = f"Error disconnecting from WiFi {self._wifi_ssid}: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def ap_on(self) -> None:
        """
        Turns on the WiFi access point with the provided SSID and password.
        """
        try:
            if not self.check_wifi_status():
                self._wifi_on()
            subprocess.run(
                [
                    "sudo",
                    "nmcli",
                    "device",
                    "wifi",
                    "hotspot",
                    "ifname",
                    self._interface,
                    "ssid",
                    self._ap_ssid,
                    "password",
                    self._ap_pass,
                ],
                check=True,
            )
            args = ["sudo", "nmcli", "connection"]
            subprocess.run(
                args + ["modify", "Hotspot", "ipv4.method", "shared"], check=True
            )
            subprocess.run(
                args + ["modify", "Hotspot", "ipv4.addresses", "10.10.10.1/24"],
                check=True,
            )
            subprocess.run(args + ["up", "Hotspot"], check=True)
            text = f"Access Point {self._ap_ssid} turned on."
            log(20, text)
        except subprocess.CalledProcessError as e:
            err = f"Error turning on Access Point {self._ap_ssid}: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def ap_off(self) -> None:
        """
        Turns off the WiFi access point.
        """
        try:
            subprocess.run(
                ["sudo", "nmcli", "connection", "down", "Hotspot"], check=True
            )
            text = f"Access Point {self._ap_ssid} turned off."
            log(20, text)
        except subprocess.CalledProcessError as e:
            err = f"Error turning off Access Point {self._ap_ssid}: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def check_connection(self) -> bool:
        """
        Checks if the WiFi interface is currently connected.
        """
        try:
            result = self._get_devices()
            if not result:
                return False
            for line in result.stdout.splitlines():
                device, state = line.split(":")
                if device == self._interface:
                    return state == "connected"
            return False
        except subprocess.CalledProcessError as e:
            err = f"Error checking connection for {self._interface}: {e.stderr.strip()}"
            log(40, err)
            return False
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)
            return False

    def check_wifi_status(self) -> bool:
        """
        Checks if the WiFi interface is turned on.
        """
        try:
            result = self._get_devices()
            if not result:
                return False
            for line in result.stdout.splitlines():
                device, state = line.split(":")
                if device == self._interface:
                    return True
            return False
        except subprocess.CalledProcessError as e:
            err = (
                f"Error checking WiFi status for {self._interface}: {e.stderr.strip()}"
            )
            log(40, err)
            return False
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)
            return False

    def _get_devices(self) -> str:
        try:
            return subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,STATE", "device"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            err = f"Error getting devices: {e.stderr.strip()}"
            log(40, err)
            return ""
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)
            return ""

    def check_wifi_connection(self):
        """
        Checks if the WiFi interface is connected to any network.
        """
        try:
            result = subprocess.run(
                [
                    "nmcli",
                    "-t",
                    "-f",
                    "ACTIVE,TYPE,DEVICE",
                    "connection",
                    "show",
                    "--active",
                ],
                capture_output=True,
                text=True,
            )
            if not result:
                return False
            active_connections = result.stdout.strip().split("\n")
            for connection in active_connections:
                parts = connection.strip().split(":")
                if len(parts) == 3:
                    active, conn_type, device = parts
                    if active == "yes" and device == "wlan0":
                        return True
            return False
        except subprocess.CalledProcessError as e:
            print(f"Failed to check Wi-Fi connection: {e}")
            return False

    def __str__(self) -> str:
        return "Wifi Controller"

    def __repr__(self) -> str:
        return "Wifi Controller"
