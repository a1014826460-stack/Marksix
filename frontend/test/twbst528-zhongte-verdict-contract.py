"""twbst528【吉美丑凶】【③肖防③码】【前后中特】的判定口径契约（DOM 级）。

背景（2026-10-01 用户报障，274 期）：
  · 【吉美丑凶】「丑凶肖【牛蛇鼠】」开 24 羊 → 页面显示「对」（应为「错」）；
    273 期「吉美肖【鸡牛龙】」开 19 鼠 → 同样显示「对」（应为「错」）。
  · 【③肖防③码】「牛蛇鼠+牛,蛇,鼠」开 24 羊 → 显示「对」（应为「错」）；
    273 期「鸡牛龙+…」开 19 鼠 → 同样显示「对」（应为「错」）。
  · 【前后中特】「后肖」开 24 羊 → 显示「错」（应为「对」，羊 ∈ 后肖 = 马羊猴鸡狗猪）；
    273 期「前肖」开 19 鼠 → 同样显示「错」（应为「对」，鼠 ∈ 前肖）。

根因：三个面板都不是平特玩法，展示的就是本期押的生肖 / 前后分组，命中口径必须是
**特肖落在展示候选里**；但它们的两个数据源模块判的是别的口径：
  · `pt3xiao`（平特3肖，mode 470）后端是七码平特口径 → 三个生肖里只要有一个以平码开出
    就判「对」（274 期开奖七个号码里含牛/蛇/鼠，于是两块面板 20 期里 19 期恒「对」）；
  · `qianhou_texiao`（前后特肖，mode 219）后端只比 `xiao` 那 2 肖 → 展示的是「后肖」，
    特肖是羊却判「错」。

正确口径（供应商模板的对/错列逐个可复核，见 `site-data-adapter.js` 上方
「面板级中特口径」注释）：
  · 吉美丑凶 / ③肖防③码：特肖 ∈ 展示的三肖，或（有真号码时）特码 ∈ 展示的码组；
  · 前后中特：特肖 ∈ 展示的「前肖/后肖」分组成员（成员从行内容解析，缺成员时才退回图例）。

本契约**故意**把两个数据源模块的 `result.isCorrect` 设成「接口口径的错误答案」：
凡是本地判定与接口判定不同的期次，只要页面显示的是本地判定，就证明适配器没有沿用接口值。

不连线上、不连数据库：本地静态服务（`frontend/public`）+ 桩 `lottery-site-data-client`
+ `add_init_script` 注入合成 payload + Playwright headless Chrome 真跑适配器后断言 DOM。

运行：$env:PYTHONIOENCODING='utf-8'; python frontend/test/twbst528-zhongte-verdict-contract.py
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
# 数组型 `canonical_modules`，所以桩要返回 `{ state, data: { data: { canonical_modules } } }`。
STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      clear: function () {},
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { data: { issue: "2026274" } } }); },
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
  // 供应商 candidate-column CSS（home.css `.mtbl td:nth-child(2) span`）会把**没有内联底色**
  // 的 span 染成芥末黄 #d1be18 —— 与审计脚本同口径，计入「黄底」。
  const MUSTARD = (v) => ['rgb(209, 190, 24)', '#d1be18']
    .includes(String(v || '').replace(/\s+/g, ' ').toLowerCase());
  const isYellow = (el) => Boolean(el) && (YELLOW(getComputedStyle(el).backgroundColor)
    || MUSTARD(getComputedStyle(el).backgroundColor));
  const isRendered = (el) => Boolean(el) && el.getClientRects().length > 0;

  const sections = Array.from(document.querySelectorAll('.lxlm, .tzlb'));
  const sectionByTitle = (title) => sections.filter((el) => {
    const head = el.querySelector('.pb-tit');
    return head && String(head.textContent || '').indexOf('【' + title + '】') >= 0;
  })[0] || null;

  const cellText = (tr, i) => {
    const td = tr.querySelectorAll(':scope > td')[i];
    return MONO(td ? td.textContent : '');
  };
  const hitTexts = (scope) => Array.from(scope.querySelectorAll('[data-prediction-hit="true"]'))
    .map((el) => MONO(el.textContent));

  const threeColumnRows = (section) => section
    ? Array.from(section.querySelectorAll('table.mtbl tbody > tr')).filter((tr) => (
        tr.querySelectorAll(':scope > td').length === 3 && /\d+\s*期/.test(cellText(tr, 0))
      ))
    : [];

  const cardRows = (section) => section
    ? Array.from(section.querySelectorAll('table tbody > tr')).filter((tr) => /\d+\s*期/.test(MONO(tr.textContent)))
    : [];

  const collect = (tr, contentIndex, resultIndex, total) => {
    const hits = hitTexts(tr);
    const result = total === 1 ? MONO(tr.textContent) : cellText(tr, resultIndex);
    return {
      issue: total === 1 ? '' : cellText(tr, 0),
      content: total === 1 ? '' : cellText(tr, contentIndex),
      result: MONO(result),
      text: MONO(tr.textContent),
      hits,
      hitsYellow: hits.length > 0 && Array.from(tr.querySelectorAll('[data-prediction-hit="true"]'))
        .every((el) => isYellow(el)),
    };
  };

  // ③肖防③码 是单格卡片：期号写在卡片头 `<p><b>` 里，候选行在卡片头之后的 `<span>` 里。
  const collectCard = (tr) => {
    const cell = tr.querySelector('td');
    const detail = cell && cell.querySelector(':scope > span');
    const term = /(\d+)\s*期/.exec(MONO(tr.textContent));
    const item = collect(tr, 1, 1, 1);
    item.issue = term ? term[1] : '';
    item.content = detail ? MONO(detail.textContent) : '';
    return item;
  };

  const output = { panels: {}, ghostMarkers: [], strayYellow: [], wrongWithHighlight: [], pendingWithHighlight: [] };

  const jimei = sectionByTitle('吉美丑凶');
  output.panels.jimei = { found: Boolean(jimei), title: jimei ? MONO(jimei.querySelector('.pb-tit').textContent) : '',
    rows: threeColumnRows(jimei).map((tr) => collect(tr, 1, 2, 3)) };

  // ③肖防③码 是单格卡片（期号 + 开奖段 + 候选行都在同一个 <td> 里）。
  const fangma = sectionByTitle('③肖防③码');
  output.panels.fangma = { found: Boolean(fangma), title: fangma ? MONO(fangma.querySelector('.pb-tit').textContent) : '',
    rows: cardRows(fangma).map(collectCard) };

  const qianhou = sectionByTitle('前后中特');
  output.panels.qianhou = { found: Boolean(qianhou), title: qianhou ? MONO(qianhou.querySelector('.pb-tit').textContent) : '',
    rows: threeColumnRows(qianhou).map((tr) => collect(tr, 1, 2, 3)) };

  document.querySelectorAll('[data-prediction-hit]').forEach((el) => {
    if (!isRendered(el)) return;
    if (!isYellow(el)) output.ghostMarkers.push({ text: MONO(el.textContent).slice(0, 30), bg: getComputedStyle(el).backgroundColor });
  });

  document.querySelectorAll('*').forEach((el) => {
    if (el.hasAttribute('data-prediction-hit')) return;
    if (!isRendered(el)) return;
    if (!isYellow(el)) return;
    const parent = el.parentElement;
    if (parent && isYellow(parent)) return;
    output.strayYellow.push({ text: MONO(el.textContent).slice(0, 30), cls: String(el.className || '') });
  });

  Array.from(document.querySelectorAll('.mtbl tbody > tr, .lxlm table tbody > tr')).forEach((tr) => {
    if (!isRendered(tr)) return;
    const hits = hitTexts(tr);
    if (!hits.length) return;
    const text = MONO(tr.textContent);
    if (text.indexOf('错') >= 0) output.wrongWithHighlight.push({ text: text.slice(0, 80), hits });
    if (text.indexOf('待开奖') >= 0) output.pendingWithHighlight.push({ text: text.slice(0, 80), hits });
  });

  return output;
}
"""


