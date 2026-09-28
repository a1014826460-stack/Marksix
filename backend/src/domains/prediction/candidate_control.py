"""Deterministic reselection of legal future prediction candidates."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass
from typing import Any, Iterator

from .generation_rules import PredictionGenerationRule
from .models import DrawTruth


class ControlledCandidateUnavailable(ValueError):
    """No candidate can satisfy the verified rule and uniqueness constraints."""


@dataclass(frozen=True)
class ControlledCandidate:
    labels: tuple[str, ...]
    signature: tuple[str, ...]
    prefix_signature: tuple[str, ...]
    verified_hit: bool


def _rng(seed: str) -> random.Random:
    value = int(hashlib.sha256(str(seed).encode("utf-8")).hexdigest(), 16) % (2**32)
    return random.Random(value)


def signature_hash(values: tuple[str, ...]) -> str:
    """Hash a canonical candidate signature for comparison with ledger reservations."""
    payload = json.dumps([str(value) for value in values], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _group_ordered_permutations(
    baseline: tuple[str, ...],
    quotas: tuple[tuple[tuple[str, ...], ...], tuple[int, ...]],
) -> Iterator[tuple[str, ...]]:
    """在**不跨分组**的前提下枚举 baseline 的顺序变体。

    baseline 本身已经按分组顺序选好（``score_labels`` 的输出），因此这里只做
    「每组内部重排」：``单双各4尾`` 的单尾位置永远只放单尾，不会把双尾换到单尾列。
    与分组配额不匹配时（例如某组元素个数不等于该组配额）不产出任何变体。
    """
    groups, widths = quotas
    blocks: list[list[str]] = []
    offset = 0
    for group, width in zip(groups, widths):
        block = list(baseline[offset:offset + width])
        offset += width
        if len(block) != width or any(label not in group for label in block):
            return
        blocks.append(block)
    if offset != len(baseline):
        return
    for combination in itertools.product(*(itertools.permutations(block) for block in blocks)):
        yield tuple(label for block in combination for label in block)


def _selection_groups(config: Any) -> tuple[tuple[tuple[str, ...], ...], tuple[int, ...]] | None:
    """返回可安全限域的「分组候选域 + 每组配额」。

    判据与 ``predict.common.selection_group_quotas`` 一致：各分组互不重叠、
    并集恰好等于配置的候选全域，且配额之和等于本次要选出的候选数。
    ``单双各4尾``（mode 30）满足：labels = 0尾..9尾，
    selection_groups = (单尾域, 双尾域)，配额 (4, 4)，两种落库列为 ``dan`` / ``shuang``。
    有些玩法（``家野4肖`` 等）的 labels 是全体生肖、分组互相重叠，此时返回 None，
    调用方退回不限域的历史行为。
    """
    groups = getattr(config, "selection_groups", None)
    widths = getattr(config, "selection_widths", None)
    if not groups or not widths or len(groups) != len(widths):
        return None
    normalized = tuple(tuple(str(label) for label in group) for group in groups)
    if any(not group for group in normalized):
        return None
    flattened = [label for group in normalized for label in group]
    if len(set(flattened)) != len(flattened):
        return None  # 分组互相重叠，位置无法归组
    labels = tuple(str(label) for label in (getattr(config, "labels", ()) or ()))
    if labels and set(flattened) != set(labels):
        return None
    resolved_widths = tuple(max(0, int(width)) for width in widths)
    label_count = int(getattr(config, "label_count", 0) or 0)
    if label_count and sum(resolved_widths) != label_count:
        return None
    return normalized, resolved_widths


def _loader_row_from_truth(truth: DrawTruth) -> dict[str, Any]:
    """把 ``DrawTruth`` 适配成 ``config.outcome_loader`` 期望的「开奖行」字典。

    各玩法的 ``outcome_loader`` 历史签名是 ``loader(row, conn)``（例如
    ``special_number_from_row`` 读 ``row["res_code"]``），而受控生成手里只有
    ``DrawTruth``。这里按同样的数据口径拼一个最小行：``res_code`` 的最后一个号码是特码，
    ``res_sx`` / ``res_color`` 分别承载 7 个号码的生肖串与特码波色。
    只用于解析「真实目标标签」，不落库、不出域、不写日志。
    """
    numbers = tuple(str(code) for code in (truth.numbers or ()) if str(code).strip())
    special = str(truth.special_code or "").strip()
    codes = list(numbers)
    if special and (not codes or codes[-1] != special):
        codes.append(special)
    zodiacs = tuple(str(value) for value in (truth.draw_zodiacs or ()))
    return {
        "res_code": ",".join(codes),
        "res_sx": ",".join(zodiacs),
        "res_color": str(truth.special_color or ""),
        "numbers": codes,
    }


def label_for_truth_outcome(config: Any, truth: DrawTruth, *, conn: Any = None) -> str | None:
    """把规则的真实命中目标解析成一个候选标签（解析不出来时返回 ``None``）。

    受控生成需要知道「哪个候选标签能让 ``verify_hit`` 成立」。多数玩法可以直接从
    ``config.outcome_loader`` 得到标签（号码/尾数/头数/生肖/波色…都是标签本身）；
    ``MIXED`` 之类的复合口径拿不到单一标签，此时返回 ``None``，调用方保持历史行为。
    """
    if not callable(getattr(config, "hit_checker", None)):
        return None
    loader = getattr(config, "outcome_loader", None)
    if not callable(loader):
        return None
    try:
        outcome = str(loader(_loader_row_from_truth(truth), conn) or "").strip()
    except Exception:  # noqa: BLE001 - 口径无法解析时不做定向搜索
        return None
    if not outcome:
        return None
    available = {str(label) for label in (getattr(config, "labels", ()) or ())}
    return outcome if outcome in available else None


#: 排除（杀号/不中）口径的规则 id：**命中**要求真实目标*离开*候选集合。
_EXCLUSION_RULE_IDS: frozenset[str] = frozenset(
    {
        "number_exclusion",
        "zodiac_exclusion",
        "tail_exclusion",
        "half_wave_exclusion",
    }
)


def _truth_must_be_in_candidate(rule: PredictionGenerationRule) -> bool:
    """「命中」是否要求真实目标**进入**候选集合。

    - 包含类规则（`number` / `zodiac` / `tail` / `head` …）：命中 = truth ∈ candidate → ``True``；
    - 排除类规则（`number_exclusion` / `zodiac_exclusion` / …）：命中 = truth ∉ candidate → ``False``；
    - 无法判定的规则（`blocked_pending_rule`、复合 `head_tail` 等，此时
      `label_for_truth_outcome` 通常也拿不到单一目标）：按包含类处理，与历史行为一致。

    方向判断必须按规则口径，而不是「真值是否在 baseline 里」——后者会把排除类玩法
    当成包含类，让 `_candidate_sequences` 的定向修复永远落在错误方向上
    （mode 88/481/485/494 实测 `candidate_space_exhausted`）。
    """
    return str(getattr(rule, "rule_id", "")) not in _EXCLUSION_RULE_IDS


def _candidate_sequences(
    *,
    predicted_labels: tuple[str, ...],
    available_labels: tuple[str, ...],
    width: int,
    seed: str,
    max_candidates: int = 32768,
    selection_quotas: tuple[tuple[tuple[str, ...], ...], tuple[int, ...]] | None = None,
    required_truth: str | None = None,
    should_hit: bool | None = None,
    truth_must_be_in_candidate: bool = True,
) -> Iterator[tuple[str, ...]]:
    """Yield a deterministic, bounded stream without materializing combinatorics.

    当配置声明了互斥候选域（``selection_quotas``）时，只产出「每组恰好取出本组配额」
    的候选：``单双各4尾`` 意味着 4 个单尾 + 4 个双尾，不会产出 3 个单尾 + 1 个双尾
    这类越界组合。

    配额是「每组取几个」，不是「把整组都取走」：``单双各4尾`` 的单尾域有 5 个尾数，
    必须允许「取哪 4 个单尾」也有选择，否则要求「不中」时（特码尾是奇数尾）会被
    钉死在必然命中的 5 选 4 上，受控候选直接耗尽。

    ``required_truth`` / ``should_hit`` / ``truth_must_be_in_candidate`` 是**可达性修复**
    （2026-09-29）：候选是「有序元组」，预算 ``max_candidates`` 又很小（默认 32768），
    因此当 ``predicted_labels`` 恰好等于候选宽度时，历史实现会把整个预算花在 baseline 的
    ``width!`` 个排列上，一个成员不同的组合都产不出来。于是所有宽号码玩法
    （mode 9/34/77/88/116/481/485/493/494…）会以两种方式「受控名存实亡」：

    1. 「需要命中、但真实特码不在 baseline 里」：mode 116 实测宽 10 时前 32768 个候选里
       含特码的数量为 **0**，必然 ``candidate_space_exhausted``；
    2. 「baseline 已在正确一侧」：预算同样被同一组号码的排列吃光，首号恒为 baseline 首号，
       mode 9 实测宽 16 时连取 60 个候选只有 **1** 个不同前缀；同一期第二个站点带
       forbidden 前缀重选会直接 ``candidate_space_exhausted``，跨站前缀契约名存实亡。

    两种情况都会让生成侧回落到随机 fallback（"strict candidate constraints were relaxed"）。
    因此定向分支（``directed``，宽度 ≥ 2 且未声明互斥候选域）统一改用
    ``directed_candidates()``：真值按规则口径进入/离开候选，首号遍历候选池，
    前缀签名互不相同。其余情况（含宽度 1 的二元玩法、限域玩法）保持历史枚举顺序。
    """
    limit = max(1, int(max_candidates))
    emitted: set[tuple[str, ...]] = set()

    def emit(candidate: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
        if len(emitted) >= limit or len(candidate) != width or candidate in emitted:
            return
        emitted.add(candidate)
        yield candidate

    baseline = _ordered_unique(predicted_labels)

    def baseline_candidates() -> Iterator[tuple[str, ...]]:
        if len(baseline) != width:
            return
        yield from emit(baseline)
        if selection_quotas is not None:
            # 限域模式的 baseline 变体必须「组内重排」，否则会把双尾换进单尾列。
            for candidate in _group_ordered_permutations(baseline, selection_quotas):
                yield from emit(candidate)
                if len(emitted) >= limit:
                    return
        else:
            for candidate in itertools.permutations(baseline):
                yield from emit(tuple(candidate))
                if len(emitted) >= limit:
                    return

    pool = list(_ordered_unique(available_labels))
    #: 「命中」到底要求真值**进入**候选还是**离开**候选，取决于规则口径：
    #: `number` / `zodiac`（包含类）要求 candidate ∋ truth；
    #: `number_exclusion` / `zodiac_exclusion`（排除/杀号类）要求 candidate ∌ truth。
    #: 旧实现只按「真值是否已在 baseline 里」判断方向，等于把排除类玩法当成包含类，
    #: 于是 mode 88/481/485/494 这类杀号玩法在需要命中时被喂进含真值的候选
    #: （`verify_hit` 必然 False，直接 `candidate_space_exhausted`），
    #: 在需要不中时又拿不到含真值的候选——定向修复对它们从来没生效过。
    required_truth_in_candidate = bool(truth_must_be_in_candidate)
    desired_inclusion = bool(should_hit) == required_truth_in_candidate
    directed = bool(
        required_truth
        and should_hit is not None
        and len(baseline) == width
        # 宽度 1 的玩法（大/小、单/双、绝杀一肖…）候选域本身就只有 1 个位，展示顺序
        # 与前缀都没有变化空间：这类玩法继续走历史的「允许重复前缀」兜底
        # （`test_control_plan_reuses_prefix_when_binary_future_mode_is_exhausted`）。
        and width >= 2
        # 声明了互斥候选域（单双各4尾等）时不能走定向重排：候选必须满足「每组恰好取出
        # 本组配额」，而按池首/首号重排会跨组串位（实测 mode 30 直接
        # `candidate_space_exhausted`）。这类玩法继续走历史配额枚举。
        and selection_quotas is None
    )
    if directed:
        # 历史预算会被 baseline 的 width! 个排列吃光，导致成员/前缀完全固定的候选流。
        # 两个方向都要重排：
        #   1. 要求真值**进入**候选（包含类命中 / 排除类不中）：池首放真值，
        #      保证 `combinations(pool, width)` 的每个组合都含真值；
        #   2. 要求真值**离开**候选（包含类不中 / 排除类命中）：把真值移出池。
        if not desired_inclusion:
            pool = [label for label in pool if label != required_truth]
        _rng(seed).shuffle(pool)
        if desired_inclusion:
            pool = [required_truth, *(label for label in pool if label != required_truth)]
    else:
        _rng(seed).shuffle(pool)

    def directed_candidates() -> Iterator[tuple[str, ...]]:
        """定向分支下「前缀多样化」的候选流（真值位置固定、首号遍历候选池）。

        为什么不能直接用 `baseline_candidates()` + `pool_candidates()`：

        - **需要命中但 baseline 缺真值**（mode 116 的线上形态）：`baseline` 的成员集合
          与目标方向相反，`width!` 个排列把预算（默认 32768）吃光，一个含真值的候选都
          产不出来 → `candidate_space_exhausted`。
        - **需要命中且 baseline 已含真值**（mode 9/34/77 的线上形态）：`baseline` 的成员
          集合是对的，但 `pool_candidates()` 会先枚举同一组号码的 `width!` 个排列，
          于是首号恒为 baseline 首号——实测 mode 9 连取 60 个候选只有 **1** 个不同前缀，
          第二个站点必然拿到重复 `prefix_hash`：`_plan_persisted_future_control` 带
          forbidden 前缀重选会直接 `candidate_space_exhausted`，生成侧回落到
          「strict candidate constraints were relaxed」的随机 fallback。跨站前缀契约
          同样名存实亡。

        这里的候选形状统一为：``[首号, 真值?, 肩部…]``。
        - 要求真值进入候选（包含类命中 / 排除类不中）：``首号 + 真值 + (width-2)`` 个
          肩部号码；
        - 要求真值离开候选（包含类不中 / 排除类命中）：``首号 + (width-1)`` 个肩部号码
          （池里已经没有真值）。

        首号逐个取自池中其它号码，因此前缀签名互不相同（49 个号码的池可给出 48 个互不
        重复的前缀），足以覆盖同一期的全部启用站点并留出重试余量。

        该函数只在「历史实现必然失败/失焦」的定向分支被调用：既有 mode 的候选选择不变，
        新增的只是「以前拿不到」的那些方向正确的候选。
        """
        ordered_pool = list(pool)
        #: 首号与肩部都取自池中真值以外的号码：**每个候选的首号都不同**，因此同一期的
        #: 两个站点必然拿到不同的前缀签名——首个候选就能通过 `reserve_control` 的
        #: prefix_hash 校验，不会像「池首组合优先」那样让第二个站点直接
        #: `candidate_space_exhausted`（mode 9 实测：池首优先时 60 个候选只有 1 个前缀）。
        #: 要求真值进入候选时，真值固定落在第二个位置（`desired_inclusion`）。
        shoulders_pool = [label for label in ordered_pool if label != required_truth]
        if len(ordered_pool) < width or not shoulders_pool:
            return
        seed_rng = _rng(f"{seed}:directional-variants")
        shoulder_count = width - 1 - (1 if desired_inclusion else 0)
        if shoulder_count < 1:
            return
        for leader_index, leader in enumerate(shoulders_pool):
            shoulders: list[str] = []
            offset = 0
            while len(shoulders) < shoulder_count and offset < len(shoulders_pool):
                candidate_label = shoulders_pool[(leader_index + offset) % len(shoulders_pool)]
                offset += 1
                if candidate_label != leader and candidate_label not in shoulders:
                    shoulders.append(candidate_label)
            if len(shoulders) < shoulder_count:
                return
            if seed_rng.randrange(2):
                shoulders = shoulders[1:] + shoulders[:1]
            body = [required_truth, *shoulders] if desired_inclusion else list(shoulders)
            yield from emit(tuple([leader, *body]))
            if len(emitted) >= limit:
                return

    def pool_candidates() -> Iterator[tuple[str, ...]]:
        if selection_quotas is not None:
            groups, widths = selection_quotas
            group_permutations: list[Iterator[tuple[str, ...]]] = []
            for group, group_width in zip(groups, widths):
                members = [label for label in pool if label in group]
                if len(members) < group_width:
                    # 某一组的候选不足以填满配额：退回不限域枚举，让命中校验自己去筛。
                    return
                group_permutations.append(
                    itertools.permutations(members, group_width),
                )
            # 先枚举每组「取哪几个 + 组内顺序」（partial permutation），再按组顺序拼接；
            # 配额天然固定，因此任何产出都满足分组候选域。
            for combination in itertools.product(*group_permutations):
                ordered = [label for block in combination for label in block]
                yield from emit(tuple(ordered))
                if len(emitted) >= limit:
                    return
            return

        for combination in itertools.combinations(pool, width):
            for candidate in itertools.permutations(combination):
                yield from emit(tuple(candidate))
                if len(emitted) >= limit:
                    return

    if directed:
        # 定向修复只在历史行为必然失败/失焦时才接管候选流。
        # 两个方向都用 `directed_candidates()`：真值位置固定（进入/离开候选），
        # 首号遍历候选池，因此跨站前缀互不相同。
        # **不要**枚举 `baseline_candidates()`：baseline 的成员集合（在「需要命中但缺真值」
        # 情形下）与目标方向相反，而且它的 `width!` 个排列会把预算吃光；
        # **也不要**直接枚举 `pool_candidates()`：它先产出同一组号码的排列，
        # 首号被 baseline 钉死（mode 9 实测 60 个候选只有 1 个前缀）。
        yield from directed_candidates()
        return

    yield from baseline_candidates()
    if len(emitted) >= limit:
        return
    yield from pool_candidates()


def choose_controlled_labels(
    *,
    config: Any,
    rule: PredictionGenerationRule,
    truth: DrawTruth,
    predicted_labels: tuple[str, ...],
    should_hit: bool,
    forbidden_prefixes: set[tuple[str, ...]],
    forbidden_signatures: set[tuple[str, ...]],
    seed: str,
    conn: Any = None,
    forbidden_prefix_hashes: set[str] | None = None,
    forbidden_signature_hashes: set[str] | None = None,
) -> ControlledCandidate:
    """Select a rule-verified candidate that does not collide with reserved signatures."""
    if not rule.supported:
        raise ControlledCandidateUnavailable(
            f"mode_id={int(getattr(config, 'default_modes_id', 0) or 0)}: unsupported_rule"
        )

    width = max(1, int(getattr(config, "label_count", 0) or len(predicted_labels) or 1))
    available_labels = tuple(getattr(config, "labels", ()) or ())
    selection_quotas = _selection_groups(config)
    # 定向搜索提示：真实目标标签 + 本期要求的方向 + 规则口径（包含/排除）。
    truth_label = label_for_truth_outcome(config, truth, conn=conn)
    for labels in _candidate_sequences(
        predicted_labels=tuple(predicted_labels),
        available_labels=available_labels,
        width=width,
        seed=seed,
        selection_quotas=selection_quotas,
        required_truth=truth_label,
        should_hit=bool(should_hit) if truth_label else None,
        truth_must_be_in_candidate=_truth_must_be_in_candidate(rule),
    ):
        signature = rule.signature(labels)
        prefix = rule.prefix_signature(labels)
        if (
            signature in forbidden_signatures
            or prefix in forbidden_prefixes
            or signature_hash(signature) in (forbidden_signature_hashes or set())
            or signature_hash(prefix) in (forbidden_prefix_hashes or set())
        ):
            continue
        verified_hit = rule.verify_hit(config, labels, truth, conn=conn)
        if verified_hit == bool(should_hit):
            return ControlledCandidate(
                labels=labels,
                signature=signature,
                prefix_signature=prefix,
                verified_hit=verified_hit,
            )

    raise ControlledCandidateUnavailable(
        f"mode_id={int(getattr(config, 'default_modes_id', 0) or 0)}: candidate_space_exhausted"
    )
