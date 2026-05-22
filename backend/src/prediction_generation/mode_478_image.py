from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODE_478_ID = 478
MODE_478_TITLE = "台湾跑马图（带图）"
MODE_478_SOURCE_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_478" / "source"
MODE_478_OUTPUT_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_478" / "prediction"
MODE_478_OUTPUT_NAME_TEMPLATE = "mode_478_type{lottery_type}_{year}{term:03d}_web{web_id}.jpg"
MODE_478_TEXT_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "MSYH.TTC"
MODE_478_TITLE_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "HYXINGZHITIF-2.TTF"
MODE_478_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MODE_478_DEFAULT_RESULT_TEXT = "01 02 03 04 05 06 07"
MODE_478_RESULT_PREFIX = "上期开奖号码："


@dataclass(frozen=True)
class TextRegion:
    name: str
    box: tuple[int, int, int, int]
    font_size_candidates: tuple[int, ...]
    fill: tuple[int, int, int, int]
    bold_offsets: tuple[tuple[int, int], ...] = ((0, 0), (1, 0), (0, 1), (1, 1))
    align: str = "center"
    left_padding: int = 0
    feather_radius: int = 0
    stroke_width: int = 0
    stroke_fill: tuple[int, int, int, int] = (255, 255, 255, 255)


@dataclass(frozen=True)
class Mode478RenderResult:
    output_path: Path
    relative_url: str
    source_record_id: str


TITLE_REGION = TextRegion(
    name="title",
    box=(0, 0, 1080, 150),
    font_size_candidates=(96, 86, 80, 76, 72, 68, 64, 60, 56, 52, 48),
    fill=(0, 0, 0, 255),
    align="left",
    left_padding=12,
    feather_radius=22,
)

RESULT_REGION = TextRegion(
    name="last_result",
    box=(175, 1545, 865, 1590),
    font_size_candidates=(34, 32, 30, 28, 26, 24, 22),
    fill=(0, 0, 0, 255),
    stroke_width=2,
    stroke_fill=(255, 255, 255, 255),
)


def _make_seed_int(seed_text: str) -> int:
    return int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32)


def _list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    files = [
        path
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in MODE_478_SUPPORTED_EXTENSIONS
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
    horizontal_padding: int = 8,
    vertical_padding: int = 4,
) -> ImageFont.FreeTypeFont:
    left, top, right, bottom = region.box
    max_width = right - left - horizontal_padding * 2
    max_height = bottom - top - vertical_padding * 2

    for size in region.font_size_candidates:
        font = load_font(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=region.stroke_width)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width and height <= max_height:
            return font

    return load_font(font_path, region.font_size_candidates[-1])


