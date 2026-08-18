# Niko's Lego Chore Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 100-point ASCII meter with a 150-brick Lego sticker chart driven by `progress.yaml`.

**Architecture:** `progress.py` loads and scores YAML (pure). `render.py` draws the 960×640 1-bit JPEG from a `Progress` object plus today's date. GitHub Actions runs pytest, then `python render.py`.

**Tech Stack:** Python 3.13, Pillow, PyYAML, pytest, GitHub Actions, existing Cloudflare JPEG download path.

## Global Constraints

- Display is 960×640, 1-bit, output `display960.jpeg` with existing download headers.
- Goal is 150; prize is a Lego set; starting_balance is 16.
- Chore ids/points in order: potty 6, quiet_voice 5, sharing 4, tidy 3, eating 2, listening 1.
- Each chore once per day; omitted or false = not earned.
- Today is `America/New_York`; no row for today → six empty stars.
- Total = min(150, starting_balance + all checked chores); never display above 150.
- Split scoring from drawing. No phone app, color, extra sizes, or point deductions.
- Cloudflare worker unchanged.

## File map

- Create: `progress.py` — YAML load, validation, scoring
- Create: `progress.yaml` — source of truth (replaces `balance.txt`)
- Create: `tests/test_progress.py` — scoring and validation
- Create: `tests/test_render.py` — 960×640 JPEG
- Modify: `render.py` — brick stack + six mission boxes; `main()` loads YAML
- Modify: `.github/workflows/pages.yml` — PyYAML, pytest before render
- Delete: `balance.txt`

---

### Task 1: Scoring from in-memory Progress

**Files:**
- Create: `progress.py`
- Test: `tests/test_progress.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class ProgressError(ValueError)`
  - `@dataclass(frozen=True) class Chore: id: str; label: str; points: int`
  - `@dataclass(frozen=True) class DayRecord: date: date; checks: dict[str, bool]`
  - `@dataclass(frozen=True) class Progress: goal: int; prize: str; starting_balance: int; timezone: str; chores: tuple[Chore, ...]; days: tuple[DayRecord, ...]`
  - `EXPECTED_CHORES: tuple[tuple[str, int], ...]` = `(("potty", 6), ("quiet_voice", 5), ("sharing", 4), ("tidy", 3), ("eating", 2), ("listening", 1))`
  - `def total_points(progress: Progress) -> int`
  - `def todays_checks(progress: Progress, today: date) -> dict[str, bool]`

- [ ] **Step 1: Write failing tests**

Create `tests/test_progress.py`:

```python
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
    day = DayRecord(date=date(2026, 8, 17), checks=_checks(
        potty=True,
        quiet_voice=True,
        sharing=True,
        tidy=True,
        eating=True,
        listening=True,
    ))
    assert total_points(_progress(day, starting_balance=0)) == 21


def test_starting_16_plus_perfect_day_is_37():
    day = DayRecord(date=date(2026, 8, 17), checks=_checks(
        potty=True,
        quiet_voice=True,
        sharing=True,
        tidy=True,
        eating=True,
        listening=True,
    ))
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_progress.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'progress'` (or import error for `total_points`).

- [ ] **Step 3: Write minimal implementation**

Create `progress.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_progress.py -v`

Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add progress.py tests/test_progress.py
git commit -m "Add scoring for weighted daily chore points."
```

---

### Task 2: Load and validate progress.yaml

**Files:**
- Modify: `progress.py`
- Modify: `tests/test_progress.py`

**Interfaces:**
- Consumes: `Progress`, `ProgressError`, `EXPECTED_CHORES` from Task 1
- Produces:
  - `def load_progress(path: Path) -> Progress`
  - `def today_in_timezone(tz_name: str) -> date`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_progress.py`:

