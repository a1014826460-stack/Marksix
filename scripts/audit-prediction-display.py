#!/usr/bin/env python
"""预测模块展示规范审计工具（十站点通用）。

用法：
    python scripts/audit-prediction-display.py                 # 审计全部站点
    python scripts/audit-prediction-display.py twsaimahui      # 只审计指定站点
    python scripts/audit-prediction-display.py --json out.json # 额外输出 JSON

扫描范围：`SITES` 里每个站点扫 `url`（主 URL，通常首页/主壳）。**部分面板只挂在文章页上**
（例如 twcf888 的「天地生肖」mode 5 只在 `/twcf888/amgst/6100` 上屏，首页没有这个面板），
只扫主 URL 会整块漏看。这类站点用可选字段 `extra_urls: [...]` 补文章页，审计时逐个页面
扫一遍；每页的 `rows` / `js_errors` 单独记录，规则判定仍**按页面内**的模块分组
（R4/R5/R8 的「同一模块相邻期」语义不跨页面），报告里每条 finding 都带来源 URL。

检查项（对应《预测模块展示规范》）：
    R1 raw_json_leak      可见文本里残留 [" / "] / \\" 等原始 JSON 片段
    R2 verdict_pending    未开奖（结果为 ？/??/???? 占位）却显示了判定
    R3 highlight_miss     本期判定为「错」，却仍有黄色高亮
    R4 highlight_hit      本期判定为「准/对」，但整行没有黄色高亮（需模块内有高亮行）
    R5 repeat_run         同一模块相邻 3 期以上展示值完全相同
    R6 empty_legend       分组说明后面为空（如「右肖:」「阴肖:」）
    R7 verdict_missing    已开奖且有判定语义的模块缺判定文字（提示级）
    R8 verdict_all_same   某模块 ≥5 期已开奖行判定全同（整列对/错的统一性告警）

黄色高亮同时用两种口径识别：元素**计算样式**（能抓到 class / bgcolor 属性造成的黄底）
与行 HTML 里的 `#FFFF00` 字面量；只统计「相对父节点新增」的黄色，容器整体黄底不算行内高亮。

退出码：0 = 无 error；1 = 存在 error。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

CHROME = r"C:\Users\Administrator\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

SITES: list[dict[str, Any]] = [
    {
        "key": "shengshi8800",
        "label": "tw8800 (盛世台湾六合彩)",
        "web_id": 4,
        "url": "https://www.tw8800.com/vendor/shengshi8800/embed.html?type=3&web=4&debug=0&page_switch=1&shell_header=1",
    },
    {
        "key": "twcaibawang",
        "label": "twcaibawang (台湾彩霸王)",
        "web_id": 5,
        "url": "https://www.twcaibawang.com/twcaibawang",
    },
    {
        "key": "twsaimahui",
        "label": "twsaimahui (台湾跑马会)",
        "web_id": 6,
        "url": "https://www.twsaimahui.com/vendor/twsaimahui/index.html",
    },
    {
        "key": "twjinniu",
        "label": "twjinniu (台湾通天网)",
        "web_id": 7,
        "url": "https://www.twtongtian.com/twjinniu",
    },
    {
        "key": "twcf888",
        "label": "twcf888 (台湾创富网)",
        "web_id": 8,
        "url": "https://www.twcf888.com/twcf888",
        # 「天地生肖」(mode 5) 等 amgst 栏目的预测面板只挂在文章页上，首页不出这个面板。
        # 文章页 ID↔标题的权威映射见 frontend/lib/twcf888-articles.ts 的 ARTICLE_DEFINITIONS
        # （6100 = 天地生肖 / mode 5）。这里只补已确认会漏看的文章页，不批量展开全部 48 篇。
        "extra_urls": [
            "https://www.twcf888.com/twcf888/amgst/6100?lottery_type=3",
        ],
    },
    {
        "key": "twssz",
        "label": "twssz (台湾神算子)",
        "web_id": 9,
        "url": "https://www.twssz.com/twssz",
    },
    {
        "key": "twbst528",
        "label": "twbst528 (台湾百事通)",
        "web_id": 10,
        "url": "https://www.twbst528.com/twbst528",
        # twbst528 的文章页是供应商静态页（域名根目录下的 N.html），页面契约见
        # frontend/public/vendor/twbst528/static-article-data-adapter.js 的 PAGE_CONTRACTS：
        # 49 与 145 都是「天地生肖」(moduleKey = title_5)，首页不出这个面板。这两个是
        # 唯一已确认的天地生肖文章页；其余 N.html 是别的玩法，不在这里批量展开。
        "extra_urls": [
            "https://www.twbst528.com/145.html",
            "https://www.twbst528.com/49.html",
        ],
    },
    {
        "key": "twjsz666",
        "label": "twjsz666 (台湾金手指)",
        "web_id": 11,
        "url": "https://www.twjsz666.com/twjsz666",
    },
    {
        "key": "twwanli",
        "label": "twwanli (台湾万利网)",
        "web_id": 12,
        "url": "https://www.twwanli.com/twwanli",
    },
    {
        "key": "twsyw",
        "label": "twsyw (台湾神预网)",
        "web_id": 13,
        "url": "https://www.twsyw.com/twsyw",
    },
]

VERDICT_TOKENS = ("准", "对", "错", "赢", "输", "中", "不中")
#: 「开奖段」锚点：`开/開` 后面必须紧跟**结果引导词或结果本身**，才算这一行的开奖段起点。
#:
#: 为什么要收紧：`verdict_of` 过去取「最后一个 开/開 之后的 16 字」当判定窗口。笑话/谜面这类
#: 正文里也常有「开」字——线上 2026-10-06 实测 shengshi8800【独家幽默】279 期的段子
#: 「…对方女的要他**开**视频，这货竟然把摄像头调整**对**着我…」把最后一个「开」落在正文里，
#: 窗口抓到「对着我」的「对」→ 假 R2（error 级）。锚点收紧后，正文里的「开视频 / 开心 /
#: 开门」都不再被当成开奖段。
VERDICT_ANCHOR_LOOKAHEAD = (
    r"[:：]|奖|出|码|碼|[\d?？待]|"
    r"[鼠牛虎兔龙蛇马羊猴鸡狗猪龍馬雞豬免]|"
    r"[蓝藍红紅绿綠波单單双雙大小家野天地前后後左右日夜阴阳陰陽金木水火土琴棋书画書畫合半平特头頭尾段]"
)
VERDICT_ANCHOR_RE = re.compile(r"(?:开|開)\s*(?=" + VERDICT_ANCHOR_LOOKAHEAD + r")")
PENDING_PATTERNS = (
    "？00", "?00", "？？？", "??????", "?????", "????", "？？", "待开",
    "猫00", "？?", "?？",
)
#: 占位结果的正则（长的在前，避免 `？？` 抢先匹配 `？？？`）。
PENDING_RE = re.compile(
    "|".join(re.escape(item) for item in sorted(PENDING_PATTERNS, key=len, reverse=True))
)
LEGEND_EMPTY_RE = re.compile(
    r"(左肖|右肖|阴肖|阳肖|文肖|武肖|有肖|无肖|吉美肖|凶丑肖|肥肖|瘦肖|"
    r"胆大生肖|胆小生肖|黑肖|白肖|黑中生肖|白边生肖|后肖|前肖|琴肖|棋肖|书肖|画肖)"
    r"\s*[:：]\s*(?=\s|$|\n|<)"
)

ROW_SCRIPT = r"""
() => {
  const out = [];
  const nodes = Array.from(document.querySelectorAll('tr, p, div, li, td, b, font, span'));
  const cands = [];
  for (const el of nodes) {
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!text || text.length > 260) continue;
    if (!/\d{2,3}\s*期/.test(text)) continue;
    // 隐藏/未渲染的元素（供应商模板里的备用行、display:none 的草稿）不算页面展示，
    // 否则会把没上屏的原始 `标签|值` 串也算成违规。
    if (el.getClientRects().length === 0) continue;
    cands.push({ el, text });
  }
  const leaves = cands.filter((item) => !cands.some((other) => other.el !== item.el && item.el.contains(other.el)));
  const containerOf = (el) => {
    let node = el;
    while (node && node !== document.body) {
      if (node.id) return '#' + node.id;
      const cls = String(node.className || '').trim();
      if (cls && /(box|Box|l\d+$|panel)/.test(cls)) return '.' + cls.split(/\s+/).slice(0, 2).join('.');
      node = node.parentElement;
    }
    return '?';
  };
  // 容器 id/class 常常是多个模块共用的（twssz 的 .box.pad、twjsz666 的 #yxym 底下挂了十几个玩法）。
  // 只按容器分组会让 R4/R5 把不同玩法混成一个模块，所以补一段「行内标签」做二级区分：
  // 取「最后一个期号」之后到第一个【『（《 或 开 之间的短文本；取不到就退回方括号里的短文本。
  const labelOf = (text) => {
    const m = text.match(/\d{2,3}\s*期\s*[:：]?\s*([^【『（(《开:：;；|]{1,16})/);
    if (m) {
      const label = m[1].replace(/[：:\s;；]+$/, '').trim();
      if (label) return label.slice(0, 16);
    }
    const bracket = text.match(/[【『（(《]([^】』）)》]{1,16})[】』）)》]/);
    if (bracket) return bracket[1].trim().slice(0, 16);
    return '';
  };
  const moduleOf = (el, text) => {
    const base = containerOf(el);
    const label = labelOf(text || '');
    return label ? base + '|' + label : base;
  };
  // 「纯候选单元格」判定：供应商常把「期号 + 玩法标签」放一个 <td>、把候选生肖/号码放另一个 <td>，
  // 候选格里既没有「开」也没有黄底，只按那两条过滤会把它丢掉，于是 R5 看不到展示值、
  // R8 也把「有候选」的模块误判成空集。这里用「像候选」的形态把它捞回来。
  const ZODIAC_CHARS = /[鼠牛虎兔龙蛇马羊猴鸡狗猪龍馬雞豬]/g;
  const looksLikeCandidates = (value) => {
    const text = String(value || '');
    const zodiacs = (text.match(ZODIAC_CHARS) || []).length;
    const numbers = (text.match(/\d{2}/g) || []).length;
    return zodiacs >= 2 || numbers >= 2 || /[尾头波]/.test(text);
  };
  // 只统计「相对父节点新增的」黄色：容器整体黄底不会被算成本行高亮，
  // 但供应商用 class（.stylesb）、bgcolor 属性或内联 style 造成的黄底都能被抓到。
  const isYellow = (value) => {
    const s = String(value || '').replace(/\s+/g, '').toLowerCase();
    return s === 'rgb(255,255,0)' || s === 'rgba(255,255,0,1)' ||
           s === '#ffff00' || s === '#ff0' || s === 'yellow' ||
           // 供应商候选列 CSS（twbst528 home.css `.mtbl td:nth-child(2) span`）的兜底
           // 高亮色 #d1be18：任何落在候选格里的 span 都会被染成这个芥末黄，
           // 与 #FFFF00 同属「命中高亮」口径，必须计入 R3/R4 判定。
           s === 'rgb(209,190,24)' || s === '#d1be18';
  };
  const countYellow = (el) => {
    let n = 0;
    const all = [el].concat(Array.from(el.querySelectorAll('*')));
    for (const node of all) {
      const cs = getComputedStyle(node);
      const parent = node.parentElement;
      const ps = parent ? getComputedStyle(parent) : null;
      const bg = isYellow(cs.backgroundColor) && !(ps && isYellow(ps.backgroundColor));
      const hasText = Boolean((node.textContent || '').trim());
      const fg = hasText && isYellow(cs.color) && !(ps && isYellow(ps.color));
      if (bg || fg) n += 1;
    }
    return n;
  };
  // 标题行 / 表头行绝不并入预测行：
  //   - 标题文本里含模块名（大小中特 / 赢家12码 / 平特5不中），会被 verdict_of 当成判定字；
  //   - 标题的黄色文字/底纹会被 countYellow 当成「本行命中高亮」。
  // 识别方式：显式 data-prediction-title="true"（页面可加），或行内带供应商标题占位
  // （data-lottery-title / data-site-domain 由页面自渲染脚本填充成「台湾彩 www.xxx.com」）。
  // twsyw 每个模块的标题行正好是首行预测行的前一个兄弟行，未开奖期会被误报成
  // 「未开奖却显示判定」+「未开奖行仍有黄底」，已开奖的「错」行会被误报成 R3。
  const isTitleRow = (el) => String(el.getAttribute('data-prediction-title') || '') === 'true'
    || Boolean(el.querySelector('[data-lottery-title],[data-site-domain]'));
  for (const item of leaves) {
    // 供应商常把一期的内容拆成多个单元格 / 相邻两个 <tr>：
    //   `<td>270期【绝杀二肖】开 马37错</td><td>鸡,马</td>`
    // 只取叶子会看不到「鸡,马」这块高亮，于是 R3（判错却有黄底）整类漏报。
    // 这里把「本单元格之后、不含期号的同辈」和「相邻的不含期号的 <tr>」合并进来，
    // 只合并含开奖段或确实带黄底的那一块，遇到下一个期号立刻停止。
    let text = item.text;
    const nodes = [item.el];
    // 从叶子沿祖先链向上最多 4 层，把「本节点之后、不含期号」的同辈逐个并进来
    // （一期的内容可能被拆在 <td> 里的多个 <span>，也可能拆在同一 <tr> 的多个 <td>）。
    let cursor = item.el;
    for (let depth = 0; depth < 4 && cursor && cursor.parentElement; depth += 1) {
      const holder = cursor.parentElement;
      let collecting = false;
      for (const child of Array.from(holder.children)) {
        if (child === cursor || child.contains(cursor)) { collecting = true; continue; }
        if (!collecting) continue;
        if (isTitleRow(child)) continue;
        const childText = (child.textContent || '').replace(/\s+/g, ' ').trim();
        if (!childText || childText.length > 260) continue;
        if (/\d{2,3}\s*期/.test(childText)) { collecting = false; break; }
        if (!/开|開/.test(childText) && countYellow(child) === 0 && !looksLikeCandidates(childText)) continue;
        if (text.length + childText.length > 220) { collecting = false; break; }
        text = (text + ' ' + childText).trim();
        nodes.push(child);
      }
      const tag = String(holder.tagName || '').toUpperCase();
      if (tag === 'TR' || tag === 'TBODY' || tag === 'TABLE' || tag === 'BODY') break;
      cursor = holder;
    }
    const host = item.el.closest('tr');
    if (host) {
      // 只并入**后面**的兄弟行：供应商把「一期」拆成两行时，内容行写在标签行之后
      // （四字玄机 / 独家幽默 / 一句真言都是「标题行 + 内容行」）。若回头并上一个兄弟行，
      // 会把上一期的内容行算到本期头上，造成「错期却有黄底」的假阳性。
      // 连续并入**多个**兄弟行，直到遇到下一个期号为止——「配对模块」会把判定留在 header 行、
      // 把命中黄底写在紧随其后的 detail 行，只并一行会漏掉那块高亮（twssz 的三肖六码/双波10码）。
      let sib = host.nextElementSibling;
      let merged = 0;
      while (sib && merged < 3) {
        if (isTitleRow(sib)) { sib = sib.nextElementSibling; continue; }
        const sibText = (sib.textContent || '').replace(/\s+/g, ' ').trim();
        if (!sibText || sibText.length > 260) break;
        if (/\d{2,3}\s*期/.test(sibText)) break;
        if (!/开|開/.test(sibText) && countYellow(sib) === 0 && !looksLikeCandidates(sibText)) break;
        if (text.length + sibText.length > 220) break;
        text = (text + ' ' + sibText).trim();
        nodes.push(sib);
        merged += 1;
        sib = sib.nextElementSibling;
      }
    }
    out.push({
      module: moduleOf(item.el, text),
      label: labelOf(text),
      text: text,
      html: nodes.map((node) => node.outerHTML).join('').slice(0, 4000),
      highlights: nodes.reduce((sum, node) => sum + countYellow(node), 0),
    });
  }
  return out;
}
"""

LEGEND_SCRIPT = r"""
() => {
  const out = [];
  const nodes = Array.from(document.querySelectorAll('tr, p, div, li, td, b, font, span'));
  for (const el of nodes) {
    const html = el.innerHTML || '';
    if (!/肖|生肖/.test(html)) continue;
    if (el.children.length > 0 && el.textContent.length > 200) continue;
    const text = (el.innerText || '').replace(/\s+/g, ' ').trim();
    if (!text || text.length > 120) continue;
    out.push({ text, html: html.slice(0, 3000) });
  }
  return out;
}
"""


@dataclass
class Finding:
    site: str
    rule: str
    level: str
    detail: str
    sample: str = ""
    #: 这条 finding 来自哪个页面（多 URL 站点必须标注来源，否则分不清是首页还是文章页）。
    url: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "rule": self.rule,
            "level": self.level,
            "detail": self.detail,
            "sample": self.sample,
            "url": self.url,
        }


@dataclass
class SiteReport:
    site: str
    label: str
    url: str
    rows: int = 0
    errors: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    row_dump: list[dict[str, Any]] = field(default_factory=list)
    #: 该站点扫过的全部页面（主 URL + extra_urls），顺序即扫描顺序。
    urls: list[str] = field(default_factory=list)
    #: 每个页面的 `{url, rows, js_errors}`，用于报告里按 URL 汇总。
    pages: list[dict[str, Any]] = field(default_factory=list)


#: R5 的「连续同值」告警阈值按模块覆盖，与生成侧
#: `backend/src/prediction_generation/diversity.py::DISPLAY_UNIQUE_WINDOW_BY_MODE` 对齐：
#: 默认 3 期（连续 3 期同值即告警）；mode 5「天地生肖」为 4 期（允许连续 3 期、禁止第 4 期），
#: 否则会把合规数据报成 R5 噪音。
DISPLAY_WINDOW_BY_MODULE_LABEL: tuple[tuple[str, int], ...] = (
    ("天地生肖", 4),
    ("四字玄机", 5),
    ("欲钱解特", 5),
)
#: 按 mode id 覆盖（与后端 `DISPLAY_UNIQUE_WINDOW_BY_MODE` 一一对应）。
#: 15「单双公式」2026-10-17 起：分类（单生肖/双生肖）最多连续 3 期同值、第 4 期换另一分类，
#: 因此阈值取 4，避免把合规的 3 连报成 R5。
DISPLAY_WINDOW_BY_MODE_ID: dict[int, int] = {5: 4, 15: 4, 52: 5, 62: 5}
DEFAULT_DISPLAY_WINDOW = 3
#: 容器 id 形如 `pred-<group>-<modeId>`（twcf888 等文章站），从中取出 mode id。
_MODULE_ID_MODE_RE = re.compile(r"(?:^|[-_])pred[-_][A-Za-z0-9]+[-_](\d+)$")


def display_window_for_module(module: str) -> int:
    """该模块「连续多少期同值即告警」的阈值。

    取值顺序：容器 id 里的 mode 号（`#pred-amgst-5` → mode 5 → 4 期）→ 模块名标签
    （`#nannv|天地生肖资料` → 4 期）→ 默认 3 期。若容器标题就是展示值本身
    （`#pred-amgst-5|地肖+蛇羊`），标签匹配必然失败，所以 mode 号这条路是主要依据。
    """
    text = str(module)
    module_id = text.split("|", 1)[0].lstrip("#")
    matched = _MODULE_ID_MODE_RE.search(module_id)
    if matched:
        mode_id = int(matched.group(1))
        if mode_id in DISPLAY_WINDOW_BY_MODE_ID:
            return int(DISPLAY_WINDOW_BY_MODE_ID[mode_id])
    for label, window in DISPLAY_WINDOW_BY_MODULE_LABEL:
        if label in text:
            return int(window)
    return DEFAULT_DISPLAY_WINDOW


def is_pending(text: str) -> bool:
    return any(token in text for token in PENDING_PATTERNS)


VERDICT_TAIL_RE = re.compile(r"(不中|[准对错赢输中])\s*[）)】\]》〉」\s。．.]*$")
# 「中奖 / 不中奖 / 必中N肖 / 中特」都是站点自带的标签文案，不是对/错判定，
# 读进来会造出大量假命中（twsaimahui 的「必中六肖/必中三肖/必中一肖」就在开奖段之后）。
VERDICT_NOISE_RE = re.compile(r"不?中奖|必中|中特")
# 排除型（杀号）玩法：判定「准/对」= 杀掉的集合里没有开奖目标 = 本来就没有可高亮的命中项，
# R4（命中却没高亮）对这类模块不适用。
EXCLUDE_MODULE_RE = re.compile(r"绝杀|绝禁|绝版杀|输尽光|杀[一二三四五六七八九十\d]|必杀")
# 「一格多玩法」的聚合卡片（A级猛料/AAA级大公开）：卡片级的「对」表示卡内至少有一处命中，
# 供应商也确实把那处命中标了黄（只是在同一张卡的别的格子里）。这类卡片按卡判定符合规范，
# 逐格看会误报 R4，故显式豁免。
AGGREGATE_CARD_RE = re.compile(r"A级大公|AAA级大公|准确率")


def _rightmost_verdict(tail: str) -> str:
    best = ""
    best_end = -1
    for token in VERDICT_TOKENS:
        start = tail.rfind(token)
        if start < 0:
            continue
        end = start + len(token)
        if end > best_end or (end == best_end and len(token) > len(best)):
            best = token
            best_end = end
    return best


def verdict_of(text: str) -> str:
    """取该行的判定文字。

    四步定位，避免四类误判：
    1. 只看**开奖结果之后**的部分——模块名里也含「中」（单双中特 / 八肖中特 / 一波中特 …），
       在整行里搜「中」会把模块名当成判定；
    2. 取**最靠右**的那个判定字——模块名里也含判定字（twcaibawang 的「输尽光」含「输」，
       行内没有「开」字时整行就是 tail），按固定 token 顺序取第一个会把它当成判定，
       而真正的判定总在行尾。结束位置相同时优先更长的 token（「不中」优于「中」）；
    3. 行内**没有**「开/開」（或没有像开奖段起点的「开/開」，例如段子正文里的「开视频」）时，
       只有当判定字出现在**行尾**（允许后面跟右括号/空白/句号）
       才认账——否则「270期七肖中特：www.xxx.com长期跟踪」这类标题/文章行里的「中」
       会被误判成判定（R2/R3/R4/R8 的主要误报来源）；
    4. 先把「中奖 / 不中奖」这类状态文案去掉——twjinniu 的 `开奖【www.xxx.com】中奖`
       会被第 1、2 步读成命中。
    """
    cleaned = VERDICT_NOISE_RE.sub("", text)
    # 只把「看起来像开奖段起点」的 开/開 当锚点（见 VERDICT_ANCHOR_RE 注释）。
    openings = list(VERDICT_ANCHOR_RE.finditer(cleaned))
    if not openings:
        tail_match = VERDICT_TAIL_RE.search(cleaned)
        return tail_match.group(1) if tail_match else ""
    # 判定字紧跟在开奖结果后面。只在「最后一个开/開」之后的短窗口里找，
    # 否则像 shengshi8800 的独家幽默那样，笑话正文里的「对我又是…」会被当成判定「对」。
    tail = cleaned[openings[-1].end():]
    window = tail[:16]
    # 占位结果（`？00` / `待开奖`）后面**紧跟**的就是判定位置：窗口只到占位符之后 2 字。
    # 否则同行的段子/谜面正文会被读成判定（线上 2026-10-06 shengshi8800【独家幽默】
    # 279 期：`開:？00 独家幽默：在网吧上网中…` 的「上网中」被读成判定「中」→ 假 R2）。
    lead = re.match(r"[\s:：]*", tail)
    body_start = lead.end() if lead else 0
    pending = PENDING_RE.match(tail[body_start:])
    if pending:
        window = tail[: body_start + pending.end() + 2]
    window_hit = _rightmost_verdict(window)
    if window_hit:
        return window_hit
    # 窗口里没有（例如「开奖【域名】」这类结构），退回「行尾判定字」口径。
    tail_match = VERDICT_TAIL_RE.search(cleaned)
    return tail_match.group(1) if tail_match else ""


def highlight_count(html: str) -> int:
    return html.upper().count("#FFFF00")


def row_highlights(row: dict[str, Any]) -> int:
    """行内黄色高亮数：取「计算样式实测值」与「HTML 字面量」的较大者。

    计算样式能抓到 class / bgcolor 属性造成的黄底，HTML 字面量能抓到样式表里
    写了 `#FFFF00` 但元素当前不在文档流内的边角情况。
    """
    computed = row.get("highlights")
    computed_count = int(computed) if isinstance(computed, (int, float)) else 0
    return max(computed_count, highlight_count(str(row.get("html") or "")))


def prediction_body(text: str) -> str:
    """把一行文本切成「本期预测正文 + 开奖段」，只返回**预测正文**。

    为什么必须切：R5 比的是「本期展示了什么」。行文本的后半段（`开 兔40错` /
    `开:47猴错`）每期都不一样（开奖号码 + 判定文字），拿整行比较会把「连续 7 期
    展示同一个候选」永远比成不相等 —— R5 因此整类漏报（线上 twcf888「天地生肖」
    279-285 连续 7 期 `地肖+蛇羊` 就是这么漏掉的）。

    切割点复用判定锚点 `VERDICT_ANCHOR_RE`（注释见上）：它定位的就是「开奖段起点」，
    正文里那些**不像开奖段**的「开」（段子里的「开视频 / 开心」）不会被误当切割点。
    一个锚点都找不到时退回旧口径「第一个 开/開」，保证没有锚点的模板（`开 ;野:…`）
    仍按原来的位置切割。
    """
    anchor = VERDICT_ANCHOR_RE.search(text)
    if anchor:
        return text[: anchor.start()]
    opening = re.search(r"开|開", text)
    return text[: opening.start()] if opening else text


def extract_display_token(text: str, label: str = "") -> str:
    """取「最后一个期号」到「开奖段」之间的展示值（预测内容）。

    取值优先级：
    1. 先按 `prediction_body` 砍掉开奖段（号码 + 判定文字）；
    2. 去掉行内标签（`270期 双波 【蓝波,绿波】 开:…` 里的 `双波`）之后；
    3. 若剩余文本里有 `【…】/『…』/（…）`，取括号内容作为展示值
       （这样 R5 比较的是「本期选了什么」，而不是每期都一样的标签）；
    4. 否则用剩余文本本身。
    剩余内容若全是标签/标点（去掉标签后什么都不剩），返回空串跳过 R5。
    """
    head = prediction_body(text)
    terms = list(re.finditer(r"\d{2,3}\s*期", head))
    if not terms:
        return ""
    raw = head[terms[-1].end():].strip()
    # 全角冒号 `：` 必须一起去掉：只写 `[::\s]` 时 `285期：内幕大公` 剥不掉冒号，
    # 后面的标签剥离（`raw.startswith(label)`）随之失配，模块名会被当成展示值。
    raw = re.sub(r"^[::：\s]+", "", raw)
    if label and raw.startswith(label):
        raw = raw[len(label):].lstrip(":： ")
    brackets = [
        part.strip()
        for part in re.findall(r"[【『（(《]([^】』）)》]*)[】』）)》]", raw)
        # `(7.)` / `(5.)` 这类是**序号标记**（twjinniu 七肖中特给每个玩法段编号），
        # 不是展示值括号；当括号取出来会得到 `7. / 5. / 3. / 9.` 这种恒定串 → 假 R5。
        if not re.fullmatch(r"\d+\s*\.", part.strip())
    ]
    joined = " / ".join(part for part in brackets if part)
    if joined:
        return joined[:40]
    without_labels = re.sub(r"[【\[（(《〈「][^】\]）)》〉」]*[】\]）)》〉」]", "", raw)
    if not re.sub(r"[\s:：,，、.。·\-—]", "", without_labels):
        return ""
    return raw[:40]


#: 展示值必须「像个预测内容」：含生肖 / 号码 / 波色 / 头尾 / 大小 / 五行 / 天地 / 前后 之类的字符。
#:
#: 这条配合 `title_modules` 取代了旧的「出现频率 ≥40% 就当成列头剔除」启发式。那条启发式的
#: 假设（「真正的相邻 3 期同值不可能在同一模块里占掉这么大比例」）正好和 R5 要抓的缺陷相反：
#: 面板卡死时就是同一份候选连着 7、8 期不动，频率必然高，于是 R5 反被压掉
#: （twcf888「天地生肖」279-285 连续 7 期 `地肖+蛇羊`、占该模块 8 行的 7/8，就是这么漏报的）。
DISPLAY_VALUE_RE = re.compile(
    r"[鼠牛虎兔龙蛇马羊猴鸡狗猪龍馬雞豬免]|\d|"
    r"[蓝藍红紅绿綠波单單双雙大小家野天地前後后左右日夜阴阳陰陽金木水火土"
    r"琴棋书画書畫合半平特头頭尾段黑白]"
)

#: 「抽取残渣」形态：展示值里还残留开奖段标记、括号、分句符等结构字符。
#:
#: 出现这些字符说明这一行的「期号 → 开奖段」没切干净（例如 `#table1799` 的
#: `285期：欲钱买特码【 开兔40` 只有半个括号、`AAA级大公开;准确率绝对100%;大胆下注!`
#: 的 `开` 落在宣传语里），此时取出来的串是模板文案而不是本期候选，不能参与 R5
#: （否则整列恒定 = 假 R5）。
JUNK_TOKEN_RE = re.compile(r"[开開【\[『「（(《〈；;！!]")


def title_modules(by_module_seq: dict[str, list[tuple[str, str]]]) -> set[str]:
    """挑出「展示值其实是模块列标题 / 标签页名」的 module。

    判据（两个都指向「这个标签每期都一样，是玩法名而不是本期展示内容」）：
    1. 容器里**只有这一个标签** —— 说明同容器下没有并列玩法名，标签恒定 ⇒ 列标题
       （`#pred-amgst-483|四头必中`：`285期【四头必中】开 兔40对 1-2-0-4`，
       真正的候选 `1-2-0-4` 落在开奖段之后，抽取只能回落到模块名）；
    2. 容器里存在**期号重叠**的另一个标签 —— 同一个期号下同容器挂了两个不同标签，
       说明它们是并列的玩法名 / 标签页（twcf888 `#pred-amgst-53` 的
       `三行中特` 与 `精准五行`、twbst528 `.center.f13` 的 `双波⑩码` 与 `六肖十八码`）。

    反例（必须保留、不能当标题剔掉）：twcf888 `#pred-amgst-5` 的 `地肖+蛇羊`
    （279-285 期）与 `天肖+狗龙`（278 期）—— 容器里确实有两个标签，但期号
    **不重叠**：这是同一个面板换了一期就换了候选，那个「标签」就是本期展示值，
    必须照常参与 R5。旧实现「出现频率 ≥40% 就当列头剔除」的启发式把这一类
    真缺陷一起压掉了（见 `DISPLAY_VALUE_RE` 注释）。
    """
    terms_of = {module: {term for term, _ in seq} for module, seq in by_module_seq.items()}
    modules_of: dict[str, set[str]] = {}
    for module in by_module_seq:
        container, sep, label = module.rpartition("|")
        if sep and label:
            modules_of.setdefault(container, set()).add(module)

    titles: set[str] = set()
    for module in by_module_seq:
        container, sep, label = module.rpartition("|")
        if not sep or not label:
            continue
        # 容器归属不明的行（`containerOf` 没找到 id/class，key 就是 `?|…`）无法区分
        # 「列标题」与「本期展示值」，按 R4/R8 的同一约定不在这里做标题判定——
        # twbst528 首页的 `?|地肖+蛇羊` 就是这样一行一个玩法值（同容器 `?` 下挂着 105 个
        # 模块），把它当标题会把「连续 6 期地肖+蛇羊」的真缺陷压掉。
        if container == "?":
            continue
        my_terms = terms_of[module]
        peers = [peer for peer in modules_of.get(container, ()) if peer != module]
        if not peers:
            titles.add(module)
            continue
        if any(my_terms & terms_of[peer] for peer in peers):
            titles.add(module)
    return titles


def is_display_value(token: str, title_token: str = "") -> bool:
    """该展示值是否「像预测内容」且不是稳定的列标题 / 抽取残渣（R5 只比较这类值）。"""
    text = str(token or "").strip()
    if not text:
        return False
    if title_token and text == str(title_token).strip():
        return False
    if JUNK_TOKEN_RE.search(text):
        return False
    return bool(DISPLAY_VALUE_RE.search(text))


def audit_rows(site_key: str, rows: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    display_seq: list[tuple[str, str, str]] = []

    for row in rows:
        text = row["text"]
        html = row["html"]
        module = row.get("module", "?")
        verdict = verdict_of(text)
        pending = is_pending(text)
        highlights = row_highlights(row)
        samples = text[:120]

        # R1 原始 JSON 残留
        if re.search(r'\["|\"\]|\\"', text):
            findings.append(Finding(site_key, "R1 raw_json_leak", "error",
                                    f"{module} 可见文本残留原始 JSON 片段", samples))

        # R2 未开奖却给判定：
        #   - 占位结果 + 命中判定（准/对/赢/中）一定是错的（没有开奖号码却宣称命中）→ error
        #   - 占位结果 + 未命中判定 → warn（多数模块用 `？00` 表示「本期无命中项」，
        #     需要人工确认该模块是不是真的未开奖）
        if pending and verdict:
            level = "error" if verdict in ("准", "对", "赢", "中") else "warn"
            findings.append(Finding(site_key, "R2 verdict_pending", level,
                                    f"{module} 结果为占位（未开奖/无命中项）却显示判定「{verdict}」", samples))

        # R3 判定为错却有高亮
        if verdict in ("错", "输", "不中") and highlights > 0:
            findings.append(Finding(site_key, "R3 highlight_miss", "error",
                                    f"{module} 判定「{verdict}」但仍有一处黄色高亮", samples))

        term_match = re.search(r"(\d{2,3})\s*期", text)
        # 只有含「开/開」的才是真正的预测行；文章列表/导航里的「N期 已更新」不算展示值。
        if term_match and re.search(r"开|開", text):
            display_seq.append(
                (module, term_match.group(1), extract_display_token(text, str(row.get("label") or "")))
            )

    # R4 命中却无高亮：按模块分组，仅当同模块其它行确有高亮时才报
    by_module: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_module.setdefault(row.get("module", "?"), []).append(row)
    for module, module_rows in by_module.items():
        if not any(row_highlights(row) > 0 for row in module_rows):
            continue
        # 模块级豁免：只要该模块任意一行自报是排除型（杀号）玩法，整模块都不报 R4——
        # 「准」= 杀掉的集合里没有开奖目标 = 本来就没有可高亮的命中项。
        # 不能只看当前行：合并后的行常常只剩「N期 开:xx准」，标签在没被并进来的兄弟里。
        if any(EXCLUDE_MODULE_RE.search(row["text"]) for row in module_rows):
            continue
        # 模块归属不明的行（跨行合并拿不到容器 id）无法可靠归因高亮，不报 R4。
        if module == "?" or module.startswith("?|"):
            continue
        # 「一格多玩法」的聚合卡片按卡判定（见 AGGREGATE_CARD_RE 注释）。
        if AGGREGATE_CARD_RE.search(module) or any(AGGREGATE_CARD_RE.search(row["text"]) for row in module_rows):
            continue
        for row in module_rows:
            if is_pending(row["text"]):
                continue
            if verdict_of(row["text"]) in ("准", "对", "赢", "中") and row_highlights(row) == 0:
                findings.append(Finding(site_key, "R4 highlight_hit", "warn",
                                        f"{module} 该行判定为命中，但本行没有黄色高亮",
                                        row["text"][:120]))

    # R5 相邻 3 期以上展示值完全相同（同一模块内、按期号降序/升序的连续段）
    by_module_seq: dict[str, list[tuple[str, str]]] = {}
    for module, term, token in display_seq:
        by_module_seq.setdefault(module, []).append((term, token))
    title_module_set = title_modules(by_module_seq)
    for module, seq in by_module_seq.items():
        _, sep, label = module.rpartition("|")
        title_token = label if (sep and module in title_module_set) else ""
        run_start = 0
        for index in range(1, len(seq) + 1):
            same = (
                index < len(seq)
                and seq[index][1] == seq[run_start][1]
                and is_display_value(seq[index][1], title_token)
            )
            if same:
                continue
            run_len = index - run_start
            token = seq[run_start][1]
            # 告警阈值必须与生成侧口径一致（见 DISPLAY_WINDOW_BY_MODULE_LABEL）：
            # 默认「连续 3 期同值」即告警；mode 5 天地生肖允许连续 3 期（window=4），
            # 否则会把合规数据报成 R5 噪音。
            if run_len >= display_window_for_module(module) and is_display_value(token, title_token):
                terms = ",".join(item[0] for item in seq[run_start:index])
                findings.append(Finding(site_key, "R5 repeat_run", "warn",
                                        f"{module} 连续 {run_len} 期展示值相同：{token!r}",
                                        terms))
            run_start = index

    # R8 某模块已开奖行全部同一个判定（「整列全对 / 整列全错」的统一性告警）
    hit_tokens = ("准", "对", "赢", "中")
    miss_tokens = ("错", "输", "不中")
    for module, module_rows in by_module.items():
        # 归属不明的容器（拿不到 id/class）与「一格多玩法」的聚合卡片不参与 R8——
        # 前者无法确定是不是同一个玩法，后者的行本来就跨玩法混排。
        if module == "?" or module.startswith("?|"):
            continue
        if AGGREGATE_CARD_RE.search(module) or any(AGGREGATE_CARD_RE.search(row["text"]) for row in module_rows):
            continue
        decided: list[str] = []
        for row in module_rows:
            text = row["text"]
            if is_pending(text):
                continue
            verdict = verdict_of(text)
            if verdict in hit_tokens:
                decided.append("hit")
            elif verdict in miss_tokens:
                decided.append("miss")
        if len(decided) < 5 or len(set(decided)) != 1:
            continue
        state = "命中（准/对）" if decided[0] == "hit" else "未命中（错）"
        findings.append(Finding(site_key, "R8 verdict_all_same", "warn",
                                f"{module} 共 {len(decided)} 期已开奖行全部判定为{state}，"
                                f"疑似判定口径写死或候选集失效",
                                ",".join(row["text"][:40] for row in module_rows[:2])))
    return findings


def audit_legends(site_key: str, legends: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for legend in legends:
        text = legend["text"]
        for match in LEGEND_EMPTY_RE.finditer(text):
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            findings.append(Finding(site_key, "R6 empty_legend", "error",
                                    f"分组说明「{name}:」后面为空",
                                    text[:120]))
    return findings


def site_urls(site: dict[str, Any], base_url: str = "") -> list[str]:
    """该站点要扫的全部页面：主 URL + `extra_urls`（去重、保持顺序）。

    `base_url` 非空时（本地预检）逐条把线上域名换成该地址。
    """
    raw_urls = [str(site.get("url") or "")]
    raw_urls.extend(str(item) for item in (site.get("extra_urls") or []))
    urls: list[str] = []
    for item in raw_urls:
        if not item or item in urls:
            continue
        urls.append(_rewrite_url(item, base_url) if base_url else item)
    return urls


def _rewrite_url(url: str, base_url: str) -> str:
    """本地预检：把线上域名换成 --base-url（例如 http://127.0.0.1:3000），保留 path/query。"""
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    base = urlsplit(base_url.rstrip("/"))
    return urlunsplit((base.scheme, base.netloc, parts.path, parts.query, parts.fragment))


