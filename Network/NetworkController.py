import subprocess
from netaddr import IPNetwork

from Logger import log


class NetworkController:
    """
    Manages network interfaces, allowing for IP configuration and network connection management.
    """

    def __init__(self) -> None:
        self._interface: str = None
        self._connection: str = None

    def get_ip_address(self) -> str:
        try:
            result = subprocess.run(
                ["nmcli", "-g", "IP4.ADDRESS", "device", "show", self._interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if not result:
                return ""
            if result.returncode == 0:
                ip_address = result.stdout.strip()
                if ip_address:
                    return ip_address.split("/")[0]
            return ""
        except subprocess.CalledProcessError as e:
            err = f"Error getting IP address for {self._interface}: {e.stderr.strip()}"
            log(40, err)
            return ""
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)
            return ""

    def _get_connection_name(self) -> str:
        """Retrieves the connection name for the specified interface."""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,DEVICE", "con", "show"],
                capture_output=True,
                text=True,
                check=True,
            )
            if not result:
                return ""
            for line in result.stdout.split("\n"):
                if line:
                    name, device = line.split(":")
                    if device == self._interface:
                        return name
            print(f"No connection found for interface {self._interface}.")
        except subprocess.CalledProcessError as e:
            err = f"Failed to retrieve connection names: {e.stderr.strip()}"
            log(40, err)
            return ""
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)
            return ""

    def set_interface(self, interface: str) -> None:
        """
        Sets the network interface to be managed and retrieves its connection name.
        """
        self._interface = interface
        self._connection = self._get_connection_name()

    def get_interface(self) -> str:
        return self._interface

    def reset_connection(self) -> None:
        try:
            if self._connection:
                args = ["sudo", "nmcli", "con"]
                subprocess.run(args + ["down", self._connection], check=True)
                subprocess.run(args + ["up", self._connection], check=True)
        except subprocess.CalledProcessError as e:
            err = f"Failed to reset connection: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def set_static_ip(self, ip: str, subnet_mask: str, gateway: str, dns: str) -> None:
        """Sets a static IP address with the given subnet mask, gateway, and DNS."""
        try:
            if self._connection:
                # Convert subnet mask to CIDR notation
                cidr_notation = IPNetwork(f"0.0.0.0/{subnet_mask}").prefixlen
                ip_cidr = f"{ip}/{cidr_notation}"
                args = ["sudo", "nmcli", "con", "mod", self._connection]
                subprocess.run(args + ["ipv4.addresses", ip_cidr], check=True)
                subprocess.run(args + ["ipv4.gateway", gateway], check=True)
                subprocess.run(args + ["ipv4.dns", dns], check=True)
                subprocess.run(args + ["ipv4.method", "manual"], check=True)
                self.reset_connection()
                text = f"Static IP {ip} set successfully on {self._connection}."
                log(20, text)
        except subprocess.CalledProcessError as e:
            err = f"Failed to set static IP: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def set_dhcp(self) -> None:
        """Enables DHCP for the specified interface."""
        try:
            if self._connection:
                args = ["sudo", "nmcli", "con", "mod", self._connection]
                subprocess.run(args + ["ipv4.method", "auto"], check=True)
                subprocess.run(args + ["ipv4.gateway", ""], check=True)
                subprocess.run(args + ["ipv4.address", ""], check=True)
                self.reset_connection()
                text = f"DHCP enabled successfully on {self._connection}."
                log(20, text)
        except subprocess.CalledProcessError as e:
            err = f"Failed to enable DHCP: {e.stderr.strip()}"
            log(40, err)
        except Exception as e:
            err = f"Unexpected error: {e}"
            log(40, err)

    def __str__(self) -> str:
        return "Network Controller"

    def __repr__(self) -> str:
        return "Network Controller"