```python
from pathlib import Path

from progress import ProgressError, load_progress


def test_load_progress_reads_yaml(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(
        """
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York
chores:
  - id: potty
    label: Potty all day
    points: 6
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
days:
  - date: 2026-08-17
    potty: true
    quiet_voice: false
    sharing: true
    tidy: true
    eating: true
    listening: true
""".strip()
        + "\n"
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
    path.write_text(": this is not: valid: yaml: [\n")
    with pytest.raises(ProgressError):
        load_progress(path)


def test_wrong_chore_list_fails(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(
        """
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York
chores:
  - id: potty
    label: Potty all day
    points: 99
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
days: []
""".strip()
        + "\n"
    )
    with pytest.raises(ProgressError):
        load_progress(path)


def test_starting_balance_out_of_range_fails(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(
        """
goal: 150
prize: Lego set
starting_balance: 200
timezone: America/New_York
chores:
  - id: potty
    label: Potty all day
    points: 6
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
days: []
""".strip()
        + "\n"
    )
    with pytest.raises(ProgressError):
        load_progress(path)


def test_duplicate_date_fails(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(
        """
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York
chores:
  - id: potty
    label: Potty all day
    points: 6
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
days:
  - date: 2026-08-17
    potty: true
  - date: 2026-08-17
    tidy: true
""".strip()
        + "\n"
    )
    with pytest.raises(ProgressError):
        load_progress(path)


def test_unknown_day_key_fails(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(
        """
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York
chores:
  - id: potty
    label: Potty all day
    points: 6
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
days:
  - date: 2026-08-17
    extra: true
""".strip()
        + "\n"
    )
    with pytest.raises(ProgressError):
        load_progress(path)


def test_missing_date_fails(tmp_path: Path):
    path = tmp_path / "progress.yaml"
    path.write_text(
        """
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York
chores:
  - id: potty
    label: Potty all day
    points: 6
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
days:
  - potty: true
""".strip()
        + "\n"
    )
    with pytest.raises(ProgressError):
        load_progress(path)
```

Also add `from datetime import date` is already present. Add `from pathlib import Path` and `load_progress` / `ProgressError` to the existing import if not already there. Keep a single import block from `progress`.

- [ ] **Step 2: Run new tests to verify they fail**

Run: `python -m pytest tests/test_progress.py::test_load_progress_reads_yaml -v`

Expected: FAIL with `ImportError` or `AttributeError: load_progress`

- [ ] **Step 3: Write loader**

Add to `progress.py` (keep existing types and scoring):

```python
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ALLOWED_DAY_KEYS = {"date"} | {chore_id for chore_id, _ in EXPECTED_CHORES}


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
```

Need PyYAML: `pip install pyyaml` locally before tests.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_progress.py -v`

Expected: PASS (all Task 1 + Task 2 tests)

- [ ] **Step 5: Commit**

```bash
git add progress.py tests/test_progress.py
git commit -m "Load and validate progress.yaml for chore scoring."
```

---

### Task 3: progress.yaml and remove balance.txt

**Files:**
- Create: `progress.yaml`
- Delete: `balance.txt`

**Interfaces:**
- Consumes: Task 2 loader schema
- Produces: repo `progress.yaml` with starting_balance 16, empty `days: []` (today's stars empty until a day is added)

- [ ] **Step 1: Add progress.yaml**

```yaml
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York

chores:
  - id: potty
    label: Potty all day
    points: 6
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

days: []
```

- [ ] **Step 2: Delete balance.txt**

- [ ] **Step 3: Confirm YAML loads**

Run: `python -c "from pathlib import Path; from progress import load_progress, total_points; p=load_progress(Path('progress.yaml')); print(total_points(p))"`

Expected: `16`

- [ ] **Step 4: Commit**

```bash
git add progress.yaml
git rm balance.txt
git commit -m "Store chore progress in YAML instead of a raw balance."
```

---

### Task 4: Draw the Lego board

**Files:**
- Modify: `render.py` (replace `render_display` and remove `load_balance` / ASCII bar)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `Progress`, `total_points`, `todays_checks` from `progress.py`
- Produces: `def render_display(progress: Progress, today: date) -> Image.Image` — 960×640, mode `"1"`
  - Title `Niko's Lego!`
  - 15×10 brick grid, one brick per point, fill bottom row left to right then up
  - Score `{total} / 150` under the stack
  - `Lego set` (from `progress.prize`) labeled at the top of the tower
  - Six boxes, two rows of three, in chore order: star, label, points
  - Keep `write_headers`, `write_index_html`, `OUTPUT_FILENAME`

- [ ] **Step 1: Write failing tests**

Create `tests/test_render.py`:

