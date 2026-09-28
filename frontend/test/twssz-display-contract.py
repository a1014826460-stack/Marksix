"""twssz 天地生肖（`精准天地+两肖`，mode 5 / `title_5`）判定口径 + 只标命中项契约。

背景（2026-09-29）：`frontend/public/vendor/twssz/site-data-adapter.js` 的
`renderTiandiHistory()` 过去用 `row.result.isCorrect`（`isHitRow()`）判定，而 vendor/接口的
`is_correct` 只比对 mode 5 的 `xiao` 列（后端 `mechanisms.py` 里 `title_5` 的
`hit_checker=contains_hit`，候选就是「生肖选 2」），天地组（天肖/地肖各 6 肖）永远不参与
判定 —— 于是「天肖里含开奖特肖」的期显示「错」（270 期「天肖+兔鸡」开 37 马）。

正确口径（与 twwanli `#tdsx`、twsyw `#nannv` 一致）：特肖落在 **天肖/地肖分组（6 肖）∪
本期 2 个候选生肖** 任一即算命中；命中时只点亮真正命中的那一项（命中两肖 → 点亮该生肖；
命中天地组 → 点亮组名；两项都命中优先点亮生肖）；未命中/未开奖零高亮。

断言用的合成分组与 `public.fixed_data` sign='天地肖' 及各站 sx.html 一致：
天肖 = 兔马猴猪牛龙；地肖 = 鼠虎蛇羊鸡狗。

站点的命中助手是 `markHitLeaf()`（写内联 `#FFFF00`：审计 `audit-prediction-display.py`
按可见黄底统计），本模块在同一次命中里同时补上跨站标准标记 `data-prediction-hit="true"`，
所以本契约**两种标记都要断言**：DOM 标记（`data-prediction-hit`）与画出来的黄底
（`getComputedStyle(...).backgroundColor === rgb(255,255,0)`）必须落在同一项上。

不连线上、不连数据库：本地静态服务（`frontend/public`）+ 桩 `lottery-site-data-client`
+ `add_init_script` 注入合成 payload + Playwright headless Chrome 真跑适配器后断言 DOM。

运行：$env:PYTHONIOENCODING='utf-8'; python frontend/test/twssz-display-contract.py
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

# twssz 适配器的 `modulesFrom()` 读 `envelope.data.data.canonical_modules`
# （回退 `envelope.data.canonical_modules`），客户端再包一层 `data`，所以桩要返回
# `{ state, data: { data: { canonical_modules: [...] } } }`。
STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      clear: function () {},
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { data: { issue: "2026270" } } }); },
      loadPredictions: function () {
        return Promise.resolve({ state: "ready", data: { data: { canonical_modules: window.__CONTRACT_MODULES__ || [] } } });
      }
    };
  }
};
"""

PROBE_JS = r"""
() => {
  const MONO = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const PAINTED_YELLOW = 'rgb(255, 255, 0)';
  const yellowOf = (root) => Array.from(root.querySelectorAll('*'))
    .filter((el) => !el.children.length && getComputedStyle(el).backgroundColor === PAINTED_YELLOW)
    .map((el) => MONO(el.textContent));
  const hitsOf = (root) => Array.from(root.querySelectorAll('[data-prediction-hit]'))
    .map((el) => MONO(el.textContent));

  const section = document.querySelector("[data-prediction-section='title_5']");
  const tiandi = section ? Array.from(section.querySelectorAll('tr')).map((tr) => {
    const text = MONO(tr.textContent);
    const content = text.match(/【[^】]*】/);
    const issue = text.match(/^\d+\s*期/);
    const result = text.match(/开\s*:.*$/);
    return {
      text,
      issue: MONO(issue ? issue[0] : ''),
      content: MONO(content ? content[0] : ''),
      result: MONO(result ? result[0] : ''),
      hits: hitsOf(tr),
      yellow: yellowOf(tr),
    };
  }) : [];

  // 「错 / 待开奖」的行一律不许出现黄底或命中标记。粒度取最内层
  // `[data-prediction-row]`（该站有的渲染器把整张卡标在 table 上，有的是 tr）。
  const badRows = [];
  let verdictRows = 0;
  const rowNodes = Array.from(document.querySelectorAll('[data-prediction-row]'))
    .filter((node) => !node.querySelector('[data-prediction-row]'));
  rowNodes.forEach((node) => {
    const text = MONO(node.textContent);
    if (!text) return;
    const verdict = text.indexOf('错') >= 0 ? '错' : text.indexOf('待开奖') >= 0 ? '待开奖' : '';
    if (!verdict) return;
    verdictRows += 1;
    const hits = hitsOf(node);
    const yellow = yellowOf(node).filter(Boolean);
    if (hits.length || yellow.length) badRows.push({ verdict, text: text.slice(0, 60), hits, yellow });
  });

  return {
    tiandi,
    hits: section ? hitsOf(section) : [],
    yellow: section ? yellowOf(section).filter(Boolean) : [],
    totalHits: document.querySelectorAll('[data-prediction-hit]').length,
    badRows,
    verdictRows,
    rowSlots: document.querySelectorAll('[data-prediction-row]').length,
    sectionSlots: document.querySelectorAll('[data-prediction-section]').length,
  };
}
"""


