from datetime import datetime as dt
from datetime import datetime
from typing import Dict

from constants import Action


class DayPlan:
    """
    Datastructure to represent a daily schedule with two time periods.
    """
    def __init__(
        self,
        first_start: str,
        first_end: str,
        second_start: str,
        second_end: str,
    ):
        self.first_start: datetime.time = dt.strptime(first_start, "%H:%M:%S").time()
        self.first_end: datetime.time = dt.strptime(first_end, "%H:%M:%S").time()
        self.second_start: datetime.time = dt.strptime(second_start, "%H:%M:%S").time()
        self.second_end: datetime.time = dt.strptime(second_end, "%H:%M:%S").time()

    def __str__(self) -> str:
        return "DayPlan"

    def __repr__(self) -> str:
        return "DayPlan"


class TimePlan:
    """
    Datastructure to represent a weekly schedule with daily plans and associated actions.
    """
    def __init__(self) -> None:
        self.id: int = None
        self.name: str = None
        self.description: str = None
        self.action: Action = Action.NONE
        self.days: Dict[str, DayPlan] = {
            "mon": None,
            "tue": None,
            "wed": None,
            "thu": None,
            "fri": None,
            "sat": None,
            "sun": None,
            "holiday": None,
        }

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name
