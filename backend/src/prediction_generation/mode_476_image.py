from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODE_476_ID = 476
MODE_476_TITLE = "跑马图解（带图）"
MODE_476_SOURCE_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_476" / "source"
MODE_476_OUTPUT_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_476" / "prediction"
MODE_476_OUTPUT_NAME_TEMPLATE = "mode_476_type{lottery_type}_{year}{term:03d}_web{web_id}.jpg"
MODE_476_TEXT_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "MSYH.TTC"
MODE_476_ISSUE_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "HYXINGZHITIF-2.TTF"
MODE_476_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MODE_476_DEFAULT_RESULT_TEXT = "01 02 03 04 05 06 07"


@dataclass(frozen=True)
class TextRegion:
    name: str
    box: tuple[int, int, int, int]
    font_size_candidates: tuple[int, ...]
    fill: tuple[int, int, int, int]
    bold_offsets: tuple[tuple[int, int], ...] = ((0, 0), (1, 0), (0, 1), (1, 1))
    shadow_offset: tuple[int, int] = (0, 1)
    shadow_fill: tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass(frozen=True)
class Mode476RenderResult:
    output_path: Path
    relative_url: str
    source_record_id: str


RESULT_REGION = TextRegion(
    name="last_result",
    box=(50, 675, 430, 725),
    font_size_candidates=(26, 24, 22, 20, 18, 16),
    fill=(0, 0, 0, 255),
)

ISSUE_REGION = TextRegion(
    name="issue",
    box=(575, 575, 720, 625),
    font_size_candidates=(34, 32, 30, 28, 26, 24, 22, 20),
    fill=(0, 0, 0, 255),
)


def _make_seed_int(seed_text: str) -> int:
    return int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32)


def _list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    files = [
        path
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in MODE_476_SUPPORTED_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"No supported image files found in directory: {directory}")
    return files


def load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    region: TextRegion,
    font_path: Path,
    horizontal_padding: int = 4,
    vertical_padding: int = 4,
) -> ImageFont.FreeTypeFont:
    left, top, right, bottom = region.box
    max_width = right - left - horizontal_padding * 2
    max_height = bottom - top - vertical_padding * 2

    for size in region.font_size_candidates:
        font = load_font(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width and height <= max_height:
            return font

    return load_font(font_path, region.font_size_candidates[-1])


def sample_box_average_color(
    image: Image.Image,
    box: tuple[int, int, int, int],
    sample_margin: int = 12,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    width, height = image.size
    sample_points: list[tuple[int, int, int, int]] = []

    sample_areas = (
        (max(0, left - sample_margin), top, left, bottom),
        (right, top, min(width, right + sample_margin), bottom),
        (left, max(0, top - sample_margin), right, top),
        (left, bottom, right, min(height, bottom + sample_margin)),
    )

    for area_left, area_top, area_right, area_bottom in sample_areas:
        if area_left >= area_right or area_top >= area_bottom:
            continue
        cropped = image.crop((area_left, area_top, area_right, area_bottom))
        sample_points.extend(list(cropped.getdata()))

    if not sample_points:
        sample_points.extend(list(image.crop(box).getdata()))

    count = len(sample_points)
    channel_sums = [sum(pixel[channel] for pixel in sample_points) for channel in range(4)]
    return tuple(int(channel_sum / count) for channel_sum in channel_sums)


def build_background_cover(
    image: Image.Image,
    box: tuple[int, int, int, int],
    sample_margin: int = 12,
) -> Image.Image:
    left, top, right, bottom = box
    color = sample_box_average_color(image, box, sample_margin=sample_margin)
    return Image.new("RGBA", (right - left, bottom - top), color)


def erase_text_region(canvas: Image.Image, region: TextRegion) -> None:
    patch = build_background_cover(canvas, region.box)
    canvas.alpha_composite(patch, dest=(region.box[0], region.box[1]))


def draw_centered_text(
    canvas: Image.Image,
    text: str,
    region: TextRegion,
    font_path: Path,
) -> None:
    draw = ImageDraw.Draw(canvas)
    font = fit_font(draw, text, region, font_path)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    left, top, right, bottom = region.box
    x = left + (right - left - text_width) / 2 - bbox[0]
    y = top + (bottom - top - text_height) / 2 - bbox[1]

    for offset_x, offset_y in region.bold_offsets:
        shadow_x = x + region.shadow_offset[0] + offset_x
        shadow_y = y + region.shadow_offset[1] + offset_y
        draw.text((shadow_x, shadow_y), text, font=font, fill=region.shadow_fill)

    for offset_x, offset_y in region.bold_offsets:
        draw.text((x + offset_x, y + offset_y), text, font=font, fill=region.fill)


def normalize_issue_text(issue: int | str) -> str:
    raw = str(issue or "").strip()
    if raw.isdigit():
        return str(int(raw))
    return raw or "N"


def normalize_result_text(numbers: str) -> str:
    parts = re.findall(r"\d+", str(numbers or ""))
    if not parts:
        return MODE_476_DEFAULT_RESULT_TEXT
    return " ".join(part.zfill(2) for part in parts[:7])


def choose_mode_476_source_image(
    *,
    lottery_type: int,
    year: int,
    term: int,
    site_web_id: int,
    source_root: Path = MODE_476_SOURCE_DIR,
) -> Path:
    seed = _make_seed_int(f"mode476:{int(lottery_type)}:{int(year)}:{int(term)}:{int(site_web_id)}")
    rng = random.Random(seed)
    return rng.choice(_list_images(source_root))


def render_mode_476_prediction_image(
    *,
    lottery_type: int,
    year: int,
    term: int,
    site_web_id: int,
    previous_result_numbers: str,
    source_root: Path = MODE_476_SOURCE_DIR,
    output_dir: Path = MODE_476_OUTPUT_DIR,
    font_path: Path = MODE_476_TEXT_FONT_PATH,
    issue_font_path: Path = MODE_476_ISSUE_FONT_PATH,
) -> Mode476RenderResult:
    source_image_path = choose_mode_476_source_image(
        lottery_type=lottery_type,
        year=year,
        term=term,
        site_web_id=site_web_id,
        source_root=source_root,
    )
    canvas = Image.open(source_image_path).convert("RGBA")

    issue_text = f"第{normalize_issue_text(term)}期"
    result_text = f"上期开奖号码：{normalize_result_text(previous_result_numbers)}"

    erase_text_region(canvas, RESULT_REGION)
    erase_text_region(canvas, ISSUE_REGION)
    draw_centered_text(canvas, result_text, RESULT_REGION, font_path)
    draw_centered_text(canvas, issue_text, ISSUE_REGION, issue_font_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = MODE_476_OUTPUT_NAME_TEMPLATE.format(
        lottery_type=int(lottery_type),
        year=int(year),
        term=int(term),
        web_id=int(site_web_id),
    )
    output_path = output_dir / output_name
    canvas.convert("RGB").save(output_path, format="JPEG", quality=94, optimize=True)

    relative_path = output_path.relative_to(_PROJECT_ROOT).as_posix()
    return Mode476RenderResult(
        output_path=output_path,
        relative_url=f"/{relative_path}",
        source_record_id=source_image_path.stem,
    )