```python
from datetime import date
from pathlib import Path

from PIL import Image

from progress import (
    EXPECTED_CHORES,
    Chore,
    DayRecord,
    Progress,
)
from render import OUTPUT_FILENAME, main, render_display


def _progress(total_source_points: int = 16, today_earned: bool = False) -> Progress:
    chores = tuple(
        Chore(id=chore_id, label=label, points=points)
        for (chore_id, points), label in zip(
            EXPECTED_CHORES,
            [
                "Potty all day",
                "Quiet voice all day",
                "Sharing & friends",
                "Tidy toys",
                "Eat by myself",
                "Listen to grown-ups",
            ],
        )
    )
    checks = {chore_id: today_earned for chore_id, _ in EXPECTED_CHORES}
    days = ()
    starting = total_source_points
    if today_earned:
        starting = 16
        days = (DayRecord(date=date(2026, 8, 17), checks=checks),)
        # 16 + 21 = 37
    return Progress(
        goal=150,
        prize="Lego set",
        starting_balance=starting,
        timezone="America/New_York",
        chores=chores,
        days=days,
    )


def test_render_display_is_960x640_one_bit():
    image = render_display(_progress(), date(2026, 8, 17))
    assert image.size == (960, 640)
    assert image.mode == "1"


def test_more_points_draw_more_ink():
    emptyish = render_display(_progress(16), date(2026, 8, 17))
    fuller = render_display(_progress(80), date(2026, 8, 17))
    assert list(fuller.getdata()).count(0) > list(emptyish.getdata()).count(0)


def test_main_writes_jpeg(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "progress.yaml").write_text(
        Path(__file__).resolve().parents[1].joinpath("progress.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    main()
    image = Image.open(tmp_path / "site" / OUTPUT_FILENAME)
    assert image.size == (960, 640)
    assert image.format == "JPEG"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_render.py::test_render_display_is_960x640_one_bit -v`

Expected: FAIL because `render_display` still takes `balance: int`.

- [ ] **Step 3: Implement drawing**

Replace `render.py` with:

