"""twjinniu (twtongtian) 友情链接板块宽度契约 —— Playwright 真渲染。

背景
----
友情链接由共享组件 ``frontend/public/vendor/_shared/managed-site-links.js`` 渲染。
该组件的 shadow 样式只有 ``:host { display: block; }``，没有任何宽度约束，
因此**宽度完全由站点页面上的挂载位置决定**：

* ``twcaibawang.com``（React）挂在 ``.page { width: 800px }`` 之内；
* ``twssz`` / ``twcf888.com`` 在标签上带内联
  ``display:block;width:100%;max-width:800px;margin:0 auto;box-sizing:border-box;``；
* ``twsyw`` 挂在内联 ``max-width:800px`` 的包裹层里；
* ``shengshi8800`` / ``twjsz666`` / ``twsaimahui`` 的 ``body`` 本身就是 720px；
* ``twbst528`` 挂在 ``.container``（672px）里。

只有 ``twjinniu`` 直接挂在 ``body`` 下且没有任何约束 —— 于是它铺满整个视口，
在 1200px 视口下比其他所有站点（672~800px）宽出一大截。

契约内容
--------
1. twjinniu 的 ``<managed-site-links>`` 必须与"800px 约束族"参照站
   （``twssz``、``twcf888.com``，两者用的是逐字相同的内联约束）实测宽度一致（±2px），
   计算样式同样是 ``max-width:800px`` + ``box-sizing:border-box`` + 水平居中。
2. twjinniu 在宽视口下不得铺满视口（回归护栏）。
3. 参照站（其它站点）的实测宽度与计算样式必须与基线完全一致 —— 即本修复
   没有改动任何其它站点，也没有改动共享组件。
4. 所有被测量的站点都真的渲染出 12 条链接（防止测到空壳元素）。

用真实的静态服务（``frontend/public``）+ ``page.route`` 桩掉 ``/api/site-links``，
不连线上、不连数据库、不起常驻服务。
"""

from __future__ import annotations

import functools
import http.server
import json
import re
import socket
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = REPO_ROOT / "frontend" / "public"
SHARED_COMPONENT = PUBLIC_DIR / "vendor" / "_shared" / "managed-site-links.js"
CHROME_CANDIDATES = (
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
)

TARGET_SITE = "twjinniu"

# 800px 约束族：与 twjinniu 修复后应当逐字同构（±2px）。
CONTROL_800 = ("twssz", "twcf888.com")

# 其它站点基线：{site: (viewport -> width)}，来自修复前实测（见报告）。
# 这些数字必须保持不变 —— 本修复只允许动 twjinniu。
STABLE_SITES = {
    "shengshi8800": {360: 360, 768: 720, 1200: 720},
    "twjsz666": {360: 360, 768: 720, 1200: 720},
    "twwanli": {360: 356, 768: 712, 1200: 712},
    "twssz": {360: 360, 768: 768, 1200: 800},
    "twcf888.com": {360: 360, 768: 768, 1200: 800},
    "twsyw": {360: 348, 768: 756, 1200: 788},
    "twsaimahui": {360: 360, 768: 720, 1200: 720},
    "twbst528": {360: 360, 768: 672, 1200: 672},
}

VIEWPORTS = (360, 768, 1200)
HEIGHT = 900
LINK_COUNT = 12
TOLERANCE_PX = 2.0
CONSTRAINT_PX = 800.0

LINKS_PAYLOAD = {
    "links": [
        {"name": f"友情站点{i:02d}", "url": f"https://example{i}.com/"}
        for i in range(1, LINK_COUNT + 1)
    ]
}

MEASURE_JS = """
() => {
  const el = document.querySelector('managed-site-links');
  if (!el) return { found: false };
  const rect = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  const shadow = el.shadowRoot;
  const inner = shadow ? shadow.querySelector('[data-links]') : null;
  return {
    found: true,
    width: rect.width,
    left: rect.left,
    display: cs.display,
    maxWidth: cs.maxWidth,
    boxSizing: cs.boxSizing,
    marginLeft: cs.marginLeft,
    marginRight: cs.marginRight,
    viewportWidth: document.documentElement.clientWidth,
    linkCount: inner ? inner.children.length : 0,
  };
}
"""


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102 - silence request logging
        pass


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve_public_dir() -> tuple[str, socketserver.ThreadingTCPServer]:
    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(PUBLIC_DIR))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", httpd


