"""
视频分段脚本：将视频按指定时长切分为多个片段

用法:
    python backend/src/test/api_test.py

输入: temp/test_vedio.mp4
输出: temp/segments/test_vedio_001.mp4, test_vedio_002.mp4, ...
每段时长: <15s
"""

import subprocess
import sys
from pathlib import Path

TEMP_DIR = Path(__file__).resolve().parent / "temp"
INPUT_VIDEO = TEMP_DIR / "test_vedio.mp4"
OUTPUT_DIR = TEMP_DIR / "segments"
SEGMENT_DURATION = 15  # 秒


def get_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败：{result.stderr.strip()}")
    return float(result.stdout.strip())


def main():
    if not INPUT_VIDEO.exists():
        print(f"错误：视频文件不存在：{INPUT_VIDEO}")
        sys.exit(1)

    duration = get_duration(INPUT_VIDEO)
    print(f"视频时长：{duration:.1f}s")

    segment_count = int(duration // SEGMENT_DURATION) + (1 if duration % SEGMENT_DURATION > 0 else 0)
    print(f"切分为 {segment_count} 段（每段 <= {SEGMENT_DURATION}s）")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = INPUT_VIDEO.stem
    output_pattern = str(OUTPUT_DIR / f"{stem}_%03d.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(INPUT_VIDEO),
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(SEGMENT_DURATION),
        "-reset_timestamps", "1",
        output_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 切分失败：{result.stderr.strip()}")

    segments = sorted(OUTPUT_DIR.glob(f"{stem}_*.mp4"))
    print(f"切分完成，共 {len(segments)} 个文件：")
    for seg in segments:
        dur = get_duration(seg)
        print(f"  {seg.name}  {dur:.1f}s  ({seg.stat().st_size / 1024 / 1024:.1f}MB)")


if __name__ == "__main__":
    main()
