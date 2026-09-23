"""twsyw 开奖标签页内联后的本地端到端回归。

背景：原先 `index.html` 用 `<iframe src="kai.html">` 承载开奖标签页，面板的期号由
站点适配器写进 **kai.html 的文档**（`knownDrawFrame.contentDocument`）。内联后标签页、
面板 iframe 与 `[data-current-issue]` 都在厂商页同一文档，适配器改为同文档查找。

本测试不依赖任何后端：用静态服务器提供 `frontend/public`，并用 Playwright 拦截
`/api/sites/twsyw/**` 返回固定数据，从而完整验证：
  1. 标签页、面板 iframe 与期号目标都内联在同一文档；
  2. 点击标签页切换面板 src，并直接调用站点适配器 `selectLottery`；
  3. 适配器把期号写回同文档的 `[data-current-issue]`；
  4. 预测资料按所选彩种渲染。

用法：
    python frontend/test/twsyw-inlined-draw-contract.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

PORT = 8877
ROOT = os.path.abspath("frontend/public")
PAGE = f"http://127.0.0.1:{PORT}/vendor/twsyw/index.html"


def prediction_payload(lottery_type: int) -> dict:
    rows = [
        {
            "issue": f"{lottery_type}{320 - index}",
            "prediction": {"tokens": ["鼠|01", "牛|02", "虎|03", "兔|04", "龙|05", "蛇|06", "马|07", "羊|08", "猴|09", "鸡|10", "狗|11", "猪|12"]},
            "result": {"isOpened": index > 0, "code": "01,02,03,04,05,06,07", "zodiac": "鼠,牛,虎,兔,龙,蛇,马", "isCorrect": index % 2 == 0},
        }
        for index in range(20)
    ]
    modules = [
        {"key": key, "rows": rows}
        for key in (
            "title_14", "juesha3xiao", "9xzt", "selected_22_codes", "shuangbo", "sixiao_sima",
            "daxiao", "title_66", "ma24", "danshuang4xiao", "siduanzhongte", "title_143",
            "title_5", "3tou", "title_279", "pt1xiao", "title_132", "qinqi",
        )
    ]
    return {"ok": True, "data": {"canonical_modules": modules}}


def wait_for_server(timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(PAGE, timeout=2):
                return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("static server did not start")


def main() -> int:
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", ROOT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    failures: list[str] = []
    try:
        wait_for_server()
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome")
            except Exception:
                browser = playwright.chromium.launch(channel="msedge")
            page = browser.new_page()
            page.on("pageerror", lambda error: failures.append(f"pageerror: {str(error)[:120]}"))

            def fulfill(route):
                match = re.search(r"lottery_type=(\d+)", route.request.url)
                lottery_type = int(match.group(1)) if match else 3
                route.fulfill(
                    json={"ok": True, "data": {"issue": f"{lottery_type}500"}}
                    if "/draw" in route.request.url
                    else prediction_payload(lottery_type)
                )

            page.route("**/api/sites/twsyw/**", fulfill)
            # 统计适配器被直接调用的次数（内联后不再走 postMessage）
            page.add_init_script(
                """
                window.__selectCalls = [];
                Object.defineProperty(window, 'TwsywSiteDataAdapter', {
                  configurable: true,
                  set(value) {
                    const original = value && value.selectLottery;
                    this.__adapter = value;
                    if (value && typeof original === 'function') {
                      value.selectLottery = function (type) { window.__selectCalls.push(Number(type)); return original.apply(this, arguments); };
                    }
                  },
                  get() { return this.__adapter; }
                });
                """
            )
            page.goto(PAGE, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)

            def check(label: str, condition: bool, detail: str = "") -> None:
                print(f"{'OK  ' if condition else 'FAIL'}  {label}{(' -> ' + detail) if detail else ''}")
                if not condition:
                    failures.append(f"{label} {detail}")

            frames = [frame for frame in page.frames if frame.url.endswith("/vendor/twsyw/index.html")]
            check("厂商页在同一文档内有开奖标签页", page.locator(".KJ-TabBox").count() == 1)
            check("没有 kai.html 中间帧", not any(frame.url.endswith("/twsyw/kai.html") for frame in page.frames))
            check("页面上不存在指向 kai.html 的活动 iframe", page.locator("iframe[src='kai.html']").count() == 0)
            check("期号目标在同文档", page.locator("[data-current-issue]").count() == 1)
            check("三个彩种标签", page.locator(".KJ-TabBox li[data-lottery-type]").count() == 3)

            panel_src = page.locator(".KJ-TabBox > div.cur .KJ-IFRAME").first.get_attribute("src") or ""
            check("默认加载台湾彩面板", "lottery_type=3" in panel_src, panel_src)
            check("首屏面板未裁切", page.locator(".KJ-TabBox > div.cur .KJ-IFRAME").first.evaluate("el => el.getBoundingClientRect().height") >= 190)

            for lottery_type in (2, 1, 3):
                page.locator(f".KJ-TabBox li[data-lottery-type='{lottery_type}']").click()
                page.wait_for_timeout(400)
                src = page.locator(".KJ-TabBox > div.cur .KJ-IFRAME").first.get_attribute("src") or ""
                check(f"点击 {lottery_type} 后面板切换", f"lottery_type={lottery_type}" in src, src)
                issue = page.locator("[data-current-issue]").inner_text().strip()
                check(f"期号写回同文档（{lottery_type}）", issue == f"{lottery_type}500", f"实际 {issue!r}")

            calls = page.evaluate("window.__selectCalls")
            check("适配器被直接调用（无 postMessage）", sorted(set(calls)) == [1, 2, 3], str(calls))
            check("预测行已渲染", page.locator("[data-prediction-content]").count() > 0, f"{page.locator('[data-prediction-content]').count()} 行")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    print(f"\n汇总：{'PASS' if not failures else 'FAIL'}（{len(failures)} 个问题）")
    for item in failures:
        print(f"   - {item}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
