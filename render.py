import math
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
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=0)


def draw_star(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    filled: bool,
) -> None:
    points: list[tuple[float, float]] = []
    for i in range(10):
        angle = math.radians(-90 + i * 36)
        radius = r if i % 2 == 0 else r * 0.4
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
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

    draw_centered(draw, progress.prize, prize_font, brick_top - 22, DISPLAY_WIDTH)

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

    return image.point(lambda pixel: 0 if pixel < 128 else 255, mode="1")


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
