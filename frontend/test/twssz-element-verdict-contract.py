"""twssz「综合资料」（mapping key `3hang`，mode 53 三行/精准五行）命中行口径契约。

背景（2026-09-29）：`frontend/public/vendor/twssz/site-data-adapter.js` 的高亮入口
`structuredHit()` 过去一律用 `candidateHit()` —— 「特码落在**正文号码清单**里的哪个标签」
就点亮哪个标签。综合资料落库的正文是「五行标签|号码清单」，而**历史遗留的 mode 53 正文
清单是按生肖五行（`fixed_data` sign='五行肖'）拼的**：

    24 → 号码五行 木，生肖羊 → 生肖五行 土（正文把 24 写在【土】清单里）
    37 → 号码五行 木，生肖马 → 生肖五行 火（正文三行里根本没有 37）
    04 → 号码五行 金，生肖兔 → 生肖五行 木（正文把 04 写在【木】清单里）

于是「接口判准（后端已按号码五行判 `is_correct`）」的期会被点到别的行、甚至一行都不点。

正确口径（与 tw8880 / twcaibawang / twsaimahui / twcf888 一致）：
  命中行 = **特码号码**（`raw.res_code` 最后一项）在权威号码五行分组
  （= `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS` = `public.fixed_data` sign='五行'）
  里的归属，落到本行预测的哪个五行标签，就点亮哪一个；与正文号码清单一律无关。
  未开奖 / 特码缺失 / 正文标签不是五行名 → 零高亮。
  **判定**仍只来自接口的 `is_correct`（本契约的合成 `isCorrect` 故意与正文清单口径冲突，
  用来证明高亮已本地按号码五行复算，不再读正文清单）。

站点的命中助手是 `markHitLeaf()`（写内联 `#FFFF00`：审计 `audit-prediction-display.py`
按可见黄底统计），所以本契约断言**画出来的黄底**（`getComputedStyle(...).backgroundColor`
== rgb(255,255,0)）落在哪一个候选上。

不连线上、不连数据库：本地静态服务（`frontend/public`）+ 桩 `lottery-site-data-client`
+ `add_init_script` 注入合成 payload + Playwright headless Chrome 真跑适配器后断言 DOM。

反例（去掉适配器里的 `hitElement` 分支 → 回到正文清单口径 → 本契约必须 FAIL）：
  269 期（正文清单口径把 24 放在【土】）会点亮【土】而不是【木】；
  267 期（正文三行里没有 37）会一行都不点亮。

运行：$env:PYTHONIOENCODING='utf-8'; python frontend/test/twssz-element-verdict-contract.py
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
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { data: { issue: "2026269" } } }); },
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

  // `renderStructuredHistory()` 首次写入 `data-prediction-section="3hang"`，之后每一轮
  // 渲染因为该属性已存在而改写成 `3hang-综合资料`（既有的 sectionKey 逻辑），所以用前缀选择器。
  const section = document.querySelector("[data-prediction-section^='3hang']");
  // 粒度取最内层 `[data-prediction-row]`：`renderStructuredHistory()` 把目标区域里
  // 每一行都标了 row，只有真正写到内容的那几行有文字。
  const rows = section
    ? Array.from(section.querySelectorAll('[data-prediction-row]'))
        .filter((node) => !node.querySelector('[data-prediction-row]'))
    : [];
  const sectionRows = rows.map((node) => ({
    text: MONO(node.textContent),
    hits: hitsOf(node),
    yellow: yellowOf(node).filter(Boolean),
  }));

  // 「错 / 待开奖」的行一律不许出现黄底或命中标记（全页，不只本模块）。
  const badRows = [];
  let verdictRows = 0;
  Array.from(document.querySelectorAll('[data-prediction-row]'))
    .filter((node) => !node.querySelector('[data-prediction-row]'))
    .forEach((node) => {
      const text = MONO(node.textContent);
      if (!text) return;
      const verdict = text.indexOf('错') >= 0 ? '错' : text.indexOf('待开奖') >= 0 ? '待开奖' : '';
      if (!verdict) return;
      verdictRows += 1;
      const hits = hitsOf(node);
      const yellow = yellowOf(node).filter(Boolean);
      if (hits.length || yellow.length) badRows.push({ verdict, text: text.slice(0, 80), hits, yellow });
    });

  return {
    found: Boolean(section),
    rows: sectionRows,
    yellow: section ? yellowOf(section).filter(Boolean) : [],
    totalHits: document.querySelectorAll('[data-prediction-hit]').length,
    badRows,
    verdictRows,
    rowSlots: document.querySelectorAll('[data-prediction-row]').length,
    sectionSlots: document.querySelectorAll('[data-prediction-section]').length,
  };
}
"""

