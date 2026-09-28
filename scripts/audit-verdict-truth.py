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

候选项来源（与后端同源，避免工具自造第二套口径）
------------------------------------------------
后端 ``serialize_public_history_row`` 取候选的文本是
``config.content_loader(row) or summarize_prediction_text(row)``，解析器是
``config.content_parser``。本脚本**使用完全相同的两步**，否则会把「后端根本没读那个
字段」误报成判定错。特别地：

* 不再把 ``title``（模块名）当候选 —— 「画龙点睛」「九攻九距」这类静态文案不是候选项；
* 不再从 ``xiao``/``code``/``jiexi`` 等列自行拼候选 —— 那是后端 ``content_loader`` 的
  职责，工具绕过去就会得到后端看不到的候选集合；
* 平特尾（``flat_tail``：mode 54/55/173）在机制解析器之后**再过一遍 ``tail_atom_labels``**，
  把「一个 item 里逗号串了多个尾标签」的正文摊平成 ``N尾`` 原子。生产库 twbst528
  ``--limit 200`` 的 ``["9尾,4尾,3尾,7尾,8尾,0尾,1尾|"]`` 就是这种形态：
  ``parse_pipe_label_content`` 只取 ``|`` 左侧且不拆逗号，会返回一个整串标签，工具按整串
  判定必然「未命中」→ 5 条假 ``false_hit``。摊平成原子后与后端 ``flat_tail_hit``
  的尾数取值空间一致。对已经是单个 ``N尾`` 的正文，该步骤是恒等变换（本地 1301 行
  flat_tail 数据零差异）。

独立真值仍然独立：真值来自机制自己的 ``outcome_loader``（或平特/五行/号码等口径），
判定用**精确集合成员**，而后端标准 contains/excludes 走的是复合 outcome 串的**子串**
匹配 —— 两者不一致本身就是本工具要报的东西。

平特尾的一处**有意不对齐**：后端 ``predict.common._tail_digits`` 收到 *tuple* 时对每个元素
整串只做一次 ``re.search(r"(\\d)\\s*尾")``，即 ``('1尾,3尾,5尾',)`` 只得到 ``{1}``（只读
**第一个**尾）。因此「第一个尾不中、后面某个尾命中」时后端会漏判，本工具按文档口径判「对」
→ 报 ``false_miss``。这是**后端的真实漏判**，工具不复刻，只以 ``tail_multi_label`` 记账。

判定结果
--------
``error``  is_correct=1 但候选项未命中（虚报命中 ``false_hit``）
           或 is_correct=0 但候选项确实命中（漏报命中 ``false_miss``）

``warn``   需要人跟进的项：
           · ``missing_res_code`` —— 该期在 ``lottery_draws`` 里**已开奖**，但行内
             ``res_code`` 为空（真实回填缺口，页面显示 ``??``）；
           · ``verdict_contract`` —— 独立真值与后端判定不一致，候选标签都是 outcome 原子
             → **疑似真不一致**，需人工核查机制 outcome 口径；
           · ``verdict_contract_atom`` —— 同上，但候选标签不是复合 outcome 的原子，后端
             标准 contains/excludes 的子串判定会退化（contains 恒「错」/ excludes 恒「对」）
             → 标签空间口径问题（不是数据错），后果是页面显示错误的准/错，需统一口径；
           · ``content_loader_gap`` —— 该 mode 在受控登记表里（有已验证的候选语义），但
             机制的 ``content_loader``/``content_parser`` 取不到候选、后端 ``is_correct``
             也是 None → 后端取数口径缺口；
           · ``tool_parse_gap`` —— 后端判得出（``is_correct`` 非空）而工具解析不出候选
             → **工具自身待办**；
           · ``vendor_undecidable`` —— vendor 聚合模块缺可复算输入。

``info``   不进入 warn/error 计数，也不进入 ``judged`` 分母：
           · ``pending_draw`` —— 该期尚未开奖（``lottery_draws`` 里也没有），无真值可判；
           · ``not_judgeable`` —— 非受控的静态文案/图片类模块（后端同样判不出），按设计不可判定；
           · ``no_is_correct`` —— 该行没有可用的 is_correct，只报告独立真值。

``judged`` 才是误差率的分母：``judged = 实际做出布尔判定的行数``，
未开奖期与不可判定模块都从分母里剔除。

专用诊断段（不计入 error/warn）
-------------------------------
* ``element_content_drift`` —— 五行玩法（mode 53/482/98 等）正文里给每个元素列出的号码
  与该元素的**权威号码五行**不一致时记账。这是**真数据问题**（正文用的是「五行肖」即
  生肖五行分组，判定用的是号码五行），本脚本只报告、不改数据、也不放宽判定规则。
* ``title_fallback`` —— 候选文本只来自模块名 ``title`` 的行数（含按机制拆分）。mode 39/68
  的标题本身就是预测正文；mode 336 这类数字成语里偶然出现生肖字时后端会从模块名算准/错。
* ``tail_multi_label`` —— 平特尾里「一个标签串了多个尾原子」的行数（含按机制拆分）。
  这是后端 ``_tail_digits`` 只读第一个尾的高风险形态（见上文「有意不对齐」）。
* ``coverage`` —— 工具覆盖的 mode 与后端受控登记表
  ``domains.prediction.generation_rules.RULE_BY_MODE_ID`` 的差集，防止受控玩法漏审。

用法
----
    # 全站（web_id 4-13）
    python scripts/audit-verdict-truth.py --json .codex-temp/verdict-truth.json

    # 单站点（位置参数 / --site key / --web-id 都支持，可重复混用）
    python scripts/audit-verdict-truth.py twjsz666
    python scripts/audit-verdict-truth.py --site twbst528
    python scripts/audit-verdict-truth.py --web-id 6 --web-id 11

    # 只看某个 mode，并放宽取样数量（默认每个模式每站点只取最近 60 行）
    python scripts/audit-verdict-truth.py --mode-id 53 --limit 200

    # 与上一次的 JSON 报告对照，直接打印逐站 error/warn 前后变化
    python scripts/audit-verdict-truth.py --json .codex-temp/vt-after.json ^
        --baseline .codex-temp/vt-before.json

    # 额外统计「已开奖但行内 res_code 为空」的回填缺口（只读，不改数据；
    # 只统计本次选中的站点，默认即全部 10 个站点）
    python scripts/audit-verdict-truth.py --check-missing-res-code --json out.json

    # 每个站点最多打印多少条 error 明细（默认 200）
    python scripts/audit-verdict-truth.py --max-findings 20

退出码
------
``0`` 无 ``error``；
``1`` 存在 ``error``；
``2`` 参数错误（未知站点 key / 未知 web_id）。

``--check-missing-res-code`` 与 ``warn`` 都不影响退出码。

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

