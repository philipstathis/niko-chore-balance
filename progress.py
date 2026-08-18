from dataclasses import dataclass
from datetime import date

EXPECTED_CHORES: tuple[tuple[str, int], ...] = (
    ("potty", 6),
    ("quiet_voice", 5),
    ("sharing", 4),
    ("tidy", 3),
    ("eating", 2),
    ("listening", 1),
)


class ProgressError(ValueError):
    """Invalid progress.yaml."""


@dataclass(frozen=True)
class Chore:
    id: str
    label: str
    points: int


@dataclass(frozen=True)
class DayRecord:
    date: date
    checks: dict[str, bool]


@dataclass(frozen=True)
class Progress:
    goal: int
    prize: str
    starting_balance: int
    timezone: str
    chores: tuple[Chore, ...]
    days: tuple[DayRecord, ...]


def total_points(progress: Progress) -> int:
    earned = 0
    points_by_id = {chore.id: chore.points for chore in progress.chores}
    for day in progress.days:
        for chore_id, points in points_by_id.items():
            if day.checks.get(chore_id):
                earned += points
    return min(progress.goal, progress.starting_balance + earned)


def todays_checks(progress: Progress, today: date) -> dict[str, bool]:
    empty = {chore.id: False for chore in progress.chores}
    for day in progress.days:
        if day.date == today:
            return {chore_id: bool(day.checks.get(chore_id)) for chore_id in empty}
    return empty
