"""twwanli 展示与判定契约：全模块居中 / 放大预测内容字号 / 只标命中项 / 三项判定口径。

覆盖用户报告的三个判定问题（2026-09-29）：
1. 【精准五行】270 期 `金+土+木` 开 37 马 应为「对」——37 的**号码五行**是木（不能
   用马的火肖），后端 `ELEMENT_NUMBER_GROUPS` 已按 fixed_data 修正；本契约断言渲染层
   忠实显示接口判定。
2. 【买啥开啥】〈〈家禽〉〉开 37 马 应为「对」——判定按 fixed_data 家禽/野兽**全组**
   （家禽=牛马羊鸡狗猪），不能用本期 jia/ye 的 4+4 子集反查。
   2026-09-29 起该模块的数据源是**后端模块「家野中特」mode 63**（moduleKey `title_63`，
   正文形如 `["家禽|牛,马,羊,鸡,狗,猪"]`：单个分类 + 该分类全组），不再读 title_14；
   本契约用「诱饵 title_14」桩断言页面不再依赖 title_14。
3. 【天地生肖】【天肖+兔鸡】开 37 马 应为「对」——特肖落在天地组或两肖任一即命中
   （vendor 只比对两肖）。

另有：全模块文字居中（含 6 个文章子页的样式块）、`[data-prediction-content]` 字号放大、
黄底只出现在命中项上（`[data-prediction-hit="true"]`），错/未开奖零黄底。

不连线上、不连数据库：本地静态服务 + 桩 `lottery-site-data-client` + 合成数据。

运行：python frontend/test/twwanli-display-contract.py
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

STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      clear: function () {},
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { issue: "2026270" } }); },
      loadPredictions: function () {
        // 适配器读 envelope.data.data.canonical_modules（客户端再包一层 data）。
        return Promise.resolve({ state: "ready", data: { data: { canonical_modules: window.__CONTRACT_MODULES__ || [] } } });
      }
    };
  }
};
"""

PROBE_JS = r"""
() => {
  const MONO = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const sectionRows = (id) => Array.from(document.querySelectorAll('#' + id + ' tr'))
    .filter((tr) => tr.querySelector('[data-prediction-issue], [data-prediction-content], [data-prediction-result]'))
    .map((tr) => ({
      text: MONO(tr.textContent),
      issue: MONO((tr.querySelector('[data-prediction-issue]') || {}).textContent || ''),
      content: MONO((tr.querySelector('[data-prediction-content]') || {}).textContent || ''),
      result: MONO((tr.querySelector('[data-prediction-result]') || {}).textContent || ''),
      hits: Array.from(tr.querySelectorAll('[data-prediction-hit="true"]')).map((el) => MONO(el.textContent)),
    }));

  const slots = Array.from(document.querySelectorAll('[data-prediction-issue], [data-prediction-content], [data-prediction-content-secondary], [data-prediction-result]'));
  const alignOffenders = [];
  slots.forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.textAlign !== 'center') {
      alignOffenders.push({ tag: el.tagName.toLowerCase(), attr: el.getAttributeNames().find((n) => n.startsWith('data-prediction')), align: cs.textAlign, text: MONO(el.textContent).slice(0, 24) });
    }
  });
  const contentFontSizes = Array.from(new Set(Array.from(document.querySelectorAll('[data-prediction-content]'))
    .map((el) => getComputedStyle(el).fontSize)));

  // 所有黄底（含供应商残留）——必须只来自命中标记
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
    msks: sectionRows('msks'),
    tdsx: sectionRows('tdsx'),
    jz5x: sectionRows('jz5x'),
    alignOffenders,
    contentFontSizes,
    strayYellow,
    totalHits: document.querySelectorAll('[data-prediction-hit="true"]').length,
  };
}
"""