# ── 后端权威表：五行号码分组 ────────────────────────────────────────
# 本脚本**不再自维护第二份五行表**。历史教训（2026-09-29）：脚本里曾内联一份
# ``ELEMENT_BY_GROUP``，它其实是 **生肖五行**（``public.fixed_data`` 里 ``sign='五行肖'``：
# 金肖=鸡/猴、木肖=兔/虎、水肖=鼠/猪、火肖=蛇/马、土肖=牛/龙/羊/狗，且完全漏掉 49），
# 与后端判定真正使用的**号码五行**（``sign='五行'``，49 码全覆盖）在 49 个号码中有 39 个
# 归属不同。用它复算 mode 53/482/98 的真值会凭空产出 false_hit/false_miss。
# 唯一权威来源是 ``predict.common.ELEMENT_NUMBER_GROUPS``（``public.api._ELEMENT_MAP``
# 也由它派生），这里直接 import，保证只有一份表。
try:
    from predict.common import ELEMENT_NUMBER_GROUPS  # noqa: E402
except Exception as exc:  # pragma: no cover - 仅在后端不可导入时触发
    raise SystemExit(
        "无法从后端权威表导入五行号码分组 predict.common.ELEMENT_NUMBER_GROUPS："
        f"{exc}"
    )


def _validate_element_number_groups() -> None:
    """启动即校验权威五行表 01-49 全覆盖且互不重叠（表坏了要立刻停，不能带病审计）。"""
    seen: dict[str, str] = {}
    for element, numbers in ELEMENT_NUMBER_GROUPS.items():
        for number in numbers:
            duplicate = seen.get(number)
            if duplicate:
                raise SystemExit(f"五行分组重复覆盖 {number}：{duplicate} / {element}")
            seen[number] = element
    expected = [f"{index:02d}" for index in range(1, 50)]
    if sorted(seen) != expected:
        missing = sorted(set(expected) - set(seen))
        raise SystemExit(
            "predict.common.ELEMENT_NUMBER_GROUPS 未覆盖 01-49，缺失："
            f"{missing if missing else '（无，可能是格式错误）'}"
        )


_validate_element_number_groups()

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
    #: 实际做出布尔判定的行数（误差率分母）；未开奖期与不可判定模块都被剔除。
    judged: int = 0
    #: 尚未开奖（lottery_draws 也没有该期）—— 无真值可判，不计入 warn。
    pending: int = 0
    #: 静态文案/图片类模块，后端同样判不出 —— 按设计不可判定，不计入 warn。
    not_judgeable: int = 0
    #: 已开奖但行内 res_code 为空（真实回填缺口，计入 warn）。
    missing_res_code: int = 0
    #: 五行分组正文与权威号码五行不一致的记账（真数据问题，不计入 error/warn）。
    element_drift: int = 0
    #: 上述记账的样例（最多 ``ELEMENT_DRIFT_SAMPLE_LIMIT`` 条，用于取证）。
    drift_samples: list[dict[str, Any]] = field(default_factory=list)
    #: 候选文本只来自模块名 ``title`` 的行数（真口径问题，不计入 error/warn）。
    title_fallback: int = 0
    #: 上述记账按机制拆分（``机制 key`` → 行数）。
    title_fallback_by_mode: dict[str, int] = field(default_factory=dict)
    #: 平特尾里「一个标签串了多个尾原子」的行数（后端只读第一个尾的高风险形态，只记账）。
    tail_multi_label: int = 0
    tail_multi_label_by_mode: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "web_id": self.web_id,
            "rows": self.rows,
            "judged": self.judged,
            "error": self.errors,
            "warn": self.warns,
            "info": self.infos,
            "pending": self.pending,
            "not_judgeable": self.not_judgeable,
            "missing_res_code": self.missing_res_code,
            "element_drift": self.element_drift,
            "element_drift_samples": self.drift_samples,
            "title_fallback": self.title_fallback,
            "title_fallback_by_mode": self.title_fallback_by_mode,
            "tail_multi_label": self.tail_multi_label,
            "tail_multi_label_by_mode": self.tail_multi_label_by_mode,
            "findings": [item.as_dict() for item in self.findings],
        }


#: 每个站点最多留几条五行分组漂移样例（取证用，避免 JSON 被刷爆）。
ELEMENT_DRIFT_SAMPLE_LIMIT = 20


def _record_element_drift(
    report: SiteReport,
    *,
    base: dict[str, Any],
    drift: list[dict[str, Any]],
    special_code: str,
) -> None:
    """把五行分组正文漂移记进站点报告（只记账，不改 level、不改数据）。"""
    if len(report.drift_samples) >= ELEMENT_DRIFT_SAMPLE_LIMIT:
        return
    report.drift_samples.append(
        {
            "site": base.get("site"),
            "web_id": base.get("web_id"),
            "mode_id": base.get("mode_id"),
            "mechanism_key": base.get("mechanism_key"),
            "year": base.get("year"),
            "term": base.get("term"),
            "special_code": special_code,
            "drift": drift,
        }
    )


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
#: 平特尾（``flat_tail``：mode 54/55/173 等）。后端 ``flat_tail_hit`` 的取值空间是
#: **尾数字**（``predict.common._tail_digits``），所以候选必须归一到 ``N尾`` 原子，
#: 不能把「一个 item 里的多个尾标签」当成一整串去比对（见 ``tail_atom_labels``）。
LABEL_SPACE_FLAT_TAIL = "flat_tail"
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

#: 元素标签集合（用于识别「元素分组」正文，例如 ``["火|01,02,…"]``）。
ELEMENT_LABELS: tuple[str, ...] = tuple(ELEMENT_NUMBER_GROUPS)

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
    #: 机制专属 outcome 是多段复合串（`头:3头|尾:7尾`），每一段都是独立的可接受标签
    #: （任一维度命中即算命中 / 杀类要求每一段都不在候选里）。真值必须按分段集合判定，
    #: 不能拿整串去和候选标签取交集。
    split_outcome_atoms: bool = False


#: hit_checker 以「多段复合 outcome、任一维度命中即算命中」为契约的机制。
#: 这些 checker 的实现都是``any(atom in labels for atom in outcome.split("|"))``，
#: 所以真值必须按 ``|`` 分段成集合，不能拿整串去和候选标签取交集
#: （历史噪音：``title_198`` 的载荷真值是 ``双数|大数|野兽``，候选是 ``野兽``，
#: 整串比较恒不命中，119 行被误报成「疑似真不一致」）。
SPLIT_OUTCOME_CHECKERS = {
    # 三头四尾：``头:3头|尾:7尾``
    "three_head_four_tail_hit",
    # MIXED 类别（项目约束：任一维度命中即算命中），见 predict/categories/mixed.py
    "mixed_dimension_contains_hit",
    "mixed_dimension_excludes_hit",
}


