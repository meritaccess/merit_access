from typing import Dict
from datetime import datetime as dt
from datetime import datetime
from typing import Tuple
import re

from .TimePlan import TimePlan, DayPlan
from constants import Action
from Logger import log


class TimePlanController:
    """
    Manages and interprets time plans for access control actions.
    """

    def __init__(self) -> None:
        self._time_plans = {}

    def get_action(self, plan_id) -> Action:
        """
        Retrieves the action for the given plan ID based on the current time and day.
        """
        try:
            if plan_id == 0:
                return Action.PULS
            if not plan_id in self._time_plans.keys():
                log(
                    30,
                    f"Time plan number {plan_id} does not exist. Please review card time plans.",
                )
                return Action.PULS
            now = dt.now()
            current_time = now.time().replace(microsecond=0)
            if self._is_holiday(now):
                day = "holiday"
            else:
                day = now.strftime("%a").lower()
            day_plan = self._time_plans[plan_id].days[day]
            action = self._time_plans[plan_id].action
            if (
                current_time > day_plan.first_start
                and current_time < day_plan.first_end
            ):
                return action
            elif (
                current_time > day_plan.second_start
                and current_time < day_plan.second_end
            ):
                return action
            return Action.NONE
        except Exception as e:
            log(40, f"Failed to get action. Error:{e}")
            return Action.PULS

    def parse_tplan(self, tplan: Tuple[str, ...]) -> None:
        """
        Parses a time plan tuple to a TimePlan object and adds it to the controller's time plans.
        """
        try:
            tplan_obj = TimePlan()
            tplan_obj.id = int(tplan[1])
            tplan_obj.name = tplan[2]
            tplan_obj.description = tplan[3]
            tplan_obj.action = Action(int(tplan[4]))
            i = 5
            for day in tplan_obj.days.keys():
                for j in range(4):
                    if not self._validate_time_str(tplan[i + j]):
                        log(
                            40,
                            f"Invalid time string for time plan number {tplan_obj.id}",
                        )
                        return
                tplan_obj.days[day] = DayPlan(
                    tplan[i], tplan[i + 1], tplan[i + 2], tplan[i + 3]
                )
                i += 4

            if self._validate_tplan(tplan_obj):
                self._time_plans[int(tplan[1])] = tplan_obj
            else:
                log(40, f"Invalid time plan number {tplan_obj.id}")

        except Exception as e:
            log(40, f"Failed to parse TimePlan. Error:{e}")

    def _validate_time_str(self, time_str: str) -> bool:
        """
        Validates that a given time string is in the correct format (HH:MM:SS).
        """
        pattern = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
        if not pattern.match(time_str):
            return False
        return True

    def _validate_tplan(self, tplan: TimePlan) -> bool:
        """
        Validates that the time plan has logically consistent time intervals.
        """
        for key, day in tplan.days.items():
            if day.first_start >= day.first_end:
                return False
            if day.first_end >= day.second_start:
                return False
            if day.second_start >= day.second_end:
                return False
        return True

    def _is_holiday(self, now: datetime) -> bool:
        """
        Checks if the current date is a holiday.
        """
        # TEMPORARY - WILL BE REPLACED
        year = now.year
        month = now.month
        day = now.day
        if month == 1 and day == 1:  # Nový rok
            return True
        if month == 5 and day == 1:  # První máj
            return True
        if month == 5 and day == 8:  # Den vítězství
            return True
        if month == 7 and day == 5:  # Cyril a Metoděj
            return True
        if month == 7 and day == 6:  # Jan Hus
            return True
        if month == 9 and day == 28:  # Česká státnost
            return True
        if month == 10 and day == 28:  # Vznik  Československa
            return True
        if month == 11 and day == 17:  # Sametová revoluce
            return True
        if month == 12 and day == 24:  # Vánoce
            return True
        if month == 12 and day == 25:  # První svátek
            return True
        if month == 12 and day == 26:  # Štepán
            return True
        if year == 2025 and month == 4 and (day == 18 or day == 21):  # Velikonoce 2025
            return True
        return False
