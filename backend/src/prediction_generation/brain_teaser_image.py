from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from prediction_generation.brain_teaser import BrainTeaserRecord


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKGROUND_PATH = _PROJECT_ROOT / "data" / "Images" / "mode_475" / "brain_teaser.png"
DEFAULT_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "MSYH.TTC"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_475" / "prediction"
DEFAULT_OUTPUT_NAME_TEMPLATE = "brain_teaser_type{lottery_type}_{year}{term:03d}_web{web_id}.jpg"

CANVAS_SIZE = (800, 626)
CURRENT_ORIGIN = (180, 120)
PREVIOUS_ORIGIN = (180, 325)
TEXT_BOX_WIDTH = 560
CURRENT_TEXT_BOX_HEIGHT = 135
PREVIOUS_TEXT_BOX_HEIGHT = 255
FONT_SIZE_CANDIDATES = (32, 30, 28, 26, 24, 22, 20, 18)
TEXT_FILL = (34, 34, 34)
LABEL_FILL = (177, 24, 24)
LINE_SPACING = 8
SECTION_GAP = 14


def load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def normalize_value(value: str) -> str:
    return str(value or "").strip() or "-"


def get_label_width(
    draw: ImageDraw.ImageDraw,
    sections: Sequence[tuple[str, str]],
    font: ImageFont.FreeTypeFont,
) -> int:
    return max((int(draw.textlength(f"{label}：", font=font)) if label else 0) for label, _ in sections)


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    raw_lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not raw_lines:
        return ["-"]

    wrapped_lines: list[str] = []
    for raw_line in raw_lines:
        current = ""
        for char in raw_line:
            candidate = f"{current}{char}"
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
                continue
            if current:
                wrapped_lines.append(current)
            current = char
        if current:
            wrapped_lines.append(current)
    return wrapped_lines or ["-"]


def build_sections(
    record: BrainTeaserRecord,
    *,
    issue_text: str,
    include_answer: bool,
    include_analysis: bool,
) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [("", f"{issue_text}{normalize_value(record.question)}")]
    if include_answer:
        sections.append(("答案", normalize_value(record.answer)))
    sections.append(("提示", normalize_value(record.tips)))
    if include_analysis:
        sections.append(("解析", normalize_value(record.analysis)))
    return sections


def measure_sections(
    draw: ImageDraw.ImageDraw,
    sections: Sequence[tuple[str, str]],
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> tuple[list[tuple[str, list[str]]], int]:
    label_width = get_label_width(draw, sections, font)
    if max_width - label_width <= 40:
        raise RuntimeError("Text box width is too small for layout.")

    layout_sections: list[tuple[str, list[str]]] = []
    total_height = 0
    for index, (label, value) in enumerate(sections):
        section_width = max_width if not label else max_width - label_width
        lines = wrap_text(draw, value, font, section_width)
        layout_sections.append((label, lines))
        _, _, _, bottom = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=LINE_SPACING)
        total_height += bottom
        if index < len(sections) - 1:
            total_height += SECTION_GAP
    return layout_sections, total_height


def pick_font_and_layout(
    draw: ImageDraw.ImageDraw,
    sections: Sequence[tuple[str, str]],
    font_path: Path,
    max_width: int,
    max_height: int,
) -> tuple[ImageFont.FreeTypeFont, list[tuple[str, list[str]]]]:
    for size in FONT_SIZE_CANDIDATES:
        font = load_font(font_path, size)
        layout_sections, total_height = measure_sections(draw, sections, font, max_width)
        if total_height <= max_height:
            return font, layout_sections

    font = load_font(font_path, FONT_SIZE_CANDIDATES[-1])
    layout_sections, _ = measure_sections(draw, sections, font, max_width)
    return font, layout_sections


def draw_sections(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    max_width: int,
    sections: Sequence[tuple[str, str]],
    font_path: Path,
    max_height: int,
) -> None:
    font, layout_sections = pick_font_and_layout(draw, sections, font_path, max_width, max_height)
    label_width = get_label_width(draw, sections, font)

    x, y = origin
    for index, (label, lines) in enumerate(layout_sections):
        text_x = x
        if label:
            label_text = f"{label}："
            draw.text((x, y), label_text, font=font, fill=LABEL_FILL)
            text_x = x + label_width
        draw.multiline_text(
            (text_x, y),
            "\n".join(lines),
            font=font,
            fill=TEXT_FILL,
            spacing=LINE_SPACING,
        )
        _, _, _, bottom = draw.multiline_textbbox(
            (text_x, y),
            "\n".join(lines),
            font=font,
            spacing=LINE_SPACING,
        )
        y = bottom
        if index < len(layout_sections) - 1:
            y += SECTION_GAP


def save_optimized_image(canvas: Image.Image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    rgb_image = canvas.convert("RGB")

    if suffix in {".jpg", ".jpeg"}:
        rgb_image.save(output_path, format="JPEG", quality=82, optimize=True, progressive=True)
        return
    if suffix == ".webp":
        rgb_image.save(output_path, format="WEBP", quality=82, method=6)
        return
    canvas.save(output_path, format="PNG", optimize=True, compress_level=9)


def render_brain_teaser_image(
    *,
    current_record: BrainTeaserRecord,
    previous_record: BrainTeaserRecord,
    current_issue_text: str,
    previous_issue_text: str,
    background_path: Path = DEFAULT_BACKGROUND_PATH,
    font_path: Path = DEFAULT_FONT_PATH,
    output_path: Path,
) -> Path:
    background = Image.open(background_path).convert("RGBA")
    if background.size != CANVAS_SIZE:
        raise ValueError(f"Background size must be {CANVAS_SIZE}, got {background.size}")

    current_sections = build_sections(
        current_record,
        issue_text=current_issue_text,
        include_answer=False,
        include_analysis=False,
    )
    previous_sections = build_sections(
        previous_record,
        issue_text=previous_issue_text,
        include_answer=True,
        include_analysis=True,
    )

    canvas = background.copy()
    draw = ImageDraw.Draw(canvas)
    draw_sections(draw, CURRENT_ORIGIN, TEXT_BOX_WIDTH, current_sections, font_path, CURRENT_TEXT_BOX_HEIGHT)
    draw_sections(draw, PREVIOUS_ORIGIN, TEXT_BOX_WIDTH, previous_sections, font_path, PREVIOUS_TEXT_BOX_HEIGHT)
    save_optimized_image(canvas, output_path)
    return output_path
