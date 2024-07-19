from datetime import datetime as dt
from HardwareComponents.DoorUnit import DoorUnit

from Logger import log
from constants import MAC


class CommandParser:

    def __init__(self, du1: DoorUnit, du2: DoorUnit) -> None:
        self._door_unit1 = du1
        self._door_unit2 = du2

    def parse_command(self, command: str) -> str:
        try:
            command_id = f"_{command[:3]}"
            command_func = getattr(self, command_id, None)
            if callable(command_func):
                return command_func(command)
            else:
                return self._unknown_command(command)
        except Exception as e:
            err = f"Error in parsing command {command}: {e}"
            log(40, err)
            return ""

    def _C02(self, command: str) -> str:
        pulse_len = float(command[3:7]) / 1000  # convert to seconds
        pulse_type = int(command[8])
        if pulse_type == 1:
            self._door_unit1.open_door(pulse_len)
        elif pulse_type == 2:
            self._door_unit2.open_door(pulse_len)
        elif pulse_type == 3:
            self._door_unit1.close_door()
        elif pulse_type == 4:
            self._door_unit2.close_door()
        elif pulse_type == 5:
            self._door_unit1.permanent_open_door()
        elif pulse_type == 6:
            self._door_unit2.permanent_open_door()
        elif pulse_type == 7:
            if self._door_unit1.permanent_open:
                self._door_unit1.close_door()
            else:
                self._door_unit1.permanent_open_door()
        elif pulse_type == 8:
            if self._door_unit2.permanent_open:
                self._door_unit2.close_door()
            else:
                self._door_unit2.permanent_open_door()
        return ""

    def _C03(self, command: str = "") -> str:
        timestamp = str(dt.timestamp(dt.now())).split(".")[0]
        return f"X03|{MAC}|{timestamp}"

    def _C13(self, command: str = "") -> str:
        last_start = self._db_controller.get_val("running", "LastStart")
        last_start = dt.strptime(last_start, "%Y-%m-%d %H:%M:%S.%f")
        curr_time = dt.now()
        time_diff = curr_time - last_start
        uptime = str(int(time_diff.total_seconds() // 60))
        return f"X13|{MAC}|Up:{uptime}"

    def _C17(self, command: str = "") -> str:
        monitor = self._door_unit1.monitor
        if monitor:
            return f"X55|{MAC}|Magnet1:On\n"
        else:
            return f"X55|{MAC}|Magnet1:Off\n"

    def _C18(self, comman: str = "") -> str:
        monitor = self._door_unit2.monitor
        if monitor:
            return f"X55|{MAC}|Magnet2:On\n"
        else:
            return f"X55|{MAC}|Magnet2:Off\n"

    def _C19(self, command: str = "") -> str:
        if self._door_unit1.permanent_open:
            return f"X55|{MAC}|Relay1:On\n"
        else:
            return f"X55|{MAC}|Relay1:Off\n"

    def _C20(self, command: str = "") -> str:
        if self._door_unit2.permanent_open:
            return f"X55|{MAC}|Relay2:On\n"
        else:
            return f"X55|{MAC}|Relay2:Off\n"

    def _unknown_command(self, command: str) -> str:
        text = f"Unknown command: {command}"
        print(text)
        log(30, text)
        return ""

    def __str__(self) -> str:
        return f"CommandParser"

    def __repr__(self) -> str:
        return f"CommandParser"
