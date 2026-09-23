#!/usr/bin/env python3
"""把厂商站点里仍然过大的图片转成 WebP，并同步改写所有引用。

为什么需要这一步：动画 GIF 换 GIF 容器几乎压不动（41 张 >250KB 里绝大多数是动图），
而 GIF 的替代品只有 WebP 能把 1 MB 级别的横幅压到几百 KB 以内。策略：

- 动画：ffmpeg(libwebp_anim) → 宽度 <= 800、帧率 <= 8、质量 50（不够小再降到 40/6fps），
  取最小结果；要求至少省 50% 才值得改格式改名。
- 静态：Pillow WebP 质量 80，宽度 <= 1280；要求至少省 45%。
- 新文件名 = 原名去扩展名 + `.webp`（同目录内按内容去重，避免同一张图存两份）。
- 引用改写：仓库内所有文本文件里出现的旧文件名（含扩展名）逐字节替换为新文件名，
  然后删除旧文件；最后校验全仓再无旧文件名残留。

用法：
    python scripts/convert-vendor-images-to-webp.py --threshold-kb 250            # dry-run
    python scripts/convert-vendor-images-to-webp.py --threshold-kb 250 --apply
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
TEXT_EXTENSIONS = {
    ".html",
    ".htm",
    ".js",
    ".mjs",
    ".cjs",
    ".css",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".xml",
    ".svg",
    ".py",
}
SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".deploy-backups"}
ANIMATED_MAX_WIDTH = 800
ANIMATED_MAX_FPS = 8
ANIMATED_QUALITY_LADDER = ((50, 8), (40, 6))
# 允许转换的最大比例（0.65 = 至少省 35%），否则不值得改格式改名。
ANIMATED_MAX_RATIO = 0.65
STATIC_MAX_WIDTH = 1280
STATIC_QUALITY = 80
STATIC_MAX_RATIO = 0.70


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def encode_animated(source: pathlib.Path, ffmpeg: str, quality: int, fps: int) -> bytes | None:
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "out.webp"
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"fps={fps},scale='min({ANIMATED_MAX_WIDTH},iw)':-1:flags=lanczos",
            "-c:v",
            "libwebp_anim",
            "-lossless",
            "0",
            "-q:v",
            str(quality),
            "-compression_level",
            "6",
            "-loop",
            "0",
            "-an",
            str(target),
        ]
        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0 or not target.exists():
            print(f"    ffmpeg failed: {result.stderr.decode('utf-8', 'replace')[:200]}", file=sys.stderr)
            return None
        return target.read_bytes()


def encode_static(source: pathlib.Path) -> bytes | None:
    with Image.open(source) as image:
        frame = image.convert("RGBA") if "A" in image.mode or image.mode == "P" else image.convert("RGB")
        if frame.width > STATIC_MAX_WIDTH:
            ratio = STATIC_MAX_WIDTH / frame.width
            frame = frame.resize((STATIC_MAX_WIDTH, max(1, round(frame.height * ratio))), Image.LANCZOS)
        buffer = io.BytesIO()
        frame.save(buffer, "WEBP", quality=STATIC_QUALITY, method=6)
        return buffer.getvalue()


def iter_text_files(root: pathlib.Path) -> list[pathlib.Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="frontend/public/vendor")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--threshold-kb", type=int, default=250)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    image_root = pathlib.Path(args.root)
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        print("ffmpeg not found: animated conversions will be skipped", file=sys.stderr)

    targets = [
        path
        for path in sorted(image_root.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and path.suffix.lower() != ".webp"
        and path.stat().st_size > args.threshold_kb * 1024
    ]
    print(f"targets: {len(targets)} files over {args.threshold_kb} KB")

    conversions: list[tuple[pathlib.Path, pathlib.Path, str, bytes]] = []
    skipped: list[dict] = []

    for path in targets:
        original = path.stat().st_size
        try:
            with Image.open(path) as image:
                animated = getattr(image, "n_frames", 1) > 1
        except Exception as exc:  # noqa: BLE001
            skipped.append({"path": str(path), "reason": f"unreadable: {exc}"})
            continue

        candidate: bytes | None = None
        label = ""
        if animated:
            if not ffmpeg:
                skipped.append({"path": str(path), "reason": "animated: ffmpeg unavailable"})
                continue
            for quality, fps in ANIMATED_QUALITY_LADDER:
                encoded = encode_animated(path, ffmpeg, quality, fps)
                if not encoded:
                    continue
                if candidate is None or len(encoded) < len(candidate):
                    candidate, label = encoded, f"animated-webp-q{quality}-fps{fps}-w{ANIMATED_MAX_WIDTH}"
                    if len(encoded) <= 300 * 1024:
                        break
            maximum = original * ANIMATED_MAX_RATIO
        else:
            candidate = encode_static(path)
            label = f"static-webp-q{STATIC_QUALITY}-w{STATIC_MAX_WIDTH}"
            maximum = original * STATIC_MAX_RATIO

        if candidate is None or len(candidate) > maximum:
            skipped.append(
                {
                    "path": str(path),
                    "reason": "no sufficient saving",
                    "before": original,
                    "best": len(candidate) if candidate else None,
                    "mode": label,
                }
            )
            continue

        digest = hashlib.sha256(candidate).hexdigest()
        reused: pathlib.Path | None = None
        for existing in path.parent.glob("*.webp"):
            if hashlib.sha256(existing.read_bytes()).hexdigest() == digest:
                reused = existing
                break
        target = reused or path.with_suffix(".webp")
        conversions.append((path, target, label, candidate))
        print(
            f"  {path.name}: {original/1024:.0f} KB -> {len(candidate)/1024:.0f} KB ({label})"
            + (f" [reuse {target.name}]" if reused else "")
        )

    if not conversions:
        print("nothing to convert")
        return 0

    replacements = {old.name: new.name for old, new, _label, _bytes in conversions}
    print(f"reference rewrites needed: {len(replacements)} distinct file names")

    if not args.apply:
        print("dry-run: nothing written")
        return 0

    # 1) 写出 WebP（直接用评估阶段选出的最优字节，避免二次编码结果不一致）
    for old, new, _label, encoded in conversions:
        same_stem = new.parent == old.parent and new.stem == old.stem
        if same_stem or not new.exists():
            new.write_bytes(encoded)

    # 2) 逐字节改写引用
    touched = 0
    for text_path in iter_text_files(repo_root):
        data = text_path.read_bytes()
        updated = data
        for old_name, new_name in replacements.items():
            if old_name.encode() in updated:
                updated = updated.replace(old_name.encode(), new_name.encode())
        if updated != data:
            text_path.write_bytes(updated)
            touched += 1
    print(f"text files rewritten: {touched}")

    # 3) 删除旧文件并校验
    for old, _new, _label, _size in conversions:
        old.unlink()

    leftovers = []
    for text_path in iter_text_files(repo_root):
        data = text_path.read_bytes()
        for old_name in replacements:
            if old_name.encode() in data:
                leftovers.append((str(text_path), old_name))
    if leftovers:
        for item in leftovers[:20]:
            print("LEFTOVER", item, file=sys.stderr)
        raise SystemExit(f"{len(leftovers)} stale references remain")

    report = [
        {"from": str(old), "to": str(new), "mode": label, "after": len(encoded)}
        for old, new, label, encoded in conversions
    ]
    if args.report:
        pathlib.Path(args.report).write_text(
            json.dumps({"conversions": report, "skipped": skipped}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"converted {len(conversions)} files; no stale references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
