"""twbst528【吉美丑凶】【③肖防③码】【前后中特】的权威 mode 绑定 + 判定口径契约（DOM 级）。

背景（2026-10-01）：
  用户报障三块面板的「对/错」不对（274 期【吉美丑凶】「丑凶肖【牛蛇鼠】」开 24 羊显示「对」、
  【③肖防③码】「牛蛇鼠+…」开 24 羊显示「对」、【前后中特】「后肖」开 24 羊显示「错」）。
  根因是这三块面板借用了别的模块的行：`pt3xiao`（平特3肖，七码平特口径 → 三肖面板 20 期里
  19 期恒「对」）与 `qianhou_texiao`（前后特肖，只比 `xiao` 列的 2 肖）。
  修法分两步，本契约覆盖第二步后的最终状态：

  1. 【吉美丑凶】← mode 155「吉美凶丑（2选1，全肖）」= `jimei_xiongchou`
     正文 `["凶丑肖|鼠,牛,虎,猴,狗,猪"]`；展示 `凶丑肖【鼠牛虎猴狗猪】`；
     命中 = 特肖 ∈ 该分组（与后端 outcome 把特肖映射成分组名 + `contains_hit` 同口径）。
  2. 【前后中特】← mode 133「前后生肖」= `qianhou_shengxiao`
     正文 `["后肖|马,羊,猴,鸡,狗,猪"]`；展示 `后肖`；命中 = 特肖 ∈ 该分组。
  3. 【③肖防③码】← mode 117「3肖4码」= `sanxiao_siwei_xiao`
     正文 `["虎|05","马|01","狗|09"]`；展示 `虎马狗+05.01.09`；命中 = 特肖 ∈ 3 肖
     （码组只展示 —— 号码半区在平台里属于 mode 123「4尾8码」，不参与 mode 117 判定）。

本契约把三个模块的 `result.isCorrect` **故意设成与本地判定相反**的错误答案，逐行证明页面
显示的是本地复算值；同时断言命中项的标黄、判定「错」/未开奖的零黄底、以及全页无幽灵标记 /
无模板残留黄底（含 `.mtbl td:nth-child(2) span` 的芥末黄兜底）。

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
  const YELLOW = (v) => ['rgb(255, 255, 0)', 'rgba(255, 255, 0, 1)', '#ffff00', '#ff0', 'yellow',
    'rgb(209, 190, 24)', '#d1be18'].includes(String(v || '').replace(/\s+/g, ' ').toLowerCase());
  const isYellow = (el) => Boolean(el) && YELLOW(getComputedStyle(el).backgroundColor);
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

  const collect = (tr, total, contentIndex, resultIndex) => {
    const hits = hitTexts(tr);
    return {
      issue: total === 1 ? '' : cellText(tr, 0),
      content: total === 1 ? '' : cellText(tr, contentIndex),
      result: total === 1 ? MONO(tr.textContent) : cellText(tr, resultIndex),
      text: MONO(tr.textContent),
      hits,
      hitsYellow: hits.length > 0 && Array.from(tr.querySelectorAll('[data-prediction-hit="true"]'))
        .every((el) => isYellow(el)),
    };
  };
  // ③肖防③码 是单格卡片：期号写在卡片头 `<p><b>`、候选行在紧随其后的 `<span>` 里。
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
    rows: threeColumnRows(jimei).map((tr) => collect(tr, 3, 1, 2)) };

  const fangma = sectionByTitle('③肖防③码');
  output.panels.fangma = { found: Boolean(fangma), title: fangma ? MONO(fangma.querySelector('.pb-tit').textContent) : '',
    rows: cardRows(fangma).map(collectCard) };

  const qianhou = sectionByTitle('前后中特');
  output.panels.qianhou = { found: Boolean(qianhou), title: qianhou ? MONO(qianhou.querySelector('.pb-tit').textContent) : '',
    rows: threeColumnRows(qianhou).map((tr) => collect(tr, 3, 1, 2)) };

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


HOU = "马,羊,猴,鸡,狗,猪"
QIAN = "鼠,牛,虎,兔,龙,蛇"
XIONG = "鼠,牛,虎,猴,狗,猪"
JIMEI = "兔,龙,蛇,马,羊,鸡"


def group_row(term, label, members, *, code="", zodiac="", is_correct=None, opened=True):
    """mode 155 / 133 的行：正文 `["分组名|成员生肖"]`（`content_parser` 取分组名当候选）。"""
    content = "%s|%s" % (label, members)
    text = json.dumps([content], ensure_ascii=False)
    return {
        "issue": "2026" + term,
        "term": term,
        "prediction": {"tokens": [content], "text": text, "extra": {"content": text}},
        "raw": {"content": text},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


def sanxiao_row(term, pairs, *, code="", zodiac="", is_correct=None, opened=True):
    """mode 117「3肖4码」的行：`["虎|05","马|01","狗|09"]`。"""
    tokens = [json.dumps(pair, ensure_ascii=False) for pair in pairs]
    text = "[%s]" % ", ".join(tokens)
    return {
        "issue": "2026" + term,
        "term": term,
        "prediction": {"tokens": list(pairs), "text": text, "extra": {"content": text}},
        "raw": {"content": text},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


def build_modules():
    """合成 payload（三个模块的 `isCorrect` 故意与本地判定相反）。

    jimei_xiongchou（155）：
      274 吉美肖 + 开 24 羊 → 对（接口给 False）
      273 凶丑肖 + 开 19 鼠 → 对（接口给 False）
      272 凶丑肖 + 开 12 羊 → 错（接口给 True）
      270 「丑凶肖」写法（本站面板文案）+ 开 35 猴 → 对（证明别名同样按成员判定）
      269 未开奖 → 待开奖
    qianhou_shengxiao（133）：
      274 后肖 + 开 24 羊 → 对（接口给 False）
      273 前肖 + 开 19 鼠 → 对（接口给 False）
      272 后肖 + 开 41 牛 → 错（接口给 True）
      271 未开奖 → 待开奖
      270 内容只列「马,羊」两个成员 + 开 35 猴 → 必须按**行内容**判「错」
    sanxiao_siwei_xiao（117）：
      274 虎马狗 + 开 37 马 → 对（接口给 False），只点亮「马」
      273 牛蛇鼠 + 开 24 羊 → 错（接口给 True）
      272 龙鼠牛 + 码组含 05 + 开 05 虎 → 错：号码半区不参与 mode 117 判定
      271 未开奖 → 待开奖
    """
    return [
        {
            "moduleKey": "jimei_xiongchou",
            "title": "吉美凶丑（2选1，全肖）",
            "rows": [
                group_row("274", "吉美肖", JIMEI, code="24", zodiac="羊", is_correct=False),
                group_row("273", "凶丑肖", XIONG, code="19", zodiac="鼠", is_correct=False),
                group_row("272", "凶丑肖", XIONG, code="12", zodiac="羊", is_correct=True),
                group_row("270", "丑凶肖", XIONG, code="35", zodiac="猴", is_correct=False),
                group_row("269", "吉美肖", JIMEI, opened=False),
            ],
        },
        {
            "moduleKey": "qianhou_shengxiao",
            "title": "前后生肖",
            "rows": [
                group_row("274", "后肖", HOU, code="24", zodiac="羊", is_correct=False),
                group_row("273", "前肖", QIAN, code="19", zodiac="鼠", is_correct=False),
                group_row("272", "后肖", HOU, code="41", zodiac="牛", is_correct=True),
                group_row("271", "前肖", QIAN, opened=False),
                group_row("270", "后肖", "马,羊", code="35", zodiac="猴", is_correct=True),
            ],
        },
        {
            "moduleKey": "sanxiao_siwei_xiao",
            "title": "三肖四尾",
            "rows": [
                sanxiao_row("274", ["虎|05", "马|01", "狗|09"], code="37", zodiac="马", is_correct=False),
                sanxiao_row("273", ["牛|06", "蛇|02", "鼠|07"], code="24", zodiac="羊", is_correct=True),
                sanxiao_row("272", ["龙|02", "鼠|30", "牛|17,05"], code="05", zodiac="虎", is_correct=True),
                sanxiao_row("271", ["马|01", "猴|11", "蛇|02"], opened=False),
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

    # ── 【吉美丑凶】(mode 155)：展示 分组名 + 6 成员，命中 = 特肖 ∈ 分组 ──────
    check("jimei", "吉美丑凶 274", 0, expect_issue="第274期", expect_content="吉美肖【兔龙蛇马羊鸡】",
          expect_result="开:24羊对", expect_hits=["羊"])
    check("jimei", "吉美丑凶 273", 1, expect_issue="第273期", expect_content="凶丑肖【鼠牛虎猴狗猪】",
          expect_result="开:19鼠对", expect_hits=["鼠"])
    check("jimei", "吉美丑凶 272", 2, expect_issue="第272期", expect_content="凶丑肖【鼠牛虎猴狗猪】",
          expect_result="开:12羊错", expect_hits=[])
    # 「丑凶肖」是本站面板/供应商模板的写法，与 mode 155 的「凶丑肖」同组，必须同样解析出成员。
    check("jimei", "吉美丑凶 270", 3, expect_issue="第270期", expect_content="丑凶肖【鼠牛虎猴狗猪】",
          expect_result="开:35猴对", expect_hits=["猴"])
    check("jimei", "吉美丑凶 269", 4, expect_issue="第269期", expect_result="待开奖", expect_hits=[])

    # ── 【前后中特】(mode 133)：展示分组名，命中 = 特肖 ∈ 分组成员 ──────────
    check("qianhou", "前后中特 274", 0, expect_issue="第274期", expect_content="后肖",
          expect_result="开:24羊对", expect_hits=["后肖"])
    check("qianhou", "前后中特 273", 1, expect_issue="第273期", expect_content="前肖",
          expect_result="开:19鼠对", expect_hits=["前肖"])
    check("qianhou", "前后中特 272", 2, expect_issue="第272期", expect_content="后肖",
          expect_result="开:41牛错", expect_hits=[])
    check("qianhou", "前后中特 271", 3, expect_issue="第271期", expect_result="待开奖", expect_hits=[])
    # 270 的行内容只列了「马,羊」：必须按**行内容**判「错」（写死分组表会误判成「对」）。
    check("qianhou", "前后中特 270", 4, expect_issue="第270期", expect_content="后肖",
          expect_result="开:35猴错", expect_hits=[])

    # ── 【③肖防③码】(mode 117)：展示 3 肖 + 码组，命中 = 特肖 ∈ 3 肖 ──────
    check("fangma", "③肖防③码 274", 0, expect_issue="274", expect_content="虎马狗+05.01.09",
          expect_result="37马对", expect_hits=["马"])
    check("fangma", "③肖防③码 273", 1, expect_issue="273", expect_content="牛蛇鼠+06.02.07",
          expect_result="24羊错", expect_hits=[])
    # 272 的码组里含 05（开奖特码正是 05 虎）：号码半区**不**参与 mode 117 判定 → 仍是「错」。
    check("fangma", "③肖防③码 272", 2, expect_issue="272", expect_content="龙鼠牛+02.30.17.05",
          expect_result="05虎错", expect_hits=[])
    check("fangma", "③肖防③码 271", 3, expect_issue="271", expect_result="待开奖", expect_hits=[])

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
          "（155/133 按分组成员判定 + 117 按 3 肖判定 + 只标命中项 + 错/未开奖零黄底）")


if __name__ == "__main__":
    main()