def _chrome_path() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


def _install_routes(page) -> None:
    # Playwright 以"后注册优先"匹配路由，因此 catch-all 必须先注册。
    page.route(
        "**/api/**",
        lambda route: route.fulfill(status=200, content_type="application/json", body="{}"),
    )
    page.route(
        "**/api/site-links*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(LINKS_PAYLOAD, ensure_ascii=False),
        ),
    )


def _measure_site(page, base_url: str, site: str, viewport: int) -> dict:
    page.goto(f"{base_url}/vendor/{site}/index.html", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("managed-site-links", state="attached", timeout=10000)
    # 等到 shadow DOM 里真的渲染出 12 条链接，避免测到尚未 hydrate 的空壳。
    page.wait_for_function(
        """(expected) => {
             const el = document.querySelector('managed-site-links');
             const inner = el && el.shadowRoot && el.shadowRoot.querySelector('[data-links]');
             return !!inner && inner.children.length === expected;
           }""",
        arg=LINK_COUNT,
        timeout=10000,
    )
    data = page.evaluate(MEASURE_JS)
    data["site"] = site
    data["viewport"] = viewport
    return data


def _collect() -> dict[tuple[str, int], dict]:
    sites = [TARGET_SITE, *STABLE_SITES.keys()]
    results: dict[tuple[str, int], dict] = {}
    base_url, httpd = _serve_public_dir()
    try:
        with sync_playwright() as playwright:
            launch_kwargs = {"headless": True}
            chrome = _chrome_path()
            if chrome:
                launch_kwargs["executable_path"] = chrome
            browser = playwright.chromium.launch(**launch_kwargs)
            try:
                for viewport in VIEWPORTS:
                    page = browser.new_page(viewport={"width": viewport, "height": HEIGHT})
                    _install_routes(page)
                    for site in sites:
                        results[(site, viewport)] = _measure_site(page, base_url, site, viewport)
                    page.close()
            finally:
                browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    return results


def _check_shared_component_untouched(failures: list[str]) -> None:
    """共享文件必须保持"零宽度约束"。

    `_shared/managed-site-links.js` 被 10 个站点共用，且 AGENTS.md 要求串行修改。
    它的 ``:host`` 块只允许 ``display: block``；任何 ``width`` / ``max-width``
    都会一次性改变全部站点的实测宽度。
    """
    source = SHARED_COMPONENT.read_text(encoding="utf-8")
    host_block = re.search(r":host\s*\{([^}]*)\}", source)
    if host_block is None:
        failures.append(
            "共享组件 :host 规则缺失或不再是 display:block —— 站点宽度契约的前提已改变"
        )
        return
    host_body = host_block.group(1)
    if "width" in host_body:
        failures.append(
            "共享组件 frontend/public/vendor/_shared/managed-site-links.js 的 :host 块"
            f"被写入了宽度约束（{host_body.strip()!r}）；宽度必须由各站点自己作用域约束"
        )
    if "display: block" not in host_body.replace("  ", " "):
        failures.append(f"共享组件 :host 规则不再是 display:block（{host_body.strip()!r}）")


def main() -> int:
    failures: list[str] = []
    results = _collect()

    print("实测 <managed-site-links> getBoundingClientRect().width（修复后目标状态）")
    header = f"{'site':<14}" + "".join(f"{f'@{vp}':>10}" for vp in VIEWPORTS) + f"{'maxWidth':>12}{'links':>7}"
    print(header)

    baseline_1200 = {
        "shengshi8800": 720,
        "twjsz666": 720,
        "twwanli": 712,
        "twssz": 800,
        "twcf888.com": 800,
        "twsyw": 788,
        "twsaimahui": 720,
        "twbst528": 672,
    }
    for site in [TARGET_SITE, *STABLE_SITES.keys()]:
        row = f"{site:<14}"
        for viewport in VIEWPORTS:
            data = results[(site, viewport)]
            row += f"{data['width']:>10.2f}"
        sample = results[(site, VIEWPORTS[-1])]
        row += f"{sample['maxWidth']:>12}{sample['linkCount']:>7}"
        print(row)
    print(f"（1200px 视口下修复前基线：twjinniu=1200 铺满视口；对照站 {baseline_1200}）\n")

    # --- 0. 真渲染 --------------------------------------------------------
    for (site, viewport), data in sorted(results.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if not data.get("found"):
            failures.append(f"{site}@{viewport}: 未找到 <managed-site-links>")
            continue
        if data["linkCount"] != LINK_COUNT:
            failures.append(
                f"{site}@{viewport}: 友情链接未真渲染（{data['linkCount']}/{LINK_COUNT} 条）"
            )

    # --- 1. twjinniu 与 800px 约束族一致 ---------------------------------
    for viewport in VIEWPORTS:
        target = results[(TARGET_SITE, viewport)]
        for control in CONTROL_800:
            ref = results[(control, viewport)]
            delta = abs(target["width"] - ref["width"])
            if delta > TOLERANCE_PX:
                failures.append(
                    f"{TARGET_SITE}@{viewport} 宽度 {target['width']:.2f} 与对照站 "
                    f"{control} 的 {ref['width']:.2f} 不一致（差 {delta:.2f}px > {TOLERANCE_PX}px）"
                )

    # --- 2. twjinniu 的 CSS 约束必须与对照站同构 -------------------------
    for viewport in VIEWPORTS:
        target = results[(TARGET_SITE, viewport)]
        ref = results[(CONTROL_800[0], viewport)]
        if target["maxWidth"] != ref["maxWidth"]:
            failures.append(
                f"{TARGET_SITE}@{viewport} 的 max-width 为 {target['maxWidth']}，"
                f"对照站 {CONTROL_800[0]} 为 {ref['maxWidth']}"
            )
        if target["boxSizing"] != "border-box":
            failures.append(
                f"{TARGET_SITE}@{viewport} 的 box-sizing 为 {target['boxSizing']}，应为 border-box"
            )
        if target["display"] != "block":
            failures.append(
                f"{TARGET_SITE}@{viewport} 的 display 为 {target['display']}，应为 block"
            )
        # 宽视口下必须居中：left + width/2 == 视口中心
        expected_left = (target["viewportWidth"] - target["width"]) / 2.0
        if abs(target["left"] - expected_left) > TOLERANCE_PX:
            failures.append(
                f"{TARGET_SITE}@{viewport} 未水平居中：left={target['left']:.2f}，"
                f"期望 {expected_left:.2f}"
            )

    # --- 3. 宽视口下不得铺满视口（回归护栏） -----------------------------
    wide = results[(TARGET_SITE, 1200)]
    if wide["width"] >= wide["viewportWidth"] - TOLERANCE_PX:
        failures.append(
            f"{TARGET_SITE}@1200 友情链接铺满视口（width={wide['width']:.2f} / "
            f"viewport={wide['viewportWidth']}），缺少宽度约束"
        )
    if wide["width"] > 900:
        failures.append(
            f"{TARGET_SITE}@1200 友情链接宽度 {wide['width']:.2f} 超出其它站点量级（上限 900px）"
        )

    # --- 4. 其它站点必须完全没被改变 -------------------------------------
    for site, expectations in STABLE_SITES.items():
        for viewport in VIEWPORTS:
            data = results[(site, viewport)]
            expected = expectations[viewport]
            if abs(data["width"] - expected) > TOLERANCE_PX:
                failures.append(
                    f"对照站 {site}@{viewport} 宽度被改变：实测 {data['width']:.2f}，"
                    f"基线 {expected}"
                )
            ref_max_width = {"twssz": "800px", "twcf888.com": "800px"}.get(site, "none")
            if data["maxWidth"] != ref_max_width:
                failures.append(
                    f"对照站 {site}@{viewport} 的 max-width 被改变：实测 {data['maxWidth']}，"
                    f"基线 {ref_max_width}"
                )

    # --- 5. 共享组件不得被写入宽度约束 -----------------------------------
    _check_shared_component_untouched(failures)

    if failures:
        print(f"FAILED: {len(failures)} 项断言未通过", file=sys.stderr)
        for message in failures:
            print(f"  - {message}", file=sys.stderr)
        return 1

    print(
        f"PASS: {TARGET_SITE} 友情链接宽度与 {CONTROL_800[0]}/{CONTROL_800[1]} 一致"
        f"（max-width:{CONSTRAINT_PX:.0f}px, 居中, box-sizing:border-box），"
        f"且其余 {len(STABLE_SITES)} 个对照站与共享组件均未被改动"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
