import subprocess


class WifiController:
    """A class to control the WiFi state on a Raspberry Pi using nmcli."""

    def __init__(
        self, wifi_ssid, wifi_pass, ap_ssid, ap_pass, logger, interface="wlan0"
    ) -> None:
        self._wifi_ssid: str = wifi_ssid
        self._wifi_pass: str = wifi_pass
        self._ap_ssid: str = ap_ssid
        self._ap_pass: str = ap_pass
        self._interface: str = interface
        self._logger = logger

    def _wifi_on(self) -> None:
        try:
            subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"], check=True)
            print(f"WiFi {self._interface} turned on.")
        except subprocess.CalledProcessError as e:
            err = f"Error turning on WiFi for {self._interface}: {e.stderr.strip()}"
            self._logger.log(1, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)

    def _wifi_off(self) -> None:
        try:
            subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"], check=True)
            print(f"WiFi {self._interface} turned off.")
        except subprocess.CalledProcessError as e:
            err = f"Error turning off WiFi for {self._interface}: {e.stderr.strip()}"
            self._logger.log(1, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)

    def wifi_connect(self) -> None:
        try:
            if not self.check_wifi_status():
                self._wifi_on()
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
                )
            if self.check_connection():
                text = f"Connected to WiFi {self._wifi_ssid}."
                print(text)
                self._logger.log(3, text)
            else:
                print(f"Failed to connect to WiFi {self._wifi_ssid}.")
        except subprocess.CalledProcessError as e:
            err = f"Error connecting to WiFi {self._wifi_ssid}: {e.stderr.strip()}"
            self._logger.log(1, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)

    def wifi_disconnect(self) -> None:
        try:
            if self.check_connection():
                subprocess.run(
                    ["sudo", "nmcli", "device", "disconnect", self._interface]
                )
            if not self.check_connection():
                text = f"Disconnected from WiFi {self._wifi_ssid}."
                print(text)
                self._logger.log(3, text)
        except subprocess.CalledProcessError as e:
            err = f"Error disconnecting from WiFi {self._wifi_ssid}: {e.stderr.strip()}"
            self._logger.log(1, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)

    def ap_on(self) -> None:
        """
        sudo nmcli connection modify Hotspot ipv4.method shared
        sudo nmcli connection modify Hotspot ipv4.addresses 10.10.10.1/24
        sudo nmcli connection up Hotspot
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
            print(text)
            self._logger.log(3, text)
        except subprocess.CalledProcessError as e:
            err = f"Error turning on Access Point {self._ap_ssid}: {e.stderr.strip()}"
            self._logger.log(1, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)

    def ap_off(self) -> None:
        try:
            subprocess.run(
                ["sudo", "nmcli", "connection", "down", "Hotspot"], check=True
            )
            text = f"Access Point {self._ap_ssid} turned off."
            print(text)
            self._logger.log(3, text)
        except subprocess.CalledProcessError as e:
            err = f"Error turning off Access Point {self._ap_ssid}: {e.stderr.strip()}"
            self._logger.log(1, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)

    def check_connection(self) -> bool:
        try:
            result = self._get_devices()
            for line in result.stdout.splitlines():
                device, state = line.split(":")
                if device == self._interface:
                    return state == "connected"
            return False
        except subprocess.CalledProcessError as e:
            err = f"Error checking connection for {self._interface}: {e.stderr.strip()}"
            self._logger.log(1, err)
            return False
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)
            return False

    def check_wifi_status(self) -> bool:
        try:
            result = self._get_devices()
            for line in result.stdout.splitlines():
                device, state = line.split(":")
                if device == self._interface:
                    return True
            return False
        except subprocess.CalledProcessError as e:
            err = (
                f"Error checking WiFi status for {self._interface}: {e.stderr.strip()}"
            )
            self._logger.log(1, err)
            return False
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)
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
            self._logger.log(1, err)
            return ""
        except Exception as e:
            err = f"Unexpected error: {e}"
            self._logger.log(1, err)
            return ""

    def check_wifi_connection(self):
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
            active_connections = result.stdout.strip().split("\n")
            for connection in active_connections:
                active, conn_type, device = connection.strip().split(":")
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
