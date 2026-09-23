#!/usr/bin/env python3
"""压缩厂商站点图片（尽量小，且不改文件名/不改容器格式）。

策略（按图片实际格式判断，忽略扩展名）：
- 静态 JPEG：质量 80、渐进式、去元数据；宽度 > 1280 时等比缩到 1280。
- 静态 PNG：无透明通道时量化到 256 色（与仅 optimize 取更小者）；有透明通道仅 optimize。
- 静态 GIF：量化到 64 色。
- 动画 GIF：量化到 64 色；帧数 >= 24 时尝试抽帧（隔帧保留、时长不变），取更小且
  视觉时长不变的结果。

只有当新体积 ≤ 原体积的 90% 时才写回，否则保留原文件；输出 JSON 报告便于核对。

用法：
    python scripts/compress-vendor-images.py --report report.json      # dry-run
    python scripts/compress-vendor-images.py --apply --report report.json
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys

from PIL import Image, ImageSequence

EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_WIDTH = 1280
MIN_SAVING_RATIO = 0.90  # 至少省 10% 才写回
JPEG_QUALITY = 80
GIF_COLORS = 64
FRAME_SKIP_MIN_FRAMES = 24


def _downscale(image: Image.Image) -> Image.Image:
    if image.width <= MAX_WIDTH:
        return image
    ratio = MAX_WIDTH / image.width
    return image.resize((MAX_WIDTH, max(1, round(image.height * ratio))), Image.LANCZOS)


def encode_static(image: Image.Image, actual_format: str) -> tuple[bytes | None, str] | None:
    scaled = _downscale(image)
    buffer = io.BytesIO()
    if actual_format == "JPEG":
        scaled.convert("RGB").save(buffer, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        return buffer.getvalue(), "jpeg-q80-progressive"
    if actual_format == "PNG":
        if "A" in scaled.mode or (scaled.mode == "P" and "transparency" in scaled.info):
            scaled.save(buffer, "PNG", optimize=True)
            return buffer.getvalue(), "png-optimize-alpha"
        best: tuple[bytes, str] | None = None
        plain = io.BytesIO()
        scaled.convert("RGB").save(plain, "PNG", optimize=True)
        best = (plain.getvalue(), "png-optimize")
        quantized = io.BytesIO()
        scaled.convert("RGB").quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(
            quantized, "PNG", optimize=True
        )
        if quantized.tell() < len(best[0]):
            best = (quantized.getvalue(), "png-256color")
        return best
    if actual_format == "WEBP":
        scaled.convert("RGBA" if "A" in scaled.mode else "RGB").save(buffer, "WEBP", quality=JPEG_QUALITY, method=6)
        return buffer.getvalue(), "webp-q80"
    if actual_format == "GIF":
        frame = scaled.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=GIF_COLORS)
        frame.save(buffer, "GIF", optimize=True)
        return buffer.getvalue(), "gif-static-64color"
    return None


def encode_animated_gif(image: Image.Image, skip: int) -> tuple[bytes, str] | None:
    frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(image)]
    if not frames:
        return None
    duration = image.info.get("duration", 100)
    if skip > 1:
        frames = frames[::skip]
    palette_frames = [
        frame.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=GIF_COLORS) for frame in frames
    ]
    buffer = io.BytesIO()
    palette_frames[0].save(
        buffer,
        "GIF",
        save_all=True,
        append_images=palette_frames[1:],
        optimize=True,
        loop=image.info.get("loop", 0),
        duration=duration * skip,
        disposal=2,
    )
    label = "gif-anim-64color" + (f"-skip{skip}" if skip > 1 else "")
    return buffer.getvalue(), label


def candidates(path: pathlib.Path) -> list[tuple[bytes, str]]:
    with Image.open(path) as image:
        actual = image.format or ""
        frames = getattr(image, "n_frames", 1)
        if frames > 1 and actual == "GIF":
            results = []
            for skip in (1, 2):
                if skip > 1 and frames < FRAME_SKIP_MIN_FRAMES:
                    continue
                encoded = encode_animated_gif(image, skip)
                if encoded:
                    results.append(encoded)
            return results
        encoded = encode_static(image, actual)
        return [encoded] if encoded else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="frontend/public/vendor")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default="")
    parser.add_argument("--min-kb", type=int, default=20, help="只处理大于该体积的文件")
    args = parser.parse_args()

    root = pathlib.Path(args.root)
    report = []
    before_total = after_total = 0
    changed = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        original = path.stat().st_size
        if original < args.min_kb * 1024:
            continue
        before_total += original
        try:
            options = candidates(path)
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {path}: {exc}", file=sys.stderr)
            after_total += original
            continue
        if not options:
            after_total += original
            continue
        best_bytes, best_label = min(options, key=lambda item: len(item[0]))
        entry = {
            "path": str(path).replace("\\", "/"),
            "before": original,
            "after": len(best_bytes),
            "mode": best_label,
            "applied": False,
        }
        if len(best_bytes) <= original * MIN_SAVING_RATIO:
            entry["applied"] = True
            changed += 1
            after_total += len(best_bytes)
            if args.apply:
                path.write_bytes(best_bytes)
        else:
            after_total += original
        report.append(entry)

    print(f"files considered: {len(report)}; written: {changed if args.apply else 0} (dry-run counts {changed})")
    print(f"total {before_total/1024/1024:.2f} MB -> {after_total/1024/1024:.2f} MB")
    worst = sorted(report, key=lambda item: -item["after"])[:15]
    print("largest results after compression:")
    for item in worst:
        print(f"  {item['after']/1024:8.0f} KB (was {item['before']/1024:8.0f} KB, {item['mode']}) {item['path']}")
    if args.report:
        pathlib.Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report written: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
