#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""预测模块渲染脚本 · 源码级静态 lint（纯标准库）。

用途
====
给新站点接入预测模块时，在**不启动服务、不打开浏览器**的前提下，先把
《预测模块展示规范》（docs/prediction-display-standard.md，S1–S8）里最容易
出事的几类写法找出来。这些写法在页面上表现为：

    恒显示「准」/「错」        -> 判定文字写死在模板或字符串里，没有三元/if 判定
    未命中也有黄底              -> #FFFF00 / class='stylesb' 出现在没有命中判定的分支
    页面出现 [" 原始 JSON      -> 对 content 直接 .split(',') 把原始 JSON 拼进页面
    整块模块空白                -> JSON.parse(d.content) 遇到普通中文串直接抛错
    写死的开奖样例              -> 开:猫00 / 开:蛇12 / 开:00准 之类固定开奖结果
    未开奖也输出判定            -> ？00 / ?? / 待开奖 与 准/错 出现在同一段文本里

它**不是** `scripts/audit-prediction-display.py` 的替代品：审计脚本跑真实浏览器，
看的是渲染结果；本工具只读源码，看的是「写法」。两者互补 ——
lint 快、能进 CI/预检，audit 准、能抓运行期问题。

用法
====
    # 扫描 frontend/public/vendor/ 下全部站点
    python scripts\\lint-prediction-renderers.py

    # 只扫描指定站点（目录名）
    python scripts\\lint-prediction-renderers.py twsaimahui twssz

    # 直接指定目录（可重复），此时忽略位置参数
    python scripts\\lint-prediction-renderers.py --dir frontend/public/vendor/twssz

    # 额外输出 JSON（给 CI / 二次统计用）
    python scripts\\lint-prediction-renderers.py --json .codex-temp\\lint.json

    # 有任何 finding（含 warn）就退出码 1；不带 --strict 时永远退出码 0
    python scripts\\lint-prediction-renderers.py --strict

退出码
======
    0  默认：扫描完成（不管有没有 finding）
    1  --strict 且存在至少一条 finding
    2  参数/路径错误（站点名不存在、--dir 不存在等）

规则与级别
==========
    L1 hardcoded_verdict        error  判定文字写死，表达式里没有任何三元条件/判定变量
    L2 unsafe_json_parse        error  JSON.parse(...) 而不是 safeParseJSON(...)
    L3 raw_content_split        warn   对 content 直接 .split(',') / .split('|')，没有先解析 JSON（信号级）
    L4 static_sample_result     error  写死的开奖样例文本（开:蛇12 / 猫00 / 开:00 之类）
    L5 unconditional_highlight  warn   #FFFF00 / stylesb 出现在没有命中判定变量的分支
    L6 pending_with_verdict     warn   ?? / ？00 / 待开奖 与 准/错 同段且无待开奖分支

排除（第三方 / 打包产物，代码里显式可见 SKIP_* 常量）
====================================================
    jquery*.js  vue.js  axios*.js  boot*.js  layui.js  swiper*.js  sweetalert*.js
    wow*.js  pintuer.js  *.min.js  bundle-<hash>.js

设计取舍（为什么宁可保守）
==========================
* 先剥注释再匹配：本仓库大量「供应商静态样例」原文躺在文件尾部的 `/* ... */`
  注释里，它们不会被渲染，所以必须先剥掉，否则 L4 会整片误报。
* 剥注释只认「// 后面不是 /」的写法：`httpApi + '/api/...'` 这类 URL 里的 `//`
  不会被误当注释（audit 场景宁可少剥，不可多剥）。
* 只扫 .js：渲染脚本是主战场；HTML 属于下一层（见「已知局限」）。

相关文档：docs/prediction-display-standard.md（S1–S8）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

# --------------------------------------------------------------------------
# 规则表（rule id -> 级别 / 说明）
# --------------------------------------------------------------------------

RULES = OrderedDict(
    [
        ("L1 hardcoded_verdict", ("error", "判定文字写死：模板/字符串里出现 准/对/错/赢/输，且该表达式没有三元条件或判定变量")),
        ("L2 unsafe_json_parse", ("error", "JSON.parse(...) 未走 safeParseJSON(...)：按字面规则命中；try/catch 包住的属于低风险，需人工确认")),
        ("L3 raw_content_split", ("warn", "对 content 直接 .split(',')/.split('|')，没有先解析 JSON：可能把 [\"兔|04\",...] 原始串拼进页面（信号级，需人工确认；本仓库历史用法多为裸列表字段）")),
        ("L4 static_sample_result", ("error", "写死的开奖样例：开:/開: 后紧跟具体生肖+两位数字，或 猫00 / 开:00 之类固定结果")),
        ("L5 unconditional_highlight", ("warn", "#FFFF00 / stylesb 出现在没有命中判定变量的分支：未命中也会黄底")),
        ("L6 pending_with_verdict", ("warn", "?? / ？00 / 待开奖 与 准/错 出现在同一段文本且没有待开奖分支：未开奖却给判定")),
    ]
)

RULE_IDS = list(RULES.keys())

# --------------------------------------------------------------------------
# 排除列表（显式可见，第三方库 / 打包产物 / 压缩产物）
# --------------------------------------------------------------------------

SKIP_FILE_GLOBS = (
    "jquery*.js",       # jquery.js / jquery.min.js / jquery-1.11.2.min.js / jquery.appear.js ...
    "vue.js",           # 完整版 vue（含 compress 版另见 vue.min.js）
    "vue.min.js",
    "vue*.min.js",
    "axios*.js",        # axios.min.js ...
    "bootstrap*.js",
    "boot*.js",
    "layui.js",
    "swiper*.js",
    "sweetalert*.js",
    "wow*.js",
    "pintuer.js",
    "*.min.js",         # 任何压缩产物
    "bundle-*.js",      # 打包产物（内容哈希命名，改源 JS 后需重建）
    "v<hex16+>.js",     # 供应商哈希产物：v4513226cdae34746b4dedf0b4dfa099e1781791509496.js
)

SKIP_FILE_REGEXES = tuple(
    re.compile(
        "^"
        + re.escape(g).replace(r"\*", ".*")
        + "$",
        re.IGNORECASE,
    )
    for g in SKIP_FILE_GLOBS
)

BUNDLE_HASH_RE = re.compile(r"^bundle-[0-9a-zA-Z_]+\.js$", re.IGNORECASE)
# v4513226cdae34746b4dedf0b4dfa099e1781791509496.js 这类供应商哈希产物
VENDOR_HASH_RE = re.compile(r"^v[0-9a-f]{16,}\.js$", re.IGNORECASE)
# <name>-<内容哈希16+位>.js / <name>.<内容哈希>.js 之类的打包产物
GENERIC_HASH_RE = re.compile(r"^[\w.-]*[-.][0-9a-f]{16,}\.js$", re.IGNORECASE)

# --------------------------------------------------------------------------
# 词法常量
# --------------------------------------------------------------------------

VERDICT_CHARS = "准对错赢输"

# 判定字符出现在「这个词就是判定」的位置：引号/标签后、数字后、字符串结尾
VERDICT_TOKEN_RE = re.compile(
    r"(?:^|[>\"'）)\]】、,，。;；:\s]|\d)([" + VERDICT_CHARS + r"])(?=$|[<\"'（(\[【、,，。;；:\s])"
)

# 待开奖占位符
PENDING_RE = re.compile(r"\?\?|\uff1f00|\uff1f\uff1f|待开奖")

# 命中判定变量（高亮条件）
HIT_VAR_RE = re.compile(
    r"\b(zj|hit|isHit|hitFlag|dsHit|isCorrect|isOpened|opened|matched|winner|zhong|中)\b|命中"
)

# 判定上下文（说明这一行的判定文字是条件产出的）
VERDICT_CONTEXT_RE = re.compile(
    r"verdictText|verdictOf|isCorrect|isHit|\bhit\b|命中|判别|判定"
)

# 正在做条件区分的迹象
CONDITIONAL_RE = re.compile(r"\?\.|\?[^?]|else|if\s*\(|switch\s*\(|catch")

# 视觉高亮字面量：
#   1) background-color: #FFFF00 / background:#FFFF00 / bgcolor="#FFFF00"
#   2) class='stylesb'（供应商 CSS 里 stylesb = background-color:#FFFF00）
# 刻意**不**把 `<font color='#FFFF00'>` 当高亮：twsaimahui 各模块标题栏用的是
# 「红底 + 黄字」（color 而非 background），不是命中高亮。
HIGHLIGHT_RE = re.compile(
    r"(?:background(?:-color)?|bgcolor)\s*[:=]\s*['\"]?\s*(?:#ffff00\b|#ff0\b|yellow\b)"
    r"|(?:\"|')stylesb(?:\"|')",
    re.IGNORECASE,
)
# 结构化的高亮写法（否则光是写 background-color 文本不算上屏）
HIGHLIGHT_CONTEXT_RE = re.compile(
    r"background(?:-color)?|bgcolor|stylesb|bgcolor\s*=", re.IGNORECASE
)

# L4：写死的开奖样例
ZODIACS = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
L4_ZODIAC_NUM_RE = re.compile(r"[开開]\s*[:：]?\s*[" + ZODIACS + r"]\s*\d{2}")
L4_CAT_NUM_RE = re.compile(r"猫\s*\d{2}")
# 开:00 / 開：12 这类**固定结果号码**：必须紧跟判定文字
# （`开:02准` / `开:00错`）。在**字符串字面量内部**匹配，
# 避免 `'开:02准' : '开:02错'` 这种跨引号误伤，也排除 `开:${code}` 动态写法。
L4_NUM_ONLY_RE = re.compile(
    r"[开開]\s*[:：]?\s*(?<!\d)\d{2}(?!\d)\s*[" + VERDICT_CHARS + r"]"
)

# L2
JSON_PARSE_RE = re.compile(r"\bJSON\s*\.\s*parse\s*\(")
SAFE_PARSE_RE = re.compile(r"\bsafeParseJSON\b")

# L3
# 字符串字面量（单引号、双引号、模板串）
STRING_LITERAL_RE = re.compile(
    r"`(?:\\.|[^`\\])*`|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"",
    re.DOTALL,
)

# 变量被无条件赋成判定文字：var x = ... '准' ... ;
UNCONDITIONAL_VERDICT_ASSIGN_RE = re.compile(
    r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]*)"
)