# 历史遗留的 mode 53 正文（**生肖五行**清单，抄自
# backend/src/tests/unit/test_repair_mode53_element_content.py 的 LEGACY_53 /
# frontend/test/twsaimahui-sanhang-element-contract.mjs）：24 在【土】、04 在【木】、
# 37 一行都没有 —— 这三处正是号码五行与生肖五行的分歧点。
LEGACY_CONTENT_53 = [
    "土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48",
    "木|04,05,16,17,28,29,40,41",
    "水|07,08,19,20,31,32,43,44",
]
# 后端修复后的正文（**号码五行**清单）：24 在【木】、04 在【金】（不在三行里）。
CANONICAL_CONTENT_53 = [
    "土|05,06,19,20,27,28,35,36,49",
    "木|07,08,15,16,23,24,37,38,45,46",
    "水|13,14,21,22,29,30,43,44",
]


def row(issue, tokens, *, res_code="", res_sx="", opened=True, is_correct=False,
        code="", zodiac="", text=""):
    """一个规范模块行：`raw` 带 res_code（特码 = 最后一项），`result` 带 vendor 判定。"""
    return {
        "issue": issue,
        "term": issue,
        "prediction": {"tokens": tokens, "text": ""},
        "raw": {"res_code": res_code, "res_sx": res_sx, "content": ",".join(tokens)},
        "result": {
            "isOpened": opened,
            "isCorrect": is_correct,
            "code": code,
            "zodiac": zodiac,
            "text": text,
        },
    }


