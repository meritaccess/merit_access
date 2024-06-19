import subprocess


class WifiController:
    """A class to control the WiFi state on a Raspberry Pi using nmcli."""

    def __init__(self, interface: str = "wlan0") -> None:
        self.interface: str = interface

    def turn_on(self) -> None:
        pass
        # subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"], check=True)
        # print(f"WiFi {self.interface} turned on.")

    def turn_off(self) -> None:
        pass
        # subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"], check=True)
        # print(f"WiFi {self.interface} turned off.")

    def check_status(self) -> None:
        result = subprocess.run(
            ["nmcli", "device", "status"], capture_output=True, text=True
        )
        if self.interface in result.stdout and "connected" in result.stdout:
            print(f"WiFi {self.interface} is currently enabled.")
        else:
            print(f"WiFi {self.interface} is currently disabled.")

    def __str__(self) -> str:
        return "Wifi Controller"

    def __repr__(self) -> str:
        return "Wifi Controller"