# 命中比对：`xiao[i].indexOf(sx) !== -1` / `sx && ...` / `code === v` 之类
DRAWN_VAR_RE = re.compile(r"\b(sx|code|res_code|res_sx|drawn|openCode|tm)\b")
COMPARE_OP_RE = re.compile(r"===|!==|==|!=|indexOf|includes|startsWith|match\(")

# L3：对原始 content 串按逗号切（"兔|04,马|..." 会切出 ["兔|04, ... 原始 JSON）
RAW_COMMA_SPLIT_RE = re.compile(r"\bcontent\b[^\n;]{0,40}?\.\s*split\s*\(\s*(['\"]),['\"]\s*\)")
# L3：按 | 切 content 片段，且结果直接进标签模板（字符串拼接的页面上屏路径）
PIPE_SPLIT_RE = re.compile(r"\bcontent\b[^;\n]{0,60}?\.\s*split\s*\(\s*(['\"])\|\1\s*\)")
TEMPLATE_INTERP_RE = re.compile(r"\$\{[^}]*\}|`[^`]*`")


# --------------------------------------------------------------------------
# 注释剥离
# --------------------------------------------------------------------------


REGEX_PREFIX_CHARS = set("(,=:[!&|?{};+-*%~^<>")


def looks_like_regex(src: str, i: int) -> bool:
    """判断 src[i] == '/' 是否开始一个正则字面量（而不是除号）。

    只在「上一个非空白字符是运算符/左括号/逗号/等号」或「前一个词是 return/typeof/case」
    时才认正则；否则按普通除号处理。这样既不把 `a / b / c` 当正则，
    也能正确跳过 `data.replace(/'/g, '"')`。
    """
    j = i - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    if j < 0:
        return True
    prev = src[j]
    if prev in REGEX_PREFIX_CHARS:
        return True
    k = j
    while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
        k -= 1
    word = src[k + 1 : j + 1]
    return word in ("return", "typeof", "case", "in", "of", "do", "else")


