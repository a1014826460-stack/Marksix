"""twssz「AAA级大公开;准确率绝对100%;大胆下注!」卡片契约：逐行判定 + 命中标黄。

报障（2026-10-03）
------------------
线上该卡片有 4 行派生候选 —— `⑨肖中特 / ⑧肖中特 / ⑦肖中特 / ⑥肖中特`，
都是同一份「九肖中特」预测的**前 9/8/7/6 肖**。旧实现：

1. 数据源绑 mode 44（`7xiao7ma`，只有 7 肖），不足的位数用固定生肖顺序补齐成 9 ——
   卡片上「⑨肖中特」有 2 个生肖并不是本期预测；
2. 判定与黄底都取**整份模块**的 `is_correct`：整份命中时四个行一起上黄底（哪怕
   ⑥肖行根本没有特肖），整份不中时四行一起零黄底；
3. 没有任何「对 / 错」文字，用户无法判断本期是否命中。

修法
----
- 数据源改为 mode 49（`9xzt` 九肖中特），缺行时才退回 `7xiao7ma` 并按固定顺序补齐；
- `⑨⑧⑦⑥` 每行**按本行展示的前 N 肖复算判定**：特肖 ∈ 本行候选 → 对，否则错；
- 命中的那一行只点亮**本行候选里真正开出的那个生肖**；判定「错」的行零黄底（S3）；
- 未开奖不写判定、不点亮（S1）；标题行补开奖段 `开:02龙` / `开:待开奖`。

本契约用「特肖在第 9 位」的桩数据真渲染，锁住「⑨肖对 + 龙黄底、⑧⑦⑥错 + 零黄底」。

不连线上、不连数据库：临时 http.server + 桩 `lottery-site-data-client`。

运行：python -X utf8 frontend/test/twssz-aaa-grade-contract.py
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO / "frontend" / "public"
CHROME = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXECUTABLE", r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)

#: 九肖中特的 9 个生肖；「龙」放在第 9 位 → 只有 ⑨肖行命中。
NINE_ZODIACS = ["猴", "羊", "马", "猪", "狗", "鼠", "牛", "虎", "龙"]
SEVEN_ZODIACS = ["猴", "羊", "马", "猪", "狗", "鼠", "牛"]

STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      clear: function () {},
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { issue: "2026207" } }); },
      loadPredictions: function () {
        return Promise.resolve({ state: "ready", data: { data: { canonical_modules: window.__CONTRACT_MODULES__ || [] } } });
      }
    };
  }
};
"""

PROBE_JS = r"""
() => {
  const cards = Array.from(document.querySelectorAll("[data-site-slot='aaa-grade-card']"));
  return cards.map((card, index) => {
    const rows = Array.from(card.querySelectorAll("tr"));
    return {
      index,
      title: String(rows[0] ? rows[0].textContent : "").replace(/\s+/g, " ").trim(),
      details: rows.slice(1).map((row) => {
        const outer = row.querySelector("font[color='#fa035a']");
        const slots = outer ? Array.from(outer.children).filter((n) => n.tagName === "FONT" || n.tagName === "SPAN") : [];
        const verdict = row.querySelector("[data-site-slot='aaa-verdict']");
        const yellow = Array.from(row.querySelectorAll("font, span"))
          .filter((leaf) => !leaf.children.length &&
            getComputedStyle(leaf).backgroundColor === "rgb(255, 255, 0)")
          .map((leaf) => String(leaf.textContent || "").trim());
        return {
          prefix: outer ? String(outer.textContent).replace(/\s+/g, " ") : "",
          values: slots.map((slot) => String(slot.textContent || "").trim()),
          verdict: verdict ? String(verdict.textContent || "").trim() : null,
          verdictColor: verdict ? String(verdict.getAttribute("color") || "") : null,
          yellow: yellow,
          inheritedVerdict: row.getAttribute("data-prediction-row"),
        };
      }),
    };
  });
}
"""