def row_pt3xiao(term, tokens, *, code="", zodiac="", is_correct=None, opened=True):
    """mode 470（平特3肖）的行：`prediction.tokens` = 三个生肖（`三肖六码` 形态再加码组）。

    `is_correct` 故意填**接口口径**（七码平特）的答案，用来证明适配器已本地复算。
    """
    text = ",".join(tokens)
    return {
        "issue": "2026" + term,
        "term": term,
        "prediction": {"tokens": tokens, "text": text, "extra": {"content": text}},
        "raw": {"content": text},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


def row_qianhou(term, label, members, *, pair, code="", zodiac="", is_correct=None, opened=True):
    """mode 219（前后特肖）的行：正文标签 `后肖|马,羊,猴,鸡,狗,猪` + `xiao` 两肖。"""
    content = "%s|%s" % (label, ",".join(members))
    return {
        "issue": "2026" + term,
        "term": term,
        "prediction": {"tokens": ['["%s"]' % content], "text": '["%s"]' % content, "extra": {"content": json.dumps([content], ensure_ascii=False)}},
        "raw": {"content": json.dumps([content], ensure_ascii=False), "xiao": ",".join(pair)},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


HOU = ["马", "羊", "猴", "鸡", "狗", "猪"]
QIAN = ["鼠", "牛", "虎", "兔", "龙", "蛇"]


def build_modules():
    """合成 payload：两个数据源模块 + 用户报障的期次。

    pt3xiao（= 吉美丑凶 与 ③肖防③码 的共同数据源）：
      274「牛蛇鼠」开 24 羊 → 两个面板都必须「错」（接口给 True）；
      273「鸡牛龙」开 19 鼠 → 同上（接口给 True）；
      272「虎猴鼠」开 11 猴 → 必须「对」并点亮「猴」（接口给 False）；
      271「龙蛇兔」+ 码组 11/23/35，开 23 猴 → 必须「对」并点亮码「23」；
      270 未开奖 → 「待开奖」零黄底。
    qianhou_texiao（= 前后中特）：
      274「后肖」开 24 羊 → 必须「对」并点亮「后肖」（接口给 False）；
      273「前肖」开 19 鼠 → 必须「对」并点亮「前肖」（接口给 False）；
      272「后肖」开 41 牛 → 必须「错」零黄底（接口给 True）；
      271 未开奖 → 「待开奖」零黄底；
      270「后肖」内容里只列了「马,羊」两个成员，开 35 猴 → 必须按**行内容**判「错」
          （写死分组表会误判成「对」）。
    """
    return [
        {
            "moduleKey": "pt3xiao",
            "title": "平特3肖",
            "display_style": "three-column",
            "rows": [
                row_pt3xiao("274", ["牛", "蛇", "鼠"], code="24", zodiac="羊", is_correct=True),
                row_pt3xiao("273", ["鸡", "牛", "龙"], code="19", zodiac="鼠", is_correct=True),
                row_pt3xiao("272", ["虎", "猴", "鼠"], code="11", zodiac="猴", is_correct=False),
                row_pt3xiao("271", ["龙", "蛇", "兔", "11", "23", "35"], code="23", zodiac="猴", is_correct=False),
                row_pt3xiao("270", ["马", "羊", "猴"], opened=False),
            ],
        },
        {
            "moduleKey": "qianhou_texiao",
            "title": "前后特肖",
            "display_style": "three-column",
            "rows": [
                row_qianhou("274", "后肖", HOU, pair=["鼠", "猴"], code="24", zodiac="羊", is_correct=False),
                row_qianhou("273", "前肖", QIAN, pair=["马", "虎"], code="19", zodiac="鼠", is_correct=False),
                row_qianhou("272", "后肖", HOU, pair=["羊", "马"], code="41", zodiac="牛", is_correct=True),
                row_qianhou("271", "前肖", QIAN, pair=["鼠", "牛"], opened=False),
                row_qianhou("270", "后肖", ["马", "羊"], pair=["马", "羊"], code="35", zodiac="猴", is_correct=True),
            ],
        },
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

    for key, label in (("jimei", "吉美丑凶"), ("fangma", "③肖防③码"), ("qianhou", "前后中特")):
        panel = data["panels"][key]
        if not panel["found"]:
            print(f"FAIL: 未找到【{label}】板块")
            raise SystemExit(1)

    def check(panel_key, label, index, *, expect_issue=None, expect_content=None,
              expect_result, expect_hits):
        rows = data["panels"][panel_key]["rows"]
        if len(rows) <= index:
            problems.append(f"{label}: 第 {index} 行未渲染")
            return
        item = rows[index]
        if expect_issue is not None and item["issue"] != expect_issue:
            problems.append(f"{label}: 期号应为『{expect_issue}』，实际 '{item['issue']}'")
        if expect_content is not None and expect_content not in item["text"]:
            problems.append(f"{label}: 候选应含『{expect_content}』，实际 '{item['content']}'")
        if expect_result not in item["result"]:
            problems.append(f"{label}: 判定应为『{expect_result}』，实际 '{item['result']}'")
        if sorted(item["hits"]) != sorted(expect_hits):
            problems.append(f"{label}: 高亮应为 {expect_hits}，实际 {item['hits']}")
        if item["hits"] and not item["hitsYellow"]:
            problems.append(f"{label}: 命中标记没有黄底（属性/背景色不一致）")

    # ── 【吉美丑凶】：特肖 ∈ 展示三肖（272 命中）/ 码组（271 命中）──────────
    # 274/273 的接口 `isCorrect=True`（七码平特口径），本地判定必须是「错」。
    check("jimei", "吉美丑凶 274", 0, expect_issue="第274期", expect_content="丑凶肖【牛蛇鼠】",
          expect_result="开:24羊错", expect_hits=[])
    check("jimei", "吉美丑凶 273", 1, expect_issue="第273期", expect_content="吉美肖【鸡牛龙】",
          expect_result="开:19鼠错", expect_hits=[])
    # 272 的接口 `isCorrect=False`，本地判定必须是「对」并点亮「猴」。
    check("jimei", "吉美丑凶 272", 2, expect_issue="第272期", expect_content="丑凶肖【虎猴鼠】",
          expect_result="开:11猴对", expect_hits=["猴"])
    # 271 是「三肖六码」形态：特肖猴不在三肖里，但特码 23 在码组里 → 对，点亮码「23」。
    check("jimei", "吉美丑凶 271", 3, expect_issue="第271期", expect_content="【11-23-35】",
          expect_result="开:23猴对", expect_hits=["23"])
    check("jimei", "吉美丑凶 270", 4, expect_issue="第270期", expect_result="待开奖", expect_hits=[])

    # ── 【③肖防③码】：生肖 +（有真号码时的）防码 ─────────────────────────
    check("fangma", "③肖防③码 274", 0, expect_issue="274", expect_content="牛蛇鼠+牛,蛇,鼠",
          expect_result="24羊错", expect_hits=[])
    check("fangma", "③肖防③码 273", 1, expect_issue="273", expect_content="鸡牛龙+鸡,牛,龙",
          expect_result="19鼠错", expect_hits=[])
    check("fangma", "③肖防③码 272", 2, expect_issue="272", expect_content="虎猴鼠+虎,猴,鼠",
          expect_result="11猴对", expect_hits=["猴"])
    # 271 的码组是真号码（11/23/35），特码 23 命中防码 → 对，点亮「23」。
    check("fangma", "③肖防③码 271", 3, expect_issue="271", expect_content="龙蛇兔+11.23.35",
          expect_result="23猴对", expect_hits=["23"])

    # ── 【前后中特】：特肖 ∈ 展示的「前肖/后肖」分组成员 ──────────────────
    # 274/273 的接口 `isCorrect=False`（只比 xiao 两肖），本地判定必须是「对」。
    check("qianhou", "前后中特 274", 0, expect_issue="第274期", expect_content="后肖",
          expect_result="开:24羊对", expect_hits=["后肖"])
    check("qianhou", "前后中特 273", 1, expect_issue="第273期", expect_content="前肖",
          expect_result="开:19鼠对", expect_hits=["前肖"])
    # 272 的接口 `isCorrect=True`，本地判定必须是「错」（牛 ∉ 后肖）。
    check("qianhou", "前后中特 272", 2, expect_issue="第272期", expect_content="后肖",
          expect_result="开:41牛错", expect_hits=[])
    check("qianhou", "前后中特 271", 3, expect_issue="第271期", expect_result="待开奖", expect_hits=[])
    # 270 的行内容只列了「马,羊」两个成员（不是标准 6 肖）：必须按行内容判「错」，
    # 写死分组表（后肖 = 马羊猴鸡狗猪）会误判成「对」。
    check("qianhou", "前后中特 270", 4, expect_issue="第270期", expect_content="后肖",
          expect_result="开:35猴错", expect_hits=[])

    # ── 全页：错期 / 未开奖期不得有黄底；不得有幽灵标记与模板残留黄底 ──────
    for item in data["wrongWithHighlight"]:
        problems.append(f"错期仍有命中标记: {item['text']} → {item['hits']}")
    for item in data["pendingWithHighlight"]:
        problems.append(f"未开奖期仍有命中标记: {item['text']} → {item['hits']}")
    for item in data["ghostMarkers"]:
        problems.append(f"幽灵命中标记（无黄底）: {item['text']} bg={item['bg']}")
    for item in data["strayYellow"]:
        problems.append(f"非命中标记的黄底: <{item['cls']}> {item['text']}")

    for key, label in (("jimei", "吉美丑凶"), ("fangma", "③肖防③码"), ("qianhou", "前后中特")):
        panel = data["panels"][key]
        print(f"{label}: {panel['title']}（{len(panel['rows'])} 行）")
        for item in panel["rows"][:5]:
            print(f"  {item['issue'] or '-'} | {item['content'] or '-'} | {item['result']} | hits={item['hits']}")
    print(f"错期带标记: {len(data['wrongWithHighlight'])}；未开奖带标记: {len(data['pendingWithHighlight'])}；"
          f"幽灵标记: {len(data['ghostMarkers'])}；杂散黄底: {len(data['strayYellow'])}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwbst528-zhongte-verdict-contract: OK"
          "（三肖面板按特肖/防码判中特 + 前后中特按展示分组判定 + 只标命中项 + 错/未开奖零黄底）")


if __name__ == "__main__":
    main()
