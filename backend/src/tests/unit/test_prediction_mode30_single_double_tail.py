"""mode 30「单双各4尾」候选域契约。

用户规则（2026-09-28 投诉）
-------------------------
「单双四尾」= 4 个单尾 + 4 个双尾，**尾数**的单双：

- `dan`（单尾）只能取 ``{1,3,5,7,9}``；
- `shuang`（双尾）只能取 ``{0,2,4,6,8}``；
- 两列各 4 个、8 个候选互不重复。

线上违约证据（`/api/kaijiang/getDsWei?web=6&type=3&num=4` 与本地 `created.mode_payload_30`）：

- 184 期 `dan=3,9,7,0`（把偶尾 0 写进单尾）
- 166 期 `dan=0,9,5,1`、179/208/213 期 `shuang` 里出现 7/1

根因：mode 30 没有登记进 ``domains.prediction.generation_rules``，
未来期走 silent fallback（通用 `predict()`），而 `predict()` 的「未来期差异保证」
在 ``predicted_labels`` 上随机挑一个位置、再从**全量标签池**里随机替换，
绕过了 `score_labels` 的 `selection_groups` 限额。受控生成路径
（`candidate_control.choose_controlled_labels`）同样只按总宽枚举，不按分组配额。

本文件钉死三点：
1. mode 30 已登记为受控规则（`tail` / `supported`），不会再走 silent fallback；
2. `predict()` 的种子替换留在本位置所属分组内（单尾位置只换成奇数尾）；
3. 受控候选取值严格按分组配额（4 单尾 + 4 双尾）。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from types import SimpleNamespace

from domains.prediction.candidate_control import (
    _candidate_sequences,
    _selection_groups,
    choose_controlled_labels,
)
from domains.prediction.generation_rules import get_generation_rule
from domains.prediction.models import DrawTruth
from predict.common import predict, selection_group_quotas
from predict.mechanisms import get_prediction_config

MODE_ID = 30
SINGLE_TAILS = {"1", "3", "5", "7", "9"}
DOUBLE_TAILS = {"0", "2", "4", "6", "8"}
#: 历史样本形状的 baseline（`score_labels` 按分组顺序产出：先单尾后双尾）
BASELINE = ("9尾", "3尾", "7尾", "1尾", "8尾", "6尾", "2尾", "4尾")


def _tails(value: str) -> list[str]:
    return [item.strip().removesuffix("尾") for item in str(value or "").split(",") if item.strip()]


def _assert_split_compliant(content: dict[str, str]) -> None:
    dan = _tails(content["dan"])
    shuang = _tails(content["shuang"])
    assert len(dan) == 4, content
    assert len(shuang) == 4, content
    assert len(set(dan) | set(shuang)) == 8, content
    assert set(dan) <= SINGLE_TAILS, f"单尾出现偶尾: {content}"
    assert set(shuang) <= DOUBLE_TAILS, f"双尾出现奇尾: {content}"


def test_mode_30_is_registered_as_a_supported_tail_rule():
    """mode 30 必须登记为受控规则，否则未来期会走 silent fallback。"""
    config = get_prediction_config("title_30")
    assert int(config.default_modes_id) == MODE_ID
    assert config.default_table == "mode_payload_30"
    assert config.label_count == 8

    rule = get_generation_rule(config)
    assert rule.supported is True
    assert rule.rule_id == "tail"
    assert rule.block_reason == ""
    # 跨站前缀宽度沿用尾数类玩法的默认值
    assert rule.cross_site_prefix_width == 1


def test_mode_30_declares_disjoint_single_and_double_tail_groups():
    """配置必须声明互不重叠的单尾/双尾候选域，且配额之和 = 候选总数。"""
    config = get_prediction_config("title_30")
    groups = config.selection_groups
    widths = config.selection_widths

    assert groups == (
        ("1尾", "3尾", "5尾", "7尾", "9尾"),
        ("0尾", "2尾", "4尾", "6尾", "8尾"),
    )
    assert widths == (4, 4)
    assert sum(widths) == config.label_count

    # 分组可划分：并集 = 候选全域、组间无交集
    flattened = [label for group in groups for label in group]
    assert len(set(flattened)) == len(flattened)
    assert set(flattened) == set(config.labels)
    assert selection_group_quotas(groups, widths, tuple(config.labels)) is not None


def test_mode_30_config_is_group_quota_eligible():
    """`_selection_groups` 必须能识别 mode 30 的分组配额（受控候选限域的前提）。"""
    config = get_prediction_config("title_30")
    quotas = _selection_groups(config)
    assert quotas is not None
    groups, widths = quotas
    assert widths == (4, 4)
    assert set(groups[0]) == {f"{tail}尾" for tail in SINGLE_TAILS}
    assert set(groups[1]) == {f"{tail}尾" for tail in DOUBLE_TAILS}


@dataclass
class _EmptySourceStub:
    """`predict()` 只需要一个「源表不存在、没有历史」的连接占位。

    所有查询都返回空结果，因此 `load_history` 是空表：`score_labels` 落到
    「全部标签同分 + random」的常规路径，随后走的就是真实代码里的
    「未来期差异保证」替换逻辑——正是本缺陷所在。
    """

    target: str = "stub-empty-source"
    queries: list[str] = field(default_factory=list)

    def table_exists(self, _name: str) -> bool:
        return False

    def execute(self, query: str, _params=None):
        self.queries.append(str(query or ""))
        return _EmptyCursor()

    def __enter__(self) -> "_EmptySourceStub":
        return self

    def __exit__(self, *_args) -> None:
        return None


class _EmptyCursor:
    def fetchone(self):
        return None

    def fetchall(self):
        return []


def _format_content(config, seed: str) -> dict[str, str]:
    """离线跑真实 `predict()`，返回 mode 30 的双列 content。"""
    result = predict(
        config=config,
        res_code=None,
        source_table=config.default_table,
        db_path="stub-empty-source",
        target_hit_rate=0.5,
        random_seed=seed,
        conn=_EmptySourceStub(),
    )
    return result["prediction"]["content"]


def test_generic_predict_seeded_replacement_stays_inside_the_group():
    """`predict()` 的「未来期差异保证」替换不得越过分组边界。

    修复前：`dan` 位置被随机换成全量标签池里的任意尾数，实测 166 期 `dan=0,9,5,1`、
    184 期 `dan=3,9,7,0`。
    """
    config = get_prediction_config("title_30")

    for seed in [f"2026{term:03d}" for term in range(150, 350)]:
        content = _format_content(config, seed)
        _assert_split_compliant(content)


def test_unguarded_predict_path_is_also_group_scoped():
    """没有 random_seed 的通用分支同样必须按分组限域。

    非台湾彩（无未来期真值）走的就是这条分支：`score_labels` 的 `selection_groups`
    只能管住初始选取，分支里的替换/随机化必须自己限域。
    """
    config = get_prediction_config("title_30")
    random.seed(20260928)
    result = predict(
        config=config,
        res_code=None,
        source_table=config.default_table,
        db_path="stub-empty-source",
        target_hit_rate=0.5,
        conn=_EmptySourceStub(),
    )
    _assert_split_compliant(result["prediction"]["content"])


def test_group_quota_replacement_is_deterministic_per_seed():
    """同一批种子重复计算必须稳定（种子化生成不引入非确定性）。"""
    config = get_prediction_config("title_30")
    for seed in ("2026184", "2026166", "2026271", "2026179"):
        first = _format_content(config, seed)
        _assert_split_compliant(first)
        assert _format_content(config, seed) == first


def test_controlled_candidate_sequences_respect_group_quotas():
    """受控候选流必须只产出 4 单尾 + 4 双尾。"""
    config = get_prediction_config("title_30")

    checked = 0
    for labels in _candidate_sequences(
        predicted_labels=BASELINE,
        available_labels=tuple(config.labels),
        width=8,
        seed="controlled-seq",
        max_candidates=256,
        selection_quotas=_selection_groups(config),
    ):
        dan = [label.removesuffix("尾") for label in labels[:4]]
        shuang = [label.removesuffix("尾") for label in labels[4:]]
        assert set(dan) <= SINGLE_TAILS, labels
        assert set(shuang) <= DOUBLE_TAILS, labels
        assert len(set(labels)) == 8, labels
        checked += 1
    assert checked > 0


def test_choose_controlled_labels_is_group_quota_compliant_for_hit_and_miss():
    """受控候选在「要求命中 / 要求不中」两种目标下都必须满足分组配额。

    要求「不中」时特码尾是奇数尾（1 尾）：单尾域 5 选 4 必须允许「不取 1 尾」，
    否则受控候选会必然命中、`ControlledCandidateUnavailable` 直接耗尽。
    """
    config = get_prediction_config("title_30")
    rule = get_generation_rule(config)
    conn = _FixedDataStub()

    for special in ("01", "12", "25", "37"):
        truth = DrawTruth(numbers=(), special_code=special)
        for should_hit in (True, False):
            candidate = choose_controlled_labels(
                config=config,
                rule=rule,
                truth=truth,
                predicted_labels=BASELINE,
                should_hit=should_hit,
                forbidden_prefixes=set(),
                forbidden_signatures=set(),
                seed=f"controlled:{special}:{should_hit}",
                conn=conn,
            )
            dan = [label.removesuffix("尾") for label in candidate.labels[:4]]
            shuang = [label.removesuffix("尾") for label in candidate.labels[4:]]
            assert set(dan) <= SINGLE_TAILS, candidate.labels
            assert set(shuang) <= DOUBLE_TAILS, candidate.labels
            assert candidate.verified_hit is should_hit


class _FixedDataStub:
    """`rule.verify_hit` 只需要一个「没有 fixed_data」的连接占位。"""

    def execute(self, *_args, **_kwargs):  # pragma: no cover - 尾数口径不会走到
        raise AssertionError("tail rule must not query the database")


def test_selection_group_quotas_rejects_overlapping_groups():
    """分组重叠（如家野 4 肖同一生肖出现在两组）时必须拒绝限域，退回旧行为。"""
    overlapping = (("牛", "马", "羊"), ("马", "羊", "鸡"))
    assert selection_group_quotas(overlapping, (2, 2), ("牛", "马", "羊", "鸡")) is None
    # 分组并集不等于候选全域时同样拒绝
    disjoint = (("牛", "马"), ("羊", "鸡"))
    assert selection_group_quotas(disjoint, (1, 1), ("牛", "马", "羊", "鸡", "狗")) is None
    assert selection_group_quotas(disjoint, (2, 2), ("牛", "马", "羊", "鸡")) is not None
    assert selection_group_quotas(None, None, ("牛",)) is None


def test_mode_30_rule_marks_no_display_uniqueness_window():
    """mode 30 是双列尾数组合，候选空间 5×5 组合充足，不纳入三期展示唯一托管。"""
    from prediction_generation.diversity import THREE_PERIOD_UNIQUE_MODE_IDS

    assert MODE_ID not in THREE_PERIOD_UNIQUE_MODE_IDS


def test_mode_30_draw_truth_outcome_is_the_special_tail():
    """受控规则的真实目标必须是特码尾数（`N尾`），不是号码或生肖。"""
    rule = get_generation_rule(get_prediction_config("title_30"))
    assert rule.truth_outcome is not None
    assert rule.truth_outcome(DrawTruth(numbers=(), special_code="37"), None) == "7尾"
    assert rule.truth_outcome(DrawTruth(numbers=(), special_code="04"), None) == "4尾"


def test_simple_namespace_without_groups_is_not_quota_scoped():
    """没有分组信息的动态配置不得被误限域（保持旧行为）。"""
    config = SimpleNamespace(
        key="title_999",
        title="无分组玩法",
        default_modes_id=999,
        labels=("甲", "乙", "丙"),
        label_count=2,
        selection_groups=None,
        selection_widths=None,
    )
    assert _selection_groups(config) is None
