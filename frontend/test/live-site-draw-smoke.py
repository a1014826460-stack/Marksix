"""十站开奖模块真实浏览器实测（只读，访问公网生产站点）。

用途：
1. 为"图片压缩 / 面板并发取数+缓存 / nginx 边缘缓存 / 预测快照"这套改动提供端到端证据；
2. 抓出站点在真实浏览器里的结构或脚本回归（例如面板未渲染、JS 报错）。

用法：
    python frontend/test/live-site-draw-smoke.py                 # 全部十站
    python frontend/test/live-site-draw-smoke.py twssz twsyw     # 指定站点
"""

from __future__ import annotations

import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

SITES = {
    "tw8800": ("www.tw8800.com", "/"),
    "twcaibawang": ("www.twcaibawang.com", "/"),
    "twsaimahui": ("www.twsaimahui.com", "/"),
    "twtongtian": ("www.twtongtian.com", "/"),
    "twcf888": ("www.twcf888.com", "/"),
    "twssz": ("www.twssz.com", "/"),
    "twbst528": ("www.twbst528.com", "/"),
    "twjsz666": ("www.twjsz666.com", "/"),
    "twwanli": ("www.twwanli.com", "/"),
    "twsyw": ("www.twsyw.com", "/"),
}

PANEL_PATH = "/vendor/shengshi8800/kj/local.html"


def inspect(page, domain: str, path: str) -> dict:
    url = f"https://{domain}{path}"
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)[:120]))
    started = time.monotonic()
    record: dict = {"site": domain, "url": url}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:  # noqa: BLE001
        record.update({"ok": False, "error": type(exc).__name__, "detail": str(exc)[:120]})
        return record
    record["domcontentloaded_ms"] = int((time.monotonic() - started) * 1000)

    # 等待开奖面板出现（同源 iframe，允许 20 秒；面板会先读倒计时再取号码）
    deadline = time.monotonic() + 20
    panel = None
    while time.monotonic() < deadline:
        panel = next((frame for frame in page.frames if PANEL_PATH in (frame.url or "")), None)
        if panel:
            break
        page.wait_for_timeout(250)
    record["panel_frame"] = bool(panel)
    if not panel:
        record["ok"] = False
        record["frames"] = [frame.url[:80] for frame in page.frames][:6]
        return record

    panel_ms = int((time.monotonic() - started) * 1000)
    record["panel_frame_ms"] = panel_ms
    try:
        panel.wait_for_selector("#refreshButton", timeout=10000)
    except Exception:  # noqa: BLE001
        pass

    # 关键指标：号码真正出现的时间（面板要等 /api/next-draw-deadline 与 /api/latest-draw）
    balls_visible_ms = None
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            first = panel.query_selector("#m1")
            value = (first.inner_text() if first else "").strip()
        except Exception:  # noqa: BLE001
            value = ""
        if value and value != "--":
            balls_visible_ms = int((time.monotonic() - started) * 1000)
            break
        page.wait_for_timeout(100)
    record["balls_visible_ms"] = balls_visible_ms

    def text(selector: str) -> str:
        try:
            node = panel.query_selector(selector)
            return re.sub(r"\s+", " ", (node.inner_text() if node else "") or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    balls = [text(f"#{name}") for name in ("m1", "m2", "m3", "m4", "m5", "m6", "s1")]
    record.update(
        {
            "issue": text("#q") or text("#currentIssue"),
            "balls": balls,
            "balls_rendered": sum(1 for value in balls if value not in ("", "--")),
            "countdown": text("#countdownBadge"),
            "refresh_state": text("#refreshState"),
            "page_errors": len(errors),
            "page_error_samples": errors[:3],
        }
    )

    # 传输体积（performance entries）
    try:
        totals = page.evaluate(
            """() => {
                const rows = performance.getEntriesByType('resource') || [];
                let images = 0, scripts = 0, documents = 0;
                let imageCount = 0, scriptCount = 0;
                for (const row of rows) {
                    const size = row.transferSize || 0;
                    if (row.initiatorType === 'img') { images += size; imageCount += 1; }
                    else if (row.initiatorType === 'script') { scripts += size; scriptCount += 1; }
                    else if (row.initiatorType === 'iframe' || row.initiatorType === 'navigation') { documents += size; }
                }
                return { images, scripts, documents, imageCount, scriptCount };
            }"""
        )
        record["transfer"] = {key: (round(value / 1024, 1) if key in ("images", "scripts", "documents") else value) for key, value in totals.items()}
    except Exception:  # noqa: BLE001
        record["transfer"] = None
    record["ok"] = bool(record.get("balls_visible_ms")) or bool(record.get("countdown"))
    return record


def main() -> int:
    wanted = sys.argv[1:] or list(SITES)
    results = []
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome")
        except Exception:
            browser = playwright.chromium.launch(channel="msedge")
        context = browser.new_context(ignore_https_errors=True)
        for key in wanted:
            if key not in SITES:
                print(f"unknown site: {key}", file=sys.stderr)
                continue
            domain, path = SITES[key]
            page = context.new_page()
            try:
                results.append(inspect(page, domain, path))
            finally:
                page.close()
        browser.close()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
