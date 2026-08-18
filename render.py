from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESIGN_WIDTH = 800
DESIGN_HEIGHT = 480
DISPLAY_WIDTH = 960
DISPLAY_HEIGHT = 640
MAX_POINTS = 100
SEGMENTS = 20
OUTPUT_FILENAME = "display960.jpeg"

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def load_balance() -> int:
    value = int(Path("balance.txt").read_text().strip())

    if not 0 <= value <= MAX_POINTS:
        raise ValueError(f"Balance must be between 0 and {MAX_POINTS}, Got {value}")

    return value


def scale(value: int, size: int, base: int) -> int:
    return value * size // base


def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    width: int,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=0)


def render_display(balance: int) -> Image.Image:
    title_font = ImageFont.truetype(
        FONT_PATH,
        scale(36, DISPLAY_WIDTH, DESIGN_WIDTH),
    )
    value_font = ImageFont.truetype(
        FONT_PATH,
        scale(66, DISPLAY_WIDTH, DESIGN_WIDTH),
    )
    bar_font = ImageFont.truetype(
        FONT_PATH,
        scale(36, DISPLAY_WIDTH, DESIGN_WIDTH),
    )
    percentage_font = ImageFont.truetype(
        FONT_PATH,
        scale(30, DISPLAY_WIDTH, DESIGN_WIDTH),
    )

    image = Image.new(
        "L",
        (DISPLAY_WIDTH, DISPLAY_HEIGHT),
        color=255,
    )

    draw = ImageDraw.Draw(image)

    draw_centered(
        draw,
        "Niko's Chore Points",
        title_font,
        scale(55, DISPLAY_HEIGHT, DESIGN_HEIGHT),
        DISPLAY_WIDTH,
    )

    draw_centered(
        draw,
        f"{balance}/{MAX_POINTS}",
        value_font,
        scale(145, DISPLAY_HEIGHT, DESIGN_HEIGHT),
        DISPLAY_WIDTH,
    )

    filled_segments = balance * SEGMENTS // MAX_POINTS

    progress_bar = (
        "["
        + ("█" * filled_segments)
        + ("░" * (SEGMENTS - filled_segments))
        + "]"
    )

    draw_centered(
        draw,
        progress_bar,
        bar_font,
        scale(260, DISPLAY_HEIGHT, DESIGN_HEIGHT),
        DISPLAY_WIDTH,
    )

    draw_centered(
        draw,
        f"{balance}%",
        percentage_font,
        scale(350, DISPLAY_HEIGHT, DESIGN_HEIGHT),
        DISPLAY_WIDTH,
    )

    return image.point(
        lambda x: 0 if x < 128 else 255,
        mode="1",
    )


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
        <title>Niko's Chore Points</title>
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
        <h1>Niko's Chore Points</h1>
        <p>10.2 inch Invisible screen (960×640)</p>
        <p>Device URL: <a class="device-url" href="{OUTPUT_FILENAME}">{OUTPUT_FILENAME}</a></p>
        <img src="{OUTPUT_FILENAME}" alt="Niko's Chore Points — 960×640" style="width: 960px;">
    </body>
    </html>
    """.strip()
    )


def main():
    balance = load_balance()

    output = Path("site")
    output.mkdir(exist_ok=True)
    (output / ".nojekyll").touch()

    image = render_display(balance)
    image.convert("L").save(output / OUTPUT_FILENAME, format="JPEG", quality=95)

    write_index_html(output)
    write_headers(output)


if __name__ == "__main__":
    main()
