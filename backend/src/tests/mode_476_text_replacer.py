from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DEFAULT_SOURCE_DIR = Path("backend/data/Images/mode_476/source")
DEFAULT_FONT_PATH = Path("backend/data/font/MSYH.TTC")
DEFAULT_ISSUE_FONT_PATH = Path("backend/data/font/HYXINGZHITIF-2.TTF")
DEFAULT_OUTPUT_DIR = Path("backend/data/Images/mode_476/output")
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class TextRegion:
    name: str
    box: tuple[int, int, int, int]
    font_size_candidates: tuple[int, ...]
    fill: tuple[int, int, int, int]
    bold_offsets: tuple[tuple[int, int], ...] = ((0, 0), (1, 0), (0, 1), (1, 1))
    shadow_offset: tuple[int, int] = (0, 1)
    shadow_fill: tuple[int, int, int, int] = (0, 0, 0, 0)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Randomly replace two text areas on one mode_476 source image.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR, help="Source image directory.")
    parser.add_argument("--output", type=Path, help="Output image path.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Default output directory.")
    parser.add_argument("--issue", default="N", help='Issue text value used in "第N期".')
    parser.add_argument(
        "--numbers",
        default="01 02 03 04 05 06 07",
        help='Winning numbers shown after "上期开奖号码：".',
    )
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT_PATH, help="Font path used to redraw the text.")
    parser.add_argument(
        "--issue-font",
        type=Path,
        default=DEFAULT_ISSUE_FONT_PATH,
        help='Font path used to redraw the "第N期" text.',
    )
    parser.add_argument("--debug-boxes", action="store_true", help="Draw debug rectangles around edited regions.")
    return parser.parse_args()


def list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Source directory not found: {directory}")
    files = [
        path for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"No supported image files found in directory: {directory}")
    return files


def choose_random_image(directory: Path) -> Path:
    return random.choice(list_images(directory))


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
        fallback = image.crop(box)
        sample_points.extend(list(fallback.getdata()))

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


def draw_debug_boxes(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    for region in (RESULT_REGION, ISSUE_REGION):
        draw.rectangle(region.box, outline=(255, 0, 0, 255), width=2)
        draw.text((region.box[0], max(0, region.box[1] - 18)), region.name, fill=(255, 0, 0, 255))


def build_output_path(image_path: Path, output_dir: Path, issue: str) -> Path:
    return output_dir / f"{image_path.stem}_issue_{issue}{image_path.suffix.lower()}"


def render_mode_476_image(
    image_path: Path,
    *,
    issue: str,
    numbers: str,
    font_path: Path,
    issue_font_path: Path,
    output_path: Path,
    debug_boxes: bool,
) -> Path:
    source = Image.open(image_path).convert("RGBA")
    canvas = source.copy()

    result_text = f"上期开奖号码：{numbers.strip()}"
    issue_text = f"第{issue.strip()}期"

    erase_text_region(canvas, RESULT_REGION)
    erase_text_region(canvas, ISSUE_REGION)
    draw_centered_text(canvas, result_text, RESULT_REGION, font_path)
    draw_centered_text(canvas, issue_text, ISSUE_REGION, issue_font_path)

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
    image_path = choose_random_image(args.source_dir)
    output_path = args.output or build_output_path(image_path, args.output_dir, args.issue)
    rendered_path = render_mode_476_image(
        image_path,
        issue=args.issue,
        numbers=args.numbers,
        font_path=args.font,
        issue_font_path=args.issue_font,
        output_path=output_path,
        debug_boxes=args.debug_boxes,
    )
    print(f"Source: {image_path}")
    print(f"Saved: {rendered_path}")


if __name__ == "__main__":
    main()