def fit_font_for_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    width: int,
    height: int,
    size_candidates: tuple[int, ...],
    stroke_width: int = 0,
) -> ImageFont.FreeTypeFont:
    for size in size_candidates:
        font = load_font(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= width and text_height <= height:
            return font
    return load_font(font_path, size_candidates[-1])


def sample_box_average_color(
    image: Image.Image,
    box: tuple[int, int, int, int],
    sample_margin: int = 16,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    width, height = image.size
    weighted_channel_sums = [0.0, 0.0, 0.0, 0.0]
    total_pixels = 0

    sample_areas = (
        (max(0, left - sample_margin), top, left, bottom),
        (right, top, min(width, right + sample_margin), bottom),
        (left, max(0, top - sample_margin), right, top),
        (left, bottom, right, min(height, bottom + sample_margin)),
    )

    for area_left, area_top, area_right, area_bottom in sample_areas:
        if area_left >= area_right or area_top >= area_bottom:
            continue
        cropped = image.crop((area_left, area_top, area_right, area_bottom)).convert("RGBA")
        pixel_count = cropped.width * cropped.height
        if pixel_count <= 0:
            continue
        stat = ImageStat.Stat(cropped)
        for channel, mean_value in enumerate(stat.mean[:4]):
            weighted_channel_sums[channel] += mean_value * pixel_count
        total_pixels += pixel_count

    if total_pixels <= 0:
        cropped = image.crop(box).convert("RGBA")
        pixel_count = cropped.width * cropped.height
        stat = ImageStat.Stat(cropped)
        for channel, mean_value in enumerate(stat.mean[:4]):
            weighted_channel_sums[channel] += mean_value * pixel_count
        total_pixels += pixel_count

    return tuple(int(channel_sum / max(1, total_pixels)) for channel_sum in weighted_channel_sums)


def build_background_cover(
    image: Image.Image,
    box: tuple[int, int, int, int],
    sample_margin: int = 16,
) -> Image.Image:
    left, top, right, bottom = box
    color = sample_box_average_color(image, box, sample_margin=sample_margin)
    return Image.new("RGBA", (right - left, bottom - top), color)


def feather_patch_edges(patch: Image.Image, feather_radius: int) -> Image.Image:
    if feather_radius <= 0:
        return patch

    width, height = patch.size
    mask = Image.new("L", (width, height), 255)
    pixels = mask.load()

    for y in range(height):
        for x in range(width):
            edge_distance = min(x, y, width - 1 - x, height - 1 - y)
            if edge_distance >= feather_radius:
                pixels[x, y] = 255
            else:
                pixels[x, y] = int(255 * edge_distance / max(1, feather_radius))

    mask = mask.filter(ImageFilter.GaussianBlur(max(1, feather_radius // 4)))
    feathered = patch.copy()
    feathered.putalpha(mask)
    return feathered


def erase_text_region(canvas: Image.Image, region: TextRegion) -> None:
    patch = build_background_cover(canvas, region.box)
    patch = feather_patch_edges(patch, region.feather_radius)
    canvas.alpha_composite(patch, dest=(region.box[0], region.box[1]))


def draw_positioned_text(
    canvas: Image.Image,
    text: str,
    region: TextRegion,
    font_path: Path,
) -> None:
    draw = ImageDraw.Draw(canvas)
    font = fit_font(draw, text, region, font_path)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=region.stroke_width)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    left, top, right, bottom = region.box
    if region.align == "left":
        x = left + region.left_padding - bbox[0]
    else:
        x = left + (right - left - text_width) / 2 - bbox[0]
    y = top + (bottom - top - text_height) / 2 - bbox[1]

    for offset_x, offset_y in region.bold_offsets:
        draw.text(
            (x + offset_x, y + offset_y),
            text,
            font=font,
            fill=region.fill,
            stroke_width=region.stroke_width,
            stroke_fill=region.stroke_fill,
        )


def split_title_text(title: str) -> tuple[str, str]:
    text = " ".join(str(title or "").split())
    number_chars: list[str] = []
    index = 0
    while index < len(text) and (text[index].isdigit() or text[index] == "-"):
        number_chars.append(text[index])
        index += 1
    numeric_part = "".join(number_chars).strip()
    chinese_part = text[index:].strip()
    return numeric_part, chinese_part


def draw_title_text(
    canvas: Image.Image,
    title: str,
    region: TextRegion,
    font_path: Path,
) -> None:
    draw = ImageDraw.Draw(canvas)
    numeric_part, chinese_part = split_title_text(title)
    left, top, right, bottom = region.box
    box_width = right - left
    box_height = bottom - top
    horizontal_padding = 24
    vertical_padding = 12
    content_width = box_width - horizontal_padding * 2
    content_height = box_height - vertical_padding * 2
    gap = 20

    if not numeric_part or not chinese_part:
        fallback_text = chinese_part or numeric_part or title
        font = fit_font(draw, fallback_text, region, font_path)
        bbox = draw.textbbox((0, 0), fallback_text, font=font)
        x = left + region.left_padding - bbox[0]
        y = top + (box_height - (bbox[3] - bbox[1])) / 2 - bbox[1]
        for offset_x, offset_y in region.bold_offsets:
            draw.text((x + offset_x, y + offset_y), fallback_text, font=font, fill=region.fill)
        return

    numeric_width_limit = max(int(content_width * 0.38), 1)
    chinese_width_limit = max(content_width - numeric_width_limit - gap, 1)

    numeric_font = fit_font_for_box(
        draw,
        numeric_part,
        font_path,
        numeric_width_limit,
        content_height,
        region.font_size_candidates,
    )
    chinese_font = fit_font_for_box(
        draw,
        chinese_part,
        font_path,
        chinese_width_limit,
        content_height,
        region.font_size_candidates,
    )

    numeric_bbox = draw.textbbox((0, 0), numeric_part, font=numeric_font)
    chinese_bbox = draw.textbbox((0, 0), chinese_part, font=chinese_font)
    numeric_x = left + horizontal_padding - numeric_bbox[0]
    chinese_x = right - horizontal_padding - (chinese_bbox[2] - chinese_bbox[0]) - chinese_bbox[0]
    numeric_y = top + (box_height - (numeric_bbox[3] - numeric_bbox[1])) / 2 - numeric_bbox[1]
    chinese_y = top + (box_height - (chinese_bbox[3] - chinese_bbox[1])) / 2 - chinese_bbox[1]

    for offset_x, offset_y in region.bold_offsets:
        draw.text(
            (numeric_x + offset_x, numeric_y + offset_y),
            numeric_part,
            font=numeric_font,
            fill=region.fill,
        )
        draw.text(
            (chinese_x + offset_x, chinese_y + offset_y),
            chinese_part,
            font=chinese_font,
            fill=region.fill,
        )


def normalize_previous_result_text(numbers: str) -> str:
    parts = re.findall(r"\d+", str(numbers or ""))
    if not parts:
        return MODE_478_DEFAULT_RESULT_TEXT
    return " ".join(part.zfill(2) for part in parts[:7])


def lottery_label_for_type(lottery_type: int) -> str:
    mapping = {
        1: "香港",
        2: "澳门",
        3: "台湾",
    }
    return mapping.get(int(lottery_type), "台湾")


def build_mode_478_title_text(*, lottery_type: int, year: int, term: int) -> str:
    return f"{int(term):03d}-{int(year)} {lottery_label_for_type(int(lottery_type))} 跑马图"


def choose_mode_478_source_image(
    *,
    lottery_type: int,
    year: int,
    term: int,
    site_web_id: int,
    source_root: Path = MODE_478_SOURCE_DIR,
) -> Path:
    seed = _make_seed_int(f"mode478:{int(lottery_type)}:{int(year)}:{int(term)}:{int(site_web_id)}")
    rng = random.Random(seed)
    return rng.choice(_list_images(source_root))


def render_mode_478_prediction_image(
    *,
    lottery_type: int,
    year: int,
    term: int,
    site_web_id: int,
    previous_result_numbers: str,
    source_root: Path = MODE_478_SOURCE_DIR,
    output_dir: Path = MODE_478_OUTPUT_DIR,
    font_path: Path = MODE_478_TEXT_FONT_PATH,
    title_font_path: Path = MODE_478_TITLE_FONT_PATH,
) -> Mode478RenderResult:
    source_image_path = choose_mode_478_source_image(
        lottery_type=lottery_type,
        year=year,
        term=term,
        site_web_id=site_web_id,
        source_root=source_root,
    )
    canvas = Image.open(source_image_path).convert("RGBA")

    title_text = build_mode_478_title_text(
        lottery_type=int(lottery_type),
        year=int(year),
        term=int(term),
    )
    result_text = f"{MODE_478_RESULT_PREFIX}{normalize_previous_result_text(previous_result_numbers)}"

    erase_text_region(canvas, TITLE_REGION)
    erase_text_region(canvas, RESULT_REGION)
    draw_title_text(canvas, title_text, TITLE_REGION, title_font_path)
    draw_positioned_text(canvas, result_text, RESULT_REGION, font_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = MODE_478_OUTPUT_NAME_TEMPLATE.format(
        lottery_type=int(lottery_type),
        year=int(year),
        term=int(term),
        web_id=int(site_web_id),
    )
    output_path = output_dir / output_name
    canvas.convert("RGB").save(output_path, format="JPEG", quality=94, optimize=True)

    relative_path = output_path.relative_to(_PROJECT_ROOT).as_posix()
    return Mode478RenderResult(
        output_path=output_path,
        relative_url=f"/{relative_path}",
        source_record_id=source_image_path.stem,
    )
