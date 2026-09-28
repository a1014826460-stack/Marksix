"""Deterministic documentation rendering for future-generation rules."""

from __future__ import annotations

from typing import Any, Iterable

from .generation_rules import get_generation_rule
from .site_page_dependencies import generation_assurance_for_mode


def _display_uniqueness_note(mode_id: int) -> str:
    """标注“相邻连续 N 期展示值不得相同”模式，供规则文档审阅。"""
    from prediction_generation.diversity import (
        THREE_PERIOD_UNIQUE_MODE_IDS,
        display_unique_window,
    )

    resolved_mode_id = int(mode_id or 0)
    if resolved_mode_id not in THREE_PERIOD_UNIQUE_MODE_IDS:
        return ""
    window = display_unique_window(resolved_mode_id)
    return f"adjacent {window} periods: display value differs"


def _unordered_set_note(mode_id: int) -> str:
    """标注“无序号码集合”模式：不做位置轮转，改为按期号的一次性展示置换。

    这些 mode 的 content 是 01-49 号码集合，展示顺序没有语义；旧的“前二唯一”轮转
    在纯号码串上本来就是空转，且会让同一批号码固定占住前几位。
    """
    from prediction_generation.diversity import is_unordered_number_set_mode

    if not is_unordered_number_set_mode(mode_id):
        return ""
    return "unordered number set: no positional rotation; adjacent: display order differs"


def _unordered_set_legend() -> str:
    """图例：说明无序号码集合模式的展示顺序契约（由派生白名单生成）。"""
    from prediction_generation.diversity import (
        UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS,
        unordered_number_set_mode_ids,
    )

    modes = " / ".join(str(mode_id) for mode_id in sorted(unordered_number_set_mode_ids()))
    excluded = " / ".join(
        str(mode_id) for mode_id in sorted(UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS)
    )
    return (
        f"Unordered number-set modules (mode {modes}) never use positional rotation: their `content` "
        "is a set of 01-49 numbers, so the display order is a per-issue permutation of the same "
        "members and the adjacent-period contract is `display order differs` instead of "
        "`full ordered signature`. The set is **derived** from the prediction-config shape "
        "(`parse_number_content` + `contains_hit`/`excludes_hit` + `labels == 01..49`), not hard-coded, "
        "so a newly discovered number-set module is covered without editing a whitelist. "
        f"Contract exceptions (mode {excluded}) keep their stored order because the order itself is the "
        "contract: mode 65 码段12 renders and judges the segment as the inclusive range "
        "`content[0]-content[-1]`."
    )