def skip_regex_literal(src: str, i: int) -> int:
    """从 src[i] == '/' 起跳过整个正则字面量（含 flags），返回结束后的下标。

    返回 i 本身表示「这其实是除号，不是正则」。
    """
    j = i + 1
    n = len(src)
    in_class = False
    while j < n:
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            return i  # 不是正则，按除号处理
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            j += 1
            while j < n and src[j].isalpha():
                j += 1
            return j
        j += 1
    return i


def strip_comments(src: str) -> str:
    """剥掉 /* */ 与 // 注释，**保持行号不变**（注释字符替换为空格）。

    只认「// 后面不是 /」的情况：`httpApi + '/api/x'`、`https://a.b/c` 这类 URL
    里的 `//` 不会被误当成注释（audit 场景宁可少剥，不可多剥）。
    字符串（'...' "..." `...`）与正则字面量内部一律不动 ——
    本仓库大量使用 `'/g'` 这类正则，不识别就会把后面的代码整段当字符串吞掉。
    """
    out = []
    i = 0
    n = len(src)
    quote = None
    while i < n:
        ch = src[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        # 非字符串状态
        if ch in "\"'`":
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = src[i + 1]
            if nxt == "*":
                end = src.find("*/", i + 2)
                if end == -1:
                    end = n
                else:
                    end += 2
                out.append("".join("\n" if c == "\n" else " " for c in src[i:end]))
                i = end
                continue
            if nxt == "/" and (i + 2 >= n or src[i + 2] != "/"):
                end = src.find("\n", i)
                if end == -1:
                    end = n
                out.append(" " * (end - i))
                i = end
                continue
            if looks_like_regex(src, i):
                end = skip_regex_literal(src, i)
                if end > i:
                    # 用空格遮蔽正则内容，但保留结束 '/' 与 flags，
                    # 避免在 `data.replace(/'/g, '"')` 里造出落单的引号。
                    masked = "".join("\n" if c == "\n" else " " for c in src[i : end - 1])
                    out.append(masked)
                    out.append("/")
                    i = end - 1
                    continue
        out.append(ch)
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def snippet_of(line: str, limit: int = 200) -> str:
    s = " ".join(line.strip().split())
    if len(s) > limit:
        s = s[: limit - 3] + "..."
    return s


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]*>", "", s)


def iter_string_literals(line: str):
    """产出 (literal_text_without_quotes, start_col) —— 作为「该行是渲染文本」的证据。"""
    for m in STRING_LITERAL_RE.finditer(line):
        raw = m.group(0)
        if len(raw) >= 2:
            yield raw[1:-1], m.start()


# --------------------------------------------------------------------------
# Finding
# --------------------------------------------------------------------------


class Finding:
    __slots__ = ("rule", "level", "site", "file", "line", "snippet")

    def __init__(self, rule: str, site: str, file: str, line: int, snippet: str):
        self.rule = rule
        self.level = RULES[rule][0]
        self.site = site
        self.file = file
        self.line = line
        self.snippet = snippet

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "level": self.level,
            "site": self.site,
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
        }


def make_finding(rule: str, site: str, rel: str, lineno: int, raw_line: str) -> Finding:
    return Finding(rule, site, rel, lineno, snippet_of(raw_line))


