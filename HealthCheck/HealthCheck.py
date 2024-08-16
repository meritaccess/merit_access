import psutil
import subprocess
import time

from Logger import log


class HealthCheck:
    """
    Monitors system health by checking CPU temperature, CPU usage, RAM usage, and disk usage.
    """

    def __init__(
        self,
        log_interval: int = 3600,
        max_cpu_temp: int = 95,
        max_cpu_usage: int = 95,
        max_ram_usage: int = 95,
        max_disk_usage: int = 95,
    ) -> None:
        self._max_cpu_temp = max_cpu_temp
        self._max_cpu_usage = max_cpu_usage
        self._max_ram_usage = max_ram_usage
        self._max_disk_usage = max_disk_usage
        self._log_interval = log_interval
        self._last_update = time.time() - self._log_interval - 1
        self._measured_values = {
            "cpu_temp": [],
            "cpu_usage": [],
            "ram_usage": [],
            "disk_usage": [],
        }
        self._average_values = {
            "cpu_temp": None,
            "cpu_usage": None,
            "ram_usage": None,
            "disk_usage": None,
        }

    def _CPU_check(self) -> None:
        """
        Checks the current CPU temperature and usage, adding the values to the measured values list.
        """
        temp = self._get_cpu_temp()
        usage = self._get_cpu_usage()
        if temp:
            self._measured_values["cpu_temp"].append(temp)
        if usage:
            self._measured_values["cpu_usage"].append(usage)

    def _get_cpu_temp(self) -> int:
        # in Celsius
        try:
            temp = subprocess.check_output(["vcgencmd", "measure_temp"])
            temp_str = temp.decode("utf-8").strip()
            temp_value = float(temp_str.split("=")[1].split("'")[0])
            return temp_value
        except subprocess.CalledProcessError as e:
            err = f"Failed to get CPU temperature. Error:{e}"
            log(40, err)
            return None

    def _get_cpu_usage(self) -> int:
        # percentage
        try:
            return psutil.cpu_percent(interval=1)
        except Exception as e:
            err = f"Failed to get CPU usage. Error:{e}"
            log(40, err)
            return None

    def _RAM_check(self) -> None:
        """
        Checks the current RAM usage, adding the value to the measured values list.
        """
        usage = self._get_ram_usage()
        if usage:
            self._measured_values["ram_usage"].append(usage)

    def _get_ram_usage(self) -> int:
        # percentage
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception as e:
            err = f"Failed to get RAM usage. Error:{e}"
            log(40, err)
            return None

    def _DISK_check(self) -> None:
        """
        Checks the current disk usage, adding the value to the measured values list.
        """
        usage = self._get_disk_usage()
        if usage:
            self._measured_values["disk_usage"].append(usage)

    def _get_disk_usage(self) -> int:
        # percentage
        try:
            disk = psutil.disk_usage("/")
            return disk.percent
        except Exception as e:
            err = f"Failed to get Disk usage. Error:{e}"
            log(40, err)
            return None

    def _check_malfunction(self) -> bool:
        """
        Checks if any measured value exceeds its corresponding threshold.
        """
        for key, value in self._average_values.items():
            if key == "cpu_temp" and value > self._max_cpu_temp:
                return True
            if key == "cpu_usage" and value > self._max_cpu_usage:
                return True
            if key == "ram_usage" and value > self._max_ram_usage:
                return True
            if key == "disk_usage" and value > self._max_disk_usage:
                return True
        return False

    def check_health(self, attepmts: int = 10) -> None:
        """
        Performs health checks for a specified number of attempts and logs average results.
        """
        try:
            for _ in range(attepmts):
                self._CPU_check()
                self._RAM_check()
                self._DISK_check()
                time.sleep(0.5)
            self._get_average_vals()

            report = f'Health check: cpu_temp: {self._average_values["cpu_temp"]}°C, cpu_usage: {self._average_values["cpu_usage"]}%, ram_usage: {self._average_values["ram_usage"]}%, disk_usage: {self._average_values["disk_usage"]}%'

            if self._check_malfunction():
                log(30, report)

            elif time.time() - self._last_update > self._log_interval:
                self._last_update = time.time()
                log(20, report)

        except Exception as e:
            err = f"Failed to check health. Error:{e}"
            log(40, err)

    def _get_average_vals(self):
        for key, values in self._measured_values.items():
            if values:
                self._average_values[key] = int(sum(values) / len(values))
            else:
                self._average_values[key] = None
