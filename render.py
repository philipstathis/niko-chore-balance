from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_WIDTH = 800
BASE_HEIGHT = 480
MAX_POINTS = 100
SEGMENTS = 20

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

DISPLAYS = {
    "display800": (800, 480),
    "display880": (880, 528),
    "display960": (960, 640),
}


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


def render_display(balance: int, width: int, height: int) -> Image.Image:
    title_font = ImageFont.truetype(
        FONT_PATH,
        scale(36, width, BASE_WIDTH),
    )
    value_font = ImageFont.truetype(
        FONT_PATH,
        scale(66, width, BASE_WIDTH),
    )
    bar_font = ImageFont.truetype(
        FONT_PATH,
        scale(36, width, BASE_WIDTH),
    )
    percentage_font = ImageFont.truetype(
        FONT_PATH,
        scale(30, width, BASE_WIDTH),
    )

    image = Image.new(
        "L",
        (width, height),
        color=255,
    )

    draw = ImageDraw.Draw(image)

    draw_centered(
        draw,
        "Niko's Chore Points",
        title_font,
        scale(55, height, BASE_HEIGHT),
        width,
    )

    draw_centered(
        draw,
        f"{balance}/{MAX_POINTS}",
        value_font,
        scale(145, height, BASE_HEIGHT),
        width,
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
        scale(260, height, BASE_HEIGHT),
        width,
    )

    draw_centered(
        draw,
        f"{balance}%",
        percentage_font,
        scale(350, height, BASE_HEIGHT),
        width,
    )

    return image.point(
        lambda x: 0 if x < 128 else 255,
        mode="1",
    )


def write_device_download(output: Path, png_path: Path, device_path: Path) -> None:
    device_path.write_bytes(png_path.read_bytes())


def write_index_html(output: Path) -> None:
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
                max-width: 100%;
                border: 1px solid #999;
            }
            .display {
                margin-bottom: 2rem;
            }
            .display h2 {
                margin: 0 0 0.5rem;
                font-size: 1.1rem;
            }
            .display p {
                margin: 0 0 0.75rem;
                color: #444;
            }
            .display a {
                color: #0366d6;
            }
            .device-url {
                font-family: monospace;
                background: #f5f5f5;
                border: 1px solid #ccc;
                padding: 0.5rem 0.75rem;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <h1>Niko's Chore Points</h1>
        <p>Browser previews use <code>.png</code> files. E-ink devices should use the extensionless device URLs below, which GitHub Pages serves as downloads instead of inline images.</p>

        <div class="display">
            <h2>7.5 inch display (800×480)</h2>
            <p>Device URL: <a class="device-url" href="display800">display800</a></p>
            <p>Browser preview: <a href="display800.png">display800.png</a></p>
            <img src="display800.png" alt="Niko's Chore Points — 800×480" style="width: 800px;">
        </div>

        <div class="display">
            <h2>Older calendar display (880×528)</h2>
            <p>Device URL: <a class="device-url" href="display880">display880</a></p>
            <p>Browser preview: <a href="display880.png">display880.png</a></p>
            <img src="display880.png" alt="Niko's Chore Points — 880×528" style="width: 880px;">
        </div>

        <div class="display">
            <h2>10.2 inch display (960×640)</h2>
            <p>Device URL: <a class="device-url" href="display960">display960</a></p>
            <p>Browser preview: <a href="display960.png">display960.png</a></p>
            <img src="display960.png" alt="Niko's Chore Points — 960×640" style="width: 960px;">
        </div>

        <div class="display">
            <h2>Default (800×480)</h2>
            <p>Device URL: <a class="device-url" href="display">display</a></p>
            <p>Browser preview: <a href="display.png">display.png</a></p>
            <img src="display.png" alt="Niko's Chore Points — default" style="width: 800px;">
        </div>
    </body>
    </html>
    """.strip()
    )


def main():
    balance = load_balance()

    output = Path("site")
    output.mkdir(exist_ok=True)
    (output / ".nojekyll").touch()

    # Keep the original default output untouched in behavior (800×480).
    default_png = output / "display.png"
    render_display(balance, BASE_WIDTH, BASE_HEIGHT).save(default_png)
    write_device_download(output, default_png, output / "display")

    for filename, (width, height) in DISPLAYS.items():
        png_path = output / f"{filename}.png"
        render_display(balance, width, height).save(png_path)
        write_device_download(output, png_path, output / filename)

    write_index_html(output)


if __name__ == "__main__":
    main()