def payload_rows(term, tokens, opened, zodiac, code):
    return {
        "term": term,
        "prediction": {"tokens": list(tokens), "text": " ".join(tokens)},
        "result": {
            "isOpened": opened,
            "isCorrect": opened,          # 故意与「逐行判定」不同，证明判定来自本地复算
            "code": code,
            "zodiac": zodiac,
            "text": "开奖" + code if opened else "待开奖",
        },
        "raw": {"res_code": code, "res_sx": zodiac},
    }


def build_modules():
    """8 张卡：第 1 张（207 期）未开奖，其余 7 张开 02 龙（龙在第 9 位）。"""
    def rows_for(tokens):
        return [
            payload_rows(str(207 - index), tokens, index != 0, "龙", "02")
            for index in range(8)
        ]

    # 九肖（存在）与七肖（诱饵）都给：卡片必须优先用九肖。
    return [
        {"moduleKey": "9xzt", "rows": rows_for(NINE_ZODIACS)},
        {"moduleKey": "7xiao7ma", "rows": rows_for(SEVEN_ZODIACS)},
    ]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):  # noqa: D102
        pass


def serve(directory: Path):
    handler = functools.partial(QuietHandler, directory=str(directory))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def render_probe():
    httpd, port = serve(WEB_ROOT)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1200})
            page.route("**/lottery-site-data-client.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=STUB_CLIENT))
            page.route("**/forced-announcement.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=""))
            page.add_init_script(f"window.__CONTRACT_MODULES__ = {json.dumps(build_modules())};")
            page.goto(f"http://127.0.0.1:{port}/vendor/twssz/index.html", wait_until="load")
            page.wait_for_timeout(6000)
            cards = page.evaluate(PROBE_JS)
            browser.close()
    finally:
        httpd.shutdown()
    return cards


def main() -> None:
    cards = render_probe()
    problems: list[str] = []
    if not cards:
        problems.append("页面上找不到 [data-site-slot='aaa-grade-card'] 卡片")

    expectations = (("⑨", 9), ("⑧", 8), ("⑦", 7), ("⑥", 6))
    for card in cards:
        if len(card["details"]) != 4:
            problems.append(f"第 {card['index'] + 1} 张卡应渲染 4 行（⑨⑧⑦⑥），实际 {len(card['details'])}")
            continue
        opened = card["index"] != 0  # 桩数据：第 1 张 207 期未开奖，其余已开奖
        expected_draw = "开:02龙" if opened else "开:待开奖"
        if expected_draw not in card["title"]:
            problems.append(f"第 {card['index'] + 1} 张卡标题缺少 {expected_draw}：{card['title'][:80]}")
        for (label, count), detail in zip(expectations, card["details"]):
            where = f"第 {card['index'] + 1} 张卡 {label}肖"
            want_values = NINE_ZODIACS[:count]
            if detail["values"] != want_values:
                problems.append(f"{where} 候选应为 {want_values}，实际 {detail['values']}")
            want_term = str(207 - card["index"])
            if not detail["prefix"].startswith(f"{want_term}期{label}肖中特:"):
                problems.append(f"{where} 前缀应为「{want_term}期{label}肖中特:」，实际 {detail['prefix'][:40]!r}")
            if detail["verdict"] is None:
                problems.append(f"{where} 缺少判定字槽 [data-site-slot='aaa-verdict']")
                continue
            if not opened:
                if detail["verdict"] != "":
                    problems.append(f"{where} 未开奖不得显示判定，实际 {detail['verdict']!r}")
            else:
                want_verdict = "对" if count == 9 else "错"
                if detail["verdict"] != want_verdict:
                    problems.append(f"{where} 判定应为「{want_verdict}」，实际 {detail['verdict']!r}")
            want_yellow = ["龙"] if (opened and count == 9) else []
            if detail["yellow"] != want_yellow:
                problems.append(f"{where} 黄底应为 {want_yellow}，实际 {detail['yellow']}")

    if problems:
        print(f"twssz-aaa-grade-contract: FAIL ({len(problems)} 项)")
        for line in problems:
            print("  - " + line)
        raise SystemExit(1)
    print(f"twssz-aaa-grade-contract: OK（{len(cards)} 张卡，逐行判定 + 只点亮命中生肖）")


if __name__ == "__main__":
    main()
