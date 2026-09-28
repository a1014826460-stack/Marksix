"""twbst528【综合绝杀】`3tou` / `3hang` 按**排除型**重做的真渲染契约。

背景（2026-09-29）
-----------------
供应商的【综合绝杀】面板（`index.html` 的 `.pb-tit` = 台湾百事通【综合绝杀】，
`table#table1`）是**杀号**语义面板：每个小节都写着 `NNN期稳杀【…】`。面板四个小节里
`juesha2xiao`(mode 473) / `juesha1wei`(mode 20) 后端本来就是 `excludes_hit`（杀中 → 对），
而 `3tou`(3头中特 mode 12) / `3hang`(3行中特 mode 53) 后端是**命中型**
（特码头 / 特码五行落在候选里 → `is_correct=true`）。旧实现直接上接口判定，于是渲染成

    188期稳杀【3头2头1头】开:38蛇对        ← 「对」来自命中型（3头 ∈ 候选）

—— 「稳杀…对」自相矛盾（杀号面板上显示「杀不掉」却判「对」），并且那一行的
`【3头2头1头】` 整段还被标了黄底（命中型高亮口径）。

口径（本轮钉死）：这两个小节在**本面板**里按排除型判定与展示 ——
**被杀集合不含开奖目标（特码头 / 特码五行）→「对」；含 →「错」**。
排除型一律**零黄底**（「对」= 没有可高亮的命中项；「错」标黄开奖值违反 S3）。
未开奖期不给判定、不高亮。判定逐期独立，不能整面板共用一个状态。

取反只在**展示层**（`renderZongheJushaHistory` 的 `invertVerdict` + `resultValue(row, true)`）：
后端 `is_correct` 是 mode 12/53 的公共语义，本站「五行来料」面板仍把 `3hang` 当命中型渲染，
所以不能改后端，也不能把这两个键加进全局 `KILL_RULE_KEYS`。

本契约不连线上、不连数据库：本地静态服务（`frontend/public`）+ 桩 `lottery-site-data-client`
+ `add_init_script` 注入合成 payload + Playwright 真跑适配器后断言 DOM。

运行：python frontend/test/twbst528-zonghe-juesha-contract.py
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

# 适配器 `modulesFrom()` 只认 `canonical_modules`，且会从 `result.data` 起逐层剥 `.data`。
STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      clear: function () {},
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { data: { issue: "2026323" } } }); },
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

  // 与适配器 `lineGroups()` 同口径：按 <br> 切分单元格里的行。
  const lineGroups = (root) => {
    const out = [[]];
    const visit = (node) => {
      if (node.nodeType === 3) { out[out.length - 1].push(String(node.nodeValue || '')); return; }
      if (node.nodeType !== 1) return;
      if (String(node.tagName).toUpperCase() === 'BR') { out.push([]); return; }
      Array.prototype.forEach.call(node.childNodes, visit);
    };
    Array.prototype.forEach.call(root ? root.childNodes : [], visit);
    return out
      .map((parts) => MONO(parts.join('')))
      .filter((text) => text.length > 0);
  };

  const sections = Array.from(document.querySelectorAll('.lxlm, .tzlb'));
  const panel = sections.filter((el) => {
    const head = el.querySelector('.pb-tit');
    return head && String(head.textContent || '').indexOf('【综合绝杀】') >= 0;
  })[0] || null;

  const cell = panel ? panel.querySelector('table#table1 tbody > tr > td') : null;
  const lines = cell ? lineGroups(cell) : [];

  // 该面板内（含被清空的模板行）的所有命中标记与黄底。
  const hitMarkers = panel ? Array.from(panel.querySelectorAll('[data-prediction-hit]')) : [];
  const yellowEls = [];
  if (panel) {
    panel.querySelectorAll('*').forEach((el) => {
      if (isYellow(el)) yellowEls.push({ tag: el.tagName, text: MONO(el.textContent).slice(0, 30) });
    });
  }

  return {
    panelFound: Boolean(panel),
    panelTitle: panel ? MONO(panel.querySelector('.pb-tit').textContent) : '',
    lines,
    lineCount: lines.length,
    hitMarkers: hitMarkers.length,
    yellowEls,
    yellowLiteral: panel ? (panel.innerHTML.match(/#FFFF00/gi) || []).length : 0,
  };
}
"""


