"""twsyw 男女中特（`#nannv`，mode 5 天地生肖）判定口径 + 只标命中项契约。

背景（2026-09-29）：`frontend/public/vendor/twsyw/site-data-adapter.js` 的 `renderNannv()`
过去用 `source.result.isCorrect === true` 判定，而 vendor/接口的 `is_correct` 只比对 mode 5
的 `xiao` 列（后端 `mechanisms.py` 里 `title_5` 的 `hit_checker=contains_hit`，候选就是
「生肖选 2」），天地组（天肖/地肖各 6 肖）永远不参与判定 —— 于是「天肖里含开奖特肖」的期
显示「错」（270 期「天肖+兔鸡」开 37 马）。

正确口径（与 twwanli `#tdsx`、twcaibawang 一致）：特肖落在 **天肖/地肖分组（6 肖）∪
本期 2 个候选生肖** 任一即算命中；命中时只点亮真正命中的那一项（命中两肖 → 点亮该生肖；
命中天地组 → 点亮组名）；未命中/未开奖零黄底。

断言用的合成分组与 `public.fixed_data` sign='天地肖' 及各站 sx.html 一致：
天肖 = 兔马猴猪牛龙；地肖 = 鼠虎蛇羊鸡狗。

不连线上、不连数据库：本地静态服务（`frontend/public`）+ 桩 `lottery-site-data-client`
+ `add_init_script` 注入合成 payload + Playwright headless Chrome 真跑适配器后断言 DOM。

运行：python frontend/test/twsyw-display-contract.py
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

# twsyw 适配器的 `modulesByKey()` 读 `envelope.data.data.canonical_modules`
# （回退 `envelope.data.data.modules`），客户端再包一层 `data`，所以桩要返回
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
  const rowsOf = (root) => Array.from(root.querySelectorAll('tr'))
    .filter((tr) => tr.querySelector('[data-prediction-issue], [data-prediction-content], [data-prediction-result]'))
    .map((tr) => ({
      text: MONO(tr.textContent),
      issue: MONO((tr.querySelector('[data-prediction-issue]') || {}).textContent || ''),
      content: MONO((tr.querySelector('[data-prediction-content]') || {}).textContent || ''),
      result: MONO((tr.querySelector('[data-prediction-result]') || {}).textContent || ''),
      hits: Array.from(tr.querySelectorAll('[data-prediction-hit="true"]')).map((el) => MONO(el.textContent)),
    }));

  const nannv = rowsOf(document.querySelector('#nannv'));

  // 「错」/「待开奖」的槽位不得出现黄底（黄底只允许来自 data-prediction-hit 标记）。
  const wrongWithHighlight = [];
  const pendingWithHighlight = [];
  Array.from(document.querySelectorAll('[data-prediction-result]')).forEach((node) => {
    const text = MONO(node.textContent);
    const scope = node.closest('tr') || node.parentElement;
    if (!scope) return;
    const hits = Array.from(scope.querySelectorAll('[data-prediction-hit="true"]')).map((el) => MONO(el.textContent));
    if (!hits.length) return;
    if (text.indexOf('错') >= 0) wrongWithHighlight.push({ result: text, hits });
    if (text.indexOf('待开奖') >= 0) pendingWithHighlight.push({ result: text, hits });
  });

  // 所有黄底（含供应商残留）——必须只来自命中标记。
  const strayYellow = [];
  document.querySelectorAll('*').forEach((el) => {
    if (el.hasAttribute('data-prediction-hit')) return;
    const cs = getComputedStyle(el);
    const ps = el.parentElement ? getComputedStyle(el.parentElement) : null;
    const norm = (v) => String(v || '').replace(/\s+/g, '').toLowerCase();
    const yellow = (v) => ['rgb(255,255,0)', 'rgba(255,255,0,1)', '#ffff00', '#ff0', 'yellow'].includes(norm(v));
    if (yellow(cs.backgroundColor) && !(ps && yellow(ps.backgroundColor))) {
      strayYellow.push({ text: MONO(el.textContent).slice(0, 30), cls: String(el.className || '') });
    }
  });

  return {
    nannv,
    nannvHitSlots: Array.from(document.querySelectorAll('#nannv [data-prediction-hit="true"]')).map((el) => MONO(el.textContent)),
    wrongWithHighlight,
    pendingWithHighlight,
    strayYellow,
    totalHits: document.querySelectorAll('[data-prediction-hit="true"]').length,
    contentSlots: document.querySelectorAll('[data-prediction-content]').length,
  };
}
"""


