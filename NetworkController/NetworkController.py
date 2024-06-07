import subprocess
from netaddr import IPNetwork


class NetworkController:
    def __init__(self, interface="eth0"):
        self.interface = interface
        self.connection = self._get_connection_name()

    def _get_connection_name(self):
        """Retrieves the connection name for the specified interface."""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,DEVICE", "con", "show"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.split("\n"):
                if line:
                    name, device = line.split(":")
                    if device == self.interface:
                        return name
            print(f"No connection found for interface {self.interface}.")
            return ""
        except subprocess.CalledProcessError as e:
            print(f"Failed to retrieve connection names: {e}")
            return ""

    def set_static_ip(self, ip, subnet_mask, gateway, dns):
        """Sets a static IP address with the given subnet mask, gateway, and DNS."""
        # Convert subnet mask to CIDR notation
        cidr_notation = IPNetwork(f"0.0.0.0/{subnet_mask}").prefixlen
        ip_cidr = f"{ip}/{cidr_notation}"
        try:
            subprocess.run(
                [
                    "sudo",
                    "nmcli",
                    "con",
                    "mod",
                    self.connection,
                    "ipv4.addresses",
                    ip_cidr,
                ],
                check=True,
            )
            subprocess.run(
                [
                    "sudo",
                    "nmcli",
                    "con",
                    "mod",
                    self.connection,
                    "ipv4.gateway",
                    gateway,
                ],
                check=True,
            )
            subprocess.run(
                ["sudo", "nmcli", "con", "mod", self.connection, "ipv4.dns", dns],
                check=True,
            )
            subprocess.run(
                [
                    "sudo",
                    "nmcli",
                    "con",
                    "mod",
                    self.connection,
                    "ipv4.method",
                    "manual",
                ],
                check=True,
            )
            subprocess.run(["sudo", "nmcli", "con", "up", self.connection], check=True)
            print(f"Static IP {ip} set successfully on {self.connection}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set static IP: {e}")

    def set_dhcp(self):
        """Enables DHCP for the specified interface."""
        try:
            subprocess.run(
                ["sudo", "nmcli", "con", "mod", self.connection, "ipv4.method", "auto"],
                check=True,
            )
            subprocess.run(["sudo", "nmcli", "con", "up", self.connection], check=True)
            print(f"DHCP enabled successfully on {self.connection}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to enable DHCP: {e}")
