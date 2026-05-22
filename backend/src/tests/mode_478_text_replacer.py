from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat


DEFAULT_SOURCE_ROOT = Path("backend/data/Images/mode_478")
DEFAULT_FONT_PATH = Path("backend/data/font/MSYH.TTC")
DEFAULT_TITLE_FONT_PATH = Path("backend/data/font/HYXINGZHITIF-2.TTF")
DEFAULT_OUTPUT_DIR = Path("backend/data/Images/mode_478/output")
DEFAULT_TITLE_TEXT = "001-206 台湾 跑马图"
DEFAULT_RESULT_PREFIX = "上期开奖号码："
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


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


TITLE_REGION = TextRegion(
    name="title",
    box=(0, 0, 170, 120),
    font_size_candidates=(80, 76, 72, 68, 64, 60, 56, 52, 48, 44, 40),
    fill=(0, 0, 0, 255),
    align="left",
    left_padding=12,
    feather_radius=22,
)

RESULT_REGION = TextRegion(
    name="last_result",
    box=(175, 1545, 865, 1580),
    font_size_candidates=(34, 32, 30, 28, 26, 24, 22),
    fill=(0, 0, 0, 255),
    stroke_width=2,
    stroke_fill=(255, 255, 255, 255),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Randomly replace two text areas on one mode_478 source image.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT, help="Source image root directory.")
    parser.add_argument("--output", type=Path, help="Output image path.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Default output directory.")
    parser.add_argument("--title", default=DEFAULT_TITLE_TEXT, help="Title text for the top region.")
    parser.add_argument(
        "--numbers",
        default="01 02 03 04 05 06 07",
        help='Winning numbers shown after "上期开奖号码：".',
    )
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT_PATH, help="Font path used to redraw the bottom text.")
    parser.add_argument(
        "--title-font",
        type=Path,
        default=DEFAULT_TITLE_FONT_PATH,
        help="Font path used to redraw the title text.",
    )
    parser.add_argument("--debug-boxes", action="store_true", help="Draw debug rectangles around edited regions.")
    return parser.parse_args()


def resolve_source_directory(source_root: Path) -> Path:
    preferred = source_root / "source"
    if preferred.exists():
        return preferred
    return source_root


def list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Source directory not found: {directory}")
    files = [
        path for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"No supported image files found in directory: {directory}")
    return files


def choose_random_image(source_root: Path) -> Path:
    return random.choice(list_images(resolve_source_directory(source_root)))


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


def split_title_text(title: str) -> tuple[str, str]:
    text = " ".join(str(title or "").split())
    if not text:
        text = DEFAULT_TITLE_TEXT

    number_chars: list[str] = []
    index = 0
    while index < len(text) and (text[index].isdigit() or text[index] == "-"):
        number_chars.append(text[index])
        index += 1

    numeric_part = "".join(number_chars).strip()
    chinese_part = text[index:].strip()
    return numeric_part, chinese_part


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
    horizontal_padding = 10
    vertical_padding = 8
    content_width = box_width - horizontal_padding * 2
    content_height = box_height - vertical_padding * 2
    gap = 8

    if not numeric_part or not chinese_part:
        fallback_text = chinese_part or numeric_part or DEFAULT_TITLE_TEXT
        font = fit_font(draw, fallback_text, region, font_path)
        bbox = draw.textbbox((0, 0), fallback_text, font=font)
        x = left + region.left_padding - bbox[0]
        y = top + (box_height - (bbox[3] - bbox[1])) / 2 - bbox[1]
        for offset_x, offset_y in region.bold_offsets:
            draw.text((x + offset_x, y + offset_y), fallback_text, font=font, fill=region.fill)
        return

    numeric_width_limit = max(int(content_width * 0.56), 1)
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


def draw_debug_boxes(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    for region in (TITLE_REGION, RESULT_REGION):
        draw.rectangle(region.box, outline=(255, 0, 0, 255), width=3)
        draw.text((region.box[0], max(0, region.box[1] - 24)), region.name, fill=(255, 0, 0, 255))


def build_output_path(image_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{image_path.stem}_edited{image_path.suffix.lower()}"


def render_mode_478_image(
    image_path: Path,
    *,
    title: str,
    numbers: str,
    font_path: Path,
    title_font_path: Path,
    output_path: Path,
    debug_boxes: bool,
) -> Path:
    source = Image.open(image_path).convert("RGBA")
    canvas = source.copy()

    title_text = str(title or "").strip() or DEFAULT_TITLE_TEXT
    result_text = f"{DEFAULT_RESULT_PREFIX}{str(numbers or '').strip() or '01 02 03 04 05 06 07'}"

    erase_text_region(canvas, TITLE_REGION)
    erase_text_region(canvas, RESULT_REGION)
    draw_title_text(canvas, title_text, TITLE_REGION, title_font_path)
    draw_positioned_text(canvas, result_text, RESULT_REGION, font_path)

    if debug_boxes:
        draw_debug_boxes(canvas)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        canvas.convert("RGB").save(output_path, quality=94, optimize=True)
    elif output_path.suffix.lower() == ".webp":
        canvas.save(output_path, format="WEBP", quality=94, method=6)
    else:
        canvas.save(output_path, format="PNG", optimize=True)
    return output_path


def main() -> None:
    args = parse_args()
    image_path = choose_random_image(args.source_root)
    output_path = args.output or build_output_path(image_path, args.output_dir)
    rendered_path = render_mode_478_image(
        image_path,
        title=args.title,
        numbers=args.numbers,
        font_path=args.font,
        title_font_path=args.title_font,
        output_path=output_path,
        debug_boxes=args.debug_boxes,
    )
    print(f"Source: {image_path}")
    print(f"Saved: {rendered_path}")


if __name__ == "__main__":
    main()