def build_modules():
    """五期综合资料（mode 53）对照：全部给**正文生肖五行清单**，只有 267/269 判准。

    `isCorrect` 一律照**后端号码五行口径**给（后端已是这个口径，不用改）：
      269 期 三行«土木水» + 特码 24 → 24 号码五行 = 木 ∈ 三行 → 准，只亮【木】
                                （正文清单把 24 放在【土】→ 旧口径会亮【土】）
      267 期 三行«土木水» + 特码 37 → 37 号码五行 = 木 ∈ 三行 → 准，只亮【木】
                                （正文三行里没有 37 → 旧口径一行都不亮）
      266 期 三行«土木水» + 特码 04 → 04 号码五行 = 金 ∉ 三行 → 错，零黄底
      270 期 三行«土木水» + 特码 24（**修复后的号码五行正文**）→ 准，同样只亮【木】
      268 期 未开奖 → 待开奖，零黄底
    """
    return [
        {"moduleKey": "3hang", "rows": [
            row("2026269", LEGACY_CONTENT_53, res_code="05,11,19,31,42,07,24", res_sx="牛,马,狗,龙,猪,蛇,羊",
                is_correct=True, code="24", zodiac="羊", text="羊24"),
            row("2026267", LEGACY_CONTENT_53, res_code="05,11,19,31,42,07,37", res_sx="牛,马,狗,龙,猪,蛇,马",
                is_correct=True, code="37", zodiac="马", text="马37"),
            row("2026266", LEGACY_CONTENT_53, res_code="05,11,19,31,42,07,04", res_sx="牛,马,狗,龙,猪,蛇,兔",
                is_correct=False, code="04", zodiac="兔", text="兔04"),
            row("2026270", CANONICAL_CONTENT_53, res_code="05,11,19,31,42,07,24", res_sx="牛,马,狗,龙,猪,蛇,羊",
                is_correct=True, code="24", zodiac="羊", text="羊24"),
            row("2026268", LEGACY_CONTENT_53, opened=False, is_correct=False),
        ]},
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
                "() => { const s = document.querySelector(\"[data-prediction-section^='3hang']\");"
                " return Boolean(s) && /2026269/.test(s.textContent); }",
                timeout=15000,
            )
            page.wait_for_timeout(400)
            first = page.evaluate(PROBE_JS)
            # 第二轮：切换彩种会先清空静态载荷再重新渲染同一批数据。黄底必须完全一致
            # （供应商样例黄标不得在第二轮活下来）。
            if first["rows"]:
                page.evaluate("window.TwsszSiteData.selectLottery(2)")
                page.wait_for_function(
                    "(expected) => { const s = document.querySelector(\"[data-prediction-section^='3hang']\");"
                    " if (!s) return false;"
                    " return s.textContent.replace(/\\s+/g, ' ').indexOf(expected) >= 0; }",
                    arg="2026269",
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
    problems: list[str] = []

    if page_errors:
        problems.append(f"页面 JS 报错: {page_errors}")
    if not first["found"]:
        problems.append("页面上找不到 [data-prediction-section^='3hang']（综合资料区块未渲染）")

    # 只保留真正写到内容的那几行（其余是供应商模板里的空行）。
    rendered = [item for item in first["rows"] if item["text"]]

    def find(issue: str):
        for item in rendered:
            if issue in item["text"]:
                return item
        return None

    def check(issue, expect_yellow, expect_result, label):
        item = find(issue)
        if item is None:
            problems.append(f"{label}: {issue} 行未渲染（已渲染 {[i['text'][:24] for i in rendered]}）")
            return
        if sorted(item["yellow"]) != sorted(expect_yellow):
            problems.append(
                f"{label}: 黄底应为 {expect_yellow}，实际 {item['yellow']}（{item['text']}）"
            )
        if expect_result not in item["text"]:
            problems.append(f"{label}: 判定应为『{expect_result}』，实际（{item['text']}）")
        # 网站自身的黄底与跨站标记都不该出现在这一行之外（本模块内）。
        if item["hits"] and sorted(item["hits"]) != sorted(expect_yellow):
            problems.append(f"{label}: data-prediction-hit 与黄底不一致（{item['hits']}）")

    # ── 269 期：正文清单把 24 放在【土】，号码五行（木）才是命中行 ──────────
    check("2026269", ["木"], "开：羊24对",
          "综合资料 269期（三行土木水 + 特码24 → 号码五行木）")
    # ── 267 期：正文三行里根本没有 37，号码五行（木）才是命中行 ─────────────
    check("2026267", ["木"], "开：马37对",
          "综合资料 267期（三行土木水 + 特码37 → 号码五行木）")
    # ── 266 期：04 号码五行是金（不在三行里），正文清单把它写在【木】────────
    check("2026266", [], "开：兔04错",
          "综合资料 266期（三行土木水 + 特码04 → 号码五行金 ∉ 三行）")
    # ── 270 期：同一特码 24 + 后端修复后的号码五行正文 → 结论必须一致 ───────
    check("2026270", ["木"], "开：羊24对",
          "综合资料 270期（号码五行正文 + 特码24 → 口径不得依赖正文清单）")
    # ── 268 期：未开奖 ─────────────────────────────────────────────────────
    check("2026268", [], "开：待开奖", "综合资料 268期（未开奖）")

    # ── 判定行数（断言不得空转）+ 全页「错/待开奖零黄底」────────────────────
    if len(rendered) < 5:
        problems.append(f"综合资料只渲染出 {len(rendered)} 行，契约需要 5 行（断言未覆盖）")
    if first["verdictRows"] < 2:
        problems.append(f"全页错期/未开奖期行数异常: {first['verdictRows']}（断言未覆盖）")
    for item in first["badRows"]:
        problems.append(
            f"{item['verdict']}期仍有黄底/标记: hits={item['hits']} yellow={item['yellow']} ← {item['text']}"
        )
    if first["totalHits"]:
        problems.append(f"综合资料不是天地模块，不应写 data-prediction-hit；实际 {first['totalHits']} 个")

    # ── 第二轮渲染必须与第一轮完全一致（样例黄标不得残留）──────────────────
    second_rows = [item for item in second["rows"] if item["text"]]
    for before, after in zip(rendered, second_rows):
        for field in ("text", "yellow"):
            if before[field] != after[field]:
                problems.append(f"重渲染不一致（{field}）：{before[field]!r} → {after[field]!r}")

    print(f"综合资料渲染行数: {len(rendered)}；整页行槽位: {first['rowSlots']}；"
          f"区块槽位: {first['sectionSlots']}；错/待开奖期行数: {first['verdictRows']}")
    for item in rendered:
        print(f"  {item['text']} | yellow={item['yellow']}")
    print(f"页面 JS 报错: {len(page_errors)}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwssz-element-verdict-contract: OK（mode 53 综合资料只按特码号码五行点亮命中行）")


if __name__ == "__main__":
    main()
