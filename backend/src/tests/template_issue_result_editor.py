from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


DEFAULT_FONT_PATH = Path("backend/data/font/MSYH.TTC")
DEFAULT_OUTPUT_DIR = Path("backend/data/Images/template_issue_result_output")
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class TextRegion:
    name: str
    box: tuple[int, int, int, int]
    text_template: str
    font_size_candidates: tuple[int, ...]
    fill: tuple[int, int, int, int]
    blur_radius: float = 1.2
    shadow_offset: tuple[int, int] = (0, 1)
    shadow_fill: tuple[int, int, int, int] = (255, 255, 255, 60)


ISSUE_REGION = TextRegion(
    name="issue",
    box=(286, 116, 498, 164),
    text_template="第{issue}期",
    font_size_candidates=(30, 28, 26, 24, 22, 20),
    fill=(118, 112, 112, 215),
)

RESULT_REGION = TextRegion(
    name="result",
    box=(165, 647, 545, 690),
    text_template="上期开奖结果{numbers}",
    font_size_candidates=(30, 28, 26, 24, 22, 20, 18),
    fill=(116, 111, 111, 215),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace the issue number and winning numbers on a template image while preserving the original background."
    )
    parser.add_argument("--input", type=Path, help="Single input image path.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing template images.")
    parser.add_argument("--output", type=Path, help="Single output image path.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for batch mode.")
    parser.add_argument("--issue", required=True, help='Issue number, for example "140".')
    parser.add_argument("--numbers", required=True, help='Winning numbers text, for example "41 45 48 01 36 30特24".')
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT_PATH, help="Font path used to redraw the text.")
    parser.add_argument(
        "--debug-boxes",
        action="store_true",
        help="Draw the configured text boxes on the output image for coordinate calibration.",
    )
    args = parser.parse_args()

    if not args.input and not args.input_dir:
        parser.error("One of --input or --input-dir is required.")
    if args.input and args.input_dir:
        parser.error("Use either --input or --input-dir, not both.")
    if args.output and args.input_dir:
        parser.error("--output can only be used together with --input.")
    return args


def list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Input directory not found: {directory}")
    files = [
        path
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
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


def sample_row_color(
    image: Image.Image,
    x_start: int,
    x_end: int,
    y: int,
) -> tuple[int, int, int, int]:
    width, height = image.size
    y = max(0, min(height - 1, y))
    x_start = max(0, min(width - 1, x_start))
    x_end = max(x_start + 1, min(width, x_end))

    pixels = [image.getpixel((x, y)) for x in range(x_start, x_end)]
    count = len(pixels)
    sums = [sum(pixel[channel] for pixel in pixels) for channel in range(4)]
    return tuple(int(channel_sum / count) for channel_sum in sums)


def rebuild_background_strip(
    image: Image.Image,
    box: tuple[int, int, int, int],
    sample_gap: int = 8,
    sample_width: int = 12,
) -> Image.Image:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    base = Image.new("RGBA", (width, height))

    left_start = left - sample_gap - sample_width
    left_end = left - sample_gap
    right_start = right + sample_gap
    right_end = right + sample_gap + sample_width

    for dy in range(height):
        y = top + dy
        left_color = sample_row_color(image, left_start, left_end, y)
        right_color = sample_row_color(image, right_start, right_end, y)
        for dx in range(width):
            ratio = 0 if width <= 1 else dx / (width - 1)
            color = tuple(
                int(left_color[channel] + (right_color[channel] - left_color[channel]) * ratio)
                for channel in range(4)
            )
            base.putpixel((dx, dy), color)

    return base.filter(ImageFilter.GaussianBlur(3))


def soften_patch_edges(patch: Image.Image, feather: int = 8) -> Image.Image:
    width, height = patch.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    inner_box = (
        feather,
        feather,
        max(feather + 1, width - feather),
        max(feather + 1, height - feather),
    )
    draw.rectangle(inner_box, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(feather / 2))

    softened = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    softened.paste(patch, (0, 0), mask)
    return softened


def erase_text_region(canvas: Image.Image, region: TextRegion) -> None:
    patch = rebuild_background_strip(canvas, region.box)
    patch = soften_patch_edges(patch)
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

    shadow_x = x + region.shadow_offset[0]
    shadow_y = y + region.shadow_offset[1]
    draw.text((shadow_x, shadow_y), text, font=font, fill=region.shadow_fill)
    draw.text((x, y), text, font=font, fill=region.fill)


def draw_debug_boxes(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    for region in (ISSUE_REGION, RESULT_REGION):
        draw.rectangle(region.box, outline=(255, 0, 0, 255), width=2)
        draw.text((region.box[0], region.box[1] - 18), region.name, fill=(255, 0, 0, 255))


def render_template(
    image_path: Path,
    *,
    issue: str,
    numbers: str,
    font_path: Path,
    output_path: Path,
    debug_boxes: bool,
) -> Path:
    source = Image.open(image_path).convert("RGBA")
    canvas = source.copy()

    issue_text = ISSUE_REGION.text_template.format(issue=issue.strip())
    result_text = RESULT_REGION.text_template.format(numbers=numbers.strip())

    erase_text_region(canvas, ISSUE_REGION)
    erase_text_region(canvas, RESULT_REGION)
    draw_centered_text(canvas, issue_text, ISSUE_REGION, font_path)
    draw_centered_text(canvas, result_text, RESULT_REGION, font_path)

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


def build_output_path(image_path: Path, output_dir: Path, issue: str) -> Path:
    return output_dir / f"{image_path.stem}_issue_{issue}{image_path.suffix.lower()}"


def main() -> None:
    args = parse_args()

    if args.input:
        output_path = args.output or build_output_path(args.input, args.output_dir, args.issue)
        rendered_path = render_template(
            args.input,
            issue=args.issue,
            numbers=args.numbers,
            font_path=args.font,
            output_path=output_path,
            debug_boxes=args.debug_boxes,
        )
        print(f"Saved: {rendered_path}")
        return

    rendered_paths: list[Path] = []
    for image_path in list_images(args.input_dir):
        output_path = build_output_path(image_path, args.output_dir, args.issue)
        rendered_paths.append(
            render_template(
                image_path,
                issue=args.issue,
                numbers=args.numbers,
                font_path=args.font,
                output_path=output_path,
                debug_boxes=args.debug_boxes,
            )
        )

    print(f"Processed {len(rendered_paths)} images into: {args.output_dir}")


if __name__ == "__main__":
    main()
