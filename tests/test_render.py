from datetime import date
from pathlib import Path

from PIL import Image

from progress import Chore, Progress
from render import OUTPUT_FILENAME, main, render_display

def _progress(starting_balance: int = 16) -> Progress:
    chores = (
        Chore(id="potty", label="Potty all day", points=6),
        Chore(id="quiet_voice", label="Quiet voice all day", points=5),
        Chore(id="sharing", label="Sharing & friends", points=4),
        Chore(id="tidy", label="Tidy toys", points=3),
        Chore(id="eating", label="Eat by myself", points=2),
        Chore(id="listening", label="Listen to grown-ups", points=1),
    )
    return Progress(
        goal=150,
        prize="Lego set",
        starting_balance=starting_balance,
        timezone="America/New_York",
        chores=chores,
        days=(),
    )


def test_render_display_is_960x640_one_bit():
    image = render_display(_progress(), date(2026, 8, 17))
    assert image.size == (960, 640)
    assert image.mode == "1"


def test_more_points_draw_more_ink():
    emptyish = render_display(_progress(16), date(2026, 8, 17))
    fuller = render_display(_progress(80), date(2026, 8, 17))
    assert fuller.convert("L").histogram()[0] > emptyish.convert("L").histogram()[0]


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