# --------------------------------------------------------------------------
# 规则实现
# --------------------------------------------------------------------------


def collect_unconditional_verdict_vars(code: str) -> set:
    """找出「被**无条件**赋成判定文字」的变量名。

    只认 `let x = '准';` 这种右值就是纯判定字符串的赋值；
    右值里带三元、模板串、函数调用的（`let x = cond ? '准' : '错'`、
    `var table = a ? b : c`）一律不收集，避免把普通变量名误判成判定变量。
    """
    names = set()
    for line in code.split("\n"):
        for m in UNCONDITIONAL_VERDICT_ASSIGN_RE.finditer(line):
            name, rhs = m.group(1), m.group(2)
            rhs = rhs.strip()
            if "?" in rhs or "`" in rhs or "(" in rhs:
                continue
            if len(rhs) == 3 and rhs[0] == rhs[2] and rhs[0] in "\"'":
                if rhs[1] in VERDICT_CHARS:
                    names.add(name)
    return names


def context_line(cleaned_lines, idx: int, radius: int = 4) -> str:
    lo = max(0, idx - radius)
    hi = min(len(cleaned_lines), idx + radius + 1)
    return "\n".join(cleaned_lines[lo:hi])


def context_before(cleaned_lines, idx: int, radius: int = 8) -> str:
    """只看**上文**的窗口。

    高亮的守卫条件（`if (...) {`）一定写在加黄底那一行之前，
    所以只看上文既能抓到守卫，又不会被文件后面某个无关的判定三元串到。
    """
    lo = max(0, idx - radius)
    return "\n".join(cleaned_lines[lo : idx + 1])


def has_verdict_condition(window: str) -> bool:
    """窗口里是否存在「用条件产出判定文字」的宽松证据（L1 行级判定、L5 兜底用）。

    证据：调用了统一判定工具（verdictText / verdictOf / isCorrect / isHit…），
    或窗口里出现了真正的三元运算符 `?`（排除 `??` / `?.`）。
    """
    if VERDICT_CONTEXT_RE.search(window):
        return True
    return "?" in re.sub(r"\?\?|\.\?", "", window)


def assigned_from_call(lines, idx: int, lookback: int = 3) -> set:
    """收集 idx 之前几行里 `x = f(...)` 得到的变量名 x。

    典型：`num = getZjNum(maValue[i], codeSplit); if (num) { ...加黄底... }`
          —— 判定由跨文件函数承担，看 `if (num)` 就知道是条件高亮。
    """
    names = set()
    lo = max(0, idx - lookback)
    for ln in lines[lo:idx]:
        for m in re.finditer(r"([A-Za-z_$][\w$]*)\s*=\s*[A-Za-z_$][\w$.]*\s*\(", ln):
            names.add(m.group(1))
    return names


def has_hit_guard(window: str, local_funcs=()) -> bool:
    """窗口里存在「命中才高亮」的守卫条件。

    典型：`if (sx && xiao[i].indexOf(sx) !== -1) { ...加黄底... }`
          `if (yuceArr[i] == kaijiangArr[k])` / `let hit = dsHit || zj;`
          `if ( matchFromEnd(str, sx) )` / `num = getZjNum(maValue[i], codeSplit); if (num) {`
          （封装过的命中判断函数 —— 本文件里定义过的函数被调用即算）

    这里刻意放宽：窗口里有 `if` / 三元，再加上「任意比较运算」「开奖值变量」或
    「本文件里定义过的判定函数被调用」，就认为高亮是条件产出的。
    放宽会漏掉真正写死的高亮，但漏报远好过把正确实现刷成一片假阳性。
    """
    if HIT_VAR_RE.search(window):
        return True
    if DRAWN_VAR_RE.search(window) and COMPARE_OP_RE.search(window):
        return True
    if re.search(r"\bif\s*\(", window) and COMPARE_OP_RE.search(window):
        return True
    if "?" in window and COMPARE_OP_RE.search(window):
        return True
    if re.search(r"\bif\s*\(", window):
        for fn in local_funcs:
            if re.search(r"\b%s\s*\(" % re.escape(fn), window):
                return True
    return False


def split_code_comment(src: str):
    """把一行切成 (代码部分, 注释部分)；没有注释时后半段为空。

    只认「// 后面不是 /」的行注释（和 strip_comments 一致），
    这样 `url: '/api/x'` 里的 `//` 不会被当成注释。
    """
    i = 0
    n = len(src)
    quote = None
    while i < n:
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            i += 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "/" and (i + 2 >= n or src[i + 2] != "/"):
            return src[:i], src[i:]
        i += 1
    return src, ""


