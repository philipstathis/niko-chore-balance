from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 480
MAX_POINTS = 100
SEGMENTS = 20

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def load_balance() -> int:
    value = int(Path("balance.txt").read_text().strip())

    if not 0 <= value <= MAX_POINTS:
        raise ValueError(f"Balance must be between 0 and {MAX_POINTS}, Got {value}")

    return value

def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]

    x = (WIDTH -width) // 2
    draw.text((x, y), text, font=font, fill=0)

def main():
    balance = load_balance()

    title_font = ImageFont.truetype(FONT_PATH, 36)
    value_font = ImageFont.truetype(FONT_PATH, 66)
    bar_font = ImageFont.truetype(FONT_PATH, 36)
    percentage_font = ImageFont.truetype(FONT_PATH, 30)

    image = Image.new(
        "L",
        (WIDTH, HEIGHT),
        color=255,
    )

    draw = ImageDraw.Draw(image)

    draw_centered(
        draw,
        "Niko's Chore Points",
        title_font,
        55,
    )

    draw_centered(
        draw,
        f"{balance}/{MAX_POINTS}",
        value_font,
        145,
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
        260,
    )

    draw_centered(
        draw,
        f"{balance}%",
        percentage_font,
        350,
    )

    # Convert to true black and white
    image = image.point(
        lambda x: 0 if x < 128 else 255,
        mode="1",
    )

    output = Path("site")
    output.mkdir(exist_ok=True)

    image.save(output / "display.png")

    # A tiny preview page for humans
    (output / "index.html").write_text(
        """
    <!doctype html>
    <html>
    <head>
        <title>Niko's Chore Points</title>
        <style>
            body {
                margin: 40px;
                background: #ddd;
                font-family: sans-serif;
            }
            img {
                width: 800px;
                max-width: 100%;
                border: 1px solid #999;
            }
    </head>
    <body>
        <img src="display.png" alt="Niko's Chore Points">
    </body>
    </html>
    """.strip()
    )


if __name__ == "__main__":
    main()