```python
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from progress import Progress, load_progress, today_in_timezone, todays_checks, total_points

DISPLAY_WIDTH = 960
DISPLAY_HEIGHT = 640
BRICK_COLS = 15
BRICK_ROWS = 10
OUTPUT_FILENAME = "display960.jpeg"
PROGRESS_PATH = Path("progress.yaml")
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    y: int,
    width: int,
    fill: int = 0,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=fill)


def draw_star(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    filled: bool,
) -> None:
    points = [
        (cx, cy - r),
        (cx + int(r * 0.3), cy - int(r * 0.3)),
        (cx + r, cy - int(r * 0.2)),
        (cx + int(r * 0.4), cy + int(r * 0.15)),
        (cx + int(r * 0.6), cy + r),
        (cx, cy + int(r * 0.45)),
        (cx - int(r * 0.6), cy + r),
        (cx - int(r * 0.4), cy + int(r * 0.15)),
        (cx - r, cy - int(r * 0.2)),
        (cx - int(r * 0.3), cy - int(r * 0.3)),
    ]
    if filled:
        draw.polygon(points, fill=0)
    else:
        draw.polygon(points, outline=0)


def brick_cell(index: int) -> tuple[int, int]:
    row_from_bottom = index // BRICK_COLS
    col = index % BRICK_COLS
    grid_row = (BRICK_ROWS - 1) - row_from_bottom
    return col, grid_row


def draw_brick(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    filled: bool,
) -> None:
    stud = max(3, height // 6)
    body_top = y + stud
    body = (x + 1, body_top, x + width - 2, y + height - 2)
    if filled:
        draw.rectangle(body, fill=0)
    else:
        draw.rectangle(body, outline=0, width=2)
    stud_w = max(4, (width - 8) // 2)
    gap = (width - 2 * stud_w) // 3
    for i in range(2):
        sx = x + gap + i * (stud_w + gap)
        box = (sx, y, sx + stud_w, body_top + 1)
        if filled:
            draw.rectangle(box, fill=0)
        else:
            draw.rectangle(box, outline=0, width=2)


def render_display(progress: Progress, today: date) -> Image.Image:
    image = Image.new("L", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=255)
    draw = ImageDraw.Draw(image)
    title_font = load_font(40)
    score_font = load_font(36)
    prize_font = load_font(22)
    box_font = load_font(20)
    points_font = load_font(18)

    draw_centered(draw, "Niko's Lego!", title_font, 12, DISPLAY_WIDTH)

    brick_left = 90
    brick_top = 78
    brick_area_w = 780
    brick_area_h = 270
    cell_w = brick_area_w // BRICK_COLS
    cell_h = brick_area_h // BRICK_ROWS
    filled = total_points(progress)

    prize_y = brick_top - 22
    draw_centered(draw, progress.prize, prize_font, prize_y, DISPLAY_WIDTH)

    for index in range(BRICK_COLS * BRICK_ROWS):
        col, grid_row = brick_cell(index)
        x = brick_left + col * cell_w
        y = brick_top + grid_row * cell_h
        draw_brick(draw, x, y, cell_w, cell_h, filled=index < filled)

    draw_centered(
        draw,
        f"{filled} / {progress.goal}",
        score_font,
        brick_top + brick_area_h + 8,
        DISPLAY_WIDTH,
    )

    checks = todays_checks(progress, today)
    grid_top = 430
    grid_left = 24
    box_w = 296
    box_h = 92
    gap_x = 12
    gap_y = 12
    for index, chore in enumerate(progress.chores):
        row, col = divmod(index, 3)
        x0 = grid_left + col * (box_w + gap_x)
        y0 = grid_top + row * (box_h + gap_y)
        x1 = x0 + box_w
        y1 = y0 + box_h
        draw.rectangle((x0, y0, x1, y1), outline=0, width=3)
        draw_star(draw, x0 + 28, y0 + box_h // 2, 16, checks[chore.id])
        draw.text((x0 + 54, y0 + 18), chore.label, font=box_font, fill=0)
        draw.text((x0 + 54, y0 + 50), f"+{chore.points}", font=points_font, fill=0)

    return image.point(lambda x: 0 if x < 128 else 255, mode="1")


def write_headers(output: Path) -> None:
    (output / "_headers").write_text(
        f"""\
/{OUTPUT_FILENAME}
  Content-Disposition: attachment
  Cache-Control: no-cache
"""
    )


def write_index_html(output: Path) -> None:
    (output / "index.html").write_text(
        f"""
    <!doctype html>
    <html>
    <head>
        <title>Niko's Lego!</title>
        <style>
            body {{
                margin: 40px;
                background: #ddd;
                font-family: sans-serif;
            }}
            img {{
                max-width: 100%;
                border: 1px solid #999;
            }}
            .device-url {{
                font-family: monospace;
                background: #f5f5f5;
                border: 1px solid #ccc;
                padding: 0.5rem 0.75rem;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <h1>Niko's Lego!</h1>
        <p>10.2 inch Invisible screen (960×640)</p>
        <p>Device URL: <a class="device-url" href="{OUTPUT_FILENAME}">{OUTPUT_FILENAME}</a></p>
        <img src="{OUTPUT_FILENAME}" alt="Niko's Lego — 960×640" style="width: 960px;">
    </body>
    </html>
    """.strip()
    )


def main() -> None:
    progress = load_progress(PROGRESS_PATH)
    today = today_in_timezone(progress.timezone)
    output = Path("site")
    output.mkdir(exist_ok=True)
    (output / ".nojekyll").touch()
    image = render_display(progress, today)
    image.convert("L").save(output / OUTPUT_FILENAME, format="JPEG", quality=95)
    write_index_html(output)
    write_headers(output)


if __name__ == "__main__":
    main()
```

Fix `test_more_points_draw_more_ink`: `_progress(80)` with empty days uses `starting_balance=80`, which is valid.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_render.py tests/test_progress.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "Draw the Lego brick stack and today's chore stars."
```

---

### Task 5: CI runs tests then renders

**Files:**
- Modify: `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: pytest suite, `python render.py`
- Produces: CI installs `pillow pyyaml pytest`, runs tests, then generates the JPEG

- [ ] **Step 1: Update workflow**

Replace the install/generate steps with:

```yaml
      - name: Install dependencies
        run: pip install pillow pyyaml pytest

      - name: Run tests
        run: python -m pytest -q

      - name: Generate display image
        run: python render.py
```

Leave checkout, Python 3.13, Pages deploy steps unchanged.

- [ ] **Step 2: Run the same commands locally**

Run: `python -m pytest -q` then `python render.py`

Expected: tests pass; `site/display960.jpeg` exists at 960×640.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pages.yml
git commit -m "Run chore board tests before generating the display."
```

---

## Self-review

1. Spec coverage: scoring, YAML validation (missing/bad YAML, wrong chores, balance range, duplicate date, unknown key, missing date), 16 starting + empty days, brick fill order, six boxes, 960 JPEG, CI PyYAML+tests, delete balance.txt, Cloudflare untouched.
2. No placeholders.
3. Names consistent: `load_progress`, `total_points`, `todays_checks`, `render_display(progress, today)`, `ProgressError`.