def row(issue, *, tokens=None, raw=None, opened=True, code="", zodiac="", text="", is_correct=False):
    return {
        "issue": issue,
        "term": issue,
        "prediction": {"tokens": tokens if tokens is not None else [], "text": ""},
        "raw": raw or {},
        "result": {"isOpened": opened, "isCorrect": is_correct, "code": code, "zodiac": zodiac, "text": text},
    }


def build_modules():
    """270/269/267 = 已开奖对照，266 = 未开奖；另加一节非本模块的错期做全页对照。

    所有 `isCorrect` 一律给 `False`：它只反映 vendor 对 `xiao` 两肖的比对结果
    （270/267 期两肖都没命中，天地组才算命中），用来证明判定已本地复算、不再依赖 vendor。
    """
    tian = "天肖|兔,马,猴,猪,牛,龙"
    di = "地肖|鼠,虎,蛇,羊,鸡,狗"
    modules = [
        # 精准天地+两肖（title_5）：候选 = 天地组(content) + 两肖(xiao)。
        # 270 天肖+兔鸡 开 37 马 → 马 ∈ 天肖组 → 对，只亮「天肖」；
        # 269 地肖+兔鸡 开 37 马 → 都不含 → 错，零高亮；
        # 267 天肖+兔鸡 开 22 鸡 → 鸡 ∈ 两肖 → 对，只亮「鸡」；
        # 266 地肖+鼠虎 未开奖 → 待开奖，零高亮。
        {"moduleKey": "title_5", "rows": [
            row("2026270", tokens=[tian], raw={"content": tian, "xiao": "兔,鸡", "res_code": "37", "res_sx": "马"},
                code="37", zodiac="马", text="37马", is_correct=False),
            row("2026269", tokens=[di], raw={"content": di, "xiao": "兔,鸡", "res_code": "37", "res_sx": "马"},
                code="37", zodiac="马", text="37马", is_correct=False),
            row("2026267", tokens=[tian], raw={"content": tian, "xiao": "兔,鸡", "res_code": "22", "res_sx": "鸡"},
                code="22", zodiac="鸡", text="22鸡", is_correct=False),
            row("2026266", tokens=[di], raw={"content": di, "xiao": "鼠,虎"}, opened=False, is_correct=False),
        ]},
        # 家野二肖（pt2xiao）：非本模块的「错期」对照，供应商模板里这一节预埋了样例黄底
        # （`【家禽+<span>兔</span>猴】`），用来验证全页错期零黄底。开奖给 45狗 而不是
        # 37马：这一个 moduleKey 同时供 A级猛料 的「平特」格，用不相干的特肖可以让
        # A级卡片保持「无命中项」，避免把它的黄底混进本契约的判定断言里。
        {"moduleKey": "pt2xiao", "rows": [
            row("2026270", tokens=["马", "龙"], code="45", zodiac="狗", text="45狗", is_correct=False),
        ]},
    ]
    for module in modules:
        for item in module["rows"]:
            assert item["result"]["isCorrect"] is False, "合成数据必须把 vendor 判定一律压成 false"
    return modules


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
    """真跑适配器：第一次渲染 + 切彩种再渲染一次（样例黄标不得在第二轮残留）。"""
    httpd, port = serve(WEB_ROOT)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            page = browser.new_page(viewport={"width": 480, "height": 1400})
            page_errors: list[str] = []
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.route(
                "**/lottery-site-data-client.js",
                lambda route: route.fulfill(status=200, content_type="application/javascript", body=STUB_CLIENT),
            )
            # 这两个共享脚本会请求 /api/*：本契约只验证渲染，桩空以保持离线与确定性。
            page.route("**/forced-announcement.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=""))
            page.route("**/managed-site-links.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=""))
            page.add_init_script(f"window.__CONTRACT_MODULES__ = {json.dumps(build_modules())};")
            page.goto(f"http://127.0.0.1:{port}/vendor/twssz/index.html", wait_until="load")
            page.wait_for_function(
                "() => { const s = document.querySelector(\"[data-prediction-section='title_5']\");"
                " return Boolean(s) && /2026270/.test(s.textContent); }",
                timeout=15000,
            )
            page.wait_for_timeout(400)
            first = page.evaluate(PROBE_JS)
            # 第二轮：切换彩种会先清空静态载荷再重新渲染同一批数据。命中标记与黄底
            # 必须完全一致（供应商样例黄标不得在第二轮活下来）。
            if first["tiandi"]:
                page.evaluate("window.TwsszSiteData.selectLottery(2)")
                page.wait_for_function(
                    "(expected) => { const s = document.querySelector(\"[data-prediction-section='title_5']\");"
                    " if (!s) return false;"
                    " const tr = s.querySelector('tr');"
                    " return tr && tr.textContent.replace(/\\s+/g, ' ').trim() === expected; }",
                    arg=first["tiandi"][0]["text"],
                    timeout=15000,
                )
                page.wait_for_timeout(300)
                second = page.evaluate(PROBE_JS)
            else:
                second = first
            browser.close()
    finally:
        httpd.shutdown()
    return first, second, page_errors


def main() -> None:
    first, second, page_errors = render_probe()
    data = first
    problems: list[str] = []

    if page_errors:
        problems.append(f"页面 JS 报错: {page_errors}")

    def check(rows, index, expect_content, expect_issue, expect_result, expect_hits, label):
        if len(rows) <= index:
            problems.append(f"{label}: 第 {index} 行未渲染")
            return
        item = rows[index]
        if expect_content is not None and expect_content not in item["content"]:
            problems.append(f"{label}: 内容应为『{expect_content}』，实际 '{item['content']}'（{item['text']}）")
        if expect_issue is not None and item["issue"] != expect_issue:
            problems.append(f"{label}: 期号应为『{expect_issue}』，实际 '{item['issue']}'")
        if expect_result is not None and expect_result not in item["result"]:
            problems.append(f"{label}: 判定应为『{expect_result}』，实际 '{item['result']}'")
        if sorted(item["hits"]) != sorted(expect_hits):
            problems.append(f"{label}: 命中标记应为 {expect_hits}，实际 {item['hits']}（{item['text']}）")
        # 站点自身的命中助手（内联 #FFFF00）必须与标记落在同一项上。
        if sorted(item["yellow"]) != sorted(expect_hits):
            problems.append(f"{label}: 黄底应为 {expect_hits}，实际 {item['yellow']}（{item['text']}）")

    tiandi = data["tiandi"]

    # ── 判定口径：特肖 ∈ 天地组 ∪ 两肖 ─────────────────────────────────
    check(tiandi, 0, "【天肖+兔鸡】", "2026270期", "开:37马对", ["天肖"],
          "天地生肖 270期（天肖+兔鸡，开37马 → 天地组命中）")
    check(tiandi, 1, "【地肖+兔鸡】", "2026269期", "开:37马错", [],
          "天地生肖 269期（地肖+兔鸡，开37马 → 都不含）")
    check(tiandi, 2, "【天肖+兔鸡】", "2026267期", "开:22鸡对", ["鸡"],
          "天地生肖 267期（天肖+兔鸡，开22鸡 → 两肖命中）")
    check(tiandi, 3, "【地肖+鼠虎】", "2026266期", "开:待开奖", [],
          "天地生肖 266期（未开奖）")

    # ── 标记范围：整页只有这两项命中（标记不落到别的模块/别的候选项） ──
    if data["hits"] != ["天肖", "鸡"]:
        problems.append(f"天地模块命中标记应为 ['天肖', '鸡']，实际 {data['hits']}")
    if data["totalHits"] != 2:
        problems.append(f"整页命中标记总数应为 2（只有天地模块用它），实际 {data['totalHits']}")

    # ── 全页：错期 / 未开奖期不得有黄底或命中标记 ───────────────────────
    # `verdictRows` 是这次检查真正扫到的「错 / 待开奖」行数（269 错、266 待开奖、
    # pt2xiao 的 270 错），为 0 说明断言空转，必须当失败处理。
    if data["verdictRows"] < 3:
        problems.append(f"全页错期/未开奖期行数异常: {data['verdictRows']}（断言未覆盖）")
    for item in data["badRows"]:
        problems.append(
            f"{item['verdict']}期仍有黄底/标记: hits={item['hits']} yellow={item['yellow']} ← {item['text']}"
        )

    # ── 第二轮渲染必须与第一轮完全一致（样例黄标不得残留） ───────────────
    for index, (before, after) in enumerate(zip(first["tiandi"], second["tiandi"])):
        if index > 3:
            break
        for field in ("text", "hits", "yellow"):
            if before[field] != after[field]:
                problems.append(f"重渲染第 {index} 行不一致（{field}）：{before[field]!r} → {after[field]!r}")

    print(f"天地模块行数: {len(tiandi)}；整页行槽位: {data['rowSlots']}；区块槽位: {data['sectionSlots']}；"
          f"命中标记总数: {data['totalHits']}")
    for index, item in enumerate(tiandi[:4]):
        print(f"  行{index}: {item['issue']} | {item['content']} | {item['result']} | "
              f"hits={item['hits']} yellow={item['yellow']}")
    print(f"错/待开奖期行数: {data['verdictRows']}；其中有黄底或标记: {len(data['badRows'])}；"
          f"页面 JS 报错: {len(page_errors)}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwssz-display-contract: OK（天地组∪两肖并集判定 + 只标命中项 + 错/未开奖零黄底）")


if __name__ == "__main__":
    main()
