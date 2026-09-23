"""twsaimahui 首页加载回归：统计脚本数、控制台错误、DOM 结构摘要。

用法：
    python frontend/test/twsaimahui-bundle-smoke.py <label>
先在合并前跑一次，合并后再跑一次，比较 JSON 摘要。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

PORT = 8899
ROOT = os.path.abspath("frontend/public")
PAGE = f"http://127.0.0.1:{PORT}/vendor/twsaimahui/index.html"


def wait_for_server(timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/vendor/twsaimahui/index.html", timeout=2):
                return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("static server did not start")


def digest(label: str) -> dict:
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", ROOT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server()
        with sync_playwright() as playwright:
            # 本机未安装 Playwright 自带 chromium 时用系统 Chrome（channel="chrome"）。
            try:
                browser = playwright.chromium.launch(channel="chrome")
            except Exception:
                browser = playwright.chromium.launch(channel="msedge")
            page = browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)[:200]))
            console_errors: list[str] = []
            page.on(
                "console",
                lambda message: console_errors.append(message.text[:200]) if message.type == "error" else None,
            )
            failed: list[str] = []
            page.on("requestfailed", lambda request: failed.append(request.url.split("/")[-1][:60]))
            for status in (404, 500):
                page.on(
                    "response",
                    lambda response: failed.append(f"{response.status}:{response.url.split('/')[-1][:50]}")
                    if response.status == status
                    else None,
                )
            page.goto(PAGE, wait_until="load", timeout=60000)
            page.wait_for_timeout(3000)
            import re

            text = re.sub(r"\s+", " ", page.evaluate("document.body.innerText")).strip()
            summary = {
                "label": label,
                "script_tags": page.evaluate("document.querySelectorAll('script[src]').length"),
                "module_script_tags": page.evaluate(
                    "Array.from(document.querySelectorAll('script[src]')).filter(s => /static\\/js\\/0\\d{2}/.test(s.getAttribute('src'))).length"
                ),
                "bundle_script_tags": page.evaluate(
                    "Array.from(document.querySelectorAll('script[src]')).filter(s => /bundle-/.test(s.getAttribute('src'))).length"
                ),
                "bundle_srcs": page.evaluate(
                    "Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src')).filter(s => /bundle-/.test(s))"
                ),
                "failed_requests": sorted(set(failed))[:20],
                "elements": page.evaluate("document.querySelectorAll('*').length"),
                "divs": page.evaluate("document.querySelectorAll('div').length"),
                "tables": page.evaluate("document.querySelectorAll('table').length"),
                "render_empty_boxes": page.evaluate(
                    "Array.from(document.querySelectorAll('*')).filter(n => (n.className || '').toString().includes('empty')).length"
                ),
                "frames": len(page.frames),
                "kj_tabbox": page.locator(".KJ-TabBox").count(),
                "kj_iframes": page.locator(".KJ-IFRAME").count(),
                "page_errors": len(errors),
                "page_error_samples": errors[:5],
                "console_errors": len(console_errors),
                "body_text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                "body_text_len": len(text),
            }
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    return summary


if __name__ == "__main__":
    print(json.dumps(digest(sys.argv[1] if len(sys.argv) > 1 else "run"), ensure_ascii=False, indent=2))
