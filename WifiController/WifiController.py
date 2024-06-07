import subprocess

class WifiController:
    """A class to control the WiFi state on a Raspberry Pi using nmcli."""

    def __init__(self, interface: str = "wlan0") -> None:
        self.interface: str = interface

    def turn_on(self) -> None:
        subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"], check=True)
        print(f"WiFi {self.interface} turned on.")

    def turn_off(self) -> None:
        subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"], check=True)
        print(f"WiFi {self.interface} turned off.")

    def check_status(self) -> None:
        result = subprocess.run(
            ["nmcli", "device", "status"], capture_output=True, text=True
        )
        if self.interface in result.stdout and "connected" in result.stdout:
            print(f"WiFi {self.interface} is currently enabled.")
        else:
            print(f"WiFi {self.interface} is currently disabled.")



# import subprocess


# class WifiController:
#     """A class to control the WiFi state on a Raspberry Pi."""

#     def __init__(self, interface: str = "wlan0") -> None:
#         self.interface: str = interface

#     def turn_on(self) -> None:
#         """Enable the WiFi interface"""
#         subprocess.run(["sudo", "ifconfig", self.interface, "up"], check=True)
#         print(f"WiFi {self.interface} turned on.")

#     def turn_off(self) -> None:
#         """Disable the WiFi interface"""
#         subprocess.run(["sudo", "ifconfig", self.interface, "down"], check=True)
#         print(f"WiFi {self.interface} turned off.")

#     def check_status(self) -> None:
#         """Check the status of the WiFi interface"""
#         result = subprocess.run(
#             ["ifconfig", self.interface], capture_output=True, text=True
#         )
#         if "UP" in result.stdout:
#             print(f"WiFi {self.interface} is currently enabled.")
#         else:
#             print(f"WiFi {self.interface} is currently disabled.")