def ternary_ranges(line: str):
    """返回该行里三元运算符的 `?..:` 区间，**能处理嵌套三元**。

    实现：遇 `?` 后取其「真分支」的结束位置（即与它同层的那个 `:`），
    真分支内部再递归。引号与括号内的 `?` `:` 一律忽略。
    例：`opened ? (zj ? '开:02准' : '开:02错') : '开:待开奖'`
        -> [(35, 39), (29, 47)]，于是两个样例号码都落在真/假分支里。
    """
    n = len(line)

    def skip_string(i):
        q = line[i]
        i += 1
        while i < n:
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == q:
                return i + 1
            i += 1
        return n

    def scan(i, depth, qdepth=None):
        """从 i 扫到本层结束，返回 (区间列表, 结束位置)。

        qdepth 为 None 表示「本层是一段自由文本，扫到行尾为止」；
        否则表示「本层是某个 `?` 的真分支，遇到同深度的 `:` 即结束」。
        """
        found = []
        while i < n:
            c = line[i]
            if c in "\"'`":
                i = skip_string(i)
                continue
            if c in "([{":
                depth += 1
                i += 1
                continue
            if c in ")]}":
                if qdepth is not None and depth <= qdepth:
                    return found, i
                depth -= 1
                i += 1
                continue
            if c == "?":
                qpos = i
                inner, j = scan(i + 1, depth, depth)
                found.extend(inner)
                if j < n and line[j] == ":":
                    found.append((qpos, j))
                    i = j + 1
                    continue
                return found, j
            if c == ":" and qdepth is not None and depth <= qdepth:
                return found, i
            i += 1
        return found, n

    spans, _ = scan(0, 0)
    return spans


def inside_ternary(line: str, pos: int, spans=None) -> bool:
    """位置 pos 是否落在三元运算符的 `? ... :` 区间内（用引号配平，避免括号干扰）。"""
    if spans is None:
        spans = ternary_ranges(line)
    for a, b in spans:
        if a < pos < b:
            return True
    return False


def pending_branch_present(x: str) -> bool:
    """该片段里是否存在「显式区分待开奖」的分支写法。

    形如 `opened ? '开:' + sx + code : '开:待开奖'` / `!opened ? '??' : '准'`。
    """
    return bool(
        re.search(r"[?:][^\"'`\n]{0,20}['\"`][^\"'`\n]{0,12}(?:\?\?|\uff1f00|待开奖)", x)
        or re.search(r"[?:][^\"'`\n]{0,20}['\"`]\s*(?:\?\?|\uff1f00|待开奖)", x)
        or re.search(r"['\"`][^\"'`\n]{0,12}(?:待开奖|\?\?)[^\"'`\n]{0,12}['\"`]\s*:", x)
    )


def pending_is_fallback(line: str, start: int, spans=None) -> bool:
    """占位符是不是「空值兜底」写法：`|| "待开奖"` / `?? '??'`。

    这种写法的语义是「取不到值时兜底」，而不是「未开奖也显示判定」。
    """
    before = line[:start]
    return bool(re.search(r"(\|\||\?\?)\s*['\"`]?\s*$", before))


def pending_is_discriminated(line: str, spans=None) -> bool:
    """该行里所有待开奖占位符，是否都已经被条件区分（落在三元分支或兜底表达式里）。"""
    ms = list(PENDING_RE.finditer(line))
    if not ms:
        return False
    return all(
        inside_ternary(line, m.start(), spans) or pending_is_fallback(line, m.start())
        for m in ms
    )


def template_interp_spans(text: str):
    """返回文本里所有 `${ ... }` 插值区间的 (start, end)，能正确处理嵌套 `{}` 与字符串。

    行级与窗口级共用：窗口就是多行拼起来的字符串，所以按纯文本扫描即可。
    """
    spans = []
    i = 0
    n = len(text)
    while i < n:
        j = text.find("${", i)
        if j == -1:
            break
        k = j + 2
        depth = 1
        quote = None
        while k < n and depth > 0:
            c = text[k]
            if quote:
                if c == "\\":
                    k += 2
                    continue
                if c == quote:
                    quote = None
            elif c in "\"'`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            k += 1
        spans.append((j, k))
        i = k
    return spans


def make_verdict_verifier(window: str):
    """生成判定函数：给定判定文字在**窗口文本**里的位置，返回 True 表示「条件产出，放行」。

    判定逻辑：
      1) 判定文字在字面量里（不在任何 `${...}` 插值里）-> 写死，报告；
      2) 在插值里，且该插值自己带三元 -> 条件产出，放行；
      3) 在插值里，整行/窗口别处有真三元（多数是 `opened ? ... : '开:待开奖'`）-> 放行；
      4) 在插值里，且窗口里调用了统一判定工具（verdictText / verdictOf / isCorrect…）-> 放行；
      5) 其余（例如 `开:${sx}${code}准`，插值里没条件、窗口也没条件）-> 报告。
    """
    interps = template_interp_spans(window)
    has_ternary = "?" in re.sub(r"\?\?|\.\?", "", window)
    has_tool = bool(VERDICT_CONTEXT_RE.search(window))

    def verify(pos: int) -> bool:
        inside = next((k for k, (a, b) in enumerate(interps) if a <= pos < b), None)
        if inside is None:
            return False
        a, b = interps[inside]
        seg = re.sub(r"\?\?|\.\?", "", window[a:b])
        return ("?" in seg) or has_ternary or has_tool

    return verify


def line_is_markup(line: str) -> bool:
    return "<" in line and ">" in line