def row(issue, *, tokens=None, text=None, raw=None, opened=True, code="", zodiac="", is_correct=None):
    return {
        "issue": issue,
        "prediction": {"tokens": tokens if tokens is not None else [], "text": text or ""},
        "raw": raw or {},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


def build_modules():
    """270/269/267 = 已开奖对照，266 = 未开奖。

    所有 `isCorrect` 故意给 `False`：它只反映 vendor 对 `xiao` 两肖的比对结果
    （270/267 期两肖都没命中，天地组才算命中），用来证明适配器已本地复算。
    """
    tian = "天肖|兔,马,猴,猪,牛,龙"
    di = "地肖|鼠,虎,蛇,羊,鸡,狗"
    modules = [
        # 男女中特（title_5）：候选 = 天地组(content) + 两肖(xiao)。
        # 270 天肖+兔鸡 开 37 马 → 马 ∈ 天肖组 → 对，只黄「天肖」；
        # 269 地肖+兔鸡 开 37 马 → 都不含 → 错，零黄底；
        # 267 天肖+兔鸡 开 22 鸡 → 鸡 ∈ 两肖 → 对，只黄「鸡」；
        # 266 地肖+鼠虎 未开奖 → 待开奖，零黄底。
        {"moduleKey": "title_5", "rows": [
            row("2026270", tokens=[tian], raw={"content": '["%s"]' % tian, "xiao": "兔,鸡"},
                code="37", zodiac="马", is_correct=False),
            row("2026269", tokens=[di], raw={"content": '["%s"]' % di, "xiao": "兔,鸡"},
                code="37", zodiac="马", is_correct=False),
            row("2026267", tokens=[tian], raw={"content": '["%s"]' % tian, "xiao": "兔,鸡"},
                code="22", zodiac="鸡", is_correct=False),
            row("2026266", tokens=[di], raw={"content": '["%s"]' % di, "xiao": "鼠,虎"},
                opened=False),
        ]},
    ]
    # 与 twwanli 契约同口径：`needsPredictionRefresh` 要求这几个 moduleKey 非空，
    # 否则会走清缓存重试分支（twsyw 现版本没有该分支，仍一并提供以防日后接入）。
    for key in ("6xzt", "pt1wei", "sitouzhongte"):
        modules.append({"moduleKey": key, "rows": [row("2026270", tokens=["鼠"], code="37", zodiac="马", is_correct=True)]})
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
            page = browser.new_page(viewport={"width": 480, "height": 1400})
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
            page.goto(f"http://127.0.0.1:{port}/vendor/twsyw/index.html", wait_until="load")
            page.wait_for_timeout(1200)
            data = page.evaluate(PROBE_JS)
            browser.close()
    finally:
        httpd.shutdown()
    return data


def main() -> None:
    data = render_probe()
    problems: list[str] = []

    def check(rows, index, expect_content, expect_issue, expect_result, expect_hits, label):
        if len(rows) <= index:
            problems.append(f"{label}: 第 {index} 行未渲染")
            return
        item = rows[index]
        if expect_content is not None and expect_content not in item["content"]:
            problems.append(f"{label}: 内容应为『{expect_content}』，实际 '{item['content']}'")
        if expect_issue is not None and item["issue"] != expect_issue:
            problems.append(f"{label}: 期号应为『{expect_issue}』，实际 '{item['issue']}'")
        if expect_result is not None and item["result"] != expect_result:
            problems.append(f"{label}: 判定应为『{expect_result}』，实际 '{item['result']}'")
        if sorted(item["hits"]) != sorted(expect_hits):
            problems.append(f"{label}: 高亮应为 {expect_hits}，实际 {item['hits']}（{item['text']}）")

    nannv = data["nannv"]

    # ── 判定口径：特肖 ∈ 天地组 ∪ 两肖 ─────────────────────────────────
    check(nannv, 0, "天肖+兔鸡", "2026270期", "开:37马对", ["天肖"],
          "男女中特 270期（天肖+兔鸡，开37马 → 天地组命中）")
    check(nannv, 1, "地肖+兔鸡", "2026269期", "开:37马错", [],
          "男女中特 269期（地肖+兔鸡，开37马 → 都不含）")
    check(nannv, 2, "天肖+兔鸡", "2026267期", "开:22鸡对", ["鸡"],
          "男女中特 267期（天肖+兔鸡，开22鸡 → 两肖命中）")
    check(nannv, 3, "地肖+鼠虎", "2026266期", "开:待开奖", [],
          "男女中特 266期（未开奖）")

    # ── 全页：错期 / 未开奖期不得有黄底 ─────────────────────────────────
    for item in data["wrongWithHighlight"]:
        problems.append(f"错期仍有黄底: {item['result']} → {item['hits']}")
    for item in data["pendingWithHighlight"]:
        problems.append(f"未开奖期仍有黄底: {item['result']} → {item['hits']}")
    for item in data["strayYellow"]:
        if "FFFF00" not in item["cls"]:
            problems.append(f"非命中标记的黄底: <{item['cls']}> {item['text']}")

    print(f"#nannv 行数: {len(nannv)}；内容槽位总数: {data['contentSlots']}；命中标记总数 {data['totalHits']}")
    for index, item in enumerate(nannv[:4]):
        print(f"  行{index}: {item['issue']} | {item['content']} | {item['result']} | hits={item['hits']}")
    print(f"错期带黄底: {len(data['wrongWithHighlight'])}；未开奖带黄底: {len(data['pendingWithHighlight'])}；"
          f"杂散黄底: {len(data['strayYellow'])}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwsyw-display-contract: OK（天地组∪两肖并集判定 + 只标命中项 + 错/未开奖零黄底）")


if __name__ == "__main__":
    main()
