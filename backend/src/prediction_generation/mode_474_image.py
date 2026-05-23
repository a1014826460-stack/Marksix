from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODE_474_ID = 474
MODE_474_TITLE_TEMPLATE = "{term}期四不像中特图"
MODE_474_IMAGE_LABEL = "上期开奖结果："
MODE_474_SIZE = (711, 744)
MODE_474_ANIMALS_ROOT = _PROJECT_ROOT / "data" / "Images" / "mode_474" / "animals"
MODE_474_FRAME_PATH = _PROJECT_ROOT / "data" / "Images" / "mode_474" / "frame.png"
MODE_474_OUTPUT_DIR = _PROJECT_ROOT / "data" / "Images" / "mode_474" / "prediction"
MODE_474_OUTPUT_NAME_TEMPLATE = "mode_474_type{lottery_type}_{year}{term:03d}_web{web_id}.jpg"
MODE_474_TITLE_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "HYXINGZHITIF-2.TTF"
MODE_474_NUMBER_FONT_PATH = _PROJECT_ROOT / "data" / "font" / "MSYH.TTC"
MODE_474_TITLE_FONT_SIZE = 52
MODE_474_RESULT_FONT_SIZE = 24
MODE_474_TITLE_CENTER_Y = 35
MODE_474_RESULT_TEXT_POINTS = ((384, 636), (287, 108))
MODE_474_PRIMARY_CUTOUT_BOX = (80, 75, 635, 660)
MODE_474_SECONDARY_CUTOUT_BOX = (90, 670, 610, 720)
MODE_474_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class Mode474RenderResult:
    output_path: Path
    relative_url: str
    title: str
    content: str
    source_record_id: str


def _make_seed_int(seed_text: str) -> int:
    return int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32)


def _list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    files = [
        path
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in MODE_474_SUPPORTED_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"No image files found in directory: {directory}")
    return files


def list_mode_474_source_images(source_root: Path = MODE_474_ANIMALS_ROOT) -> list[Path]:
    images: list[Path] = []
    for year_dir_name in ("2022", "2023"):
        images.extend(_list_images(source_root / year_dir_name))
    if not images:
        raise FileNotFoundError(f"No source images found under: {source_root}")
    return images


def ensure_size(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGBA")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


@lru_cache(maxsize=16)
def _load_rgba_image_cached(image_path: str, size: tuple[int, int] | None = None) -> Image.Image:
    image = Image.open(image_path).convert("RGBA")
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image.copy()


def resolve_font(font_path: Path, font_size: int) -> ImageFont.FreeTypeFont:
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(str(font_path), font_size)


@lru_cache(maxsize=16)
def resolve_font_cached(font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
    path = Path(font_path)
    if not path.exists():
        raise FileNotFoundError(f"Font file not found: {path}")
    return ImageFont.truetype(str(path), font_size)


def normalize_res_code(res_code: str) -> str:
    raw = str(res_code or "").strip()
    if re.fullmatch(r"\d{14}", raw):
        parts = [raw[index:index + 2] for index in range(0, 14, 2)]
    else:
        parts = re.findall(r"\d+", raw)

    if len(parts) != 7:
        raise ValueError("res_code must contain exactly 7 numbers.")

    return ",".join(part.zfill(2) for part in parts)


def build_mode_474_title(term: int | str) -> str:
    return MODE_474_TITLE_TEMPLATE.format(term=str(term))


def text_size(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int]:
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
    bbox = probe.textbbox((0, 0), text, font=font)
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])
    return width, height


