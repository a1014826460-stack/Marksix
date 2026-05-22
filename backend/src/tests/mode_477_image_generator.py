from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKGROUND_PATH = _PROJECT_ROOT / "data" / "Images" / "mode_477" / "pg.jpg"
DEFAULT_SOURCE_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_477" / "source"
DEFAULT_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "MSYH.TTC"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_477" / "output"
DEFAULT_OUTPUT_PATH = DEFAULT_OUTPUT_DIR / "mode_477_generated.jpg"

CANVAS_SIZE = (624, 744)
PRIMARY_CUTOUT_BOX = (95, 380, 535, 535)
SECONDARY_CUTOUT_BOX = (220, 610, 425, 655)
CURRENT_ORIGIN = (180, 120)
PREVIOUS_ORIGIN = (180, 325)
TEXT_BOX_WIDTH = 340
CURRENT_TEXT_BOX_HEIGHT = 170
PREVIOUS_TEXT_BOX_HEIGHT = 300
LINE_SPACING = 10
SECTION_GAP = 12
FONT_SIZE_CANDIDATES = (30, 28, 26, 24, 22, 20, 18, 16)
TEXT_FILL = (52, 52, 52, 255)

DEFAULT_PAYLOAD = [
    {
        "issue": "140",
        "title": "澳门传真",
        "subtitle": "《内部绝密信封》第140期",
        "author": "---致彩民",
        "recipient": "各位彩民：",
        "greeting": "你们好！",
        "last_result": "上期开奖号码24号，红球，羊生肖。",
        "last_message": "昨天我在信中羊明显，大家都中了大奖吧！",
        "answer": "上期答案：24",
        "analysis": "140期解：羊鼠牛虎兔龙蛇猪",
        "footer": "上期开奖 结果41 45 48 01 36 30特24",
    }
]


