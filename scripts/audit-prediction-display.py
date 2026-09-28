#!/usr/bin/env python
"""预测模块展示规范审计工具（十站点通用）。

用法：
    python scripts/audit-prediction-display.py                 # 审计全部站点
    python scripts/audit-prediction-display.py twsaimahui      # 只审计指定站点
    python scripts/audit-prediction-display.py --json out.json # 额外输出 JSON

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
import collections
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
PENDING_PATTERNS = (
    "？00", "?00", "？？？", "??????", "?????", "????", "？？", "待开",
    "猫00", "？?", "?？",
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
           s === '#ffff00' || s === '#ff0' || s === 'yellow';
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "rule": self.rule,
            "level": self.level,
            "detail": self.detail,
            "sample": self.sample,
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
    3. 行内**没有**「开/開」时，只有当判定字出现在**行尾**（允许后面跟右括号/空白/句号）
       才认账——否则「270期七肖中特：www.xxx.com长期跟踪」这类标题/文章行里的「中」
       会被误判成判定（R2/R3/R4/R8 的主要误报来源）；
    4. 先把「中奖 / 不中奖」这类状态文案去掉——twjinniu 的 `开奖【www.xxx.com】中奖`
       会被第 1、2 步读成命中。
    """
    cleaned = VERDICT_NOISE_RE.sub("", text)
    openings = list(re.finditer(r"开|開", cleaned))
    if not openings:
        tail_match = VERDICT_TAIL_RE.search(cleaned)
        return tail_match.group(1) if tail_match else ""
    # 判定字紧跟在开奖结果后面。只在「最后一个开/開」之后的短窗口里找，
    # 否则像 shengshi8800 的独家幽默那样，笑话正文里的「对我又是…」会被当成判定「对」。
    tail = cleaned[openings[-1].end():]
    window_hit = _rightmost_verdict(tail[:16])
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


def extract_display_token(text: str, label: str = "") -> str:
    """取「最后一个期号」到「开/開」之间的展示值（预测内容）。

    取值优先级：
    1. 去掉行内标签（`270期 双波 【蓝波,绿波】 开:…` 里的 `双波`）之后；
    2. 若剩余文本里有 `【…】/『…』/（…）`，取括号内容作为展示值
       （这样 R5 比较的是「本期选了什么」，而不是每期都一样的标签）；
    3. 否则用剩余文本本身。
    剩余内容若全是标签/标点（去掉标签后什么都不剩），返回空串跳过 R5。
    """
    opening = re.search(r"开|開", text)
    head = text[: opening.start()] if opening else text
    terms = list(re.finditer(r"\d{2,3}\s*期", head))
    if not terms:
        return ""
    raw = head[terms[-1].end():].strip()
    raw = re.sub(r"^[::\s]+", "", raw)
    if label and raw.startswith(label):
        raw = raw[len(label):].lstrip(":： ")
    brackets = [part.strip() for part in re.findall(r"[【『（(《]([^】』）)》]*)[】』）)》]", raw)]
    joined = " / ".join(part for part in brackets if part)
    if joined:
        return joined[:40]
    without_labels = re.sub(r"[【\[（(《〈「][^】\]）)》〉」]*[】\]）)》〉」]", "", raw)
    if not re.sub(r"[\s:：,，、.。·\-—]", "", without_labels):
        return ""
    return raw[:40]


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
    for module, seq in by_module_seq.items():
        # 标签降噪：某个 token 在该模块里出现频率 ≥40%（且至少 3 行）时，它是模块名/列头而不是
        # 展示值，真正的「相邻 3 期同值」不可能在同一模块里占掉这么大比例。
        # 只在模块有 ≥6 行时启用，避免小样本整块被跳过。
        label_tokens: set[str] = set()
        if len(seq) >= 6:
            counts = collections.Counter(token for _, token in seq if token)
            threshold = max(3, len(seq) * 0.4)
            label_tokens = {token for token, count in counts.items() if count >= threshold}
        run_start = 0
        for index in range(1, len(seq) + 1):
            same = (
                index < len(seq)
                and seq[index][1] == seq[run_start][1]
                and seq[index][1] != ""
                and seq[index][1] not in label_tokens
            )
            if same:
                continue
            run_len = index - run_start
            token = seq[run_start][1]
            if run_len >= 3 and token and token not in label_tokens:
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


def audit_site(site: dict[str, Any], *, headless: bool = True, base_url: str = "") -> SiteReport:
    from playwright.sync_api import sync_playwright

    url = site["url"]
    if base_url:
        # 本地预检：把线上域名换成 --base-url（例如 http://127.0.0.1:3000）
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(url)
        base = urlsplit(base_url.rstrip("/"))
        url = urlunsplit((base.scheme, base.netloc, parts.path, parts.query, parts.fragment))

    report = SiteReport(site=site["key"], label=site["label"], url=url)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=headless)
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.on("pageerror", lambda exc: report.errors.append(str(exc)[:200]))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=180000)
            page.wait_for_timeout(12000)
            frames = [frame for frame in page.frames]
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"goto failed: {exc}")
            browser.close()
            return report

        all_rows: list[dict[str, Any]] = []
        all_legends: list[dict[str, Any]] = []
        for frame in frames:
            try:
                all_rows.extend(frame.evaluate(ROW_SCRIPT) or [])
                all_legends.extend(frame.evaluate(LEGEND_SCRIPT) or [])
            except Exception:  # noqa: BLE001 - 跨域 frame 直接跳过
                continue
        browser.close()

    report.rows = len(all_rows)
    report.row_dump = all_rows
    report.findings.extend(audit_rows(site["key"], all_rows))
    report.findings.extend(audit_legends(site["key"], all_legends))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", nargs="*", help="站点 key，留空表示全部")
    parser.add_argument("--json", dest="json_path", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--base-url", default="", help="本地预检：替换站点域名为该地址（如 http://127.0.0.1:3000）")
    parser.add_argument("--dump-rows", default="", help="把抓到的每一行（module/text/highlights）写到该 JSON，便于人工复核")
    args = parser.parse_args()

    targets = [site for site in SITES if not args.sites or site["key"] in args.sites]
    if not targets:
        print("没有匹配的站点，可选：", ", ".join(site["key"] for site in SITES))
        return 1

    reports: list[SiteReport] = []
    for site in targets:
        print(f"=== auditing {site['key']} …", flush=True)
        report = audit_site(site, headless=not args.headed, base_url=args.base_url)
        reports.append(report)
        errors = [f for f in report.findings if f.level == "error"]
        warns = [f for f in report.findings if f.level == "warn"]
        print(f"    rows={report.rows} js_errors={len(report.errors)} error={len(errors)} warn={len(warns)}")

    text_lines = ["# 预测模块展示规范审计报告", ""]
    for report in reports:
        text_lines.append(f"## {report.label}  ({report.url})")
        text_lines.append(f"- 扫描行数：{report.rows}")
        if report.errors:
            text_lines.append(f"- JS 报错：{report.errors}")
        if not report.findings:
            text_lines.append("- 未发现违规 ✅")
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
        dump_payload = {
            report.site: [
                {
                    "module": row.get("module", "?"),
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
