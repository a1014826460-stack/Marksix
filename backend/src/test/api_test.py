"""
Qwen 换脸视频生成脚本 (wan2.2-animate-mix)

用法:
    python backend/src/test/api_test.py

前置条件:
    - ffmpeg 已安装并在 PATH 中
    - backend/.env.local 中已配置 DASHSCOPE_API_KEY
    - temp/test_image.png（人脸图片）和 temp/test_vedio.mp4（驱动视频）已就绪

流程:
    1. 检查/裁剪视频时长 <= 29s
    2. 上传图片和视频到 DashScope 获取临时 URL
    3. 提交 wan2.2-animate-mix 异步换脸任务
    4. 每 30s 轮询任务状态直到完成
    5. 下载结果视频到 temp/output_wan_animate.mp4
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

import requests

# ---- 路径配置 ----
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = Path(__file__).resolve().parent / "temp"

INPUT_IMAGE = TEMP_DIR / "test_image.png"
INPUT_VIDEO = TEMP_DIR / "test_vedio.mp4"
TRIMMED_VIDEO = TEMP_DIR / "test_vedio_trimmed.mp4"
OUTPUT_VIDEO = TEMP_DIR / "output_wan_animate.mp4"

MAX_VIDEO_DURATION = 29  # 秒

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/api/v1"
DASHSCOPE_GEN = f"{DASHSCOPE_BASE}/services/aigc/image2video/video-synthesis"
DASHSCOPE_UPLOAD = f"{DASHSCOPE_BASE}/uploads"

POLL_INTERVAL = 30  # 秒


def load_api_key() -> str:
    env_file = PROJECT_DIR / ".env.local"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        print("错误：未找到 DASHSCOPE_API_KEY，请检查 backend/.env.local")
        sys.exit(1)
    return key


def get_video_duration(path: Path) -> float:
    """用 ffprobe 获取视频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败：{result.stderr.strip()}")
    return float(result.stdout.strip())


def trim_video(input_path: Path, output_path: Path, max_duration: int) -> Path:
    """若视频超过 max_duration 秒，裁剪前 max_duration 秒并返回裁剪后路径"""
    duration = get_video_duration(input_path)
    print(f"原始视频时长：{duration:.1f}s")
    if duration <= max_duration:
        print("视频时长符合要求，无需裁剪")
        return input_path

    print(f"视频超过 {max_duration}s，裁剪前 {max_duration}s...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-t", str(max_duration),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 裁剪失败：{result.stderr.strip()}")
    print(f"裁剪完成：{output_path}")
    return output_path


def upload_file(api_key: str, file_path: Path, resource_type: str) -> str:
    """上传文件到 DashScope，返回可使用的外部 URL"""
    ext = file_path.suffix.lstrip(".")
    content_type_map = {
        "image": {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"},
        "video": {"mp4": "video/mp4", "mov": "video/quicktime"},
    }
    content_type = content_type_map[resource_type].get(ext, f"{resource_type}/{ext}")

    # 1. 获取上传 URL
    print(f"正在获取 {file_path.name} 的上传地址...")
    resp = requests.post(
        DASHSCOPE_UPLOAD,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "wan2.2-animate-mix",
            "action": "getHttpsUrl",
            "resource_type": resource_type,
            "content_type": content_type,
        },
        timeout=30,
    )
    resp.raise_for_status()
    upload_info = resp.json()
    upload_url = upload_info["output"]["upload_url"]
    file_url = upload_info["output"]["url"]

    # 2. PUT 文件
    print(f"正在上传 {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.1f}MB)...")
    with open(file_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f, headers={"Content-Type": content_type}, timeout=300)
        put_resp.raise_for_status()

    print(f"上传完成：{file_url}")
    return file_url


def submit_task(api_key: str, image_url: str, video_url: str) -> str:
    """提交异步换脸任务，返回 task_id"""
    payload = {
        "model": "wan2.2-animate-mix",
        "input": {
            "image_url": image_url,
            "video_url": video_url,
        },
        "parameters": {
            "mode": "wan-std",
        },
    }
    print("正在提交换脸任务...")
    resp = requests.post(
        DASHSCOPE_GEN,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    task_id = result["output"]["task_id"]
    print(f"任务已提交，task_id = {task_id}")
    return task_id


def poll_task(api_key: str, task_id: str) -> dict:
    """轮询任务状态直到结束"""
    url = f"{DASHSCOPE_GEN}/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    attempt = 0

    while True:
        attempt += 1
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result["output"]["task_status"]

        print(f"[轮询 #{attempt}] 状态：{status}")

        if status == "SUCCEEDED":
            print("任务成功完成！")
            return result
        if status == "FAILED":
            error_msg = result.get("output", {}).get("message", result.get("message", "未知错误"))
            raise RuntimeError(f"任务失败：{error_msg}")
        if status in ("CANCELED", "UNKNOWN"):
            raise RuntimeError(f"任务异常终止：{status}")

        time.sleep(POLL_INTERVAL)


def download_result(video_url: str, output_path: Path):
    """下载生成的视频"""
    print(f"正在下载结果视频到 {output_path}...")
    resp = requests.get(video_url, timeout=300, stream=True)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"下载完成：{output_path} ({size_mb:.1f}MB)")


def main():
    print("=" * 60)
    print("Qwen 换脸视频生成 (wan2.2-animate-mix)")
    print("=" * 60)

    # 0. 加载配置
    api_key = load_api_key()
    print(f"API Key: {api_key[:12]}...{api_key[-4:]}")

    # 1. 检查输入文件
    for f in [INPUT_IMAGE, INPUT_VIDEO]:
        if not f.exists():
            print(f"错误：输入文件不存在：{f}")
            sys.exit(1)
    print(f"输入图片：{INPUT_IMAGE}")
    print(f"输入视频：{INPUT_VIDEO}")

    # 2. 裁剪视频（如需要）
    video_for_upload = trim_video(INPUT_VIDEO, TRIMMED_VIDEO, MAX_VIDEO_DURATION)

    # 3. 上传文件
    image_url = upload_file(api_key, INPUT_IMAGE, "image")
    video_url = upload_file(api_key, video_for_upload, "video")

    # 4. 提交任务
    task_id = submit_task(api_key, image_url, video_url)

    # 5. 轮询结果
    try:
        result = poll_task(api_key, task_id)
    except KeyboardInterrupt:
        print(f"\n轮询中断。可用以下 task_id 手动查询：{task_id}")
        sys.exit(1)

    # 6. 下载结果
    output_video_url = result["output"]["video_url"]
    download_result(output_video_url, OUTPUT_VIDEO)

    print("=" * 60)
    print(f"全部完成！输出文件：{OUTPUT_VIDEO}")
    print("=" * 60)


if __name__ == "__main__":
    main()