def check_file(rel_path: str, abs_path: str, site: str):
    """对单个文件跑全部规则，返回 Finding 列表。"""
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError:
        return []

    code = strip_comments(raw)
    raw_lines = raw.split("\n")
    lines = code.split("\n")
    findings = []

    verdict_vars = collect_unconditional_verdict_vars(code)
    local_funcs = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", code))

    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        raw_line = raw_lines[idx] if idx < len(raw_lines) else line
        lineno = idx + 1
        window = context_line(lines, idx, radius=3)
        before_window = context_before(lines, idx, radius=8)
        line_code, line_comment = split_code_comment(line)
        tern = ternary_ranges(line_code)

        # ---------------- L1 hardcoded_verdict ----------------
        # 判定文字「写死」的定义：它在字面量里（不在任何 `${...}` 插值里），
        # 并且整行没有任何真三元、附近也没有统一判定工具。
        #   `<td>${d.term}期本期买 开:${sx}${code}准</td>`  -> 写死（准 在模板字面量里）
        #   `<td>开:${sx?(zj?'准':'错'):'??'}</td>`         -> 正常（准 在插值的三元里）
        #   `let verdictTxt = ... ? '准' : '错';` 之后用 ${verdictTxt} -> 正常
        verify_verdict = make_verdict_verifier(window)
        # 「紧邻的上一个非空行是含三元/判定的赋值，本行只是插值它的结果」也算条件产出：
        #   let resTxt = opened ? (`开:...准`) : '开:待开奖';   <- 上一个非空行
        #   resTxt = resTxt;                                   <- 本行
        # 只跨过空行，不跨过别的语句 —— 否则文件后半段的无关三元会把写死判定洗白。
        prev_code = ""
        for back in range(idx - 1, max(-1, idx - 6), -1):
            if lines[back].strip():
                prev_code = lines[back]
                break
        prev_has_verdict_assign = bool(
            has_verdict_condition(prev_code) or VERDICT_CONTEXT_RE.search(prev_code)
        )
        # 本行/上一行存在「条件产出判定」的结构就放行：
        #   `x === 'ok' ? '准' : '错'`（三元）
        #   `if (verdict === 'ok') return '准';`（if + 比较）
        line_has_ternary = "?" in re.sub(r"\?\?|\.\?", "", line)
        verdict_guarded = (
            line_has_ternary
            or (
                CONDITIONAL_RE.search(line)
                and COMPARE_OP_RE.search(line)
                and any(c in line for c in VERDICT_CHARS)
            )
            or prev_has_verdict_assign
            or (VERDICT_CONTEXT_RE.search(line))
        )
        hit = False
        if not verdict_guarded:
            for lit, lstart in iter_string_literals(line):
                # 注意：位置必须直接取自**原始字面量**，不能先 strip_tags ——
                # 去标签会改变下标，导致 `${...}` 位置判断全部错位。
                for m in VERDICT_TOKEN_RE.finditer(lit):
                    if not VERDICT_TOKEN_RE.search(strip_tags(m.group(0))):
                        continue
                    if verify_verdict(lstart + 1 + m.start(1)):
                        continue
                    hit = True
                    break
                if hit:
                    break
            # 模板里插值了「被无条件赋成判定文字」的变量：
            #   let zz = content[i] + '准';  ...  ${zz}   -> 写死
            if not hit:
                for name in verdict_vars:
                    pos = line.find(name)
                    if pos != -1 and not verify_verdict(pos):
                        hit = True
                        break
        if hit:
            findings.append(make_finding("L1 hardcoded_verdict", site, rel_path, lineno, raw_line))

        # ---------------- L2 unsafe_json_parse ----------------
        if JSON_PARSE_RE.search(line) and not SAFE_PARSE_RE.search(line):
            findings.append(make_finding("L2 unsafe_json_parse", site, rel_path, lineno, raw_line))

        # ---------------- L3 raw_content_split ----------------
        l3 = False
        # 信号 A：对原始 content 串按逗号切 —— "兔|04,马|..." 会切成 ["兔|04, ... 原始 JSON
        if RAW_COMMA_SPLIT_RE.search(line):
            l3 = True
        # 信号 B：按 | 切 content 片段，而且同一行就把结果拼进标签模板/字符串
        elif PIPE_SPLIT_RE.search(line) and TEMPLATE_INTERP_RE.search(line):
            l3 = True
        if l3:
            findings.append(make_finding("L3 raw_content_split", site, rel_path, lineno, raw_line))

        # ---------------- L4 static_sample_result ----------------
        # 只在**代码部分**匹配，并且只有当「写死样例」不是三元分支的产物时才报：
        #   `opened ? (zj ? '开:02准' : '开:02错') : '开:待开奖'`  —— 三元分支，放行
        #   `html += '<td>开:蛇12准</td>'`                        —— 写死，报告
        l4_hit = False
        for m in L4_ZODIAC_NUM_RE.finditer(line_code):
            if not inside_ternary(line_code, m.start(), tern):
                l4_hit = True
                break
        if not l4_hit:
            for m in L4_CAT_NUM_RE.finditer(line_code):
                if not inside_ternary(line_code, m.start(), tern):
                    l4_hit = True
                    break
        if not l4_hit:
            # 开:00 / 開：12 —— 固定样例号码：必须在**字符串字面量内部**
            # （排除 开:${x} 之类动态写法，也避免跨引号误伤）
            for lit, lstart in iter_string_literals(line_code):
                for m in L4_NUM_ONLY_RE.finditer(lit):
                    if not inside_ternary(line_code, lstart + 1 + m.start(), tern):
                        l4_hit = True
                        break
        if l4_hit:
            findings.append(make_finding("L4 static_sample_result", site, rel_path, lineno, raw_line))

        # ---------------- L5 unconditional_highlight ----------------
        if (
            HIGHLIGHT_RE.search(line)
            and HIGHLIGHT_CONTEXT_RE.search(line)
            and line_is_markup(line)
        ):
            # 注释里的 #FFFF00（例如「// 旧写法 background-color:#FFFF00 会导致…」）不算
            comment_mentions_only = bool(line_comment) and not HIGHLIGHT_RE.search(line_code)
            if not comment_mentions_only:
                guarded = has_hit_guard(before_window, local_funcs) or has_verdict_condition(
                    before_window
                )
                if not guarded:
                    # 本文件里定义过的判定/取数函数被调用（如
                    # `num = getZjNum(maValue[i], codeSplit); if (num) {`），
                    # 视为命中条件已由该函数承担。
                    for fn in local_funcs:
                        if re.search(r"\b%s\s*\(" % re.escape(fn), before_window):
                            guarded = True
                            break
                if not guarded:
                    # 跨文件函数（如 util.js 的 getZjNum）赋值后再用 if 判空/判真
                    call_vars = assigned_from_call(lines, idx)
                    guarded = bool(call_vars) and any(
                        re.search(r"\bif\s*\([^)]*\b%s\b" % re.escape(v), before_window)
                        for v in call_vars
                    )
                if not guarded:
                    findings.append(
                        make_finding("L5 unconditional_highlight", site, rel_path, lineno, raw_line)
                    )

        # ---------------- L6 pending_with_verdict ----------------
        if PENDING_RE.search(line_code) and any(c in line_code for c in VERDICT_CHARS):
            # 只有「显式区分待开奖」才算已处理：
            #   opened ? '开:' + sx + code : '开:待开奖'            -> 正确（行内分支）
            #   "开:" + (code ? ... : String(text || "待开奖")) + (correct ? "对" : "错")
            #                                                      -> 正确（占位符本身在三元里）
            #   '开:？00准' / '开:??准' / return "？00准"            -> 缺陷（未开奖也给判定）
            pending_spans = [m.span() for m in PENDING_RE.finditer(line_code)]
            decided = (
                pending_branch_present(line_code)
                or pending_branch_present(context_before(lines, idx, radius=1))
                or pending_is_discriminated(line_code, tern)
            )
            if not decided:
                findings.append(
                    make_finding("L6 pending_with_verdict", site, rel_path, lineno, raw_line)
                )

    return findings


