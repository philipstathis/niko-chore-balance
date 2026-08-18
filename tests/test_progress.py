from datetime import date

import pytest

from progress import (
    EXPECTED_CHORES,
    Chore,
    DayRecord,
    Progress,
    todays_checks,
    total_points,
)


def _chores() -> tuple[Chore, ...]:
    return tuple(
        Chore(id=chore_id, label=chore_id, points=points)
        for chore_id, points in EXPECTED_CHORES
    )


def _checks(**earned: bool) -> dict[str, bool]:
    checks = {chore_id: False for chore_id, _ in EXPECTED_CHORES}
    checks.update(earned)
    return checks


def _progress(*days: DayRecord, starting_balance: int = 16) -> Progress:
    return Progress(
        goal=150,
        prize="Lego set",
        starting_balance=starting_balance,
        timezone="America/New_York",
        chores=_chores(),
        days=days,
    )


def test_perfect_day_adds_21():
    day = DayRecord(
        date=date(2026, 8, 17),
        checks=_checks(
            potty=True,
            quiet_voice=True,
            sharing=True,
            tidy=True,
            eating=True,
            listening=True,
        ),
    )
    assert total_points(_progress(day, starting_balance=0)) == 21


def test_starting_16_plus_perfect_day_is_37():
    day = DayRecord(
        date=date(2026, 8, 17),
        checks=_checks(
            potty=True,
            quiet_voice=True,
            sharing=True,
            tidy=True,
            eating=True,
            listening=True,
        ),
    )
    assert total_points(_progress(day)) == 37


def test_total_caps_at_150():
    perfect = _checks(
        potty=True,
        quiet_voice=True,
        sharing=True,
        tidy=True,
        eating=True,
        listening=True,
    )
    days = tuple(
        DayRecord(date=date(2026, 1, day), checks=perfect)
        for day in range(1, 9)
    )
    assert total_points(_progress(*days, starting_balance=16)) == 150


def test_omitted_chore_counts_as_not_earned():
    day = DayRecord(date=date(2026, 8, 17), checks={"potty": True})
    assert total_points(_progress(day, starting_balance=0)) == 6


def test_todays_checks_empty_when_no_row():
    checks = todays_checks(_progress(), date(2026, 8, 17))
    assert checks == {chore_id: False for chore_id, _ in EXPECTED_CHORES}


def test_todays_checks_uses_matching_date():
    day = DayRecord(
        date=date(2026, 8, 17),
        checks=_checks(potty=True, tidy=True),
    )
    checks = todays_checks(_progress(day), date(2026, 8, 17))
    assert checks["potty"] is True
    assert checks["tidy"] is True
    assert checks["quiet_voice"] is False