_SEMANTIC_NOTES: tuple[str, ...] = (
    "\n".join(
        (
            "Wave-label modules (mode 38 双波中特 / mode 143 一波中特) store the candidate as the **wave label** itself",
            "(`蓝波,绿波`, or `[\"蓝波|03,04,…\",\"绿波|05,06,…\"]`), so their `content_parser` must be",
            "`parse_literal_label_content`; `parse_zodiac_content` only recognizes zodiac characters and returns an empty",
            "tuple for wave labels, which made `is_correct` permanently `null` for mode 38 before 2026-09-28.",
            "The special-number wave comes from `res_color` (last value → 红波/蓝波/绿波) with `fixed_data` sign `波色`",
            "as fallback (`predict.categories.size_parity.special_wave_from_row`) and is embedded in the composite outcome",
            "by `public.api._compute_outcome_from_row`.",
        )
    ),
    "\n".join(
        (
            "Half-wave modules (mode 58 绝杀半波 / mode 490 杀两半波) predict the candidate as the **half-wave label**",
            "itself (`蓝双` / `绿单`), so `_compute_outcome_from_row` must also carry the half-wave atom",
            "(`{波色}{单双}` = `蓝双`) next to the wave and parity atoms; without it the `label in outcome` substring",
            "check can never match and `excludes_hit` returns `True` for every row (the whole column was permanently",
            "\"对\" before 2026-09-28).",
        )
    ),
    "\n".join(
        (
            "Mode 492 三头四尾 is a `PredictionCategory.MIXED` play (`头:` / `尾:` label prefixes), so its hit semantics",
            "follow the repo-wide mixed rule — **any dimension hits** (特码头或特尾任一落入对应候选即命中), implemented by",
            "`predict.mechanisms.three_head_four_tail_hit` and mirrored by",
            "`frontend/lib/prediction-contract.ts::verifyVerdictAgainstCandidates`.",
        )
    ),
    "\n".join(
        (
            "Mode 30 单双各4尾 splits its candidate across two columns: `dan` must hold 4 **single** tails",
            "(`1尾/3尾/5尾/7尾/9尾`, each tail at most once) and `shuang` must hold 4 **double** tails",
            "(`0尾/2尾/4尾/6尾/8尾`). The generator draws every tail from its own group",
            "(`predict.common.selection_group_quotas` / `domains.prediction.candidate_control` group quotas),",
            "so `0尾` can never appear in `dan` and `1尾` can never appear in `shuang`.",
        )
    ),
    "\n".join(
        (
            "Mode 251 家野两肖 stores its正文 in the **`title`** column (`家禽|牛,马,羊,鸡,狗,猪` = group|members)",
            "and its candidates in **`xiao`**, whose supplier width is **always 2** (两肖, e.g. `蛇,龙`).",
            "The candidate width must therefore come from the `xiao` column; `parse_pipe_label_content(title)`",
            "splits the **group members** on commas and yields 6, which generated `xiao` with 6 zodiacs per issue",
            "(all webs/types, 200+ rows) and made the renderer print `家禽+6肖`. Fixed on 2026-09-28:",
            "`_classify_second_stage_config` infers the width with `_infer_group_widths(..., (\"xiao\",))`",
            "(`label_count = 2`, same as mode 142 「家野2肖（家野选1，生肖选2）」). Already persisted rows are",
            "**not** rewritten; the compat route takes the width-2 semantic prefix instead.",
        )
    ),
    "\n".join(
        (
            "Mode 116 10码中特（登记日期 2026-09-29）is a dynamic module: its config is discovered from",
            "`mode_payload_tables` as `title_116` (`mode_payload_116`, 10 candidates, `label_count=10`),",
            "so it never appears in the static `PREDICTION_CONFIGS` manifest. Semantics: **特码号码落入候选号码集合即命中**",
            "— `outcome_loader=special_number_from_row`, `content_parser=parse_number_content`,",
            "`hit_checker=contains_hit`. Before registration `get_generation_rule()` returned `blocked_pending_rule`,",
            "so future issues were generated as a silent random 10/49 draw with no rule verification and no rolling",
            "hit-rate control. Cross-site prefix width is **2** (same family shape as mode 77 14码中特; mode 34 24码 uses 3):",
            "10 ordered pairs = 90 distinct prefixes, which is satisfiable for the handful of sites enabled per issue.",
            "Mode 116 is also an unordered number-set module, but the display permutation is applied **only when",
            "`control_plan is None`** (`prediction_generation.service`), so a controlled row is persisted in exactly the",
            "order whose prefix was reserved — the cross-site prefix contract and the adjacent-period full-signature",
            "contract stay valid.",
        )
    ),
    "\n".join(
        (
            "Number-set modules (mode 9 16码 / 34 24码 / 77 14码中特 / 88 杀7码 / 116 10码中特 / 481 稳杀10码 /",
            "485 内幕5不中 / 493 精选22码 / 494 稳杀7码) store `content` as a comma-separated set of `01`-`49` numbers.",
            "Their display order carries no semantics — every renderer judges by set membership (`contains` for the",
            "inclusion family, `excludes` for the 杀/不中 family) and highlights the matching number by membership, so a",
            "permutation of the same members cannot change any verdict. `prediction_generation.diversity` therefore",
            "**derives** the module set from the config shape (`parse_number_content` + `contains_hit`/`excludes_hit` +",
            "`labels == 01..49` + `label_count` inside the label space) instead of maintaining a hand-written whitelist;",
            "`UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS` holds the contract exceptions, currently mode 65",
            "码段12 and mode 156 杀码段（13连码）: their front end renders and judges the candidate as the inclusive range",
            "`content[0]-content[-1]`, so permuting the members would break both the displayed segment and its verdict.",
            "Controlled rows (`control_plan is not None`) skip `enforce_prediction_diversity` entirely, so a reserved",
            "cross-site `prefix_signature` always equals the first `cross_site_prefix_width` numbers of the persisted row.",
        )
    ),
    "\n".join(
        (
            "Mode 65 码段12 / 特码段 is **deliberately left unregistered** in `generation_rules._RULE_BY_MODE_ID`.",
            "It looks like the sibling number-set family (`mode_payload_65`, 12 candidates, `parse_number_content`,",
            "`contains_hit`, `label_count=12`), but its candidate is a **contiguous ascending segment** (`01`-`12`,",
            "`13`-`24`, `25`-`36`, `37`-`49`) because the front end renders and judges it as the inclusive range",
            "`content[0]-content[-1]` (`shengshi8800/static/js/016teduan.js` and",
            "`legacy-prediction-verdict.js::verdictOf(65, …)`, which is order-sensitive and therefore also listed in",
            "`UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS`). The generic `number` rule would let",
            "`candidate_control` emit any 12-subset of `01`-`49`, which would render a meaningless range",
            "(e.g. `01-42` covering numbers that are not candidates) and would change the verdict; registering it",
            "would therefore make the displayed segment inconsistent with the verified rule. Mode 65 is instead served",
            "by its dedicated row generator `prediction_generation.service._generate_mode_65_row`, which already derives",
            "the segment from the truth and honours the target hit/miss decision, so future rows are correct without a",
            "generic rule.",
        )
    ),
)