def audit_site(
    site: dict[str, Any],
    *,
    headless: bool = True,
    base_url: str = "",
    wait_ms: int = 12000,
) -> SiteReport:
    from playwright.sync_api import sync_playwright

    urls = site_urls(site, base_url)
    report = SiteReport(site=site["key"], label=site["label"], url=urls[0], urls=list(urls))
    multi = len(urls) > 1

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=headless)
        for page_url in urls:
            page_errors: list[str] = []
            page = browser.new_page(viewport={"width": 900, "height": 1200})
            page.on("pageerror", lambda exc, bucket=page_errors: bucket.append(str(exc)[:200]))
            rows: list[dict[str, Any]] = []
            legends: list[dict[str, Any]] = []
            try:
                page.goto(page_url, wait_until="domcontentloaded", timeout=180000)
                # 「站点数据客户端 + 供应商聚合 payload」的站点首屏可能要几十秒才渲染预测行
                # （twbst528 线上实测约 39 s），等待窗口太短会只扫到供应商模板行，
                # 线上审计因此空跑（rows 偏少甚至 0）。默认仍保持历史上的 12 s，
                # 慢站用 `--wait-ms` 显式加长。
                page.wait_for_timeout(max(1000, int(wait_ms)))
                frames = [frame for frame in page.frames]
            except Exception as exc:  # noqa: BLE001
                page_errors.append(f"goto failed: {exc}")
                frames = []
            else:
                for frame in frames:
                    try:
                        rows.extend(frame.evaluate(ROW_SCRIPT) or [])
                        legends.extend(frame.evaluate(LEGEND_SCRIPT) or [])
                    except Exception:  # noqa: BLE001 - 跨域 frame 直接跳过
                        continue
            finally:
                page.close()

            # 多 URL 站点把页面来源写进错误串；单 URL 站点保持历史输出不变（js_errors 仍是裸消息）。
            report.errors.extend(
                f"[{page_url}] {message}" if multi else message for message in page_errors
            )
            report.pages.append({"url": page_url, "rows": len(rows), "js_errors": page_errors})
            report.rows += len(rows)
            # 每行打上来源页面，`--dump-rows` 与报告里才能按 URL 归因。
            for row in rows:
                row["url"] = page_url
            report.row_dump.extend(rows)

            # 规则判定按页面分组跑：R4/R5/R8 的「同一模块相邻期」只在**本页**成立，
            # 跨页合并会把首页与文章页的同期号行接成一段，造出假 R5。
            for finding in audit_rows(site["key"], rows):
                finding.url = page_url
                report.findings.append(finding)
            for finding in audit_legends(site["key"], legends):
                finding.url = page_url
                report.findings.append(finding)

        browser.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", nargs="*", help="站点 key，留空表示全部")
    parser.add_argument("--json", dest="json_path", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--base-url", default="", help="本地预检：替换站点域名为该地址（如 http://127.0.0.1:3000）")
    parser.add_argument("--dump-rows", default="", help="把抓到的每一行（url/module/label/text/highlights）写到该 JSON，便于人工复核")
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=12000,
        help="页面加载后等待渲染的毫秒数（默认 12000；慢站如 twbst528 线上建议 90000）",
    )
    args = parser.parse_args()

    targets = [site for site in SITES if not args.sites or site["key"] in args.sites]
    if not targets:
        print("没有匹配的站点，可选：", ", ".join(site["key"] for site in SITES))
        return 1

    reports: list[SiteReport] = []
    for site in targets:
        print(f"=== auditing {site['key']} …", flush=True)
        report = audit_site(
            site,
            headless=not args.headed,
            base_url=args.base_url,
            wait_ms=args.wait_ms,
        )
        reports.append(report)
        errors = [f for f in report.findings if f.level == "error"]
        warns = [f for f in report.findings if f.level == "warn"]
        print(f"    rows={report.rows} js_errors={len(report.errors)} error={len(errors)} warn={len(warns)}")

    text_lines = ["# 预测模块展示规范审计报告", ""]
    for report in reports:
        text_lines.append(f"## {report.label}  ({report.url})")
        text_lines.append(f"- 扫描行数：{report.rows}（{len(report.pages)} 个页面）")
        if report.errors:
            text_lines.append(f"- JS 报错：{report.errors}")
        if not report.findings:
            text_lines.append("- 未发现违规 ✅")
        # 多 URL 站点按页面分组，明确每条违规来自首页还是文章页；单 URL 站点保持原样。
        if len(report.pages) > 1:
            text_lines.append("- 页面明细：")
            for page in report.pages:
                text_lines.append(f"  - {page['url']} → 行数 {page['rows']}")
            for page in report.pages:
                page_findings = [item for item in report.findings if item.url == page["url"]]
                if not page_findings:
                    continue
                text_lines.append(f"- 来源 {page['url']}：")
                for finding in page_findings:
                    mark = "ERROR" if finding.level == "error" else "warn"
                    text_lines.append(
                        f"  - [{mark}] `{finding.rule}` {finding.detail} | 样例：{finding.sample}"
                    )
        else:
            for finding in report.findings:
                mark = "ERROR" if finding.level == "error" else "warn"
                text_lines.append(f"- [{mark}] `{finding.rule}` {finding.detail} | 样例：{finding.sample}")
        text_lines.append("")

    report_path = args.json_path.replace(".json", ".md") if args.json_path else "audit-prediction-display.md"
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(text_lines))
    print(f"文本报告已写入 {report_path}")

    if args.json_path:
        payload = {
            "sites": [
                {
                    "site": report.site,
                    "label": report.label,
                    "url": report.url,
                    "urls": report.urls,
                    "pages": report.pages,
                    "rows": report.rows,
                    "js_errors": report.errors,
                    "findings": [finding.as_dict() for finding in report.findings],
                }
                for report in reports
            ]
        }
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
        print(f"JSON 报告已写入 {args.json_path}")

    if args.dump_rows:
        # 多 URL 站点：`row_dump` 带 `url` 字段，人工复核时能分清每一行来自哪个页面。
        dump_payload = {
            report.site: [
                {
                    "url": row.get("url", report.url),
                    "module": row.get("module", "?"),
                    "label": row.get("label", ""),
                    "text": row.get("text", ""),
                    "highlights": row_highlights(row),
                    "verdict": verdict_of(str(row.get("text") or "")),
                    "pending": is_pending(str(row.get("text") or "")),
                }
                for row in report.row_dump
            ]
            for report in reports
        }
        with open(args.dump_rows, "w", encoding="utf-8") as handle:
            json.dump(dump_payload, handle, ensure_ascii=False, indent=1)
        print(f"逐行明细已写入 {args.dump_rows}")

    total_errors = sum(1 for report in reports for f in report.findings if f.level == "error")
    print(f"== total error={total_errors}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