def is_exclude_mechanism(title: str, key: str) -> bool:
    haystack = f"{title} {key}"
    return any(word in haystack for word in ("杀", "绝杀", "不中", "输尽", "排除"))


def element_content_drift(content: str) -> list[dict[str, Any]]:
    """五行分组正文里「元素 → 号码列表」与权威号码五行不一致时返回差异明细。

    这是**真数据问题**的取证函数（正文写的是生肖五行分组，判定用的是号码五行），
    只记账、不参与 error/warn，也绝不修改数据。

    返回形如 ``[{"label": "木", "declared": [...], "authoritative": [...],
    "unexpected": [...], "missing": [...]}]``；正文不是元素分组时返回 ``[]``。
    """
    text = str(content or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return []
    items = parsed if isinstance(parsed, list) else [parsed]
    drift: list[dict[str, Any]] = []
    for item in items:
        raw = str(item or "").strip()
        if "|" not in raw:
            continue
        label, numbers = raw.split("|", 1)
        label = label.strip()
        if label not in ELEMENT_LABELS:
            continue
        declared = sorted(
            {chunk for chunk in (part.strip() for part in numbers.split(",")) if chunk.isdigit()}
        )
        declared = [f"{int(chunk):02d}" for chunk in declared]
        authoritative = sorted(ELEMENT_NUMBER_GROUPS.get(label, ()))
        if declared == authoritative:
            continue
        drift.append(
            {
                "label": label,
                "declared": declared,
                "authoritative": authoritative,
                "unexpected": sorted(set(declared) - set(authoritative)),
                "missing": sorted(set(authoritative) - set(declared)),
            }
        )
    return drift


def content_looks_like_element_groups(content: str) -> bool:
    """`["火|01,02,…"]` 形式的五行分组候选（用来识别动态配置的五行玩法）。"""
    return bool(__import__("re").search(r'"\s*[金木水火土]\s*\|', str(content or "")))


def candidate_text_from_title_only(
    row: dict[str, Any],
    loader_text: str,
    check_text: str,
) -> bool:
    """候选文本是否只来自 **模块名** ``title``。

    ``public.api.summarize_prediction_text`` 的最后兜底是 ``title``，所以当
    ``content_loader`` 与 ``content`` 都为空时，后端会把模块标题当候选正文：
    · 「画龙点睛 / 投鼠忌器 / 亡羊补牢」（mode 39）与四句成语（mode 68）里，标题**就是**
      预测正文（每个成语点一个生肖），属正常载荷；
    · 「五马分尸 / 四马攒蹄」（mode 336 的数字类成语）里出现生肖字只是巧合，后端的准/错
      就从模块名算出来了 —— 这才是「把模块名当候选」的噪音。
    工具不做取舍（那需要逐 mode 白名单），只把这件事记账，供口径负责人决策。
    """
    if loader_text or str(row.get("content") or "").strip():
        return False
    title = str(row.get("title") or "").strip()
    return bool(title) and str(check_text or "").strip() == title


#: 尾标签之间的分隔符；与后端 ``predict.common._tail_digits`` 的
#: ``re.split(r"[,|，、\s]+")`` 保持同一套（另加 ``;`` / ``/`` 两个常见写法）。
_TAIL_LABEL_SEPARATORS = __import__("re").compile(r"[,，、;；/|\s]+")


def tail_atom_labels(labels: list[str]) -> list[str]:
    """把平特尾的候选标签归一到 ``N尾`` **原子**集合。

    背景（生产库 twbst528 ``--limit 200`` 暴露，2026-09-28）：mode 54（平特1尾）的深层
    历史正文长这样 —— ``["9尾,4尾,3尾,7尾,8尾,0尾,1尾|"]``：多个尾标签用逗号串在 ``|``
    **左侧**、右侧号码清单为空。``parse_pipe_label_content`` 只取 ``|`` 左侧、且**不拆逗号**，
    于是它返回一个整串标签 ``9尾,4尾,…,1尾``；工具按整串做集合成员判定 → 与真值
    ``{9尾,4尾,…}`` 无交集 → 恒判「未命中」→ 5 条假 ``false_hit``。

    归一规则（与 ``predict.common._tail_digits`` 同取值空间，逐 token 而不是逐字符）：
      · ``N尾`` → 尾数 ``N``（例 ``9尾`` → ``9尾``）；
      · 逗号/顿号/斜杠等分隔的一段里出现多个 ``N尾`` → 每个都算一个原子；
      · 纯 1~2 位号码 token（无 ``尾``）→ 取**末位**（``13`` → ``3尾``），
        与 ``_tail_digits`` 的「多位数取最后一位」一致；
      · 其它 token（中文、诗句、``后落码`` 这类分组名）→ 不产出候选。

    这里只把「一个 item 里的多个标签」摊平成原子，**不改变**判定规则
    （仍是「开奖 7 码尾集合 ∩ 候选尾集合 ≠ ∅」），所以不是放宽 error 判定。

    与后端的一处**有意的不对齐**（不复制后端缺陷）：``_tail_digits`` 收到 *tuple* 时对
    每个元素整串只做一次 ``re.search(r"(\\d)\\s*尾")``，即 ``('1尾,3尾,5尾',)`` 只得到 ``{1}``
    （**只读第一个尾**）。因此当正文里第一个尾不中、而后面某个尾命中时，后端会判「错」、
    本工具按文档口径判「对」→ 工具会报 ``false_miss``。这是**后端的真实漏判**，工具不复刻，
    只在报告里以 ``tail_multi_label`` 记账，便于口径负责人决定是否修后端。
    """
    out: list[str] = []
    for label in labels:
        for token in _TAIL_LABEL_SEPARATORS.split(str(label or "")):
            token = token.strip()
            if not token:
                continue
            matches = __import__("re").findall(r"(\d)\s*尾", token)
            if not matches and token.isdigit() and len(token) <= 2:
                matches = [token[-1]]
            for digit in matches:
                atom = f"{int(digit)}尾"
                if atom not in out:
                    out.append(atom)
    return out


def tail_label_carries_multiple_atoms(raw_labels: list[str]) -> bool:
    """某个**原始**标签里是否同时带了 ≥2 个尾原子（``9尾,4尾,…``）。

    只用于记账（``tail_multi_label``）：这一类正文是后端 ``_tail_digits`` 只读第一个尾的
    高风险区，工具在这里与后端可能给出相反的结论（工具判「对」、后端判「错」），
    需要口径负责人知道有多少行落在该形态上。
    """
    pattern = __import__("re").compile(r"(\d)\s*尾")
    for label in raw_labels:
        if len(set(pattern.findall(str(label or "")))) > 1:
            return True
    return False


def parse_content_labels(
    content: str,
    label_space: str,
    config: Any = None,
    *,
    prefer_mechanism_parser: bool = True,
) -> list[str]:
    """解析候选项标签：**优先复用后端机制自己的 content_parser**。

    后端 ``_check_correct_by_mechanism`` 用的就是 ``config.content_parser``，
    工具必须用同一个解析器，否则会把「后端解析出的候选」和「工具自己解析出的候选」
    的差异当成判定错误（历史噪音：``title_110`` 的 ``parse_pipe_label_content``
    只取 ``后落码`` 这个分组名，而通用解析器会去抓号码）。

    ``prefer_mechanism_parser=False`` 或机制没有可用解析器时，退回按
    ``label_space`` 的通用解析（用于``config is None`` 的动态玩法兜底）。

    ``split_outcome_atoms`` 机制（如「三头四尾」）尤其必须走机制解析器：它的候选是
    ``头:2头`` / ``尾:6尾`` 这种带维度前缀的标签，通用解析器拿不到。

    ``label_space == LABEL_SPACE_FLAT_TAIL``（平特尾，mode 54/55/173）时，机制解析器的
    输出会再过一遍 ``tail_atom_labels``：把「一个 item 里逗号串起来的多个尾标签」摊平成
    ``N尾`` 原子。否则 ``["9尾,4尾,…,1尾|"]`` 这类正文只会得到一个整串标签，判定恒不命中。
    """
    text = str(content or "").strip()
    if not text:
        return []
    labels: list[str] = []
    if prefer_mechanism_parser and config is not None:
        parser = getattr(config, "content_parser", None)
        if callable(parser):
            try:
                labels = [str(item).strip() for item in parser(text) if str(item).strip()]
            except Exception:
                labels = []
    if labels:
        if label_space == LABEL_SPACE_FLAT_TAIL:
            return tail_atom_labels(labels) or labels
        return labels
    try:
        from predict.common import parse_json_or_plain_content
        from predict.mechanisms import parse_number_content, parse_pipe_label_content, parse_zodiac_content
        from predict.categories.content_columns import parse_tail_digit_content, parse_zodiac_chars

        if label_space == LABEL_SPACE_FLAT_TAIL:
            # 机制解析器不可用时的兜底：直接对原文做尾原子归一（先按 `|` 左侧取正文，
            # 与 parse_pipe_label_content 的取值侧一致）。
            left = text
            try:
                items = list(parse_json_or_plain_content(text))
            except Exception:
                items = []
            if items:
                left = "|".join(items)
            return tail_atom_labels([left.split("|", 1)[0] if "|" in left else left])
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
) -> tuple[str, set[str], bool] | None:
    """返回 (真实开奖标签, 可接受标签集合, 是否为「分段任一命中」口径)。

    绝杀/平特这类玩法可能有多个可接受标签（平特尾要看开奖 7 个号码的尾数），
    因此返回集合而不是单值。标签口径必须与 ``content_parser`` 的输出一致：
    例如「公式四尾」的标签是 ``6尾`` 而不是号码 ``06``。

    第三个返回值只对 ``split_outcome_atoms`` 机制为 True：它的机制专属 outcome 是多段复合串
    （``头:3头|尾:7尾``），每一段都是独立的可接受标签（任一维度命中即算命中）。
    """
    if mechanism.flat_tail:
        tails = {f"{int(code) % 10}尾" for code in (all_codes or [special_code]) if code.isdigit()}
        return ("", tails, False) if tails else None
    if mechanism.flat_zodiac:
        pool = set(all_zodiacs or ([special_zodiac] if special_zodiac else []))
        return ("", pool, False) if pool else None
    if not special_code:
        return None

    # 首选机制自己的 outcome_loader：它才是该玩法真实命中目标的权威口径。
    loader = getattr(config, "outcome_loader", None) if config is not None else None
    if loader is not None:
        try:
            value = str(loader(row, _FIXED_CONN_HOLDER.get("conn")) or "").strip()
            if value:
                if mechanism.split_outcome_atoms:
                    parts = {part.strip() for part in value.split("|") if part.strip()}
                    if parts:
                        return (value, parts, False)
                return (value, {value}, False)
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
    return (label, {label}, False)


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