# --------------------------------------------------------------------------
# 文件发现
# --------------------------------------------------------------------------


def is_skipped(filename: str) -> bool:
    if BUNDLE_HASH_RE.match(filename):
        return True
    if VENDOR_HASH_RE.match(filename):
        return True
    if GENERIC_HASH_RE.match(filename):
        return True
    for rx in SKIP_FILE_REGEXES:
        if rx.match(filename):
            return True
    return False


def iter_js_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for name in sorted(filenames):
            if not name.lower().endswith(".js"):
                continue
            if is_skipped(name):
                continue
            yield os.path.join(dirpath, name)


def resolve_targets(args, repo_root: str):
    """返回 (targets, errors)；targets 为 [(site_label, dir_path)]。"""
    errors = []
    targets = []

    if args.dir:
        for d in args.dir:
            path = d if os.path.isabs(d) else os.path.join(os.getcwd(), d)
            if not os.path.isdir(path):
                errors.append("--dir 不存在或不是目录：%s" % d)
                continue
            targets.append((os.path.basename(os.path.normpath(path)), path))
        return targets, errors

    vendor_root = os.path.join(repo_root, "frontend", "public", "vendor")
    if not os.path.isdir(vendor_root):
        errors.append("找不到 vendor 根目录：%s" % vendor_root)
        return targets, errors

    if not args.sites:
        for name in sorted(os.listdir(vendor_root)):
            path = os.path.join(vendor_root, name)
            if os.path.isdir(path):
                targets.append((name, path))
        return targets, errors

    available = {}
    for name in sorted(os.listdir(vendor_root)):
        if os.path.isdir(os.path.join(vendor_root, name)):
            available[name] = os.path.join(vendor_root, name)

    for wanted in args.sites:
        if wanted in available:
            targets.append((wanted, available[wanted]))
            continue
        # 容错：twcaibawang -> twcaibawang.com
        cands = [k for k in available if k.split(".")[0] == wanted]
        if len(cands) == 1:
            targets.append((cands[0], available[cands[0]]))
            continue
        errors.append(
            "站点不存在：%s（可用：%s）" % (wanted, ", ".join(sorted(available)))
        )
    return targets, errors


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------


def print_findings(findings, show_all: bool):
    by_site = OrderedDict()
    for f in findings:
        by_site.setdefault(f.site, []).append(f)
    for site, items in by_site.items():
        print("\n=== %s (%d) ===" % (site, len(items)))
        for f in items:
            print(
                "%-9s %-5s %s:%d\n    %s"
                % (f.rule.split()[0], f.level, f.file, f.line, f.snippet)
            )


