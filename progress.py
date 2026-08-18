from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

EXPECTED_CHORES: tuple[tuple[str, int], ...] = (
    ("potty", 6),
    ("quiet_voice", 5),
    ("sharing", 4),
    ("tidy", 3),
    ("eating", 2),
    ("listening", 1),
)
ALLOWED_DAY_KEYS = {"date"} | {chore_id for chore_id, _ in EXPECTED_CHORES}


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


def today_in_timezone(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def load_progress(path: Path) -> Progress:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProgressError(f"Missing progress file: {path}") from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ProgressError("Invalid YAML") from exc

    if not isinstance(data, dict):
        raise ProgressError("progress.yaml must be a mapping")

    chores = _parse_chores(data.get("chores"))
    starting_balance = data.get("starting_balance")
    if not isinstance(starting_balance, int) or not 0 <= starting_balance <= 150:
        raise ProgressError("starting_balance must be an integer between 0 and 150")

    goal = data.get("goal")
    if goal != 150:
        raise ProgressError("goal must be 150")

    prize = data.get("prize")
    if not isinstance(prize, str) or not prize:
        raise ProgressError("prize must be a non-empty string")

    timezone = data.get("timezone")
    if not isinstance(timezone, str) or not timezone:
        raise ProgressError("timezone must be a non-empty string")

    days = _parse_days(data.get("days"))
    return Progress(
        goal=goal,
        prize=prize,
        starting_balance=starting_balance,
        timezone=timezone,
        chores=chores,
        days=days,
    )


def _parse_chores(raw: object) -> tuple[Chore, ...]:
    if not isinstance(raw, list) or len(raw) != len(EXPECTED_CHORES):
        raise ProgressError("chores must be the six expected chores in order")

    chores: list[Chore] = []
    for index, expected in enumerate(EXPECTED_CHORES):
        expected_id, expected_points = expected
        item = raw[index]
        if not isinstance(item, dict):
            raise ProgressError("each chore must be a mapping")
        chore_id = item.get("id")
        points = item.get("points")
        label = item.get("label")
        if chore_id != expected_id or points != expected_points:
            raise ProgressError("chores must match expected ids and points in order")
        if not isinstance(label, str) or not label:
            raise ProgressError("each chore needs a label")
        chores.append(Chore(id=chore_id, label=label, points=points))
    return tuple(chores)


def _parse_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ProgressError("date must be YYYY-MM-DD") from exc
    raise ProgressError("date must be YYYY-MM-DD")


def _parse_days(raw: object) -> tuple[DayRecord, ...]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ProgressError("days must be a list")

    days: list[DayRecord] = []
    seen: set[date] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ProgressError("each day must be a mapping")
        if "date" not in item:
            raise ProgressError("each day needs a date")
        unknown = set(item) - ALLOWED_DAY_KEYS
        if unknown:
            raise ProgressError(f"unknown day key: {sorted(unknown)[0]}")
        day_date = _parse_date(item["date"])
        if day_date in seen:
            raise ProgressError(f"duplicate date: {day_date.isoformat()}")
        seen.add(day_date)
        checks: dict[str, bool] = {}
        for chore_id, _ in EXPECTED_CHORES:
            value = item.get(chore_id, False)
            if not isinstance(value, bool):
                raise ProgressError(f"{chore_id} must be true or false")
            checks[chore_id] = value
        days.append(DayRecord(date=day_date, checks=checks))
    return tuple(days)