def row(issue, *, tokens=None, text=None, raw=None, groups=None,
        opened=True, code="", zodiac="", is_correct=None):
    prediction = {"tokens": tokens if tokens is not None else [], "text": text or ""}
    if groups is not None:
        prediction["groups"] = groups
    return {
        "issue": issue,
        "prediction": prediction,
        "raw": raw or {},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


def build_modules():
    """270 = 用户报障期（37 马）；269 = 对照（未命中）；268 = 未开奖。"""
    modules = [
        # 买啥开啥（**mode 63 = 家野中特 → moduleKey `title_63`**）：正文是「单个分类 + 该分类全组」，
        # 展示那个分类、判定按 fixed_data 家禽/野兽 6+6 全组比对特肖。
        # 270 预测「家禽」+ 特肖马（马 ∈ 家禽全组）→ 准；这里故意把桩里的
        # `result.isCorrect` 置 false：判定必须本地按全组算，不能采信供应商字段。
        # 269 预测「野兽」+ 特肖马 → 错（isCorrect 反而给 true，同样不得采信）。
        # 268 未开奖 → 无判定、零高亮。
        {"moduleKey": "title_63", "rows": [
            row("2026270", tokens=["家禽|牛,马,羊,鸡,狗,猪"],
                text='["家禽|牛,马,羊,鸡,狗,猪"]',
                raw={"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
                code="37", zodiac="马", is_correct=False),
            row("2026269", tokens=["野兽|兔,猴,虎,蛇,鼠,龙"],
                text='["野兽|兔,猴,虎,蛇,鼠,龙"]',
                raw={"content": '["野兽|兔,猴,虎,蛇,鼠,龙"]'},
                code="37", zodiac="马", is_correct=True),
            row("2026268", tokens=["家禽|牛,马,羊,鸡,狗,猪"],
                text='["家禽|牛,马,羊,鸡,狗,猪"]',
                raw={"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}, opened=False),
        ]},
        # title_14（家禽野兽两组）是**诱饵桩**：【买啥开啥】不得再读它。
        # 这里给成明显不同的数据（期号 260-262、预测「野兽」、开奖分类「野兽」），
        # 一旦适配器退回按 title_14 渲染，下面「页面不再依赖 title_14」的断言必失败。
        # 只保留给 #jhtz 文章位（27.html）用的行数，避免影响其它段落。
        {"moduleKey": "title_14", "rows": [
            row("2026262", tokens=["野兽|鼠,虎,兔,龙"], text="野兽|鼠,虎,兔,龙;家禽|牛,马",
                raw={"jia": ["鼠", "虎", "兔", "龙"], "ye": ["牛", "马"],
                     "domestic_wild_prediction_category": "野兽",
                     "domestic_wild_category": "野兽"},
                code="37", zodiac="马", is_correct=True),
            row("2026261", tokens=["野兽|鼠,虎,兔,龙"], text="野兽|鼠,虎,兔,龙;家禽|牛,马",
                raw={"jia": ["鼠", "虎", "兔", "龙"], "ye": ["牛", "马"],
                     "domestic_wild_prediction_category": "野兽",
                     "domestic_wild_category": "野兽"},
                code="37", zodiac="马", is_correct=True),
            row("2026260", tokens=["野兽|鼠,虎,兔,龙"], text="野兽|鼠,虎,兔,龙;家禽|牛,马",
                raw={"jia": ["鼠", "虎", "兔", "龙"], "ye": ["牛", "马"],
                     "domestic_wild_prediction_category": "野兽",
                     "domestic_wild_category": "野兽"},
                code="37", zodiac="马", is_correct=True),
        ]},
        # 天地生肖（title_5）：270 「天肖+兔鸡」开 37 马 → 马 ∈ 天肖组 → 对；
        # 269 「地肖+兔鸡」开 37 马 → 都不含 → 错；267 「天肖+兔鸡」开 鸡 → 命中两肖之一 → 对。
        {"moduleKey": "title_5", "rows": [
            row("2026270", tokens=["天肖"], raw={"xiao": ["兔", "鸡"]}, code="37", zodiac="马", is_correct=False),
            row("2026269", tokens=["地肖"], raw={"xiao": ["兔", "鸡"]}, code="37", zodiac="马", is_correct=False),
            row("2026267", tokens=["天肖"], raw={"xiao": ["兔", "鸡"]}, code="22", zodiac="鸡", is_correct=False),
            # 268 未开奖：预测内容必须照常显示（天地组+两肖），只有开奖槽是待开奖。
            row("2026268", tokens=["天肖"], raw={"xiao": ["兔", "鸡"]}, opened=False),
        ]},
        # 精准五行（3hang）：接口（后端按号码五行修正后）判定为 对。
        {"moduleKey": "3hang", "rows": [
            row("2026270", tokens=["金", "土", "木"], code="37", zodiac="马", is_correct=True),
            row("2026269", tokens=["金", "水", "火"], code="37", zodiac="马", is_correct=False),
            row("2026268", tokens=["金", "水", "火"], opened=False),
        ]},
    ]
    # needsPredictionRefresh 要求这三个模块非空，否则会走重试分支
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
            page.route("**/forced-announcement.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=""))
            page.add_init_script(f"window.__CONTRACT_MODULES__ = {json.dumps(build_modules())};")
            page.goto(f"http://127.0.0.1:{port}/vendor/twwanli/index.html", wait_until="load")
            page.wait_for_timeout(1200)
            data = page.evaluate(PROBE_JS)

            subpages = {}
            for name in ("21.html", "22.html", "25.html", "26.html", "27.html", "28.html"):
                page.goto(f"http://127.0.0.1:{port}/vendor/twwanli/{name}", wait_until="domcontentloaded")
                page.wait_for_timeout(60)
                subpages[name] = page.evaluate(
                    "() => { const el = document.querySelector('[data-prediction-content]');"
                    " return el ? { align: getComputedStyle(el).textAlign, size: getComputedStyle(el).fontSize } : null; }"
                )
            data["subpages"] = subpages
            browser.close()
    finally:
        httpd.shutdown()
    return data


def main() -> None:
    data = render_probe()
    problems: list[str] = []

    # ── 1. 全模块居中 ────────────────────────────────────────────────────
    for item in data["alignOffenders"]:
        problems.append(f"槽位未居中: {item['attr']} align={item['align']} :: {item['text']}")
    for name, info in data["subpages"].items():
        if not info:
            problems.append(f"子页缺少预测内容槽: {name}")
        elif info["align"] != "center":
            problems.append(f"子页未居中: {name} align={info['align']}")

    # ── 3. 预测内容字号放大 ──────────────────────────────────────────────
    sizes = data["contentFontSizes"]
    for size in sizes:
        value = float(str(size).replace("px", "") or 0)
        if value < 26:
            problems.append(f"预测内容字号未放大: {size}（应为 26px）")
    if not sizes:
        problems.append("页面上没有 [data-prediction-content] 槽位")

    # ── 黄底只能在命中项上 ──────────────────────────────────────────────
    for item in data["strayYellow"]:
        if "FFFF00" not in item["cls"]:
            problems.append(f"非命中标记的黄底: <{item['cls']}> {item['text']}")

    # ── 2/5/6 判定 ──────────────────────────────────────────────────────
    def check(rows, index, expect_content, expect_verdict, expect_hits, label):
        if len(rows) <= index:
            problems.append(f"{label}: 第 {index} 行未渲染")
            return
        item = rows[index]
        if expect_content is not None and expect_content not in item["content"]:
            problems.append(f"{label}: 内容应为『{expect_content}』，实际 '{item['content']}'")
        if expect_verdict and expect_verdict not in item["text"]:
            problems.append(f"{label}: 判定应为『{expect_verdict}』，实际 '{item['text']}'")
        if sorted(item["hits"]) != sorted(expect_hits):
            problems.append(f"{label}: 高亮应为 {expect_hits}，实际 {item['hits']}（{item['text']}）")

    check(data["msks"], 0, "家禽", "准", ["家禽"],
          "买啥开啥 270期（mode63 title_63 家禽|牛,马,羊,鸡,狗,猪 + 特肖马 → 准）")
    check(data["msks"], 1, "野兽", "错", [],
          "买啥开啥 269期（mode63 预测野兽 + 特肖马 → 错，零黄底）")
    check(data["msks"], 2, "家禽", "？00", [],
          "买啥开啥 268期（未开奖 → 仍显示 mode63 已生成的预测「家禽」，开奖槽待开奖，零黄底）")

    # ── 预测内容与开奖状态解耦：未开奖期不得把「待开奖」写进预测内容槽 ──────
    # 后端 mode 63 对 2026272 已生成正文（线上实测 `["野兽|兔,猴,虎,蛇,鼠,龙"]`），
    # 旧实现 `!isOpened → 〈〈待开奖〉〉` 会把已生成的预测整块吞掉。
    adapter_path = REPO / "frontend" / "public" / "vendor" / "twwanli" / "site-data-adapter.js"
    adapter = adapter_path.read_text(encoding="utf-8")
    # 只匹配"带引号的代码用法"，避免误伤说明注释里的同一字面量。
    for token in ('"〈〈待开奖〉〉"', '"天地〈〈待开奖〉〉"'):
        if token in adapter:
            problems.append(f"适配器仍把「待开奖」写进预测内容槽: {token}")
    if "if (!parts.isOpened) {" not in adapter:
        problems.append("适配器缺少「未开奖期照常显示预测」的分支")

    # ── 买啥开啥：未开奖行不得出现判定（准/错），且零黄底 ────────────────
    if len(data["msks"]) > 2:
        unopened = data["msks"][2]
        for verdict in ("准", "错"):
            if verdict in unopened["result"] or verdict in unopened["content"]:
                problems.append(f"买啥开啥 268期未开奖不得显示判定，实际 '{unopened['text']}'")
        if unopened["hits"]:
            problems.append(f"买啥开啥 268期未开奖不得有高亮，实际 {unopened['hits']}")

    # ── 买啥开啥：数据源必须是 mode 63（title_63），页面不再依赖 title_14 ──
    # 桩里的 title_14 给的是 262/261/260 期、预测「野兽」的诱饵数据；只要页面仍然显示
    # mode 63 的期号与分类，就证明它读的是 title_63。
    DECOY_ISSUES = ("2026262", "2026261", "2026260")
    MODE63_ISSUES = ("2026270", "2026269", "2026268")
    for index, (expected_issue, decoy_issue) in enumerate(zip(MODE63_ISSUES, DECOY_ISSUES)):
        if len(data["msks"]) <= index:
            problems.append(f"买啥开啥: 第 {index} 行未渲染，无法校验数据源")
            continue
        issue = data["msks"][index]["issue"]
        if expected_issue not in issue:
            problems.append(f"买啥开啥: 第 {index} 行期号应来自 mode 63（{expected_issue}），实际 '{issue}'")
        if decoy_issue in issue:
            problems.append(f"买啥开啥: 第 {index} 行仍在读 title_14 诱饵数据（{decoy_issue}）")
    # 诱饵 title_14 的三行分类全是「野兽」，若页面退回 title_14，270 行会变成「野兽 + 错」。
    if len(data["msks"]) > 0:
        first = data["msks"][0]
        if "家禽" not in first["content"] or "错" in first["result"]:
            problems.append(f"买啥开啥 270期未按 mode 63 的家禽分类渲染：'{first['text']}'")

    check(data["tdsx"], 0, "天肖+兔鸡", "对", ["天肖"], "天地生肖 270期（天肖+兔鸡，开37马）")
    check(data["tdsx"], 1, "地肖+兔鸡", "错", [], "天地生肖 269期（地肖+兔鸡，开37马）")
    check(data["tdsx"], 2, "天肖+兔鸡", "对", ["鸡"], "天地生肖 267期（天肖+兔鸡，开22鸡）")
    if len(data["tdsx"]) > 3:
        check(data["tdsx"], 3, "天肖+兔鸡", "？00", [],
              "天地生肖 268期（未开奖 → 仍显示预测「天肖+兔鸡」，开奖槽待开奖，零黄底）")
    else:
        problems.append("天地生肖: 268 期（未开奖）未渲染，无法验证预测内容与开奖状态解耦")

    check(data["jz5x"], 0, "金+土+木", "对", ["金+土+木"], "精准五行 270期（金+土+木 开37马）")
    check(data["jz5x"], 1, "金+水+火", "错", [], "精准五行 269期（金+水+火 开37马）")

    print(f"居中检查: {len(data['alignOffenders'])} 处槽位非居中；预测内容字号集合 {sizes}")
    print(f"杂散黄底: {len(data['strayYellow'])} 处；命中标记总数 {data['totalHits']}")
    print(f"判定抽查: 买啥开啥 {len(data['msks'])} 行 / 天地生肖 {len(data['tdsx'])} 行 / 精准五行 {len(data['jz5x'])} 行")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwwanli-display-contract: OK（全模块居中 + 预测内容放大 + 只标命中项 + 三项判定正确）")


if __name__ == "__main__":
    main()