def print_summary(findings):
    total = len(findings)
    err = sum(1 for f in findings if f.level == "error")
    warn = total - err
    print("\n" + "=" * 72)
    print("统计：%d 条 finding（error=%d, warn=%d）" % (total, err, warn))

    rule_counter = Counter(f.rule for f in findings)
    print("\n按规则：")
    for rid in RULE_IDS:
        lvl = RULES[rid][0]
        print("  %-34s %-5s %d" % (rid, lvl, rule_counter.get(rid, 0)))

    site_counter = Counter(f.site for f in findings)
    site_err = Counter(f.site for f in findings if f.level == "error")
    site_warn = Counter(f.site for f in findings if f.level == "warn")
    if site_counter:
        print("\n按站点：")
        for site in sorted(site_counter):
            print(
                "  %-22s total=%-5d error=%-5d warn=%-5d"
                % (site, site_counter[site], site_err[site], site_warn[site])
            )
    return total, err, warn


def print_rule_help():
    print("规则清单：")
    for rid, (lvl, desc) in RULES.items():
        print("  %-34s %-5s %s" % (rid, lvl, desc))
    print("\n排除的文件（第三方/打包/压缩产物）：")
    print("  " + ", ".join(SKIP_FILE_GLOBS))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def build_arg_parser():
    p = argparse.ArgumentParser(
        prog="lint-prediction-renderers.py",
        description=(
            "源码级静态 lint：给新站点接入预测模块时，提前发现「判定/高亮/静态样例」类缺陷"
            "（恒显示准/错、未命中黄底、页面出现 [\" 原始 JSON、写死的开奖样例）。"
        ),
        epilog=(
            "示例：\n"
            "  python scripts\\lint-prediction-renderers.py\n"
            "  python scripts\\lint-prediction-renderers.py twsaimahui\n"
            "  python scripts\\lint-prediction-renderers.py --dir frontend/public/vendor/twssz --json out.json\n"
            "  python scripts\\lint-prediction-renderers.py --strict\n"
            "\n"
            "退出码：0=扫描完成；1=--strict 且存在 finding；2=参数错误。\n"
            "规则：L1 hardcoded_verdict / L2 unsafe_json_parse / L3 raw_content_split /\n"
            "      L4 static_sample_result / L5 unconditional_highlight / L6 pending_with_verdict。\n"
            "规范见 docs/prediction-display-standard.md（S1–S8）。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "sites",
        nargs="*",
        help="站点目录名（如 twsaimahui）；留空＝扫描 frontend/public/vendor/ 下所有站点",
    )
    p.add_argument(
        "--dir",
        action="append",
        default=[],
        metavar="PATH",
        help="直接指定要扫描的目录（可重复；指定后忽略位置参数 sites）",
    )
    p.add_argument("--json", metavar="PATH", help="把完整结果写入 JSON 文件")
    p.add_argument(
        "--strict",
        action="store_true",
        help="存在任何 finding（含 warn）时退出码为 1；默认退出码始终为 0",
    )
    p.add_argument(
        "--max-per-file",
        type=int,
        default=0,
        metavar="N",
        help="每个文件最多打印 N 条（0=不限）；JSON 始终输出全量",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="只输出统计，不逐条打印 finding",
    )
    p.add_argument("--list-rules", action="store_true", help="打印规则清单与排除列表后退出")
    return p


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        print_rule_help()
        return 0

    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)

    targets, errors = resolve_targets(args, repo_root)
    if errors:
        for e in errors:
            print("错误：%s" % e, file=sys.stderr)
        return 2
    if not targets:
        print("错误：没有找到任何可扫描的目录", file=sys.stderr)
        return 2

    print("仓库根目录：%s" % repo_root)
    print("扫描目标：%s" % ", ".join(s for s, _ in targets))
    print(
        "排除规则：%s" % ", ".join(SKIP_FILE_GLOBS)
    )

    findings = []
    scanned = 0
    for site, path in targets:
        for abs_path in iter_js_files(path):
            rel = os.path.relpath(abs_path, repo_root).replace("\\", "/")
            scanned += 1
            findings.extend(check_file(rel, abs_path, site))

    findings.sort(key=lambda f: (f.site, f.file, f.line, f.rule))

    if not args.quiet:
        shown = findings
        if args.max_per_file > 0:
            shown = []
            per_file = Counter()
            for f in findings:
                key = (f.site, f.file)
                if per_file[key] < args.max_per_file:
                    shown.append(f)
                    per_file[key] += 1
        print_findings(shown, args.max_per_file == 0)

    total, err, warn = print_summary(findings)
    print("\n扫描文件数：%d" % scanned)

    if args.json:
        out = {
            "tool": "lint-prediction-renderers",
            "repo_root": repo_root,
            "targets": [s for s, _ in targets],
            "scanned_files": scanned,
            "skip_globs": list(SKIP_FILE_GLOBS),
            "rules": {k: {"level": v[0], "description": v[1]} for k, v in RULES.items()},
            "totals": {"total": total, "error": err, "warn": warn},
            "findings": [f.as_dict() for f in findings],
        }
        out_path = args.json if os.path.isabs(args.json) else os.path.join(os.getcwd(), args.json)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("JSON 已写入：%s" % out_path)

    if args.strict and findings:
        print("\n--strict：存在 %d 条 finding，退出码 1" % total)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