def judge(
    *,
    mechanism: Mechanism,
    content_labels: list[str],
    truth_labels: set[str],
    require_all: bool = False,
) -> bool | None:
    """独立复算：候选项是否命中真实开奖（同一口径下的集合成员判定）。

    五行分组（`["火|01,02,09,..."]`）的候选标签是元素名，而真实命中目标是
    「特码所属五行」。这类标签不能靠标签集合直接判定，必须先把特码落到元素上，
    因此这里额外要求「特码号码确实出现在该元素分组的号码列表里」，避免误报 hit。

    ``require_all=True`` 时要求真值集合的**每一项**都出现在候选里；默认是「任一命中」。
    """
    candidates = {str(item).strip() for item in content_labels if str(item).strip()}
    if not candidates or not truth_labels:
        return None
    hit = truth_labels <= candidates if require_all else bool(candidates & truth_labels)
    if mechanism.exclude:
        return not hit
    return hit


def element_group_confirms_hit(content_labels: list[str], special_code: str) -> bool:
    """五行玩法：真实特码是否落在候选元素**号码五行**分组里。

    口径必须与 ``public/api.py::_ELEMENT_MAP`` 一致 —— 即按**号码**判五行
    （37 → 木），不是按生肖判五行（马为火肖）。号码五行唯一来源是
    ``predict.common.ELEMENT_NUMBER_GROUPS``（``public.fixed_data`` sign='五行'）。
    """
    code = f"{int(special_code):02d}" if special_code.isdigit() else ""
    if not code:
        return False
    for label in content_labels:
        if code in ELEMENT_NUMBER_GROUPS.get(str(label).strip(), ()):
            return True
    return False


#: 后端标准 contains/excludes 走的是复合 outcome 串的「子串」判定（见
#: ``public/api.py::_check_correct_by_mechanism``）。这些 checker 的候选标签必须本身是
#: outcome 的原子，否则判定会退化。
SUBSTRING_OUTCOME_CHECKERS = {"contains_hit", "excludes_hit"}