def _semantic_notes() -> str:
    """审阅用的候选形态说明（纯静态文本，不含任何开奖真值）。

    返回值以换行结尾：渲染器把每个 block 直接作为列表项拼接，末尾多一个 `\\n` 才能让
    说明段落与清单表格之间**恰好**保留一行空行（与既有生成文档保持一致，避免每次
    重新生成都产生空白行噪声）。空项会被过滤，历史上 mode 251 的段落是手写进文档的，
    重新生成会丢。
    """
    notes = [note for note in _SEMANTIC_NOTES if note]
    return "\n\n".join(notes) + "\n"


def _outcome_description(rule_id: str) -> str:
    descriptions = {
        "zodiac": "special zodiac is in any candidate",
        "zodiac_flat": "any drawn number's zodiac is in any candidate",
        "tail_flat": "any drawn number's tail is in any candidate",
        "zodiac_exclusion": "special zodiac is absent from every candidate",
        "number": "special number is in any candidate",
        "number_exclusion": "special number is absent from every candidate",
        "head": "special number head is in any candidate",
        "tail": "special number tail is in any candidate",
        "tail_exclusion": "special number tail is absent from every candidate",
        "size": "special number size is in any candidate",
        "parity": "special number parity is in any candidate",
        "wave": "special number wave is in any candidate",
        "half_wave_exclusion": "special half-wave is absent from every candidate",
        "head_tail": "special number head OR tail is in its candidate group (mixed: any dimension)",
        "combined_parity": "special digit-sum parity is in any candidate",
        "combined_size": "special digit-sum size is in any candidate",
        "blocked_pending_rule": "blocked_pending_rule",
    }
    return descriptions.get(rule_id, rule_id)