@dataclass(frozen=True)
class Mode477Payload:
    issue: str
    title: str
    subtitle: str
    author: str
    recipient: str
    greeting: str
    last_result: str
    last_message: str
    answer: str
    analysis: str
    footer: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a mode_477 test image from one random source image.")
    parser.add_argument("--background", type=Path, default=DEFAULT_BACKGROUND_PATH, help="Background image path.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR, help="Source image directory.")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT_PATH, help="Unified font path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output image path.")
    parser.add_argument(
        "--payload-json",
        help="Optional JSON array payload string. Defaults to the built-in sample payload.",
    )
    return parser.parse_args()


def load_payload(payload_json: str | None) -> Mode477Payload:
    raw_payload: Sequence[dict[str, Any]]
    if payload_json:
        raw_payload = json.loads(payload_json)
    else:
        raw_payload = DEFAULT_PAYLOAD

    if not raw_payload:
        raise ValueError("Payload cannot be empty.")

    item = raw_payload[0]
    return Mode477Payload(
        issue=str(item.get("issue") or "").strip(),
        title=str(item.get("title") or "").strip(),
        subtitle=str(item.get("subtitle") or "").strip(),
        author=str(item.get("author") or "").strip(),
        recipient=str(item.get("recipient") or "").strip(),
        greeting=str(item.get("greeting") or "").strip(),
        last_result=str(item.get("last_result") or "").strip(),
        last_message=str(item.get("last_message") or "").strip(),
        answer=str(item.get("answer") or "").strip(),
        analysis=str(item.get("analysis") or "").strip(),
        footer=str(item.get("footer") or "").strip(),
    )


def list_source_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Source directory not found: {directory}")
    files = [
        path for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    if not files:
        raise FileNotFoundError(f"No source images found in: {directory}")
    return files


def choose_random_source_image(directory: Path) -> Path:
    return random.choice(list_source_images(directory))


def ensure_size(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGBA")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def cutout_regions(source_image: Image.Image) -> Image.Image:
    source = ensure_size(source_image, CANVAS_SIZE)
    result = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    result.alpha_composite(source.crop(PRIMARY_CUTOUT_BOX), (PRIMARY_CUTOUT_BOX[0], PRIMARY_CUTOUT_BOX[1]))
    result.alpha_composite(source.crop(SECONDARY_CUTOUT_BOX), (SECONDARY_CUTOUT_BOX[0], SECONDARY_CUTOUT_BOX[1]))
    return result


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    raw_lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not raw_lines:
        return ["-"]

    wrapped: list[str] = []
    for raw_line in raw_lines:
        current = ""
        for char in raw_line:
            candidate = f"{current}{char}"
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
                continue
            if current:
                wrapped.append(current)
            current = char
        if current:
            wrapped.append(current)
    return wrapped or ["-"]


def build_current_sections(payload: Mode477Payload) -> list[str]:
    return [
        payload.title,
        payload.subtitle,
        payload.author,
        payload.recipient,
        payload.greeting,
        payload.last_result,
        payload.last_message,
    ]


def build_previous_sections(payload: Mode477Payload) -> list[str]:
    sections = build_current_sections(payload)
    if payload.answer:
        sections.append(payload.answer)
    if payload.analysis:
        sections.append(payload.analysis)
    if payload.footer:
        sections.append(payload.footer)
    return sections


def layout_section_lines(
    draw: ImageDraw.ImageDraw,
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> tuple[list[str], int]:
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(wrap_text(draw, line, font, max_width))
    _, _, _, bottom = draw.multiline_textbbox(
        (0, 0),
        "\n".join(wrapped_lines),
        font=font,
        spacing=LINE_SPACING,
    )
    total_height = bottom
    total_height += max(0, len(lines) - 1) * SECTION_GAP
    return wrapped_lines, total_height


def pick_font(
    draw: ImageDraw.ImageDraw,
    lines: Sequence[str],
    font_path: Path,
    max_width: int,
    max_height: int,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in FONT_SIZE_CANDIDATES:
        font = load_font(font_path, size)
        wrapped_lines, total_height = layout_section_lines(draw, lines, font, max_width)
        if total_height <= max_height:
            return font, wrapped_lines
    font = load_font(font_path, FONT_SIZE_CANDIDATES[-1])
    wrapped_lines, _ = layout_section_lines(draw, lines, font, max_width)
    return font, wrapped_lines


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    lines: Sequence[str],
    font_path: Path,
    max_width: int,
    max_height: int,
) -> None:
    font, wrapped_lines = pick_font(draw, lines, font_path, max_width, max_height)
    x, y = origin
    text = "\n".join(wrapped_lines)
    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=TEXT_FILL,
        spacing=LINE_SPACING,
    )


def save_optimized_image(canvas: Image.Image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rgb_image = canvas.convert("RGB")
    rgb_image.save(output_path, format="JPEG", quality=86, optimize=True, progressive=True)


def generate_mode_477_image(
    *,
    background_path: Path,
    source_dir: Path,
    font_path: Path,
    output_path: Path,
    payload: Mode477Payload,
) -> Path:
    background = Image.open(background_path).convert("RGBA")
    if background.size != CANVAS_SIZE:
        raise ValueError(f"Background size must be {CANVAS_SIZE}, got {background.size}")

    source_path = choose_random_source_image(source_dir)
    source_image = Image.open(source_path)

    canvas = background.copy()
    canvas.alpha_composite(cutout_regions(source_image), (0, 0))

    draw = ImageDraw.Draw(canvas)
    draw_text_block(
        draw,
        CURRENT_ORIGIN,
        build_current_sections(payload),
        font_path,
        TEXT_BOX_WIDTH,
        CURRENT_TEXT_BOX_HEIGHT,
    )
    draw_text_block(
        draw,
        PREVIOUS_ORIGIN,
        build_previous_sections(payload),
        font_path,
        TEXT_BOX_WIDTH,
        PREVIOUS_TEXT_BOX_HEIGHT,
    )

    save_optimized_image(canvas, output_path)
    return output_path


def main() -> None:
    args = parse_args()
    payload = load_payload(args.payload_json)
    output_path = generate_mode_477_image(
        background_path=args.background,
        source_dir=args.source_dir,
        font_path=args.font,
        output_path=args.output,
        payload=payload,
    )
    print(f"Generated mode_477 test image: {output_path}")


if __name__ == "__main__":
    main()