def reference_verdict(
    *,
    config: Any,
    row: dict[str, Any],
    content_labels: list[str],
    truth: bool,
) -> tuple[str, list[str], str]:
    """交叉核对机制自己的 hit_checker，并给出**不一致的原因分类**。

    返回 ``(classification, non_atomic_labels, outcome)``：

    * ``agree``      —— checker 复算结果与独立真值一致（不一致只能来自判定实现缺陷）；
    * ``atom``       —— 候选标签不是复合 outcome 的原子，且后端标准 contains/excludes
      用的正是子串匹配：这是**判定口径问题**（标签空间没对齐），不是数据错，
      但也不能当成工具口径错一笔勾销 —— 它说明该玩法整列的判定都不可信；
    * ``diverge``    —— 候选标签都是 outcome 原子，checker 复算仍然和独立真值不一致
      → **疑似真不一致**，需要人工核查机制 outcome 口径。
    * ``unknown``    —— 无法复算（缺 config / outcome 为空 / 抛异常），保持原判为 error。
    """
    if config is None:
        return ("unknown", [], "")
    checker = getattr(config, "hit_checker", None)
    if checker is None:
        return ("unknown", [], "")
    labels = tuple(str(item) for item in content_labels)
    if not labels:
        return ("unknown", [], "")
    try:
        from public.api import _compute_outcome_from_row

        outcome = _compute_outcome_from_row(row)
    except Exception:
        return ("unknown", [], "")
    if not outcome:
        return ("unknown", [], "")

    atoms = {value.strip() for value in outcome.split("|") if value.strip()}
    non_atomic = [label for label in labels if label not in atoms]
    try:
        agrees = bool(checker(outcome, labels)) == bool(truth)
    except Exception:
        return ("unknown", non_atomic, outcome)
    if agrees:
        return ("agree", non_atomic, outcome)
    checker_name = str(getattr(checker, "__name__", "") or "")
    if non_atomic and checker_name in SUBSTRING_OUTCOME_CHECKERS:
        return ("atom", non_atomic, outcome)
    return ("diverge", non_atomic, outcome)


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
            split_outcome_atoms=checker_name in SPLIT_OUTCOME_CHECKERS,
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
    configs: dict[int, Any],
    limit: int,
) -> SiteReport:
    from public.api import serialize_public_history_row, summarize_prediction_text

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

                # 候选文本/解析器与后端 ``_check_correct_by_mechanism`` 保持同源：
                # ``content_loader(row) or summarize_prediction_text(row)`` + 机制自带的
                # ``content_parser``。工具自选字段 / 自选解析器只会制造口径噪音
                # （历史噪音：把 ``title`` 当候选、从 ``xiao``/``jiexi`` 自行拼候选）。
                loader_text = content_loader_text(config, row)
                check_text = loader_text or summarize_prediction_text(row)
                # 平特尾的候选必须归一到 `N尾` 原子（后端 flat_tail_hit 的取值空间），
                # 其它玩法沿用机制自己的 label_space。
                effective_label_space = (
                    LABEL_SPACE_FLAT_TAIL if mechanism.flat_tail else mechanism.label_space
                )
                content_labels = parse_content_labels(
                    check_text,
                    effective_label_space,
                    config,
                    prefer_mechanism_parser=True,
                )
                # 平特尾「一个标签串了多个尾原子」的取证（后端只读第一个尾，只记账）。
                if mechanism.flat_tail:
                    raw_tail_labels = parse_content_labels(
                        check_text,
                        mechanism.label_space,
                        config,
                        prefer_mechanism_parser=True,
                    )
                    if tail_label_carries_multiple_atoms(raw_tail_labels):
                        report.tail_multi_label += 1
                        tkey = str(mechanism.key)
                        report.tail_multi_label_by_mode[tkey] = (
                            report.tail_multi_label_by_mode.get(tkey, 0) + 1
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
                    judge(
                        mechanism=mechanism,
                        content_labels=content_labels,
                        truth_labels=truth_pair[1],
                        require_all=truth_pair[2],
                    )
                    if truth_pair
                    else None
                )
                # 五行分组玩法：候选标签是元素名，判定真值必须落到特码号码上。
                # 命中类要求特码属于某个候选元素；绝杀类（杀 N 行）要求特码不属于任何候选元素。
                if mechanism.label_space == LABEL_SPACE_ELEMENT or content_looks_like_element_groups(
                    str(check_text)
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
                    content=str(check_text),
                    res_code=",".join(all_codes) if all_codes else str(row.get("res_code") or ""),
                    res_sx=special_zodiac,
                )

                # 五行分组正文 vs 权威号码五行：真数据问题，只记账，不参与 error/warn。
                drift = element_content_drift(str(check_text))
                if drift:
                    report.element_drift += 1
                    _record_element_drift(report, base=base, drift=drift, special_code=special_code)

                # 「把模块名当候选」的取证：只记账，不参与 error/warn（见函数 docstring）。
                if content_labels and candidate_text_from_title_only(row, loader_text, check_text):
                    report.title_fallback += 1
                    key = str(mechanism.key)
                    report.title_fallback_by_mode[key] = report.title_fallback_by_mode.get(key, 0) + 1

                if truth is None:
                    if not special_code:
                        if draw_key not in draw_index:
                            # 该期尚未开奖：行内没有开奖号码，lottery_draws 里也查不到。
                            # 无真值可判 → info，并从 ``judged`` 分母中剔除（不算 warn）。
                            report.pending += 1
                            report.infos += 1
                            report.findings.append(
                                Finding(
                                    level="info",
                                    rule="pending_draw",
                                    detail="该期尚未开奖（lottery_draws 里也没有开奖号码），无真值可判",
                                    is_correct=is_correct,
                                    truth=None,
                                    **base,
                                )
                            )
                        else:
                            # 真实回填缺口：期号已开奖，行内 res_code 却为空，页面显示 `??`。
                            report.missing_res_code += 1
                            report.warns += 1
                            report.findings.append(
                                Finding(
                                    level="warn",
                                    rule="missing_res_code",
                                    detail=(
                                        "已开奖但行内 res_code 为空（页面显示 `??`）：lottery_draws 已有"
                                        "该期开奖号码，但库里没有当期生肖，脚本不做回填；需补跑回填任务"
                                        "写回 res_code/res_sx"
                                    ),
                                    is_correct=is_correct,
                                    truth=None,
                                    **base,
                                )
                            )
                    elif is_correct is None and mode_id in load_controlled_mode_ids():
                        # 受控 mode（后端已登记已验证的候选语义）却取不到候选，且后端
                        # ``is_correct`` 也是 None → 后端 content_loader/content_parser 与
                        # 该表的实际候选列不匹配（实例：mode 484/489 的候选在 ``xiao``/``code``
                        # 列，而 content_loader 是 ``default_content_from_row``，读的是空的
                        # ``content``）→ 整列没有准/错。真 gap，报 warn。
                        report.warns += 1
                        report.findings.append(
                            Finding(
                                level="warn",
                                rule="content_loader_gap",
                                detail=(
                                    "受控 mode 但取不到候选：机制的 content_loader/content_parser "
                                    "与该表实际候选列不匹配，后端 is_correct 亦为 None（该列不会有准/错）。"
                                    "需后端补 content_loader，或确认该模块按设计不展示准/错"
                                ),
                                is_correct=None,
                                truth=None,
                                **base,
                            )
                        )
                    elif is_correct is None:
                        # 非受控 mode，且后端在同一行、同一解析器下也判不出
                        # （``_check_correct_by_mechanism`` 在候选为空时返回 None）
                        # → 该模块本身没有候选集合语义（静态文案/图片/诗句），按设计不可判定，
                        # 既不是工具缺陷也不是数据错。
                        report.not_judgeable += 1
                        report.infos += 1
                        report.findings.append(
                            Finding(
                                level="info",
                                rule="not_judgeable",
                                detail=(
                                    "静态文案/图片类模块：候选文本解析不出集合（后端判定同样为 None），"
                                    "本工具按设计不判定"
                                ),
                                is_correct=None,
                                truth=None,
                                **base,
                            )
                        )
                    else:
                        # 后端判得出而工具判不出 → 工具自身待办（真 gap）。
                        report.warns += 1
                        report.findings.append(
                            Finding(
                                level="warn",
                                rule="tool_parse_gap",
                                detail=(
                                    "后端判定非空（is_correct 有值）而工具复算不出候选/真值口径"
                                    " → 工具自身待办"
                                ),
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

                report.judged += 1

                if bool(is_correct) != bool(truth):
                    classification, non_atomic, outcome = reference_verdict(
                        config=config,
                        row=row,
                        content_labels=content_labels,
                        truth=truth,
                    )
                    if classification == "agree":
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
                        continue
                    report.warns += 1
                    if classification == "atom":
                        rule = "verdict_contract_atom"
                        detail = (
                            "标签空间口径问题（不是数据错，也不是本工具放宽）：候选标签不是复合 "
                            f"outcome 的原子（非原子候选={non_atomic[:6]}），后端标准 contains/excludes "
                            "的子串判定会退化 → contains 恒判「错」、excludes 恒判「对」，页面会显示错误的"
                            "准/错。修法是统一标签口径（后端把分组标签展开为号码/原子，或正文改写成 "
                            "outcome 原子），不能在工具侧放宽"
                        )
                    elif classification == "diverge":
                        rule = "verdict_contract"
                        detail = (
                            "疑似真不一致：候选标签都是 outcome 原子，机制 checker 复算仍与独立真值"
                            f"相反（outcome={outcome[:80]!r}），需人工核查机制 outcome 口径"
                        )
                    else:
                        rule = "verdict_contract"
                        detail = "无法交叉复算（缺 config / outcome 为空 / checker 抛错），保守降级为 warn"
                    report.findings.append(
                        Finding(
                            level="warn",
                            rule=rule,
                            detail=detail,
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
                    # 模块自己都没给出 is_correct（``wuxiao_wuma`` / ``shuangbo_12ma`` 的
                    # is_correct 就是 None）→ 没有可比对的判定，不计数、不报 warn。
                    continue
                report.rows += 1
                result = row.get("result") or {}
                special_code = str(result.get("res_code") or "")
                special_zodiac = str(result.get("res_sx") or "")
                vendor_base = dict(
                    site=site,
                    web_id=web_id,
                    schema="vendor",
                    mode_id=mode_id,
                    mechanism_key=module_key,
                    year=str(row.get("year") or ""),
                    term=str(row.get("term") or ""),
                    content=json.dumps(_vendor_raw_blobs(row), ensure_ascii=False)[:400],
                    res_code=special_code,
                    res_sx=special_zodiac,
                )
                if not special_code:
                    # 未开奖：无真值可判，与 mode 表一视同仁地按 pending 处理，不计 warn。
                    report.pending += 1
                    report.infos += 1
                    report.findings.append(
                        Finding(
                            level="info",
                            rule="pending_draw",
                            detail="vendor 行未开奖（result.res_code 为空），无真值可判",
                            is_correct=bool(row.get("is_correct")),
                            truth=None,
                            **vendor_base,
                        )
                    )
                    continue
                truth = judge_vendor_row(
                    module_key=module_key,
                    row=row,
                    special_code=special_code,
                    special_zodiac=special_zodiac,
                )
                is_correct = bool(row.get("is_correct"))
                if truth is None:
                    # 以前这里是无声的 ``warns += 1``，报告里看不到任何行 → 无法跟进。
                    report.warns += 1
                    report.findings.append(
                        Finding(
                            level="warn",
                            rule="vendor_undecidable",
                            detail=(
                                "vendor 模块缺少可复算的判定输入（候选池为空或模块口径未登记），"
                                f"展示候选={_vendor_candidates(row, by_mode[mode_id])[:8] if mode_id in by_mode else []}"
                            ),
                            is_correct=is_correct,
                            truth=None,
                            **vendor_base,
                        )
                    )
                    continue
                report.judged += 1
                if truth != is_correct:
                    report.errors += 1
                    report.findings.append(
                        Finding(
                            level="error",
                            rule="false_hit" if is_correct else "false_miss",
                            detail=(
                                f"vendor 模块 is_correct={int(is_correct)} 与独立真值不一致"
                            ),
                            is_correct=is_correct,
                            truth=truth,
                            **vendor_base,
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
    """把 vendor 聚合行里对外可见的候选项归一成与玩法一致的标签集合。

    仅用于诊断打印。vendor 模块的 ``is_correct`` **不是**拿「展示候选池」比对出来的
    （``public_yixiao_yima`` 用推荐一肖一码、``shujinguang`` 用前二肖），
    判定口径由 ``judge_vendor_row`` 按模块规则各自复算。
    """
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


def audit_missing_res_code(
    conn: Any,
    draw_index: dict[tuple[str, str], dict[str, Any]],
    *,
    web_ids: set[int] | None = None,
) -> dict[str, Any]:
    """统计「期号已开奖但行内 res_code 为空」的行，并给出建议补跑命令。

    这些行在页面上会显示 `??`（未开奖占位）。修法只能是补跑回填任务写回
    `res_code`/`res_sx`/`res_color`，脚本本身**不执行**任何写入。

    ``web_ids`` 为本次审计选中的站点；``None`` 表示不按站点过滤（全部 web_id）。
    只扫 ``created`` schema（页面实际读的是镜像表）。
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
            and (web_ids is None or int(row["web_id"] or 0) in web_ids)
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


# ── 受控玩法覆盖度自检 ───────────────────────────────────────────

#: 后端受控登记表 ``RULE_BY_MODE_ID`` 的 mode_id 集合（懒加载缓存）。
_CONTROLLED_MODE_IDS: set[int] = set()


def load_controlled_mode_ids() -> set[int]:
    """后端受控登记表 ``domains.prediction.generation_rules.RULE_BY_MODE_ID`` 的 mode_id。

    「受控」= 后端已经为该 mode 登记了**已验证的未来期命中规则**（``truth_outcome`` +
    ``hit_checker``），也就是该项目自己认定「这个 mode 有确定候选语义」的清单。
    工具用它区分：
    * 受控 mode 取不到候选 → 后端取数/解析口径缺口（真 gap，报 warn）；
    * 非受控 mode 取不到候选 → 静态文案/图片模块，按设计不可判定（报 info）。
    """
    global _CONTROLLED_MODE_IDS
    if _CONTROLLED_MODE_IDS:
        return _CONTROLLED_MODE_IDS
    try:
        from domains.prediction.generation_rules import RULE_BY_MODE_ID
    except Exception:  # noqa: BLE001
        return set()
    _CONTROLLED_MODE_IDS = {int(item) for item in RULE_BY_MODE_ID}
    return _CONTROLLED_MODE_IDS


def coverage_report(by_mode: dict[int, Mechanism]) -> dict[str, Any]:
    """对照后端受控登记表 ``RULE_BY_MODE_ID`` 检查工具是否漏审受控 mode。

    后端唯一的「受控生成」权威登记表是
    ``domains.prediction.generation_rules.RULE_BY_MODE_ID``；工具必须覆盖它的每一个
    mode_id，否则未来期受控玩法可能出现判定缺陷而无人发现。
    """
    try:
        controlled = load_controlled_mode_ids()
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "reason": f"无法导入受控登记表：{exc}",
            "controlled_modes": 0,
            "tool_modes": len(by_mode),
            "missing_modes": [],
            "unregistered_modes": sorted(by_mode),
        }
    if not controlled:
        return {
            "available": False,
            "reason": "受控登记表为空或不可导入",
            "controlled_modes": 0,
            "tool_modes": len(by_mode),
            "missing_modes": [],
            "unregistered_modes": sorted(by_mode),
        }
    tool = set(int(item) for item in by_mode)
    return {
        "available": True,
        "reason": "",
        "controlled_modes": len(controlled),
        "tool_modes": len(tool),
        "missing_modes": sorted(controlled - tool),
        "unregistered_modes": sorted(tool - controlled),
    }


# ── 与基线 JSON 对照（收敛过程的固定验收动作）───────────────────


def compare_with_baseline(baseline: dict[str, Any], reports: list[SiteReport]) -> dict[str, Any]:
    """把本次结果与一份历史 JSON 报告逐站对照，给出 error/warn 前后变化。

    用来验证「工具口径修正」这类收敛动作：``error``/``warn`` 的下降必须能逐站对上，
    并且不允许出现某个站点 ``error`` 反而上升（那通常意味着工具改动引入了噪音）。
    """
    old = {str(item.get("site")): item for item in baseline.get("sites") or []}
    rows: list[dict[str, Any]] = []
    for report in reports:
        before = old.get(report.site) or {}
        rows.append(
            {
                "site": report.site,
                "rows": report.rows,
                "error_before": int(before.get("error") or 0),
                "error_after": report.errors,
                "warn_before": int(before.get("warn") or 0),
                "warn_after": report.warns,
                "judged": report.judged,
                "pending": report.pending,
                "not_judgeable": report.not_judgeable,
                "missing_res_code": report.missing_res_code,
                "element_drift": report.element_drift,
            }
        )
    return {
        "baseline_generated_at": str(baseline.get("generated_at") or ""),
        "error_before": sum(int(item["error_before"]) for item in rows),
        "error_after": sum(int(item["error_after"]) for item in rows),
        "warn_before": sum(int(item["warn_before"]) for item in rows),
        "warn_after": sum(int(item["warn_after"]) for item in rows),
        "sites": rows,
    }


def format_comparison(comparison: dict[str, Any]) -> str:
    lines = [
        "== 与基线对照（error / warn 前后）",
        f"   基线 generated_at={comparison['baseline_generated_at']}",
        f"   {'site':<14}{'error前':>8}{'error后':>8}{'warn前':>8}{'warn后':>8}"
        f"{'judged':>8}{'pending':>8}{'不可判定':>9}{'缺res_code':>10}{'五行漂移':>9}",
    ]
    regression: list[str] = []
    for item in comparison["sites"]:
        if int(item["error_after"]) > int(item["error_before"]):
            regression.append(str(item["site"]))
        lines.append(
            f"   {item['site']:<14}{item['error_before']:>8}{item['error_after']:>8}"
            f"{item['warn_before']:>8}{item['warn_after']:>8}{item['judged']:>8}"
            f"{item['pending']:>8}{item['not_judgeable']:>9}"
            f"{item['missing_res_code']:>10}{item['element_drift']:>9}"
        )
    lines.append(
        f"   {'合计':<14}{comparison['error_before']:>8}{comparison['error_after']:>8}"
        f"{comparison['warn_before']:>8}{comparison['warn_after']:>8}"
    )
    if regression:
        lines.append(f"   [注意] 以下站点 error 反而上升，需检查是否新引入噪音：{regression}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("sites", nargs="*", help="站点 key（如 twjsz666），留空表示全部 10 个站点")
    parser.add_argument("--web-id", dest="web_ids", type=int, action="append", default=[],
                        help="按 web_id 指定站点，可重复")
    parser.add_argument("--site", dest="site_keys", action="append", default=[],
                        help="按站点 key 指定站点，可重复")
    parser.add_argument("--mode-id", dest="mode_ids", type=int, action="append", default=[],
                        help="只审计指定 mode_id，可重复（会同时缩小覆盖度自检范围）")
    parser.add_argument("--limit", type=int, default=60,
                        help="每个模式每站点最多审计多少**行**（默认 60；按 term 倒序取最近的行。"
                             "注意同一期可能有多个 type 行，所以 60 行未必是 60 期）")
    parser.add_argument("--json", dest="json_path", default="", help="把结果写入 JSON 文件")
    parser.add_argument(
        "--check-missing-res-code",
        action="store_true",
        help="额外统计「已开奖但行内 res_code 为空」的回填缺口"
             "（只读、不改数据、不影响退出码；只统计本次选中的站点）",
    )
    parser.add_argument("--max-findings", type=int, default=200,
                        help="每个站点最多打印多少条 error 明细（默认 200）")
    parser.add_argument("--baseline", dest="baseline_path", default="",
                        help="与一份历史 JSON 报告对照，打印逐站 error/warn 前后变化"
                             "（只做对照，不改变退出码）")
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
    # 覆盖度衡量的是**工具能力**（工具认不认这个 mode），因此按未被 --mode-id 过滤的全量算。
    coverage = coverage_report(by_mode)
    if args.mode_ids:
        allowed = set(int(item) for item in args.mode_ids)
        by_mode = {mode_id: item for mode_id, item in by_mode.items() if mode_id in allowed}
        configs = {mode_id: item for mode_id, item in configs.items() if mode_id in allowed}

    print(f"=== 预测判定真值校验：{len(targets)} 个站点 / 本次审计 {len(by_mode)} 个机制 / "
          f"{len(draw_index)} 期开奖索引", flush=True)
    if args.mode_ids:
        print(f"    （--mode-id 过滤已生效：只审计 {sorted(by_mode)}）", flush=True)
    if coverage["available"]:
        print(
            f"    覆盖度（不受 --mode-id 过滤影响）：受控 mode "
            f"{coverage['controlled_modes']} 个，工具覆盖 {coverage['tool_modes']} 个，未被覆盖 "
            f"{len(coverage['missing_modes'])} 个"
            + (f" -> {coverage['missing_modes']}" if coverage["missing_modes"] else ""),
            flush=True,
        )
    else:
        print(f"    [warn] 覆盖度自检不可用：{coverage['reason']}", flush=True)

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
            configs=configs,
            limit=max(1, int(args.limit)),
        )
        reports.append(report)
        print(
            f"    {site:<14} rows={report.rows:<7} judged={report.judged:<7} "
            f"error={report.errors:<4} warn={report.warns:<5} info={report.infos:<6} "
            f"pending={report.pending:<5} not_judgeable={report.not_judgeable:<5} "
            f"missing_res_code={report.missing_res_code:<4} element_drift={report.element_drift}",
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
    total_judged = sum(item.judged for item in reports)
    total_pending = sum(item.pending for item in reports)
    total_not_judgeable = sum(item.not_judgeable for item in reports)
    total_missing = sum(item.missing_res_code for item in reports)
    total_drift = sum(item.element_drift for item in reports)
    total_title_fallback = sum(item.title_fallback for item in reports)
    total_tail_multi = sum(item.tail_multi_label for item in reports)
    print(
        f"== 合计 rows={total_rows} judged={total_judged} error={total_error} "
        f"warn={total_warn} info={total_info} | pending={total_pending} "
        f"not_judgeable={total_not_judgeable} missing_res_code={total_missing} "
        f"element_drift={total_drift} title_fallback={total_title_fallback} "
        f"tail_multi_label={total_tail_multi}"
    )
    if total_judged:
        print(f"== 误差率 error/judged = {total_error}/{total_judged} "
              f"= {total_error / total_judged:.4%}")

    # ── 五行分组正文漂移（真数据问题，未修；详见报告说明）──────────
    drift_sites = [item for item in reports if item.element_drift]
    if drift_sites or total_drift:
        print(
            f"== [真数据问题·未修] 五行分组正文与权威号码五行不一致：{total_drift} 行"
            f"（{len(drift_sites)} 个站点）。正文用的是「五行肖/生肖五行」分组，"
            f"判定用的是号码五行；需由数据侧统一，脚本只报告不改口径。"
        )
        for item in drift_sites:
            print(f"     {item.site}: {item.element_drift} 行")
        for sample in (drift_sites[0].drift_samples[:3] if drift_sites else []):
            labels = ", ".join(
                f"{entry['label']}: 正文={entry['declared'][:4]}…/权威={entry['authoritative'][:4]}…"
                for entry in sample["drift"]
            )
            print(
                f"     e.g. mode={sample['mode_id']} {sample['year']}-{sample['term']} "
                f"特码={sample['special_code']} {labels}"
            )

    # ── 候选来自模块名的取证（真口径问题，未修）──────────────────────
    if total_title_fallback:
        agg: dict[str, int] = {}
        for item in reports:
            for key, value in item.title_fallback_by_mode.items():
                agg[key] = agg.get(key, 0) + int(value)
        top = sorted(agg.items(), key=lambda pair: -pair[1])
        print(
            f"== [真口径问题·未修] 候选文本只来自模块名 title：{total_title_fallback} 行"
            f"（{len(agg)} 个机制）。mode 39/68 的标题本身就是预测正文（成语点生肖），"
            "属正常载荷；mode 336 这类数字成语里偶然出现生肖字时，后端会从模块名算出准/错"
            "（如「五马分尸」「四马攒蹄」），需口径负责人逐 mode 决定是否收敛。"
        )
        for key, value in top[:12]:
            print(f"     {key}: {value} 行")

    # ── 平特尾多尾标签的取证（后端只读第一个尾的高风险形态，未修）──────
    if total_tail_multi:
        tail_agg: dict[str, int] = {}
        for item in reports:
            for key, value in item.tail_multi_label_by_mode.items():
                tail_agg[key] = tail_agg.get(key, 0) + int(value)
        top_tail = sorted(tail_agg.items(), key=lambda pair: -pair[1])
        print(
            f"== [后端口径风险·未修] 平特尾里「一个标签串了多个尾原子」：{total_tail_multi} 行"
            f"（{len(tail_agg)} 个机制）。工具已按文档口径摊平成 N尾 原子；"
            "后端 predict.common._tail_digits 对 tuple 元素整串只取**第一个** N尾，"
            "所以当第一个尾不中、后面某个尾命中时后端会漏判（工具报 false_miss = 真漏判）。"
        )
        for key, value in top_tail[:12]:
            print(f"     {key}: {value} 行")

    missing_report = None
    if args.check_missing_res_code:
        missing_report = audit_missing_res_code(conn, draw_index, web_ids=set(targets))
        print(
            f"== res_code 回填缺口：{missing_report['total']} 行"
            f"（已开奖但行内 res_code 为空，页面显示 `??`；仅统计本次选中的站点）"
        )
        for item in missing_report["tables"][:15]:
            print(f"     created.{item['table']}: {item['rows']} 行")
        print(missing_report["suggested_command"])

    comparison = None
    if args.baseline_path:
        try:
            with open(args.baseline_path, encoding="utf-8") as handle:
                baseline = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            print(f"== [warn] 无法读取基线 {args.baseline_path}：{exc}")
        else:
            comparison = compare_with_baseline(baseline, reports)
            print(format_comparison(comparison))

    if args.json_path:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database": os.environ.get("DATABASE_URL", ""),
            "rows": total_rows,
            "judged": total_judged,
            "error": total_error,
            "warn": total_warn,
            "info": total_info,
            "pending": total_pending,
            "not_judgeable": total_not_judgeable,
            "missing_res_code": total_missing,
            "element_drift": total_drift,
            "title_fallback": total_title_fallback,
            "tail_multi_label": total_tail_multi,
            "coverage": coverage,
            "sites": [item.as_dict() for item in reports],
        }
        if missing_report is not None:
            payload["missing_res_code_gap"] = missing_report
        if comparison is not None:
            payload["comparison"] = comparison
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
        print(f"JSON 报告已写入 {args.json_path}")

    return 1 if total_error else 0


if __name__ == "__main__":
    sys.exit(main())
