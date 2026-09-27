#!/usr/bin/env python
"""预测判定真值校验：复算每一行「候选项是否命中真实开奖」，与行内 is_correct 比对。

背景
----
站点页面每行显示的「准 / 错」最终来自后端对预测行的判定字段 ``is_correct``：
``backend/src/public/api.py::serialize_public_history_row`` 会按每个玩法机制的
``content_loader / content_parser / hit_checker`` 从行数据复算 ``is_correct``；
``backend/src/vendor/homepage_modules.py`` 里的 vendor 聚合模块则各自复算。
本脚本**不信任**这些实现与前端契约，而是用一份独立的真值口径重新判定：

    真值命中 = 该玩法语义下，预测行的候选项集合命中真实开奖
      · contains 玩法（中特/杀号以外的多数）：真实特码 ∈ 候选号码，
        或真实特肖 ∈ 候选生肖
      · excludes 玩法（绝杀/不中/输尽光类）：真实特码 ∉ 候选号码，
        或真实特肖 ∉ 候选生肖
      · 平特肖（flat_zodiac）：开奖 7 个号码的生肖集合 ∩ 候选生肖 ≠ ∅
      · 平特尾（flat_tail）：开奖 7 个号码的尾数集合 ∩ 候选尾数 ≠ ∅

比对对象是**行内/接口里的 is_correct 值**（本仓库不把该值落库，而是读时复算，
因此脚本通过 ``serialize_public_history_row`` 取「站点当前会展示的 is_correct」，
对 vendor 聚合行则取 ``build_vendor_homepage_modules`` 的 ``is_correct``）。

判定结果
--------
``error``  is_correct=1 但候选项未命中（虚报命中）
           或 is_correct=0 但候选项确实命中（漏报命中）
``warn``   无法判定：行内没有开奖号码且 lottery_draws 里也查不到该期开奖、
           或内容不可解析出任何候选项
``info``   该行没有可供比对的 is_correct（例如脚本无法构造机制配置）

用法
----
    # 全站（web_id 4-13）
    python scripts/audit-verdict-truth.py --json .codex-temp/verdict-truth.json

    # 单站点（key 或 --web-id 都支持）
    python scripts/audit-verdict-truth.py twjsz666
    python scripts/audit-verdict-truth.py --web-id 6 --web-id 11

    # 只看全量行（默认每个模式每站点只取最近 N 期）
    python scripts/audit-verdict-truth.py --limit 200

退出码：0 = 无 error；1 = 存在 error。

数据库连接：按 ``DATABASE_URL`` 环境变量；未设置时使用
``postgresql://postgres:2225427@127.0.0.1:5432/liuhecai``（本地开发默认）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "backend" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# 必须在 import db / predict 之前设置，predict.common 在 import 时读取默认 DSN。
DEFAULT_DSN = "postgresql://postgres:2225427@127.0.0.1:5432/liuhecai"
os.environ.setdefault("DATABASE_URL", DEFAULT_DSN)

SITES: dict[int, str] = {
    4: "shengshi8800",
    5: "twcaibawang",
    6: "twsaimahui",
    7: "twjinniu",
    8: "twcf888",
    9: "twssz",
    10: "twbst528",
    11: "twjsz666",
    12: "twwanli",
    13: "twsyw",
}

#: vendor 聚合模块 → 主要来源 mode_id（用于取机制语义）
VENDOR_MODULE_MODE_IDS: dict[str, int] = {
    "wuxiao_wuma": 47,
    "public_yixiao_yima": 151,
    "shuangbo_12ma": 38,
    "shujinguang": 44,
    "daxiao_2tou": 57,
    "tiandi_2xiao": 5,
    "dujia_gongshi": 28,
    "tw_pmt_image": 478,
}

ZODIAC_CHARS = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
SEPARATORS = ",，、|/\\ \t[]\"'·.-—+"
_ZODIAC_ALIASES = {"龍": "龙", "馬": "马", "雞": "鸡", "豬": "猪"}


@dataclass
class Finding:
    level: str
    site: str
    web_id: int
    schema: str
    mode_id: int | None
    mechanism_key: str
    term: str
    year: str
    rule: str
    detail: str
    content: str = ""
    res_code: str = ""
    res_sx: str = ""
    is_correct: bool | None = None
    truth: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "site": self.site,
            "web_id": self.web_id,
            "schema": self.schema,
            "mode_id": self.mode_id,
            "mechanism_key": self.mechanism_key,
            "year": self.year,
            "term": self.term,
            "rule": self.rule,
            "detail": self.detail,
            "content": self.content[:400],
            "res_code": self.res_code,
            "res_sx": self.res_sx,
            "is_correct": self.is_correct,
            "truth": self.truth,
        }


@dataclass
class SiteReport:
    site: str
    web_id: int
    rows: int = 0
    errors: int = 0
    warns: int = 0
    infos: int = 0
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "web_id": self.web_id,
            "rows": self.rows,
            "error": self.errors,
            "warn": self.warns,
            "info": self.infos,
            "findings": [item.as_dict() for item in self.findings],
        }


# ── 文本 → 候选项 ────────────────────────────────────────────────


def _iter_scalars(value: Any) -> list[str]:
    """把任意 JSON 结构摊平成字符串列表。"""
    out: list[str] = []
    if value is None:
        return out
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        if text:
            out.append(text)
        return out
    if isinstance(value, dict):
        for nested in value.values():
            out.extend(_iter_scalars(nested))
        return out
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            out.extend(_iter_scalars(nested))
        return out
    return out


def _split_candidates(blob: str) -> list[str]:
    """把一段内容拆成候选项字符串（`标签|号码,号码` 同时保留标签与号码）。"""
    text = str(blob or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, (list, dict)):
        return _iter_scalars(parsed)

    stripped = text.strip("[]\"'")
    parts: list[str] = []
    for chunk in stripped.replace("|", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    if len(parts) <= 1 and not parts:
        for chunk in stripped.replace("|", " ").split():
            if chunk.strip():
                parts.append(chunk.strip())
    return parts or [stripped]


def candidate_numbers(blobs: list[str]) -> set[str]:
    """候选项里的号码集合（两位数字串）。"""
    out: set[str] = set()
    for blob in blobs:
        for part in _split_candidates(blob):
            digits = "".join(ch for ch in part if ch.isdigit())
            if digits and len(digits) <= 2:
                out.add(digits.zfill(2))
    return out


def candidate_zodiacs(blobs: list[str]) -> set[str]:
    """候选项里的生肖集合。"""
    out: set[str] = set()
    for blob in blobs:
        for part in _split_candidates(blob):
            for ch in part:
                if ch in ZODIAC_CHARS:
                    out.add(ch)
    return out


def candidate_tails(blobs: list[str]) -> set[str]:
    """候选项里的尾数集合（`3尾` / `03,13,23,33,43` 都能解析）。"""
    out: set[str] = set()
    for blob in blobs:
        for part in _split_candidates(blob):
            match = __import__("re").search(r"(\d)\s*尾", part)
            if match:
                out.add(match.group(1))
                continue
            digits = "".join(ch for ch in part if ch.isdigit())
            if len(digits) == 1:
                out.add(digits)
            elif len(digits) == 2:
                out.add(str(int(digits) % 10))
    return out


def split_codes(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    out: list[str] = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            out.append(chunk.zfill(2))
    return out


def split_zodiacs(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [_ZODIAC_ALIASES.get(item.strip(), item.strip()) for item in text.split(",") if item.strip()]


# ── 真值判定 ─────────────────────────────────────────────────────


#: 玩法标签「取值空间」——决定候选项与真实开奖目标怎么归一化后比较。
#: 与后端 ``PredictionConfig.content_parser`` 一一对应，避免把「6尾」当成号码 06。
LABEL_SPACE_TAIL = "tail"        # 尾数：1尾 / 1
LABEL_SPACE_NUMBER = "number"    # 号码：01-49
LABEL_SPACE_ZODIAC = "zodiac"    # 生肖：鼠…猪
LABEL_SPACE_WAVE = "wave"        # 波色：红波/蓝波/绿波
LABEL_SPACE_HALF_WAVE = "half_wave"  # 半波：红双/蓝单…
LABEL_SPACE_HEAD = "head"        # 头数：0头…4头
LABEL_SPACE_SEGMENT = "segment"  # 段位：1段…7段
LABEL_SPACE_PARITY = "parity"    # 单双
LABEL_SPACE_SIZE = "size"        # 大小
LABEL_SPACE_ELEMENT = "element"  # 五行
LABEL_SPACE_RAW = "raw"          # 无法归类：直接用原始标签

_PARSER_LABEL_SPACE: dict[str, str] = {
    "parse_tail_digit_content": LABEL_SPACE_TAIL,
    "parse_number_content": LABEL_SPACE_NUMBER,
    "parse_zodiac_content": LABEL_SPACE_ZODIAC,
    "parse_zodiac_chars": LABEL_SPACE_ZODIAC,
    "parse_wave_chars": LABEL_SPACE_WAVE,
    "parse_half_wave_chars": LABEL_SPACE_HALF_WAVE,
    "parse_head_content": LABEL_SPACE_HEAD,
    "parse_segment_content": LABEL_SPACE_SEGMENT,
    "parse_parity_content": LABEL_SPACE_PARITY,
    "parse_size_content": LABEL_SPACE_SIZE,
    "parse_element_content": LABEL_SPACE_ELEMENT,
}

#: 用 `标签|号码` 分组表达的玩法（单双 / 大小 / 头数 / 尾数 / 波色 …），
#: 标签空间无法只靠 content_parser 名判断，额外按机制 key 兜底。
_MECHANISM_LABEL_SPACE: dict[str, str] = {
    "danshuangtema": LABEL_SPACE_PARITY,
    "daxiao": LABEL_SPACE_SIZE,
    "size_parity_mode": LABEL_SPACE_SIZE,
    "dxztt1": LABEL_SPACE_SIZE,
    "shuangbo": LABEL_SPACE_WAVE,
    "shaliangbanbo": LABEL_SPACE_HALF_WAVE,
    "jueshabanbo": LABEL_SPACE_HALF_WAVE,
    "3tou": LABEL_SPACE_HEAD,
    "4tou": LABEL_SPACE_HEAD,
    "sitouzhongte": LABEL_SPACE_HEAD,
    "liangtouzxt": LABEL_SPACE_HEAD,
    "three_head_four_tail": LABEL_SPACE_HEAD,
    "gongshi_siw": LABEL_SPACE_TAIL,
    "siduanzhongte": LABEL_SPACE_SEGMENT,
    "sihangzhongte": LABEL_SPACE_ELEMENT,
}

#: 五行分组（与 ``public/api.py::_ELEMENT_BY_GROUP`` 一致）；用于交叉核对元素候选。
ELEMENT_BY_GROUP: dict[str, tuple[str, ...]] = {
    "金": ("10", "11", "22", "23", "34", "35", "46", "47"),
    "木": ("04", "05", "16", "17", "28", "29", "40", "41"),
    "水": ("07", "08", "19", "20", "31", "32", "43", "44"),
    "火": ("01", "02", "13", "14", "25", "26", "37", "38"),
    "土": ("03", "06", "09", "12", "15", "18", "21", "24", "27", "30", "33", "36", "39", "42", "45", "48"),
}

#: vendor 聚合模块的真实判定规则（不能直接借用来源 mode_id 的机制语义）。
#: `public_yixiao_yima` 的 is_correct 只比对筛选出的「推荐一肖一码」，
#: 而展示的候选池是 9 肖 / 14 码集合，两者口径不一致 → undecidable。
VENDOR_RULES: dict[str, str] = {
    "wuxiao_wuma": "contains_code_or_zodiac",
    "public_yixiao_yima": "undecidable",
    "shuangbo_12ma": "contains_code_or_zodiac",
    "shujinguang": "exclude_zodiac",
    "daxiao_2tou": "size_or_tou",
    "tiandi_2xiao": "contains_zodiac",
    "dujia_gongshi": "per_dimension",
    "tw_pmt_image": "undecidable",
}


@dataclass
class Mechanism:
    key: str
    mode_id: int
    title: str
    parser_name: str
    checker_name: str
    exclude: bool
    flat_zodiac: bool
    flat_tail: bool
    label_space: str


def is_exclude_mechanism(title: str, key: str) -> bool:
    haystack = f"{title} {key}"
    return any(word in haystack for word in ("杀", "绝杀", "不中", "输尽", "排除"))


def mechanism_blobs(loader_text: str, row: dict[str, Any], prediction_text: str) -> list[str]:
    """构造候选项文本来源：机制 content_loader → prediction_text → 行内可见字段。"""
    blobs: list[str] = []
    if loader_text:
        blobs.append(loader_text)
    if prediction_text and prediction_text not in blobs:
        blobs.append(prediction_text)
    for key in ("content", "title", "xiao", "code", "picks", "code_15", "jiexi", "ds", "dx"):
        value = row.get(key)
        if value:
            text = str(value).strip()
            if text and text not in blobs:
                blobs.append(text)
    for key in ("xiao_1", "xiao_2", "nan", "nv", "zu1", "zu2", "zu3", "wei", "bo", "banbo"):
        value = row.get(key)
        if value:
            text = str(value).strip()
            if text and text not in blobs:
                blobs.append(text)
    return blobs


def parse_content_labels(content: str, label_space: str) -> list[str]:
    """按共同口径解析候选项标签（优先复用后端机制自己的 content_parser）。"""
    text = str(content or "").strip()
    if not text:
        return []
    try:
        from predict.common import parse_json_or_plain_content
        from predict.mechanisms import parse_number_content, parse_pipe_label_content, parse_zodiac_content
        from predict.categories.content_columns import parse_tail_digit_content, parse_zodiac_chars

        if label_space == LABEL_SPACE_TAIL:
            return list(parse_tail_digit_content(text))
        if label_space == LABEL_SPACE_NUMBER:
            return list(parse_number_content(text))
        if label_space == LABEL_SPACE_ZODIAC:
            values = list(parse_zodiac_content(text))
            return values or list(parse_zodiac_chars(text))
        items = list(parse_json_or_plain_content(text))
        return [item.split("|", 1)[0].strip() if "|" in item else item.strip() for item in items]
    except Exception:
        return []


def truth_label(
    *,
    mechanism: Mechanism,
    config: Any,
    row: dict[str, Any],
    special_code: str,
    all_codes: list[str],
    special_zodiac: str,
    all_zodiacs: list[str],
    label_space: str,
) -> tuple[str, set[str]] | None:
    """返回 (真实开奖标签, 可接受标签集合)。

    绝杀/平特这类玩法可能有多个可接受标签（平特尾要看开奖 7 个号码的尾数），
    因此返回集合而不是单值。标签口径必须与 ``content_parser`` 的输出一致：
    例如「公式四尾」的标签是 ``6尾`` 而不是号码 ``06``。
    """
    if mechanism.flat_tail:
        tails = {f"{int(code) % 10}尾" for code in (all_codes or [special_code]) if code.isdigit()}
        return ("", tails) if tails else None
    if mechanism.flat_zodiac:
        pool = set(all_zodiacs or ([special_zodiac] if special_zodiac else []))
        return ("", pool) if pool else None
    if not special_code:
        return None

    # 首选机制自己的 outcome_loader：它才是该玩法真实命中目标的权威口径。
    loader = getattr(config, "outcome_loader", None) if config is not None else None
    if loader is not None:
        try:
            value = str(loader(row, _FIXED_CONN_HOLDER.get("conn")) or "").strip()
            if value:
                return (value, {value})
        except Exception:
            pass

    if label_space == LABEL_SPACE_NUMBER:
        label = f"{int(special_code):02d}"
    elif label_space == LABEL_SPACE_TAIL:
        label = f"{int(special_code) % 10}尾"
    elif label_space == LABEL_SPACE_ZODIAC:
        if not special_zodiac:
            return None
        label = special_zodiac
    elif special_zodiac:
        label = special_zodiac
    else:
        label = special_code
    return (label, {label})


def judge_vendor_row(
    *,
    module_key: str,
    row: dict[str, Any],
    special_code: str,
    special_zodiac: str,
) -> bool | None:
    """按 vendor 聚合模块各自的展示口径独立复算命中真值。"""
    rule = VENDOR_RULES.get(module_key, "undecidable")
    if rule == "undecidable" or not special_code:
        return None

    if rule == "contains_code_or_zodiac":
        zod, codes = _vendor_token_sets(row)
        if not zod and not codes:
            return None
        return special_code in codes or (bool(special_zodiac) and special_zodiac in zod)

    if rule == "contains_zodiac":
        zod, _codes = _vendor_token_sets(row)
        if not zod:
            return None
        return bool(special_zodiac) and special_zodiac in zod

    if rule == "exclude_zodiac":
        zod, _codes = _vendor_token_sets(row)
        if not zod:
            return None
        return not (bool(special_zodiac) and special_zodiac in zod)

    if rule == "size_or_tou":
        # 「大小+2头」：号码够大 / 够小 或 两位号码以预测头数开头，任一成立即命中。
        label = str(row.get("daxiao") or "").strip()
        tou = str(row.get("tou_code") or "").strip()
        number = int(special_code)
        size_ok = (label == "大" and number >= 25) or (label == "小" and number <= 24)
        tou_ok = bool(tou) and special_code.zfill(2).startswith(tou)
        if not label and not tou:
            return None
        return size_ok or tou_ok

    if rule == "per_dimension":
        # 「独家公式」：单双 / 大小 / 尾数 三个维度分别判定，任一维度命中即算命中。
        formula = row.get("formula")
        if not isinstance(formula, dict):
            return None
        number = int(special_code)
        hits: list[bool] = []
        for name, part in formula.items():
            if not isinstance(part, dict):
                continue
            labels = {str(item).strip() for item in (part.get("labels") or []) if str(item).strip()}
            if not labels:
                continue
            if name == "parity":
                hits.append(("双" if number % 2 == 0 else "单") in labels)
            elif name == "size":
                hits.append(("大" if number >= 25 else "小") in labels)
            else:
                hits.append(str(number % 10) in labels)
        return any(hits) if hits else None

    return None


def _vendor_token_sets(row: dict[str, Any]) -> tuple[set[str], set[str]]:
    """vendor 行 → (生肖集合, 号码集合)。"""
    zodiacs: set[str] = set()
    codes: set[str] = set()
    blobs: list[str] = []
    for name in ("groups", "code_groups", "xiao_groups"):
        group = row.get(name)
        if isinstance(group, dict):
            for value in group.values():
                blobs.extend(_iter_scalars(value))
    for name in ("picks", "xiao_pair", "xiao", "tiandi"):
        value = row.get(name)
        if value:
            blobs.extend(_iter_scalars(value))
    for name in ("code",):
        value = row.get(name)
        if value:
            blobs.extend(_iter_scalars(value))
    best = row.get("best_pick")
    if isinstance(best, dict):
        blobs.extend(_iter_scalars(best))

    for blob in blobs:
        for part in _split_candidates(str(blob)):
            part = part.strip()
            if not part:
                continue
            digits = "".join(ch for ch in part if ch.isdigit())
            if digits and len(digits) <= 2:
                codes.add(f"{int(digits):02d}")
            for ch in part:
                if ch in ZODIAC_CHARS:
                    zodiacs.add(ch)
    return zodiacs, codes


def find_vendor_mechanism(module_key: str, by_key: dict[str, Mechanism], by_mode: dict[int, Mechanism]) -> Mechanism | None:
    mechanism = by_key.get(module_key) or by_key.get(f"legacy_{module_key}")
    if mechanism is not None:
        return mechanism
    mode_id = VENDOR_MODULE_MODE_IDS.get(module_key)
    return by_mode.get(mode_id) if mode_id is not None else None


def judge(
    *,
    mechanism: Mechanism,
    content_labels: list[str],
    truth_labels: set[str],
) -> bool | None:
    """独立复算：候选项是否命中真实开奖（同一口径下的集合成员判定）。

    五行分组（`["火|01,02,09,..."]`）的候选标签是元素名，而真实命中目标是
    「特码所属五行」。这类标签不能靠标签集合直接判定，必须先把特码落到元素上，
    因此这里额外要求「特码号码确实出现在该元素分组的号码列表里」，避免误报 hit。
    """
    candidates = {str(item).strip() for item in content_labels if str(item).strip()}
    if not candidates or not truth_labels:
        return None
    hit = bool(candidates & truth_labels)
    if mechanism.exclude:
        return not hit
    return hit


def element_group_confirms_hit(content_labels: list[str], special_code: str) -> bool:
    """五行玩法：真实特码是否出现在候选元素分组的号码列表里。"""
    code = f"{int(special_code):02d}" if special_code.isdigit() else ""
    if not code:
        return False
    for label in content_labels:
        if code in ELEMENT_BY_GROUP.get(str(label).strip(), ()):
            return True
    return False


def content_looks_like_element_groups(content: str) -> bool:
    """`["火|01,02,…"]` 形式的五行分组候选（用来识别动态配置的五行玩法）。"""
    return bool(__import__("re").search(r'"\s*[金木水火土]\s*\|', str(content or "")))


def reference_agrees(
    *,
    config: Any,
    row: dict[str, Any],
    content_labels: list[str],
    truth: bool,
) -> bool:
    """交叉核对：机制自己的 hit_checker 用「复合 outcome 串 + 解析标签」复算，结果是否一致。

    后端 ``public/api.py::_check_correct_by_mechanism`` 对标准 contains/excludes 走的是
    ``label in outcome`` 的**子串**判定，而 outcome 是 ``|`` 分隔的复合标签串。
    当玩法标签本身不是一个 outcome 原子（例如「绝杀半波」的候选是 ``蓝双``，
    而 outcome 只会给出 ``蓝波``/``双``）时，``excludes_hit`` 会恒等于 True，
    这类行不适合直接判为 error —— 脚本把它降级为 warn/verdict_contract，
    由报告指出「机制判定口径与展示候选口径不一致」。
    """
    if config is None:
        return True
    checker = getattr(config, "hit_checker", None)
    if checker is None:
        return True
    labels = tuple(str(item) for item in content_labels)
    if not labels:
        return True
    try:
        from public.api import _compute_outcome_from_row

        outcome = _compute_outcome_from_row(row)
        if not outcome:
            return True
        return bool(checker(outcome, labels)) == bool(truth)
    except Exception:
        return True


#: outcome_loader 需要 (row, conn)；用真实 DB 连接供 fixed_data 兜底映射使用。
_FIXED_CONN_HOLDER: dict[str, Any] = {}


# ── 数据访问 ─────────────────────────────────────────────────────


def load_existing_tables(conn: Any) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for schema in ("created", "public"):
        rows = conn.execute(
            "select table_name from information_schema.tables where table_schema = ?",
            (schema,),
        ).fetchall()
        out[schema] = {str(row["table_name"]) for row in rows}
    return out


def load_draw_index(conn: Any) -> dict[tuple[str, str], dict[str, Any]]:
    """(year, term) → 开奖记录（只取已开奖）。只用于「行内没有开奖号码」时补真值。"""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        rows = conn.execute(
            "select year, term, numbers, is_opened from public.lottery_draws "
            "where is_opened = 1 and numbers is not null and numbers <> ''"
        ).fetchall()
    except Exception:
        return index
    for row in rows:
        key = (str(row["year"] or "").strip(), str(row["term"] or "").strip())
        if key[0] and key[1]:
            index[key] = dict(row)
    return index


def draw_truth_from_payload(numbers: Any, zodiacs: Any) -> tuple[str, list[str], str, list[str]]:
    codes: list[str] = []
    for chunk in str(numbers or "").replace(" ", "").split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            codes.append(f"{int(chunk):02d}")
    zods = split_zodiacs(zodiacs)
    special_code = codes[-1] if codes else ""
    special_zodiac = zods[-1] if zods else ""
    return special_code, codes, special_zodiac, zods


def build_mechanisms() -> tuple[dict[int, Mechanism], dict[str, Mechanism], dict[int, Any]]:
    """构造 mode_id → 机制语义，并返回机制配置对象（用于 content_loader）。"""
    from predict.mechanisms import PREDICTION_CONFIGS, build_title_prediction_configs

    configs: dict[str, Any] = dict(PREDICTION_CONFIGS)
    try:
        configs.update(build_title_prediction_configs())
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 动态机制配置构建失败，只用静态配置：{exc}", file=sys.stderr)

    by_mode: dict[int, Mechanism] = {}
    by_key: dict[str, Mechanism] = {}
    holder: dict[int, Any] = {}
    for key, config in configs.items():
        mode_id = int(getattr(config, "default_modes_id", 0) or 0)
        title = str(getattr(config, "title", "") or "")
        parser_name = str(getattr(getattr(config, "content_parser", None), "__name__", "") or "")
        checker_name = str(getattr(getattr(config, "hit_checker", None), "__name__", "") or "")
        label_space = _PARSER_LABEL_SPACE.get(parser_name, "") or _MECHANISM_LABEL_SPACE.get(
            key, LABEL_SPACE_RAW
        )
        mechanism = Mechanism(
            key=key,
            mode_id=mode_id,
            title=title,
            parser_name=parser_name,
            checker_name=checker_name,
            exclude=(checker_name in {"excludes_hit", "excludes_hit_exact"})
            or is_exclude_mechanism(title, key),
            flat_zodiac=bool(getattr(config, "flat_zodiac", False)),
            flat_tail=bool(getattr(config, "flat_tail", False)),
            label_space=label_space,
        )
        by_key[key] = mechanism
        if mode_id and mode_id not in by_mode:
            by_mode[mode_id] = mechanism
            holder[mode_id] = config
    return by_mode, by_key, holder


def content_loader_text(config: Any, row: dict[str, Any]) -> str:
    if config is None:
        return ""
    loader = getattr(config, "content_loader", None)
    if loader is None:
        return ""
    try:
        return str(loader(row) or "")
    except Exception:
        return ""


# ── 主审计 ───────────────────────────────────────────────────────


def audit_site(
    conn: Any,
    *,
    site: str,
    web_id: int,
    tables: dict[str, set[str]],
    draw_index: dict[tuple[str, str], dict[str, Any]],
    by_mode: dict[int, Mechanism],
    by_key: dict[str, Mechanism],
    configs: dict[int, Any],
    limit: int,
) -> SiteReport:
    from public.api import serialize_public_history_row

    report = SiteReport(site=site, web_id=web_id)
    mode_ids = sorted(set(by_mode))

    for mode_id in mode_ids:
        table = f"mode_payload_{mode_id}"
        mechanism = by_mode[mode_id]
        config = configs.get(mode_id)
        for schema in ("created", "public"):
            if table not in tables.get(schema, set()):
                continue
            try:
                rows = conn.execute(
                    f"select * from {schema}.{table} where web_id = ? "
                    f"order by cast(term as integer) desc limit ?",
                    (web_id, limit),
                ).fetchall()
            except Exception:
                conn.rollback()
                continue
            for raw_row in rows:
                row = dict(raw_row)
                report.rows += 1
                special_code, all_codes, special_zodiac, all_zodiacs = draw_truth_from_payload(
                    row.get("res_code"), row.get("res_sx")
                )
                draw_key = (str(row.get("year") or "").strip(), str(row.get("term") or "").strip())
                # 行内没有开奖号码时不做真值回填：本库 lottery_draws 只有开奖号码、
                # 没有当期生肖，凭号码反推生肖会引入跨年生肖表误差，宁可不判定。
                # 这里只记录该期在 lottery_draws 里是否已开奖，供报告诊断使用。

                served = None
                if special_code:
                    try:
                        served = serialize_public_history_row(row, config)
                    except Exception:
                        served = None
                is_correct = None if served is None else served.get("is_correct")

                loader_text = content_loader_text(config, row)
                content_labels = parse_content_labels(
                    loader_text or str(row.get("content") or ""), mechanism.label_space
                )
                truth_pair = truth_label(
                    mechanism=mechanism,
                    config=config,
                    row=row,
                    special_code=special_code,
                    all_codes=all_codes,
                    special_zodiac=special_zodiac,
                    all_zodiacs=all_zodiacs,
                    label_space=mechanism.label_space,
                )
                truth = (
                    judge(mechanism=mechanism, content_labels=content_labels, truth_labels=truth_pair[1])
                    if truth_pair
                    else None
                )
                # 五行分组玩法：候选标签是元素名，判定真值必须落到特码号码上。
                # 命中类要求特码属于某个候选元素；绝杀类（杀 N 行）要求特码不属于任何候选元素。
                if mechanism.label_space == LABEL_SPACE_ELEMENT or content_looks_like_element_groups(
                    str(loader_text or row.get("content") or "")
                ):
                    in_candidate_element = element_group_confirms_hit(content_labels, special_code)
                    if truth is not None:
                        truth = (not in_candidate_element) if mechanism.exclude else in_candidate_element

                base = dict(
                    site=site,
                    web_id=web_id,
                    schema=schema,
                    mode_id=mode_id,
                    mechanism_key=mechanism.key,
                    term=str(row.get("term") or ""),
                    year=str(row.get("year") or ""),
                    content=str(loader_text or row.get("content") or ""),
                    res_code=",".join(all_codes) if all_codes else str(row.get("res_code") or ""),
                    res_sx=special_zodiac,
                )

                if truth is None:
                    report.warns += 1
                    if not special_code:
                        detail = (
                            "无法判定：行内 res_code 为空"
                            + (
                                "（lottery_draws 已有该期开奖号码，但库里没有当期生肖，不做回填）"
                                if draw_key in draw_index
                                else "，且 lottery_draws 也没有该期开奖"
                            )
                        )
                        rule = "missing_res_code"
                    else:
                        detail = "无法判定：内容解析不出任何候选项，或该玩法缺少真实命中目标口径"
                        rule = "undecidable"
                    report.findings.append(
                        Finding(
                            level="warn",
                            rule=rule,
                            detail=detail,
                            is_correct=is_correct,
                            truth=None,
                            **base,
                        )
                    )
                    continue

                if is_correct is None:
                    report.infos += 1
                    report.findings.append(
                        Finding(
                            level="info",
                            rule="no_is_correct",
                            detail="该行没有可用的 is_correct（机制配置缺失或未开奖），只报告独立真值",
                            is_correct=None,
                            truth=truth,
                            **base,
                        )
                    )
                    continue

                if bool(is_correct) != bool(truth):
                    if not reference_agrees(
                        config=config,
                        row=row,
                        content_labels=content_labels,
                        truth=truth,
                    ):
                        report.warns += 1
                        report.findings.append(
                            Finding(
                                level="warn",
                                rule="verdict_contract",
                                detail=(
                                    "机制判定口径与展示候选口径不一致：该玩法候选标签不是"
                                    "复合 outcome 的原子，后端子串判定会失真；需先统一口径"
                                ),
                                is_correct=bool(is_correct),
                                truth=truth,
                                **base,
                            )
                        )
                        continue
                    report.errors += 1
                    report.findings.append(
                        Finding(
                            level="error",
                            rule="false_hit" if is_correct else "false_miss",
                            detail=(
                                f"is_correct={int(bool(is_correct))} 但候选项未命中真实开奖"
                                if is_correct
                                else "is_correct=0 但候选项确实命中真实开奖"
                            ),
                            is_correct=bool(is_correct),
                            truth=truth,
                            **base,
                        )
                    )
            break  # created 优先；该模式在该站点只取一张表

    # ── vendor 聚合模块（frontend/lib/prediction-contract.ts 的输入来源）──
    try:
        from vendor.homepage_modules import build_vendor_homepage_modules
    except Exception:  # noqa: BLE001
        build_vendor_homepage_modules = None  # type: ignore[assignment]

    if build_vendor_homepage_modules is not None:
        try:
            payload = build_vendor_homepage_modules(
                os.environ["DATABASE_URL"], site_id=web_id, lottery_type=3, history_limit=20
            )
        except Exception:  # noqa: BLE001
            payload = {"data": []}
        for module in payload.get("data") or []:
            module_key = str(module.get("module_key") or "")
            mode_id = VENDOR_MODULE_MODE_IDS.get(module_key)
            if VENDOR_RULES.get(module_key, "undecidable") == "undecidable":
                continue
            for row in module.get("history") or []:
                if row.get("is_correct") is None:
                    continue
                report.rows += 1
                result = row.get("result") or {}
                special_code = str(result.get("res_code") or "")
                special_zodiac = str(result.get("res_sx") or "")
                if not special_code:
                    report.warns += 1
                    continue
                truth = judge_vendor_row(
                    module_key=module_key,
                    row=row,
                    special_code=special_code,
                    special_zodiac=special_zodiac,
                )
                is_correct = bool(row.get("is_correct"))
                if truth is None:
                    report.warns += 1
                    continue
                if truth != is_correct:
                    report.errors += 1
                    report.findings.append(
                        Finding(
                            level="error",
                            rule="false_hit" if is_correct else "false_miss",
                            site=site,
                            web_id=web_id,
                            schema="vendor",
                            mode_id=mode_id,
                            mechanism_key=module_key,
                            year=str(row.get("year") or ""),
                            term=str(row.get("term") or ""),
                            detail=(
                                f"vendor 模块 is_correct={int(is_correct)} 与独立真值不一致"
                            ),
                            content=json.dumps(_vendor_raw_blobs(row), ensure_ascii=False)[:400],
                            res_code=special_code,
                            res_sx=special_zodiac,
                            is_correct=is_correct,
                            truth=truth,
                        )
                    )
    return report


def _vendor_raw_blobs(row: dict[str, Any]) -> list[str]:
    blobs: list[str] = []
    for name in ("groups", "code_groups", "xiao_groups"):
        group = row.get(name)
        if isinstance(group, dict):
            for value in group.values():
                blobs.extend(_iter_scalars(value))
    for name in ("picks", "xiao_pair", "xiao", "tiandi", "daxiao", "code", "tou_code", "text", "display_text"):
        value = row.get(name)
        if value:
            blobs.extend(_iter_scalars(value))
    best = row.get("best_pick")
    if isinstance(best, dict):
        blobs.extend(_iter_scalars(best))
    formula = row.get("formula")
    if isinstance(formula, dict):
        for part in formula.values():
            if isinstance(part, dict):
                blobs.extend(_iter_scalars(part.get("labels")))
    return blobs


def _vendor_candidates(row: dict[str, Any], mechanism: Mechanism) -> list[str]:
    """把 vendor 聚合行里对外可见的候选项归一成与玩法一致的标签集合。"""
    blobs: list[str] = []
    for name in ("groups", "code_groups", "xiao_groups"):
        group = row.get(name)
        if isinstance(group, dict):
            for value in group.values():
                blobs.extend(_iter_scalars(value))

    zodiac_names = ("picks", "xiao_pair", "xiao", "tiandi", "daxiao")
    number_names = ("code", "tou_code")
    for name in zodiac_names + number_names + ("text", "display_text"):
        value = row.get(name)
        if value:
            blobs.extend(_iter_scalars(value))
    best = row.get("best_pick")
    if isinstance(best, dict):
        blobs.extend(_iter_scalars(best))
    formula = row.get("formula")
    if isinstance(formula, dict):
        for part in formula.values():
            if isinstance(part, dict):
                blobs.extend(_iter_scalars(part.get("labels")))

    labels: list[str] = []
    for blob in blobs:
        for part in _split_candidates(str(blob)):
            part = part.strip()
            if not part:
                continue
            if mechanism.label_space == LABEL_SPACE_TAIL:
                match = __import__("re").search(r"(\d)\s*尾", part)
                if match:
                    labels.append(f"{match.group(1)}尾")
                continue
            if mechanism.label_space == LABEL_SPACE_NUMBER:
                digits = "".join(ch for ch in part if ch.isdigit())
                if digits and len(digits) <= 2:
                    labels.append(f"{int(digits):02d}")
                continue
            label = part.split("|", 1)[0].strip() if "|" in part else part
            if label:
                labels.append(label)
    return labels


# ── res_code 回填缺口诊断（只读，不改数据）───────────────────────


def audit_missing_res_code(conn: Any, draw_index: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    """统计「期号已开奖但行内 res_code 为空」的行，并给出建议补跑命令。

    这些行在页面上会显示 `??`（未开奖占位）。修法只能是补跑回填任务写回
    `res_code`/`res_sx`/`res_color`，脚本本身**不执行**任何写入。
    """
    # 不用 LIKE '%'（qmark→format 转换后会与 psycopg 的 % 占位冲突），改在 Python 侧过滤。
    table_names = [
        str(row["table_name"])
        for row in conn.execute(
            "select table_name from information_schema.tables where table_schema = 'created'"
        ).fetchall()
    ]
    tables = [
        {"table_name": name}
        for name in sorted(table_names)
        if name.startswith("mode_payload_")
    ]
    per_table: list[dict[str, Any]] = []
    for table_row in tables:
        table = str(table_row["table_name"])
        columns = {
            str(item["column_name"])
            for item in conn.execute(
                "select column_name from information_schema.columns "
                "where table_schema = 'created' and table_name = ?",
                (table,),
            ).fetchall()
        }
        if not {"res_code", "web_id", "year", "term"}.issubset(columns):
            continue
        try:
            rows = conn.execute(
                f"select web_id, year, term from created.{table} "
                "where res_code is null or res_code = ''"
            ).fetchall()
        except Exception:
            conn.rollback()
            continue
        missing = [
            dict(row)
            for row in rows
            if (str(row["year"] or "").strip(), str(row["term"] or "").strip()) in draw_index
        ]
        if missing:
            per_table.append({"table": table, "rows": len(missing)})

    per_table.sort(key=lambda item: -int(item["rows"]))
    return {
        "tables": per_table,
        "total": sum(int(item["rows"]) for item in per_table),
        "suggested_command": (
            "# 只补跑回填任务（本脚本不会执行；请在授权环境按需运行）：\n"
            "#   python backend/src/app.py ... 后调用管理端回填接口，或直接调用\n"
            "#   domains.prediction.backfill_service.backfill_single_draw() 逐期补跑。\n"
            "# 回填仓库函数：backend/src/domains/prediction/backfill_repository.py"
            "::fill_missing_created_prediction_result_fields\n"
            "# 它会按 type/year/term 命中行，且只在字段为空时写入，不会覆盖预测正文。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sites", nargs="*", help="站点 key（如 twjsz666），留空表示全部 10 个站点")
    parser.add_argument("--web-id", dest="web_ids", type=int, action="append", default=[],
                        help="按 web_id 指定站点，可重复")
    parser.add_argument("--site", dest="site_keys", action="append", default=[],
                        help="按站点 key 指定站点，可重复")
    parser.add_argument("--mode-id", dest="mode_ids", type=int, action="append", default=[],
                        help="只审计指定 mode_id，可重复")
    parser.add_argument("--limit", type=int, default=60, help="每个模式每站点最多审计多少期（默认 60）")
    parser.add_argument("--json", dest="json_path", default="", help="把结果写入 JSON 文件")
    parser.add_argument(
        "--check-missing-res-code",
        action="store_true",
        help="额外统计「已开奖但行内 res_code 为空」的回填缺口（只读，不改数据）",
    )
    parser.add_argument("--max-findings", type=int, default=200, help="每个站点最多打印多少条 finding")
    args = parser.parse_args()

    requested: set[int] = set()
    for key in list(args.sites) + list(args.site_keys):
        matched = [web_id for web_id, site in SITES.items() if site == key]
        if not matched:
            print(f"未知站点 key：{key}（可选：{', '.join(SITES.values())}）")
            return 2
        requested.update(matched)
    requested.update(int(item) for item in args.web_ids)
    unknown = sorted(item for item in requested if item not in SITES)
    if unknown:
        print(f"未知 web_id：{unknown}（可选：{sorted(SITES)}）")
        return 2
    targets = sorted(requested) if requested else sorted(SITES)

    import db  # noqa: E402

    conn = db.connect()
    _FIXED_CONN_HOLDER["conn"] = conn
    tables = load_existing_tables(conn)
    draw_index = load_draw_index(conn)
    by_mode, by_key, configs = build_mechanisms()
    if args.mode_ids:
        allowed = set(int(item) for item in args.mode_ids)
        by_mode = {mode_id: item for mode_id, item in by_mode.items() if mode_id in allowed}
        configs = {mode_id: item for mode_id, item in configs.items() if mode_id in allowed}

    print(f"=== 预测判定真值校验：{len(targets)} 个站点 / {len(by_mode)} 个机制 / "
          f"{len(draw_index)} 期开奖索引", flush=True)

    reports: list[SiteReport] = []
    for web_id in targets:
        site = SITES[web_id]
        report = audit_site(
            conn,
            site=site,
            web_id=web_id,
            tables=tables,
            draw_index=draw_index,
            by_mode=by_mode,
            by_key=by_key,
            configs=configs,
            limit=max(1, int(args.limit)),
        )
        reports.append(report)
        print(
            f"    {site:<14} rows={report.rows:<7} error={report.errors:<4} "
            f"warn={report.warns:<5} info={report.infos}",
            flush=True,
        )
        shown = 0
        for finding in report.findings:
            if finding.level != "error" or shown >= args.max_findings:
                continue
            shown += 1
            print(
                f"      [{finding.rule}] mode={finding.mode_id} {finding.schema} "
                f"{finding.year}-{finding.term} {finding.mechanism_key}: {finding.detail} | "
                f"开奖={finding.res_code}{finding.res_sx} 内容={finding.content[:80]!r}"
            )

    total_error = sum(item.errors for item in reports)
    total_warn = sum(item.warns for item in reports)
    total_info = sum(item.infos for item in reports)
    total_rows = sum(item.rows for item in reports)
    print(
        f"== 合计 rows={total_rows} error={total_error} warn={total_warn} info={total_info}"
    )

    missing_report = None
    if args.check_missing_res_code:
        missing_report = audit_missing_res_code(conn, draw_index)
        print(
            f"== res_code 回填缺口：{missing_report['total']} 行"
            f"（已开奖但行内 res_code 为空，页面显示 `??`）"
        )
        for item in missing_report["tables"][:15]:
            print(f"     created.{item['table']}: {item['rows']} 行")
        print(missing_report["suggested_command"])

    if args.json_path:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database": os.environ.get("DATABASE_URL", ""),
            "rows": total_rows,
            "error": total_error,
            "warn": total_warn,
            "info": total_info,
            "sites": [item.as_dict() for item in reports],
        }
        if missing_report is not None:
            payload["missing_res_code"] = missing_report
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
        print(f"JSON 报告已写入 {args.json_path}")

    return 1 if total_error else 0


if __name__ == "__main__":
    sys.exit(main())
