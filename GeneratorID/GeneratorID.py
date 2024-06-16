import hashlib
import platform
import subprocess

from Logger.Logger import Logger


class GeneratorID:
    def __init__(self):
        self._logger = Logger()
        self._serial_numbers = (
            self._get_cpu_serial(),
            self._get_disk_serial(),
            self._get_network_card_serial(),
        )

    def _get_cpu_serial(self) -> str:
        try:
            if platform.system() == "Linux":
                command = "cat /proc/cpuinfo | grep Serial | awk '{print $3}'"
                serial = subprocess.check_output(command, shell=True).decode().strip()
            else:
                serial = ""
        except Exception as e:
            self._logger.log(1, e)
        return serial

    def _get_disk_serial(self) -> str:
        try:
            if platform.system() == "Linux":
                command = "lsblk -o SERIAL"
                serial = (
                    subprocess.check_output(command, shell=True)
                    .decode()
                    .split("\n")[1]
                    .strip()
                )
            else:
                serial = ""
        except Exception as e:
            self._logger.log(1, e)
        return serial

    def _get_network_card_serial(self) -> str:
        try:
            if platform.system() == "Linux":
                command = "cat /sys/class/net/$(ls /sys/class/net | grep -v lo | head -n 1)/address"
                serial = subprocess.check_output(command, shell=True).decode().strip()
                serial = hashlib.sha256(serial.encode()).hexdigest()
            else:
                serial = ""
        except Exception as e:
            self._logger.log(1, e)
        return serial

    def _check_serial_numbers(self) -> bool:
        for number in self._serial_numbers:
            if not number:
                return False
        return True

    def generate_uid(self) -> str:
        try:
            if not self._check_serial_numbers():
                raise Exception("Could not get all serial numbers")

            hardware_info = "".join(self._serial_numbers)
            unique_id = hashlib.sha256(hardware_info.encode()).hexdigest()
            return unique_id

        except Exception as e:
            self._logger.log(1, e)