def _dynamic_registered_mode_rows(configs: Iterable[Any]) -> list[tuple[int, str, str, Any]]:
    """登记了受控规则、但**不在本次配置清单**里的动态玩法。

    `PREDICTION_CONFIGS` 只维护静态玩法；像 `title_116`（10码中特）这样的动态配置由
    `predict.registry_builder` 在运行时从 `mode_payload_tables` 发现，永远不会出现在
    静态清单里。如果文档只渲染传入的 configs，这些**已经放行受控生成**的 mode 就会从
    审阅清单里消失（mode 116 登记前后都是这个状态，审阅者无从发现）。

    这里以 `generation_rules` 的登记表为准补一份清单：只列出「已登记且受控」的 mode，
    不含任何开奖真值、也不依赖数据库里是否存在该表，因此文档保持确定性。
    """
    from .generation_rules import RULE_BY_MODE_ID

    present = {
        int(getattr(config, "default_modes_id", 0) or 0)
        for config in configs
    }
    present.discard(0)
    rows: list[tuple[int, str, str, Any]] = []
    for mode_id, key, title in _DYNAMIC_MODE_METADATA:
        rule = RULE_BY_MODE_ID.get(mode_id)
        if rule is None or not rule.supported or mode_id in present:
            continue
        rows.append((mode_id, key, title, _dynamic_mode_config(mode_id, key, title)))
    return rows


#: 动态登记表里需要进入审阅文档的 module 元数据（title 允许为空）。
_DYNAMIC_MODE_METADATA: tuple[tuple[int, str, str], ...] = (
    (9, "title_9", "16码"),
    (88, "title_88", "杀7码"),
    (116, "title_116", "10码中特"),
)


def _dynamic_mode_config(mode_id: int, key: str, title: str) -> Any:
    """只需要 `default_modes_id` / `title` / `key` 的轻量载体。

    渲染器只按 `default_modes_id` 查规则登记表与 assurance，不读 content/labels，
    因此这里不连数据库也能给出确定性的审阅行。
    """
    from types import SimpleNamespace

    return SimpleNamespace(key=key, title=title, default_modes_id=mode_id)


def render_prediction_module_rules(configs: Iterable[Any]) -> str:
    """Render the registered rules without exposing any future draw information."""
    configs = list(configs)
    rows: list[tuple[int, str, str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for config in configs:
        mode_id = int(getattr(config, "default_modes_id", 0) or 0)
        key = str(getattr(config, "key", "") or "")
        identity = (mode_id, key)
        if identity in seen:
            continue
        seen.add(identity)
        rows.append((mode_id, key, str(getattr(config, "title", "") or ""), config))

    rows.extend(_dynamic_registered_mode_rows(configs))

    lines = [
        "# Prediction Module Future-Generation Rules",
        "",
        "This document is generated from the internal rule manifest. It documents candidate semantics only and never contains future draw values.",
        "",
        _unordered_set_legend(),
        "",
        _semantic_notes(),
        "| mode_id | key | title | rule | outcome semantics | assurance | future control | uniqueness |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for mode_id, key, title, config in sorted(rows, key=lambda item: (item[0], item[1])):
        rule = get_generation_rule(config)
        status = "supported" if rule.supported else f"blocked: {rule.block_reason}"
        assurance = generation_assurance_for_mode(mode_id)
        uniqueness = f"cross-site prefix: {rule.cross_site_prefix_width}; adjacent: full ordered signature"
        unordered_note = _unordered_set_note(mode_id)
        if unordered_note:
            uniqueness = f"cross-site prefix: {rule.cross_site_prefix_width}; {unordered_note}"
        display_note = _display_uniqueness_note(mode_id)
        if display_note:
            uniqueness = f"{uniqueness}; {display_note}"
        lines.append(
            f"| {mode_id} | {key} | {title} | {rule.rule_id} | "
            f"{_outcome_description(rule.rule_id)} | {assurance} | {status} | {uniqueness} |"
        )
    return "\n".join(lines) + "\n"


def write_prediction_module_rules(path: str, configs: Iterable[Any]) -> None:
    """Write the deterministic document using UTF-8 without exposing truth data."""
    from pathlib import Path

    Path(path).write_text(render_prediction_module_rules(configs), encoding="utf-8")
