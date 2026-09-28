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


def _candidate_sequences(
    *,
    predicted_labels: tuple[str, ...],
    available_labels: tuple[str, ...],
    width: int,
    seed: str,
    max_candidates: int = 32768,
    selection_quotas: tuple[tuple[tuple[str, ...], ...], tuple[int, ...]] | None = None,
) -> Iterator[tuple[str, ...]]:
    """Yield a deterministic, bounded stream without materializing combinatorics.

    当配置声明了互斥候选域（``selection_quotas``）时，只产出「每组恰好取出本组配额」
    的候选：``单双各4尾`` 意味着 4 个单尾 + 4 个双尾，不会产出 3 个单尾 + 1 个双尾
    这类越界组合。

    配额是「每组取几个」，不是「把整组都取走」：``单双各4尾`` 的单尾域有 5 个尾数，
    必须允许「取哪 4 个单尾」也有选择，否则要求「不中」时（特码尾是奇数尾）会被
    钉死在必然命中的 5 选 4 上，受控候选直接耗尽。
    """
    limit = max(1, int(max_candidates))
    emitted: set[tuple[str, ...]] = set()

    def emit(candidate: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
        if len(emitted) >= limit or len(candidate) != width or candidate in emitted:
            return
        emitted.add(candidate)
        yield candidate

    baseline = _ordered_unique(predicted_labels)
    if len(baseline) == width:
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
    _rng(seed).shuffle(pool)
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
    for labels in _candidate_sequences(
        predicted_labels=tuple(predicted_labels),
        available_labels=available_labels,
        width=width,
        seed=seed,
        selection_quotas=selection_quotas,
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