def draw_artistic_title(
    canvas: Image.Image,
    text: str,
    center_y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    width, height = text_size(text, font)
    x = (canvas.width - width) // 2
    y = int(center_y - height / 2)

    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).text((x, y), text, font=font, fill=255)

    shadow = mask.filter(ImageFilter.GaussianBlur(4))
    shadow_layer = Image.new("RGBA", canvas.size, (60, 10, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda value: min(160, int(value * 0.7))))
    shadow_layer = ImageChops.offset(shadow_layer, 3, 4)
    canvas.alpha_composite(shadow_layer)

    glow = mask.filter(ImageFilter.GaussianBlur(10))
    glow_layer = Image.new("RGBA", canvas.size, (255, 171, 48, 0))
    glow_layer.putalpha(glow.point(lambda value: min(165, int(value * 0.65))))
    canvas.alpha_composite(glow_layer)

    title_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    title_draw = ImageDraw.Draw(title_layer)
    color_top = (255, 248, 196, 255)
    color_mid = (255, 205, 82, 255)
    color_bottom = (194, 51, 18, 255)
    start_y = max(0, y)
    end_y = min(canvas.height, y + height)
    gradient_height = max(1, end_y - start_y)

    for row in range(start_y, end_y):
        progress = (row - start_y) / max(1, gradient_height - 1)
        if progress < 0.5:
            local = progress / 0.5
            red = int(color_top[0] + (color_mid[0] - color_top[0]) * local)
            green = int(color_top[1] + (color_mid[1] - color_top[1]) * local)
            blue = int(color_top[2] + (color_mid[2] - color_top[2]) * local)
        else:
            local = (progress - 0.5) / 0.5
            red = int(color_mid[0] + (color_bottom[0] - color_mid[0]) * local)
            green = int(color_mid[1] + (color_bottom[1] - color_mid[1]) * local)
            blue = int(color_mid[2] + (color_bottom[2] - color_mid[2]) * local)
        title_draw.line([(x, row), (x + width, row)], fill=(red, green, blue, 255), width=1)

    title_layer.putalpha(mask)
    canvas.alpha_composite(title_layer)

    highlight_cut = Image.new("L", canvas.size, 0)
    highlight_draw = ImageDraw.Draw(highlight_cut)
    highlight_limit = y + max(1, height // 3)
    for row in range(max(0, y), min(canvas.height, highlight_limit)):
        alpha = int(180 * (1 - (row - y) / max(1, highlight_limit - y)))
        highlight_draw.line([(x, row), (x + width, row)], fill=alpha, width=1)
    highlight_mask = ImageChops.multiply(mask, highlight_cut)
    highlight_layer = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    highlight_layer.putalpha(highlight_mask)
    canvas.alpha_composite(highlight_layer)


def draw_result_text(
    canvas: Image.Image,
    res_code: str,
    number_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    rng: random.Random,
) -> None:
    point_x, point_y = rng.choice(MODE_474_RESULT_TEXT_POINTS)
    draw = ImageDraw.Draw(canvas)
    label_width, label_height = text_size(MODE_474_IMAGE_LABEL, number_font)
    code_width, code_height = text_size(res_code, number_font)
    total_width = label_width + code_width
    total_height = max(label_height, code_height)
    x = int(point_x - total_width / 2)
    y = int(point_y - total_height / 2)

    draw.text((x + 2, y + 2), MODE_474_IMAGE_LABEL, font=number_font, fill=(0, 0, 0, 90))
    draw.text((x, y), MODE_474_IMAGE_LABEL, font=number_font, fill=(204, 34, 20))
    code_x = x + label_width
    draw.text((code_x + 2, y + 2), res_code, font=number_font, fill=(0, 0, 0, 90))
    draw.text((code_x, y), res_code, font=number_font, fill=(204, 34, 20))


def build_two_region_cutout(
    source_image: Image.Image,
    canvas_size: tuple[int, int] = MODE_474_SIZE,
    primary_box: tuple[int, int, int, int] = MODE_474_PRIMARY_CUTOUT_BOX,
    secondary_box: tuple[int, int, int, int] = MODE_474_SECONDARY_CUTOUT_BOX,
) -> Image.Image:
    source = ensure_size(source_image, canvas_size)
    result = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    result.alpha_composite(source.crop(primary_box), (primary_box[0], primary_box[1]))
    result.alpha_composite(source.crop(secondary_box), (secondary_box[0], secondary_box[1]))
    return result


def choose_mode_474_source_image(
    *,
    year: int,
    term: int,
    site_web_id: int,
    source_root: Path = MODE_474_ANIMALS_ROOT,
) -> Path:
    seed = _make_seed_int(f"mode474:{int(year)}:{int(term)}:{int(site_web_id)}")
    rng = random.Random(seed)
    images = list_mode_474_source_images(source_root)
    return rng.choice(images)


def render_mode_474_prediction_image(
    *,
    res_code: str,
    lottery_type: int,
    year: int,
    term: int,
    site_web_id: int,
    source_root: Path = MODE_474_ANIMALS_ROOT,
    frame_path: Path = MODE_474_FRAME_PATH,
    output_dir: Path = MODE_474_OUTPUT_DIR,
    title_font_path: Path = MODE_474_TITLE_FONT_PATH,
    number_font_path: Path = MODE_474_NUMBER_FONT_PATH,
    title_font_size: int = MODE_474_TITLE_FONT_SIZE,
    result_font_size: int = MODE_474_RESULT_FONT_SIZE,
) -> Mode474RenderResult:
    normalized_res_code = normalize_res_code(res_code)
    source_image_path = choose_mode_474_source_image(
        year=year,
        term=term,
        site_web_id=site_web_id,
        source_root=source_root,
    )

    frame = _load_rgba_image_cached(str(frame_path), MODE_474_SIZE)
    base = frame.copy()
    source_image = _load_rgba_image_cached(str(source_image_path))
    cutout = build_two_region_cutout(source_image)
    base.alpha_composite(cutout, (0, 0))

    title_font = resolve_font_cached(str(title_font_path), title_font_size)
    number_font = resolve_font_cached(str(number_font_path), result_font_size)
    rng = random.Random(_make_seed_int(f"mode474:text:{int(year)}:{int(term)}:{int(site_web_id)}"))
    title_text = build_mode_474_title(term)

    draw_artistic_title(base, title_text, MODE_474_TITLE_CENTER_Y, title_font)
    draw_result_text(base, normalized_res_code, number_font, rng)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = MODE_474_OUTPUT_NAME_TEMPLATE.format(
        lottery_type=int(lottery_type),
        year=int(year),
        term=int(term),
        web_id=int(site_web_id),
    )
    output_path = output_dir / output_name
    base.convert("RGB").save(output_path, format="JPEG", quality=92)

    relative_path = output_path.relative_to(_PROJECT_ROOT).as_posix()
    return Mode474RenderResult(
        output_path=output_path,
        relative_url=f"/{relative_path}",
        title=title_text,
        content="",
        source_record_id=source_image_path.stem,
    )
