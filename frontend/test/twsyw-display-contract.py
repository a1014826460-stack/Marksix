"""twsyw 展示契约：男女中特（`#nannv`）+「展示即候选」判定口径（10 个位置）。

## 一、男女中特（`#nannv`，mode 5 天地生肖）

背景（2026-09-29）：`frontend/public/vendor/twsyw/site-data-adapter.js` 的 `renderNannv()`
过去用 `source.result.isCorrect === true` 判定，而 vendor/接口的 `is_correct` 只比对 mode 5
的 `xiao` 列（后端 `mechanisms.py` 里 `title_5` 的 `hit_checker=contains_hit`，候选就是
「生肖选 2」），天地组（天肖/地肖各 6 肖）永远不参与判定 —— 于是「天肖里含开奖特肖」的期
显示「错」（270 期「天肖+兔鸡」开 37 马）。

正确口径（与 twwanli `#tdsx`、twcaibawang 一致）：特肖落在 **天肖/地肖分组（6 肖）∪
本期 2 个候选生肖** 任一即算命中；命中时只点亮真正命中的那一项（命中两肖 → 点亮该生肖；
命中天地组 → 点亮组名）；未命中/未开奖零黄底。

## 二、「展示即候选」（2026-09-29 追加，10 个位置）

缺陷形态：**展示的候选是某份资料的子集，判定却用整份资料**。两种症状：
  · 展示被裁到前 N 个、判定却用整份资料 → 命中落在被裁掉的部分时「显示对却没有黄底」；
  · 一行展示多路候选、判定只取第一路 → 「另一个维度命中却显示错」。

统一口径：判定必须以该单元格**真正展示的候选**为准（展示子集就是候选集），判定字也按展示
候选本地复算、不透明传 `result.isCorrect`：

| 位置（section） | 展示的候选 | 修正后的判定 |
|---|---|---|
| `#top_xiao_code` | 9 肖前 8/5/3/1 肖、24 码前 10/6/1 码（7 格共用 8 组） | 逐格用该格展示的那几个候选 |
| `#qixiao` | 9 肖前 7 肖 | 特肖 ∈ 前 7 肖 |
| `#gold6xiao` | 9 肖前 6 肖 + 平特一肖前 1 肖 | 两路任一命中即「对」，只点亮命中那一路 |
| `#winner12` | 精选22码前 12 码 | 特码 ∈ 前 12 码 |
| `#five_no_hit` | 精选22码前 5 码 | 特码 ∈ 前 5 码 |
| `#lianma` | 24 码前 12 码 + 四段资料 | 两路任一命中即「对」 |
| `#kill3wei` | 五尾资料前 3 尾 | 特码尾 ∈ 前 3 尾 |
| `#danshuang` | 合数单双 + 合数大小 | 任一维度命中即「对」，只点亮命中那一项 |
| `#hblvxiao` | 双波（3 波里的 2 波）+ 一波 | 任一维度命中即「对」，只点亮命中那一项 |
| `#composite_kill` | 绝杀三肖 + 五尾 + 三头 + 合数单双（四路） | 四路分别复算，任一路命中即「对」 |

`#composite_kill` 的绝杀三肖是排除型玩法（backend `juesha3xiao`：`hit_checker=excludes_hit`，
特肖**不在**展示的三肖里才算这一路杀中），杀中没有可点亮的候选项；其余三路是包含型，
命中时点亮命中的那一项。

断言用的合成分组与 `public.fixed_data` sign='天地肖' 及各站 sx.html 一致：
天肖 = 兔马猴猪牛龙；地肖 = 鼠虎蛇羊鸡狗。

**反向验证**：所有合成行的 `isCorrect` 都被故意设成与期望相反的假值（期望「对」的行给
`False`，期望「错」的行给 `True`），因此任何一处只要还透传 `isCorrect`，对应断言必然 FAIL。

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
  const rowsOf = (root) => Array.from((root || document).querySelectorAll('tr'))
    .filter((tr) => tr.querySelector('[data-prediction-issue], [data-prediction-content], [data-prediction-result]'))
    .map((tr) => ({
      text: MONO(tr.textContent),
      issue: MONO((tr.querySelector('[data-prediction-issue]') || {}).textContent || ''),
      content: MONO((tr.querySelector('[data-prediction-content]') || {}).textContent || ''),
      result: MONO((tr.querySelector('[data-prediction-result]') || {}).textContent || ''),
      hits: Array.from(tr.querySelectorAll('[data-prediction-hit="true"]')).map((el) => MONO(el.textContent)),
    }));

  const nannv = rowsOf(document.querySelector('#nannv'));

  const SECTIONS = [
    'top_xiao_code', 'qixiao', 'gold6xiao', 'winner12', 'lianma',
    'danshuang', 'hblvxiao', 'kill3wei', 'five_no_hit', 'composite_kill',
  ];
  const sections = {};
  SECTIONS.forEach((id) => { sections[id] = rowsOf(document.querySelector('#' + id)); });

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
    sections,
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


def prow(issue, tokens, code="", zodiac="", opened=True, is_correct=False):
    """合成资料行。`is_correct` 默认 `False`，需要「反口径」证明时显式传 `True`。"""
    return row(issue, tokens=tokens, raw={}, opened=opened, code=code, zodiac=zodiac, is_correct=is_correct)


ZODIAC9 = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴"]  # 9肖：八肖=前8 五肖=前5 三肖=前3 一肖=前1
MA24 = [f"{n:02d}" for n in range(1, 25)]  # 24码：10码=前10 6码=前6 1码=前1
SEL22 = [f"{n:02d}" for n in range(1, 23)]  # 精选22码：12码=前12 5码=前5
TAILS5 = ["0尾", "3尾", "7尾", "1尾", "9尾"]  # 五尾：绝杀三尾只取前 3 尾
TAILS_ALT = ["4尾", "5尾", "8尾", "2尾", "0尾"]
KILL3 = ["鼠", "牛", "虎"]  # 绝杀三肖（排除型）
HEADS_A = ["0头", "1头", "2头"]
HEADS_B = ["3头", "4头", "0头"]

# ── 各机制合成资料（多个 section 共用同一份模块，index 对齐） ──────────────

# 9肖：供 #top_xiao_code（组 0-7 的 4 个肖格）、#qixiao（前7）、#gold6xiao（前6）、#jiuxiao
NINE_ROWS = [
    prow("2026270", ZODIAC9, code="37", zodiac="蛇"),  # 第6肖：八肖/七肖/六肖中；五肖/三肖/一肖不中
    prow("2026269", ZODIAC9, code="03", zodiac="虎"),  # 第3肖：八肖/五肖/三肖/七肖/六肖中；一肖不中
    prow("2026268", ZODIAC9, code="01", zodiac="鼠"),  # 第1肖：全中
    prow("2026267", ZODIAC9, code="09", zodiac="猴"),  # 第9肖：八肖/七肖/六肖全不中（被裁掉的部分）
    prow("2026266", ZODIAC9, code="08", zodiac="羊"),  # 第8肖：八肖中；七肖/六肖不中
    prow("2026265", ZODIAC9, code="07", zodiac="马"),  # 第7肖：八肖/七肖中；五肖/六肖不中
    prow("2026264", ZODIAC9, code="05", zodiac="龙"),  # 第5肖：八肖/五肖/七肖/六肖中；三肖不中
    prow("2026263", ZODIAC9, opened=False),
]

# 24码：供 #top_xiao_code（组 0-7 的 3 个码格）、#m24、#lianma（前12）
MA_ROWS = [
    prow("2026270", MA24, code="12", zodiac="马"),  # 第12码：10码/6码/1码全不中；连码前12命中
    prow("2026269", MA24, code="08", zodiac="羊"),  # 第8码：10码中；6码/1码不中
    prow("2026268", MA24, code="06", zodiac="蛇"),  # 第6码：10码/6码中；1码不中
    prow("2026267", MA24, code="01", zodiac="鼠"),  # 第1码：全中
    prow("2026266", MA24, code="20", zodiac="猪"),  # 第20码：全不中
    prow("2026265", MA24, code="18", zodiac="虎"),  # 第18码：全不中；连码靠四段 3段 救回
    prow("2026264", MA24, code="16", zodiac="猴"),  # 第16码：全不中
    prow("2026263", MA24, opened=False),
]

# 平特一肖：只供 #gold6xiao（前1肖）
FLAT_ROWS = [
    prow("2026270", ["鼠"], code="37", zodiac="蛇"),  # 六肖中、一肖不中
    prow("2026269", ["鼠"], code="03", zodiac="虎"),
    prow("2026268", ["鼠"], code="01", zodiac="鼠"),  # 两路都中
    prow("2026267", ["鼠"], code="09", zodiac="猴"),  # 两路都不中
    prow("2026266", ["羊"], code="08", zodiac="羊"),  # 六肖不中（第8肖）、一肖命中
    prow("2026265", ["鼠"], code="07", zodiac="马"),  # 六肖不中（第7肖）、一肖不中
    prow("2026264", ["鼠"], code="05", zodiac="龙"),  # 六肖中
    prow("2026263", ["鼠"], opened=False),
]

# 四段中特：只供 #lianma（四段资料）；段位 = ((特码-1)//7)+1
SEGMENT_ROWS = [
    prow("2026270", ["1段", "3段", "5段", "7段"], code="12"),  # 12 → 2段 → 不中
    prow("2026269", ["1段", "3段", "4段", "5段"], code="08"),  # 08 → 2段 → 不中
    prow("2026268", ["1段", "2段", "3段", "4段"], code="06"),  # 06 → 1段 → 中
    prow("2026267", ["1段", "5段", "6段", "7段"], code="01"),  # 01 → 1段 → 中
    prow("2026266", ["1段", "2段", "4段", "5段"], code="20"),  # 20 → 3段 → 不中
    prow("2026265", ["3段", "5段", "6段", "7段"], code="18"),  # 18 → 3段 → 中（码被裁掉，靠这一路）
    prow("2026264", ["1段", "2段", "4段", "5段"], code="16"),  # 16 → 3段 → 不中
    prow("2026263", ["1段", "2段", "3段", "4段"], opened=False),
]

# 精选22码：供 #winner12（前12）与 #five_no_hit（前5）
SEL_ROWS = [
    prow("2026270", SEL22, code="15", zodiac="蛇", is_correct=True),  # 第15码：12码/5码全不中（旧口径会显示对）
    prow("2026269", SEL22, code="03", zodiac="虎"),  # 第3码：12码/5码都中
    prow("2026268", SEL22, code="08", zodiac="羊", is_correct=True),  # 第8码：12码中、5码不中
    prow("2026267", SEL22, code="05", zodiac="龙"),  # 第5码：12码/5码都中
    prow("2026266", SEL22, opened=False),
]

# 五尾中特：供 #kill3wei（前3尾）、#pt1wei/#qiw（全5尾）、#composite_kill（五尾这一路）
TITLE66_ROWS = [
    prow("2026270", TAILS5, code="15", zodiac="蛇", is_correct=True),  # 5尾 ∉ 前3（旧口径会显示对）
    prow("2026269", TAILS5, code="37", zodiac="蛇"),  # 7尾 ∈ 前3
    prow("2026268", TAILS5, code="13", zodiac="虎"),  # 3尾 ∈ 前3
    prow("2026267", TAILS5, code="21", zodiac="鼠", is_correct=True),  # 1尾 ∉ 前3、∈ 全5（被裁掉的那部分）
    prow("2026266", TAILS_ALT, code="34", zodiac="牛"),  # 4尾 ∈ 前3
    prow("2026265", TAILS_ALT, code="20", zodiac="猪"),  # 0尾 ∉ 前3
    prow("2026264", TAILS5, opened=False),
]

# 三头中特：供 #santou/#kill1tou（全3头）、#composite_kill（三头这一路）
HEADS_ROWS = [
    prow("2026270", HEADS_B, code="37", zodiac="马"),
    prow("2026269", HEADS_B, code="15", zodiac="鼠"),
    prow("2026268", HEADS_B, code="34", zodiac="牛"),
    prow("2026267", HEADS_A, code="31", zodiac="牛"),
    prow("2026266", HEADS_A, code="46", zodiac="虎"),
    prow("2026265", HEADS_A, opened=False),
]

# 绝杀三肖（排除型）：只供 #composite_kill，是四路里的第一路
KILL_ROWS = [
    prow("2026270", KILL3, code="15", zodiac="马"),  # 马 ∉ 三肖 → 这一路杀中（没有可点亮的项）
    prow("2026269", KILL3, code="15", zodiac="鼠"),  # 鼠 ∈ 三肖 → 这一路失败，靠合数单双
    prow("2026268", KILL3, code="34", zodiac="牛"),  # 这一路失败，靠三头（3头 ∈）
    prow("2026267", KILL3, code="31", zodiac="牛"),  # 这一路失败，靠五尾（1尾 ∈）
    prow("2026266", KILL3, code="46", zodiac="虎", is_correct=True),  # 四路全不中（旧口径会显示对）
    prow("2026265", KILL3, opened=False),
]

# 合数单双：供 #danshuang（维度1）与 #composite_kill（第四路）
PARITY_ROWS = [
    prow("2026270", ["合单"], code="37", zodiac="马"),  # 37 → 合数10 → 合双 → 不中
    prow("2026269", ["合双"], code="37", zodiac="马"),  # 合双 → 中
    prow("2026268", ["合双"], code="21", zodiac="虎", is_correct=True),  # 21 → 合数3 → 合单 → 不中（旧口径会显示对）
    prow("2026267", ["合单"], code="05", zodiac="龙"),  # 05 → 合数5 → 合单 → 中
    prow("2026266", ["合", "单"], code="29", zodiac="鼠"),  # 单字 token 形态：29 → 合数11 → 合单 → 中
    prow("2026265", ["合单"], opened=False),
]

# 合数大小：只供 #danshuang（维度2）。合数 ≥7 → 合数大
SIZE_ROWS = [
    prow("2026270", ["合数大"], code="37", zodiac="马"),  # 合数10 → 合数大 → 中
    prow("2026269", ["合数小"], code="37", zodiac="马"),  # 合数10 → 合数大 → 不中
    prow("2026268", ["合数大"], code="21", zodiac="虎"),  # 合数3 → 合数小 → 不中
    prow("2026267", ["合数小"], code="05", zodiac="龙"),  # 合数5 → 合数小 → 中
    prow("2026266", ["合", "数", "大"], code="29", zodiac="鼠"),  # 单字 token 形态：合数11 → 合数大 → 中
    prow("2026265", ["合数大"], opened=False),
]

# 双波中特（3 波选 2）：供 #hblvxiao（双波这一路）与 #shuangbo
# 波色：红波 01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46
#       蓝波 03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48
#       绿波 05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49
SHUANGBO_ROWS = [
    prow("2026270", ["红波", "蓝波"], code="22", zodiac="蛇", is_correct=True),  # 22 → 绿波（被裁掉的第3波）
    prow("2026269", ["红波", "绿波"], code="37", zodiac="蛇"),  # 蓝波 ∉ 双波、∈ 一波
    prow("2026268", ["蓝波", "绿波"], code="37", zodiac="虎"),  # 蓝波 ∈ 双波
    prow("2026267", ["红", "波", "蓝", "波"], code="41", zodiac="鼠"),  # 单字 token 形态；41 → 蓝波 ∈
    prow("2026266", ["红波", "绿波"], code="05", zodiac="龙"),  # 05 → 绿波 ∈ 双波
    prow("2026265", ["红波", "蓝波"], code="46", zodiac="马"),  # 46 → 红波 ∈ 双波
    prow("2026264", ["红波", "蓝波"], code="05", zodiac="羊", is_correct=True),  # 绿波 ∉ 两路（旧口径会显示对）
    prow("2026263", ["红波", "蓝波"], opened=False),
]

# 一波中特：只供 #hblvxiao（一波这一路）
WAVE1_ROWS = [
    prow("2026270", ["绿波"], code="22", zodiac="蛇"),  # 22 → 绿波 → 一波命中
    prow("2026269", ["蓝波"], code="37", zodiac="蛇"),
    prow("2026268", ["红波"], code="37", zodiac="虎"),
    prow("2026267", ["绿", "波"], code="41", zodiac="鼠"),  # 单字 token 形态；41 → 蓝波 → 不中
    prow("2026266", ["蓝波"], code="05", zodiac="龙"),
    prow("2026265", ["绿波"], code="46", zodiac="马"),
    prow("2026264", ["红波"], code="05", zodiac="羊"),
    prow("2026263", ["绿波"], opened=False),
]


# ── 期望表 ────────────────────────────────────────────────────────────────
# #top_xiao_code：8 组 × 7 格（八肖/五肖/三肖/一肖 = 9肖前 8/5/3/1，10码/6码/1码 = 24码前 10/6/1）
# 每项 = (肖组下标, 码组下标, [(是否命中, 命中项文本) × 7])
TOP_XIAO_EXPECT = [
    (0, 0, [(True, "蛇"), (False, ""), (False, ""), (False, ""), (False, ""), (False, ""), (False, "")]),
    (1, 1, [(True, "虎"), (True, "虎"), (True, "虎"), (False, ""), (True, "08"), (False, ""), (False, "")]),
    (2, 2, [(True, "鼠"), (True, "鼠"), (True, "鼠"), (True, "鼠"), (True, "06"), (True, "06"), (False, "")]),
    (3, 3, [(False, ""), (False, ""), (False, ""), (False, ""), (True, "01"), (True, "01"), (True, "01")]),
    (4, 4, [(True, "羊"), (False, ""), (False, ""), (False, ""), (False, ""), (False, ""), (False, "")]),
    (5, 5, [(True, "马"), (False, ""), (False, ""), (False, ""), (False, ""), (False, ""), (False, "")]),
    (6, 6, [(True, "龙"), (True, "龙"), (False, ""), (False, ""), (False, ""), (False, ""), (False, "")]),
    (7, 7, [(False, ""), (False, ""), (False, ""), (False, ""), (False, ""), (False, ""), (False, "")]),
]
TOP_XIAO_SLOTS = ["八肖", "五肖", "三肖", "一肖", "10码", "6码", "1码"]

# 9 肖前 7：#top_xiao_code / #qixiao / #gold6xiao（前6+1肖）共用同一批 9xzt 行
QIXIAO_EXPECT = [(0, True, ["蛇"]), (1, True, ["虎"]), (2, True, ["鼠"]), (3, False, []),
                 (4, False, []), (5, True, ["马"]), (6, True, ["龙"]), (7, None, [])]
GOLD6XIAO_EXPECT = [(0, True, ["蛇"]), (1, True, ["虎"]), (2, True, ["鼠", "鼠"]), (3, False, []),
                    (4, True, ["羊"]), (5, False, []), (6, True, ["龙"]), (7, None, [])]
WINNER12_EXPECT = [(0, False, []), (1, True, ["03"]), (2, True, ["08"]), (3, True, ["05"]), (4, None, [])]
FIVE_NO_HIT_EXPECT = [(0, False, []), (1, True, ["03"]), (2, False, []), (3, True, ["05"]), (4, None, [])]
LIANMA_EXPECT = [(0, True, ["12"]), (1, True, ["08"]), (2, True, ["06", "1段"]), (3, True, ["01", "1段"]),
                 (4, False, []), (5, True, ["3段"]), (6, False, []), (7, None, [])]
KILL3WEI_EXPECT = [(0, False, []), (1, True, ["7尾"]), (2, True, ["3尾"]), (3, False, []),
                   (4, True, ["4尾"]), (5, False, []), (6, None, [])]
DANSHUANG_EXPECT = [(0, True, ["合数大"]), (1, True, ["合双"]), (2, False, []),
                    (3, True, ["合单", "合数小"]), (4, True, ["合单", "合数大"]), (5, None, [])]
HBLVXIAO_EXPECT = [(0, True, ["绿波"]), (1, True, ["蓝波"]), (2, True, ["蓝波"]), (3, True, ["蓝波"]),
                   (4, True, ["绿波"]), (5, True, ["红波"]), (6, False, []), (7, None, [])]
COMPOSITE_EXPECT = [(0, True, []), (1, True, ["合双"]), (2, True, ["3头"]), (3, True, ["1尾"]),
                    (4, False, []), (5, None, [])]


def build_modules():
    """男女中特 270/269/267 = 已开奖对照，266 = 未开奖。

    `title_5` 的 `isCorrect` 故意给 `False`：它只反映 vendor 对 `xiao` 两肖的比对结果
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
        # 「展示即候选」10 个位置共用的合成资料（同一个 moduleKey 会被多个 section 消费）。
        {"moduleKey": "9xzt", "rows": NINE_ROWS},
        {"moduleKey": "ma24", "rows": MA_ROWS},
        {"moduleKey": "pt1xiao", "rows": FLAT_ROWS},
        {"moduleKey": "siduanzhongte", "rows": SEGMENT_ROWS},
        {"moduleKey": "selected_22_codes", "rows": SEL_ROWS},
        {"moduleKey": "title_66", "rows": TITLE66_ROWS},
        {"moduleKey": "3tou", "rows": HEADS_ROWS},
        {"moduleKey": "juesha3xiao", "rows": KILL_ROWS},
        {"moduleKey": "title_132", "rows": PARITY_ROWS},
        {"moduleKey": "title_279", "rows": SIZE_ROWS},
        {"moduleKey": "shuangbo", "rows": SHUANGBO_ROWS},
        {"moduleKey": "title_143", "rows": WAVE1_ROWS},
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
    checks = 0

    def check(rows, index, expect_content, expect_issue, expect_result, expect_hits, label):
        nonlocal checks
        checks += 1
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

    def check_content(rows, index, expect, label):
        """展示的候选必须**正好**是这一份（多一个都算错：例如七肖不能把第 8、9 肖也显示出来）。"""
        nonlocal checks
        checks += 1
        if len(rows) <= index:
            problems.append(f"{label}: 第 {index} 行未渲染")
            return
        if rows[index]["content"] != expect:
            problems.append(f"{label}: 展示候选应为『{expect}』，实际 '{rows[index]['content']}'")

    def verdict_case(index, source, hit, hits, label):
        """按 source 行的开奖字段生成期望：判定字 = 开:<特码><特肖>对/错。"""
        result = source["result"]
        return {
            "index": index, "opened": result["isOpened"], "code": result["code"],
            "zodiac": result["zodiac"], "hit": hit, "hits": hits, "label": label,
        }

    def run_cases(section_id, cases, describe):
        rows = data["sections"][section_id]
        for case in cases:
            if not case["opened"]:
                expect = "开:待开奖"
            else:
                expect = f"开:{case['code']}{case['zodiac']}{'对' if case['hit'] else '错'}"
            check(rows, case["index"], None, None, expect, case["hits"], f"{describe} {case['label']}")
        return rows

    nannv = data["nannv"]

    # ══ 一、男女中特（#nannv）：特肖 ∈ 天地组 ∪ 两肖 ═══════════════════════
    check(nannv, 0, "天肖+兔鸡", "2026270期", "开:37马对", ["天肖"],
          "男女中特 270期（天肖+兔鸡，开37马 → 天地组命中）")
    check(nannv, 1, "地肖+兔鸡", "2026269期", "开:37马错", [],
          "男女中特 269期（地肖+兔鸡，开37马 → 都不含）")
    check(nannv, 2, "天肖+兔鸡", "2026267期", "开:22鸡对", ["鸡"],
          "男女中特 267期（天肖+兔鸡，开22鸡 → 两肖命中）")
    check(nannv, 3, "地肖+鼠虎", "2026266期", "开:待开奖", [],
          "男女中特 266期（未开奖）")

    # ══ 二、#top_xiao_code：8 组 × 7 格各自只用该格展示的候选 ═══════════════
    top = data["sections"]["top_xiao_code"]
    if len(top) != 56:
        problems.append(f"#top_xiao_code: 应有 56 个数据行，实际 {len(top)}")
    for group, (xiao_index, ma_index, slots) in enumerate(TOP_XIAO_EXPECT):
        for slot, (hit, hit_text) in enumerate(slots):
            source = NINE_ROWS[xiao_index] if slot < 4 else MA_ROWS[ma_index]
            case = verdict_case(group * 7 + slot, source, hit, [hit_text] if hit_text else [],
                                f"组{group} {TOP_XIAO_SLOTS[slot]}")
            run_cases("top_xiao_code", [case], "特码开奖结果")
    # 展示的候选必须正好是该格的那一份（不是整份 9 肖 / 24 码）
    check_content(top, 0, "鼠牛虎兔龙蛇马羊", "特码开奖结果 组0 八肖（9肖前8）")
    check_content(top, 1, "鼠牛虎兔龙", "特码开奖结果 组0 五肖（9肖前5）")
    check_content(top, 2, "鼠牛虎", "特码开奖结果 组0 三肖（9肖前3）")
    check_content(top, 3, "鼠", "特码开奖结果 组0 一肖（9肖前1）")
    check_content(top, 4, "01.02.03.04.05.06.07.08.09.10", "特码开奖结果 组0 10码（24码前10）")
    check_content(top, 5, "01.02.03.04.05.06", "特码开奖结果 组0 6码（24码前6）")
    check_content(top, 6, "01", "特码开奖结果 组0 1码（24码前1）")
    # 期号格仍带格名，且第 8 组（未开奖）零黄底
    check(top, 56 - 7, "鼠牛虎兔龙蛇马羊", "2026263期 八肖", "开:待开奖", [],
          "特码开奖结果 组7 八肖（未开奖）")

    # ══ 三、#qixiao：9 肖前 7 肖 ════════════════════════════════════════
    qixiao = run_cases(
        "qixiao",
        [verdict_case(i, NINE_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in QIXIAO_EXPECT],
        "七肖中特",
    )
    check_content(qixiao, 0, "鼠牛虎兔龙蛇马", "七肖中特 第0行（9肖前7，第8/9肖不算候选）")
    check_content(qixiao, 3, "鼠牛虎兔龙蛇马", "七肖中特 第3行（猴是第9肖，被裁掉）")

    # ══ 四、#gold6xiao：九肖前 6 肖 + 平特一肖前 1 肖 ═════════════════════
    gold = run_cases(
        "gold6xiao",
        [verdict_case(i, NINE_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in GOLD6XIAO_EXPECT],
        "黄金六肖",
    )
    check_content(gold, 0, "九肖资料：鼠牛虎兔龙蛇；平特一肖资料：鼠", "黄金六肖 第0行（6肖+1肖）")
    check_content(gold, 4, "九肖资料：鼠牛虎兔龙蛇；平特一肖资料：羊", "黄金六肖 第4行（羊是第8肖，只在一肖里）")

    # ══ 五、#winner12：精选22码前 12 码 ══════════════════════════════════
    winner = run_cases(
        "winner12",
        [verdict_case(i, SEL_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in WINNER12_EXPECT],
        "赢钱12码",
    )
    check_content(winner, 0, "精选22码资料：01.02.03.04.05.06.07.08.09.10.11.12",
                  "赢钱12码 第0行（22码前12）")

    # ══ 六、#five_no_hit：精选22码前 5 码 ════════════════════════════════
    five = run_cases(
        "five_no_hit",
        [verdict_case(i, SEL_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in FIVE_NO_HIT_EXPECT],
        "平特5不中",
    )
    check_content(five, 0, "五码资料：01.02.03.04.05", "平特5不中 第0行（22码前5）")

    # ══ 七、#lianma：24 码前 12 码 + 四段资料 ════════════════════════════
    lianma = run_cases(
        "lianma",
        [verdict_case(i, MA_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in LIANMA_EXPECT],
        "复试连码",
    )
    check_content(lianma, 0, "24码资料：01.02.03.04.05.06.07.08.09.10.11.12；四段资料：1段 3段 5段 7段",
                  "复试连码 第0行（24码前12 + 四段）")

    # ══ 八、#kill3wei：五尾资料前 3 尾 ══════════════════════════════════
    kill3 = run_cases(
        "kill3wei",
        [verdict_case(i, TITLE66_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in KILL3WEI_EXPECT],
        "绝杀三尾",
    )
    check_content(kill3, 0, "五尾资料：0尾 3尾 7尾", "绝杀三尾 第0行（五尾前3）")
    check_content(kill3, 3, "五尾资料：0尾 3尾 7尾", "绝杀三尾 第3行（1尾是全5尾的第4尾，被裁掉）")

    # ══ 九、#danshuang：合数单双 + 合数大小（两路任一命中） ════════════════
    danshuang = run_cases(
        "danshuang",
        [verdict_case(i, PARITY_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in DANSHUANG_EXPECT],
        "单双中特",
    )
    check_content(danshuang, 0, "合数单双资料：合单；合数大小资料：合数大", "单双中特 第0行（两路都展示）")
    check_content(danshuang, 4, "合数单双资料：合单；合数大小资料：合数大", "单双中特 第4行（单字 token 形态）")

    # ══ 十、#hblvxiao：双波 + 一波（两路任一命中） ════════════════════════
    hblvxiao = run_cases(
        "hblvxiao",
        [verdict_case(i, SHUANGBO_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in HBLVXIAO_EXPECT],
        "红蓝绿肖",
    )
    check_content(hblvxiao, 0, "双波资料：红波 蓝波；一波资料：绿波", "红蓝绿肖 第0行（双波2波+一波1波）")
    check_content(hblvxiao, 3, "双波资料：红波 蓝波；一波资料：绿波", "红蓝绿肖 第3行（单字 token 形态）")

    # ══ 十一、#composite_kill：绝杀三肖 + 五尾 + 三头 + 合数单双（四路） ═══
    composite = run_cases(
        "composite_kill",
        [verdict_case(i, KILL_ROWS[i], hit, hits, f"第{i}行") for i, hit, hits in COMPOSITE_EXPECT],
        "综合绝杀",
    )
    check_content(
        composite, 0,
        "绝杀三肖：鼠牛虎；五尾资料：0尾 3尾 7尾 1尾 9尾；三头资料：3头 4头 0头；合数单双：合单",
        "综合绝杀 第0行（四路都展示）",
    )

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
    print(f"断言数: {checks}")
    for section_id in ("top_xiao_code", "qixiao", "gold6xiao", "winner12", "lianma", "kill3wei",
                       "danshuang", "hblvxiao", "five_no_hit", "composite_kill"):
        rows = data["sections"][section_id]
        print(f"  #{section_id}: {len(rows)} 行；首行 = {rows[0]['issue']} | {rows[0]['content']} | "
              f"{rows[0]['result']} | hits={rows[0]['hits']}")
    print(f"错期带黄底: {len(data['wrongWithHighlight'])}；未开奖带黄底: {len(data['pendingWithHighlight'])}；"
          f"杂散黄底: {len(data['strayYellow'])}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwsyw-display-contract: OK（#nannv 天地组∪两肖并集 + 10 处「展示即候选」逐格复算 + 只标命中项 + 错/未开奖零黄底）")


if __name__ == "__main__":
    main()
