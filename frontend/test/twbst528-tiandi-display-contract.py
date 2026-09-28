"""twbst528【天地+②肖】判定口径 + 只标命中项渲染契约。

背景（2026-09-28）：`frontend/public/vendor/twbst528/site-data-adapter.js` 的
`renderTiandiErxiaoHistory()` 过去把候选串交给通用的 `highlightTokens()`，并且
「对/错」直接用接口的 `result.isCorrect`。而 vendor/接口的 `is_correct` 只比对 mode 5
的 `xiao` 那 2 肖（后端 `mechanisms.py` 里 `title_5` 的 `hit_checker=contains_hit`，
候选就是「生肖选 2」），**天地组（6 肖）永远不参与判定** —— 于是「天肖里含开奖特肖」
的期显示「错」（270 期「天肖+兔鸡」开 37 马）。同时通用口径只做
`candidate === zodiac` 比对，组名「天肖」永远不可能等于某个生肖字，所以组名从不标黄。

正确口径（与 twwanli `#tdsx`、twsyw `#nannv`、twcaibawang 一致）：特肖落在
**天肖/地肖分组（6 肖）∪ 本期 2 个候选生肖** 任一即命中；命中时只点亮真正命中的那一项
（命中两肖 → 点亮该生肖；命中天地组 → 点亮组名；两项都命中时优先点亮生肖）；
未命中/未开奖零黄底。

断言用的合成分组与 `public.fixed_data` sign='天地肖' 及各站 `sx.html` 一致：
天肖 = 兔马猴猪牛龙；地肖 = 鼠虎蛇羊鸡狗。

适配器源码事实（本契约据此构造 payload）：
- envelope：`modulesFrom()` 从 `result.data` 起逐层剥 `.data`，直到某层出现数组型
  `canonical_modules`（只认 `canonical_modules`）；因此桩客户端返回
  `{ state, data: { data: { canonical_modules } } }`。
- moduleKey：`index.html` 的【天地+②肖】面板由 `renderTiandiErxiaoHistory(modules.tiandi_2xiao)`
  供应，即 `tiandi_2xiao`（**不是** `title_5`；`title_5` 在本站供「左右中特」）。
- 行字段：`row.issue/term`、`row.raw.tiandi`（"天肖"/"地肖"）、`row.raw.xiao_pair`
  （2 个候选生肖的数组）、`row.result.{isOpened, code, zodiac, isCorrect}`。
- 标记：自建 marker `<span data-prediction-hit="true" style="background-color:#FFFF00">`。

不连线上、不连数据库：本地静态服务（`frontend/public`）+ 桩 `lottery-site-data-client`
+ `add_init_script` 注入合成 payload + Playwright headless Chrome 真跑适配器后断言 DOM。

运行：$env:PYTHONIOENCODING='utf-8'; python frontend/test/twbst528-tiandi-display-contract.py
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

# twbst528 适配器 `modulesFrom()` 从 `result.data` 起逐层剥 `.data`，直到某层出现
# 数组型 `canonical_modules`（只认 `canonical_modules`，没有 `modules` 回退），
# 所以桩要返回 `{ state, data: { data: { canonical_modules: [...] } } }`。
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

# 这几个共享脚本会请求 /api/*：本契约只验证渲染，桩空以保持离线与确定性。
STUBBED_EMPTY = (
    "**/forced-announcement.js",
    "**/managed-site-links.js",
    "**/unified-return-top.js",
)

PROBE_JS = r"""
() => {
  const MONO = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const YELLOW = (v) => ['rgb(255, 255, 0)', 'rgba(255, 255, 0, 1)', '#ffff00', '#ff0', 'yellow']
    .includes(String(v || '').replace(/\s+/g, ' ').toLowerCase());
  const isYellow = (el) => Boolean(el) && YELLOW(getComputedStyle(el).backgroundColor);

  // 按标题定位【天地+②肖】板块（与 sectionByTitle 同口径：读 .pb-tit 里的【…】）。
  const sections = Array.from(document.querySelectorAll('.lxlm, .tzlb'));
  const tiandi = sections.filter((el) => {
    const head = el.querySelector('.pb-tit');
    return head && String(head.textContent || '').indexOf('【天地+②肖】') >= 0;
  })[0] || null;

  const cellText = (tr, i) => {
    const td = tr.querySelectorAll(':scope > td')[i];
    return MONO(td ? td.textContent : '');
  };
  const hitTexts = (scope) => Array.from(scope.querySelectorAll('[data-prediction-hit="true"]'))
    .map((el) => MONO(el.textContent));

  const rows = [];
  if (tiandi) {
    Array.from(tiandi.querySelectorAll('table.mtbl tbody > tr'))
      .filter((tr) => tr.querySelectorAll(':scope > td').length === 3)
      .forEach((tr, index) => {
        const hits = hitTexts(tr);
        rows.push({
          index,
          issue: cellText(tr, 0),
          content: cellText(tr, 1),
          result: cellText(tr, 2),
          hits,
          // 命中标记必须真的带黄底（属性和背景色同生共死）。
          hitsYellow: hits.length > 0 && Array.from(tr.querySelectorAll('[data-prediction-hit="true"]'))
            .every((el) => isYellow(el)),
        });
      });
  }

  // (a) 标记属性必须与黄底一致：带属性却没黄底 = 幽灵标记。
  const ghostMarkers = [];
  document.querySelectorAll('[data-prediction-hit]').forEach((el) => {
    if (!isYellow(el)) ghostMarkers.push({ text: MONO(el.textContent).slice(0, 30), bg: getComputedStyle(el).backgroundColor });
  });

  // (b) 页面上任何「相对父节点新增」的黄底都必须来自命中标记（模板残留黄底 = 杂散）。
  const strayYellow = [];
  document.querySelectorAll('*').forEach((el) => {
    if (el.hasAttribute('data-prediction-hit')) return;
    if (!isYellow(el)) return;
    const parent = el.parentElement;
    if (parent && isYellow(parent)) return;
    strayYellow.push({
      text: MONO(el.textContent).slice(0, 30),
      cls: String(el.className || ''),
    });
  });

  // (c) 全页：判定为「错」或「待开奖」的行不得带任何命中标记。
  const wrongWithHighlight = [];
  const pendingWithHighlight = [];
  Array.from(document.querySelectorAll('.mtbl tbody > tr')).forEach((tr) => {
    const hits = hitTexts(tr);
    if (!hits.length) return;
    const text = MONO(tr.textContent);
    if (text.indexOf('错') >= 0) wrongWithHighlight.push({ text: text.slice(0, 80), hits });
    if (text.indexOf('待开奖') >= 0) pendingWithHighlight.push({ text: text.slice(0, 80), hits });
  });

  return {
    sectionFound: Boolean(tiandi),
    sectionTitle: tiandi ? MONO(tiandi.querySelector('.pb-tit').textContent) : '',
    rows,
    ghostMarkers,
    strayYellow,
    wrongWithHighlight,
    pendingWithHighlight,
    pageHitMarkers: document.querySelectorAll('[data-prediction-hit="true"]').length,
  };
}
"""


def row(issue, *, tiandi, pair, opened=True, code="", zodiac="", is_correct=None):
    result = {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct}
    return {
        "issue": issue,
        "term": issue[-3:],
        "prediction": {"tokens": [], "text": "%s+%s" % (tiandi, "".join(pair)), "extra": {}},
        "raw": {"tiandi": tiandi, "xiao_pair": list(pair)},
        "result": result,
    }


def build_modules():
    """270/269/267 = 已开奖对照，266 = 未开奖。

    所有 `isCorrect` 故意给 `False`：它只反映 vendor 对 `xiao` 两肖的比对结果
    （270/267 期两肖都没命中，命中落在天地组），用来证明适配器已本地复算而不依赖它。
    """
    modules = [
        {
            "moduleKey": "tiandi_2xiao",
            "title": "天地两肖",
            "display_style": "single-line",
            "rows": [
                # 270 天肖+兔鸡 开 37 马 → 马 ∈ 天肖组 → 对，只黄「天肖」；
                # 269 地肖+兔鸡 开 37 马 → 天地组与两肖都不含 → 错，零黄底；
                # 267 天肖+兔鸡 开 22 鸡 → 鸡 ∈ 两肖 → 对，只黄「鸡」；
                # 266 地肖+鼠虎 未开奖 → 待开奖，零黄底。
                row("2026270", tiandi="天肖", pair=["兔", "鸡"], code="37", zodiac="马", is_correct=False),
                row("2026269", tiandi="地肖", pair=["兔", "鸡"], code="37", zodiac="马", is_correct=False),
                row("2026267", tiandi="天肖", pair=["兔", "鸡"], code="22", zodiac="鸡", is_correct=False),
                row("2026266", tiandi="地肖", pair=["鼠", "虎"], opened=False),
            ],
        },
    ]
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
    httpd, port = serve(WEB_ROOT)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            page = browser.new_page(viewport={"width": 480, "height": 1600})
            page.route(
                "**/lottery-site-data-client.js",
                lambda route: route.fulfill(status=200, content_type="application/javascript", body=STUB_CLIENT),
            )
            for pattern in STUBBED_EMPTY:
                page.route(pattern, lambda route: route.fulfill(
                    status=200, content_type="application/javascript", body=""))
            page.add_init_script(f"window.__CONTRACT_MODULES__ = {json.dumps(build_modules())};")
            page.goto(f"http://127.0.0.1:{port}/vendor/twbst528/index.html", wait_until="load")
            page.wait_for_timeout(1200)
            data = page.evaluate(PROBE_JS)
            browser.close()
    finally:
        httpd.shutdown()
    return data


def main() -> None:
    data = render_probe()
    problems: list[str] = []

    if not data["sectionFound"]:
        print("FAIL: 未找到【天地+②肖】板块（.pb-tit 里没有【天地+②肖】）")
        raise SystemExit(1)

    def check(index, expect_content, expect_issue, expect_result, expect_hits, label):
        rows = data["rows"]
        if len(rows) <= index:
            problems.append(f"{label}: 第 {index} 行未渲染")
            return
        item = rows[index]
        if expect_content is not None and item["content"] != expect_content:
            problems.append(f"{label}: 内容应为『{expect_content}』，实际 '{item['content']}'")
        if expect_issue is not None and item["issue"] != expect_issue:
            problems.append(f"{label}: 期号应为『{expect_issue}』，实际 '{item['issue']}'")
        if expect_result is not None and item["result"] != expect_result:
            problems.append(f"{label}: 判定应为『{expect_result}』，实际 '{item['result']}'")
        if sorted(item["hits"]) != sorted(expect_hits):
            problems.append(f"{label}: 高亮应为 {expect_hits}，实际 {item['hits']}")
        if item["hits"] and not item["hitsYellow"]:
            problems.append(f"{label}: 命中标记没有黄底（属性/背景色不一致）")

    # ── 判定口径：特肖 ∈ 天地组 ∪ 两肖；只点亮命中项 ────────────────────
    check(0, "天肖+兔鸡", "第270期", "开:37马对", ["天肖"],
          "天地+②肖 270期（天肖+兔鸡，开37马 → 天地组命中）")
    check(1, "地肖+兔鸡", "第269期", "开:37马错", [],
          "天地+②肖 269期（地肖+兔鸡，开37马 → 都不含）")
    check(2, "天肖+兔鸡", "第267期", "开:22鸡对", ["鸡"],
          "天地+②肖 267期（天肖+兔鸡，开22鸡 → 两肖命中）")
    check(3, "地肖+鼠虎", "第266期", "开:待开奖", [],
          "天地+②肖 266期（未开奖）")

    # ── 全页：错期 / 未开奖期不得有黄底 ─────────────────────────────────
    for item in data["wrongWithHighlight"]:
        problems.append(f"错期仍有命中标记: {item['text']} → {item['hits']}")
    for item in data["pendingWithHighlight"]:
        problems.append(f"未开奖期仍有命中标记: {item['text']} → {item['hits']}")
    for item in data["ghostMarkers"]:
        problems.append(f"幽灵命中标记（无黄底）: {item['text']} bg={item['bg']}")
    for item in data["strayYellow"]:
        problems.append(f"非命中标记的黄底: <{item['cls']}> {item['text']}")

    print(f"板块: {data['sectionTitle']}；行数: {len(data['rows'])}；"
          f"全页命中标记: {data['pageHitMarkers']}")
    for item in data["rows"][:4]:
        print(f"  行{item['index']}: {item['issue']} | {item['content']} | {item['result']} "
              f"| hits={item['hits']}")
    print(f"错期带标记: {len(data['wrongWithHighlight'])}；未开奖带标记: {len(data['pendingWithHighlight'])}；"
          f"幽灵标记: {len(data['ghostMarkers'])}；杂散黄底: {len(data['strayYellow'])}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwbst528-tiandi-display-contract: OK"
          "（天地组∪两肖并集判定 + 只标命中项 + 错/未开奖零黄底）")


if __name__ == "__main__":
    main()