def row(term, tokens, *, opened=True, code="", zodiac="", is_correct=None):
    return {
        "issue": term,
        "term": term,
        "prediction": {"tokens": list(tokens), "text": "".join(tokens), "extra": {}},
        "raw": {},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


def build_modules():
    """合成数据：同一期（191）在四个小节里给出可区分的判定，钉死「逐小节口径」。

    期号取 191/190/189（与模板里烤死的样例期号 233/323/322/321/320/319 不同年或不同期），
    于是走 `makeRowResolver` 的「模板读不到期号 → 按行号」兜底 —— 与线上真实 payload 同形状
    （线上期号是 191/190/…，模板样例是 233/323/…），配对顺序确定。

    `3tou` / `3hang` 的 `isCorrect` **故意与候选清单相反**，用来证明适配器是按
    「开奖号码 ∈ 本行候选自己声明的号码清单」本地复算，而不是拿接口值取反：

    | 小节 | 期号 | 被杀集合（候选清单） | 特码 | 接口 isCorrect | 期望展示 |
    | --- | --- | --- | --- | --- | --- |
    | juesha2xiao（后端 excludes_hit） | 191 | 狗 虎 | 45 | true（杀中） | 开:45狗对 |
    | juesha2xiao | 190 | 兔 羊 | 09 | false（杀失败） | 开:09狗错 |
    | juesha1wei（后端 excludes_hit） | 191 | 7尾 | 45 | true（杀中） | 开:45狗对 |
    | 3tou | 191 | 3头2头1头 | 38（∈3头） | true | 开:38蛇错 |
    | 3tou | 190 | 1头3头4头 | 09（∉） | false | 开:09狗对 |
    | 3tou | 189 | 1头2头4头 | 未开奖 | — | 开:待开奖 |
    | 3hang | 191 | 土金水（土含 45） | 45（∈土） | **false**（接口与候选相反） | 开:45狗错 |
    | 3hang | 190 | 火土水（都不含 29） | 29（∉） | **true**（接口与候选相反） | 开:29虎对 |
    """
    return [
        {
            "moduleKey": "juesha2xiao",
            "title": "绝杀二肖",
            "rows": [
                row("191", ["狗", "虎"], code="45", zodiac="狗", is_correct=True),
                row("190", ["兔", "羊"], code="09", zodiac="狗", is_correct=False),
            ],
        },
        {
            "moduleKey": "juesha1wei",
            "title": "绝杀一尾",
            "rows": [
                row("191", ["7尾|07,17,27,37,47"], code="45", zodiac="狗", is_correct=True),
            ],
        },
        {
            "moduleKey": "3tou",
            "title": "3头中特",
            "rows": [
                row("191", ["3头|30,31,32,33,34,35,36,37,38,39",
                            "2头|20,21,22,23,24,25,26,27,28,29",
                            "1头|10,11,12,13,14,15,16,17,18,19"],
                    code="38", zodiac="蛇", is_correct=True),
                row("190", ["1头|10,11,12,13,14,15,16,17,18,19",
                            "3头|30,31,32,33,34,35,36,37,38,39",
                            "4头|40,41,42,43,44,45,46,47,48,49"],
                    code="09", zodiac="狗", is_correct=False),
                row("189", ["1头|10,11,12,13,14,15,16,17,18,19",
                            "2头|20,21,22,23,24,25,26,27,28,29",
                            "4头|40,41,42,43,44,45,46,47,48,49"], opened=False),
            ],
        },
        {
            "moduleKey": "3hang",
            "title": "3行中特",
            "rows": [
                # 45 写在【土】组的清单里 → 杀失败（错）；接口故意给 false。
                row("191", ["土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48",
                            "金|10,11,22,23,34,35,46,47",
                            "水|07,08,19,20,31,32,43,44"],
                    code="45", zodiac="狗", is_correct=False),
                # 29 不在【火/土/水】任何一份清单里 → 杀中（对）；接口故意给 true。
                row("190", ["火|01,02,13,14,25,26,37,38,49",
                            "土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48",
                            "水|07,08,19,20,31,32,43,44"],
                    code="29", zodiac="虎", is_correct=True),
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

    if not data["panelFound"]:
        print("FAIL: 未找到【综合绝杀】面板（.pb-tit 里没有【综合绝杀】）")
        raise SystemExit(1)

    lines = data["lines"]
    print(f"面板: {data['panelTitle']}；可见行: {len(lines)}")
    for index, text in enumerate(lines):
        print(f"  [{index}] {text}")

    # 面板行序（index.html#table1）：①（绝杀二肖）×6 行 → ②（绝杀二尾）×6 行
    #   → ③（绝杀一头 = 3tou）×6 行 → ④（绝杀一行 = 3hang）×6 行。
    # 每个小节的模板里有 6 行（样例期号 233/323/322/321/320/319），没有对应数据行的
    # 模板行必须被清空（不得残留 `鼠龙 / 虎鼠 / 12马对` 这类样例），所以这里断言的是
    # **可见行全序列**。
    expected = [
        "（绝杀二肖）",
        "191期稳杀【狗虎】开:45狗对",
        "190期稳杀【兔羊】开:09狗错",
        "（绝杀二尾）",
        "191期稳杀【7尾】开:45狗对",
        "（绝杀一头）",
        "191期稳杀【3头2头1头】开:38蛇错",
        "190期稳杀【1头3头4头】开:09狗对",
        "189期稳杀【1头2头4头】开:待开奖",
        "（绝杀一行）",
        "191期稳杀【土金水】开:45狗错",
        "190期稳杀【火土水】开:29虎对",
    ]
    if lines != expected:
        problems.append("综合绝杀面板可见行序列不符：")
        problems.append(f"  期望 {expected}")
        problems.append(f"  实际 {lines}")

    # 逐期独立：同一小节里相邻两期判定必须不同（不能整行/整小节共用一个状态）。
    section3 = [text for text in lines if "【3头" in text or "【1头" in text]
    if len(section3) != 3 or not (section3[0].endswith("错") and section3[1].endswith("对")
                                  and section3[2].endswith("待开奖")):
        problems.append(f"小节③ 必须逐期独立判定（191 错 / 190 对 / 189 未开奖），实际 {section3}")

    # 本地复算优先于接口值：3tou/3hang 的接口 `isCorrect` 故意与候选清单一相反，
    # 渲染结果必须跟**候选清单**一致，而不是接口值取反。
    line_3hang_191 = [text for text in lines if "【土金水】" in text]
    line_3hang_190 = [text for text in lines if "【火土水】" in text]
    if not (line_3hang_191 and line_3hang_191[0].endswith("错")):
        problems.append(f"3hang 191（45 写在【土】清单里 → 杀失败）必须显示「错」，实际 {line_3hang_191}")
    if not (line_3hang_190 and line_3hang_190[0].endswith("对")):
        problems.append(f"3hang 190（29 不在任何候选清单里 → 杀中）必须显示「对」，实际 {line_3hang_190}")

    # 同一期（191）在小节① 是「对」（后端本身就是排除型，接口 true = 杀中），
    # 在小节③ 是「错」（候选清单含 38 的 3头 = 杀失败）—— 证明取反/复算是**按小节**生效，
    # 而不是整个面板统一翻转。
    line_191_kill_native = [text for text in lines if "【狗虎】" in text]
    line_191_kill_inverted = [text for text in lines if "【3头2头1头】" in text]
    if not (line_191_kill_native and line_191_kill_native[0].endswith("对")):
        problems.append(f"191 期小节①（juesha2xiao，接口 true = 杀中）必须显示「对」，实际 {line_191_kill_native}")
    if not (line_191_kill_inverted and line_191_kill_inverted[0].endswith("错")):
        problems.append(
            f"191 期小节③（3tou，38 的 3头 在候选清单里 = 杀失败）必须显示「错」，实际 {line_191_kill_inverted}")

    # 排除型零黄底：整个面板不得有任何命中标记或黄底（含被清空的模板行）。
    if data["hitMarkers"]:
        problems.append(f"排除型面板不得有命中标记，实际 {data['hitMarkers']} 处")
    if data["yellowEls"]:
        problems.append(f"排除型面板不得有黄底元素，实际 {data['yellowEls'][:3]}")
    if data["yellowLiteral"]:
        problems.append(f"排除型面板不得有 #FFFF00 字面量，实际 {data['yellowLiteral']} 处")

    print(f"面板命中标记: {data['hitMarkers']}；黄底元素: {len(data['yellowEls'])}；"
          f"#FFFF00 字面量: {data['yellowLiteral']}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwbst528-zonghe-juesha-contract: OK"
          "（3tou/3hang 按排除型取反 + 逐期独立 + 排除型零黄底）")


if __name__ == "__main__":
    main()
