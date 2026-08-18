from datetime import date
from pathlib import Path

import pytest

from progress import (
    EXPECTED_CHORES,
    Chore,
    DayRecord,
    Progress,
    ProgressError,
    load_progress,
    todays_checks,
    total_points,
)

CHORES_YAML = """
chores:
  - id: potty
    label: Potty all day
    points: {potty_points}
  - id: quiet_voice
    label: Quiet voice all day
    points: 5
  - id: sharing
    label: Sharing & friends
    points: 4
  - id: tidy
    label: Tidy toys
    points: 3
  - id: eating
    label: Eat by myself
    points: 2
  - id: listening
    label: Listen to grown-ups
    points: 1
"""


def _write_progress(
    tmp_path: Path,
    *,
    days: str = "days: []",
    starting_balance: int = 16,
    potty_points: int = 6,
) -> Path:
    path = tmp_path / "progress.yaml"
    path.write_text(
        (
            f"goal: 150\n"
            f"prize: Lego set\n"
            f"starting_balance: {starting_balance}\n"
            f"timezone: America/New_York\n"
            + CHORES_YAML.format(potty_points=potty_points)
            + days
            + "\n"
        ),
        encoding="utf-8",
    )
    return path



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


def test_load_progress_reads_yaml(tmp_path: Path):
    path = _write_progress(
        tmp_path,
        days="""
days:
  - date: 2026-08-17
    potty: true
    quiet_voice: false
    sharing: true
    tidy: true
    eating: true
    listening: true
""",
    )
    progress = load_progress(path)
    assert progress.starting_balance == 16
    assert progress.chores[0].label == "Potty all day"
    assert total_points(progress) == 32
    assert todays_checks(progress, date(2026, 8, 17))["potty"] is True
    assert todays_checks(progress, date(2026, 8, 17))["quiet_voice"] is False


def test_missing_file_fails(tmp_path: Path):
    with pytest.raises(ProgressError):
        load_progress(tmp_path / "missing.yaml")


def test_bad_yaml_fails(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(": this is not: valid: yaml: [\n", encoding="utf-8")
    with pytest.raises(ProgressError):
        load_progress(path)


def test_wrong_chore_list_fails(tmp_path: Path):
    path = _write_progress(tmp_path, potty_points=99)
    with pytest.raises(ProgressError):
        load_progress(path)


def test_starting_balance_out_of_range_fails(tmp_path: Path):
    path = _write_progress(tmp_path, starting_balance=200)
    with pytest.raises(ProgressError):
        load_progress(path)


def test_duplicate_date_fails(tmp_path: Path):
    path = _write_progress(
        tmp_path,
        days="""
days:
  - date: 2026-08-17
    potty: true
  - date: 2026-08-17
    tidy: true
""",
    )
    with pytest.raises(ProgressError):
        load_progress(path)


def test_unknown_day_key_fails(tmp_path: Path):
    path = _write_progress(
        tmp_path,
        days="""
days:
  - date: 2026-08-17
    extra: true
""",
    )
    with pytest.raises(ProgressError):
        load_progress(path)


def test_missing_date_fails(tmp_path: Path):
    path = _write_progress(
        tmp_path,
        days="""
days:
  - potty: true
""",
    )
    with pytest.raises(ProgressError):
        load_progress(path)
