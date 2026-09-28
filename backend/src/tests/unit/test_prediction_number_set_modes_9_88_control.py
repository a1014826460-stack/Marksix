"""复审接入的号码集合玩法受控规则：16码（mode 9）与杀7码（mode 88）。

2026-09-29 复审结论（与 mode 116 同族的两个漏登记 mode）：
- **mode 9 16码**（动态 `title_9`，表 `mode_payload_9`，站点 twsaimahui `035ma16.js`
  → `/api/kaijiang/getCode?num=16`）：候选是 16 个逗号分隔号码，
  `hit_checker=contains_hit`（特码号码落入集合即命中）。登记前
  `get_generation_rule()` 返回 `blocked_pending_rule` → 未来期 silent fallback。
- **mode 88 杀7码**（动态 `title_88`，站点 twsaimahui `056s7m.js` → `getShama`）：
  候选是 7 个**排除**号码，`hit_checker=excludes_hit`（特码不在集合内才算命中）。
  前台 `056s7m.js` 的 `zj = opened && !hitAny` 与之一致。

两个 mode 都登记 `cross_site_prefix_width=2`：
- mode 9：16 个号码的有序前两位 = 16*15 = 240 种；本部署同期启用站点数 1（web 6），240 > 1。
- mode 88：7 个号码的有序前两位 = 7*6 = 42 种；本部署同期启用站点数 2（web 6/8），42 > 2。

mode 65（码段12）**故意不登记**：候选必须是升序连续段区间（前台按
`content[0]-content[-1]` 渲染与判定），通用 `number` 规则会产出任意 12-子集，破坏段语义。
"""

from __future__ import annotations

from db import connect
from domains.prediction.candidate_control import _candidate_sequences, choose_controlled_labels
from domains.prediction.generation_control_repository import reserve_control
from domains.prediction.generation_rules import RULE_BY_MODE_ID, get_generation_rule
from domains.prediction.models import DrawTruth
from domains.prediction.simulation_service import SimulationConfig
from prediction_generation.service import _plan_persisted_future_control
from predict.mechanisms import build_title_prediction_configs
from tables import ensure_admin_tables

#: 与仓库其它 PostgreSQL 用例一致：本地开发库 DSN。
_DSN = "postgresql://postgres:2225427@127.0.0.1:5432/liuhecai"

_CACHE: dict[str, object] = {}


def _dynamic_config(key: str):
    """`title_9` / `title_88` 是动态发现的配置，必须从本地库构建。"""
    if not _CACHE:
        _CACHE.update(build_title_prediction_configs(_DSN))
    config = _CACHE.get(key)
    assert config is not None, f"mode_payload_tables 缺少 {key} 或本地库不可用"
    return config


def _truth(special: str) -> DrawTruth:
    return DrawTruth(("01", "02", "03", "04", "05", "06", special), special, "虎", "绿波")


#: 厂商热度排序的典型冻结前缀（16 码，**不含**特码 27）。
_FROZEN_16 = (
    "23", "39", "08", "22", "36", "18", "15", "26",
    "14", "05", "45", "16", "20", "40", "33", "44",
)
#: 同一条候选，把末位换成特码 27（命中方向）。
_HIT_16 = (*_FROZEN_16[:15], "27")
#: 基线本身已含特码 27 的形态（命中率控制下「要求命中」时的常见 baseline）。
_BASELINE_WITH_27 = (*_FROZEN_16[:10], "27", *_FROZEN_16[11:])
#: 杀7码的冻结候选（不含特码 27）。
_FROZEN_7 = ("01", "17", "14", "28", "03", "20", "36")
#: 杀7码候选含特码 27（不中方向）：杀号类只要把特码写进候选就必然失败。
_HIT_7 = (*_FROZEN_7[:6], "27")


# ---------- (a) 规则登记 ----------


def test_modes_9_and_88_are_registered_with_the_correct_direction():
    rule_9 = get_generation_rule(_dynamic_config("title_9"))
    assert rule_9.rule_id == "number"
    assert rule_9.supported is True
    assert rule_9.block_reason == ""
    assert rule_9.cross_site_prefix_width == 2

    rule_88 = get_generation_rule(_dynamic_config("title_88"))
    assert rule_88.rule_id == "number_exclusion"
    assert rule_88.supported is True
    assert rule_88.block_reason == ""
    assert rule_88.cross_site_prefix_width == 2


def test_mode_65_stays_unregistered_with_a_documented_reason():
    """mode 65 的候选是段区间，通用号码规则会破坏「升序连续」契约。"""
    rule = get_generation_rule(_dynamic_config("title_65"))
    assert rule.supported is False
    assert rule.block_reason == "missing_verified_rule"
    assert 65 not in RULE_BY_MODE_ID


def test_number_family_prefix_widths_are_reviewable():
    """号码类玩法的跨站前缀宽度必须在登记表里可见，便于审阅前缀空间。"""
    widths = {
        mode_id: RULE_BY_MODE_ID[mode_id].cross_site_prefix_width
        for mode_id in (9, 34, 77, 88, 116, 481, 485, 493, 494)
    }
    assert widths == {9: 2, 34: 3, 77: 2, 88: 2, 116: 2, 481: 2, 485: 2, 493: 3, 494: 2}


# ---------- (b) verify_hit 双向 ----------


def test_mode_9_verify_hit_is_contains():
    config = _dynamic_config("title_9")
    rule = get_generation_rule(config)

    assert config.label_count == 16
    assert rule.verify_hit(config, _HIT_16, _truth("27"), conn=None) is True
    assert rule.verify_hit(config, _FROZEN_16, _truth("27"), conn=None) is False
    assert rule.verify_hit(config, _FROZEN_16, _truth("23"), conn=None) is True
    # 02 也必须逐位判定：`contains_hit` 是子串判定，编号之间不能互相“蹭”命中。
    # 号码标签恒为两位，因此任何 outcome 都恰好等于某个标签本身或不属于任何标签。
    assert rule.verify_hit(config, _FROZEN_16, _truth("02"), conn=None) is False
    assert rule.verify_hit(config, _FROZEN_16, _truth("49"), conn=None) is False
    # 集合语义：顺序无关
    assert rule.verify_hit(config, tuple(reversed(_HIT_16)), _truth("27"), conn=None) is True


def test_mode_88_verify_hit_is_excludes():
    config = _dynamic_config("title_88")
    rule = get_generation_rule(config)

    assert config.label_count == 7
    # 特码不在 7 个杀码里 -> 命中（杀中）
    assert rule.verify_hit(config, _FROZEN_7, _truth("27"), conn=None) is True
    # 特码在杀码里 -> 不中（杀失败）
    assert rule.verify_hit(config, _HIT_7, _truth("27"), conn=None) is False
    # 反向断言：绝不能按 contains 判
    assert rule.verify_hit(config, _HIT_7, _truth("27"), conn=None) is not True


# ---------- (c) 候选可达性（宽号码玩法） ----------


def test_wide_number_candidates_reach_the_requested_direction():
    """16 码/7 码在「需要命中但 baseline 缺真值」时都必须能产出正确候选。"""
    for key, baseline, width in (
        ("title_9", _FROZEN_16, 16),
        ("title_88", _FROZEN_7, 7),
    ):
        config = _dynamic_config(key)
        rule = get_generation_rule(config)

        hit = choose_controlled_labels(
            config=config,
            rule=rule,
            truth=_truth("27"),
            predicted_labels=baseline,
            should_hit=True,
            forbidden_prefixes=set(),
            forbidden_signatures=set(),
            seed=f"{key}-hit",
        )
        assert hit.verified_hit is True, key
        assert len(hit.labels) == width
        assert hit.prefix_signature == hit.labels[:2]
        if rule.rule_id == "number":
            assert "27" in hit.labels
        else:
            assert "27" not in hit.labels

        miss = choose_controlled_labels(
            config=config,
            rule=rule,
            truth=_truth("27"),
            predicted_labels=baseline,
            should_hit=False,
            forbidden_prefixes=set(),
            forbidden_signatures=set(),
            seed=f"{key}-miss",
        )
        assert miss.verified_hit is False, key
        assert len(miss.labels) == width
        if rule.rule_id == "number_exclusion":
            assert "27" in miss.labels


def test_baseline_thats_already_on_the_right_side_still_varies_the_prefix():
    """复审定位的第二个可达性缺陷：baseline 已在正确一侧时前缀被钉死。

    mode 9/34/77 的线上 baseline 由 `score_labels("hot")` + 期号种子生成，
    **所有站点同一条**。当它已经含特码时，旧实现只枚举这组号码的 `width!` 个排列，
    于是首号恒为 baseline 首号：实测连取 60 个候选只有 **1** 个不同前缀，
    `_plan_persisted_future_control` 带 forbidden 前缀重选直接
    `candidate_space_exhausted`，生成侧回落随机 fallback，跨站前缀契约名存实亡。
    """
    config = _dynamic_config("title_9")
    rule = get_generation_rule(config)
    pool = tuple(f"{number:02d}" for number in range(1, 50))

    baseline = _BASELINE_WITH_27
    assert "27" in baseline

    def directed_prefixes(seed: str, count: int = 60) -> list[tuple[str, ...]]:
        generator = _candidate_sequences(
            predicted_labels=baseline,
            available_labels=pool,
            width=16,
            seed=seed,
            required_truth="27",
            should_hit=True,
            truth_must_be_in_candidate=True,
        )
        prefixes = []
        for _ in range(count):
            try:
                candidate = next(generator)
            except StopIteration:
                break
            assert "27" in candidate
            prefixes.append(candidate[:2])
        return prefixes

    prefixes = directed_prefixes("mode9-baseline-correct")
    assert len(set(prefixes)) >= 20, prefixes
    # 同一期不同站点（seed 不同）必须能从**首个**候选就拿到不同前缀
    assert directed_prefixes("site:6", 1)[0] != directed_prefixes("site:8", 1)[0]

    # 端到端：两个站点在同一期拿到不同前缀，第二个站点不再 candidate_space_exhausted
    import tempfile
    from pathlib import Path

    db_path = str(Path(tempfile.mkdtemp()) / "prefix-diversity.sqlite3")
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        plans = []
        for web in (6, 8):
            plan = _plan_persisted_future_control(
                conn=conn, config=config, lottery_type=3, site_id=web, site_web_id=web,
                draw={"year": 2026, "term": 271}, truth=_truth("27"),
                simulation_config=SimulationConfig(target_hit_rate=1.0),
                mechanism_key="title_9", predicted_labels=baseline,
            )
            assert plan is not None and plan.verified_hit is True
            plans.append(plan)
            assert reserve_control(
                conn, lottery_type_id=3, year=2026, term=271, mode_id=9, web_id=web,
                rule_id=plan.rule_id, rule_revision=plan.rule_revision,
                target_hit=plan.target_hit, verified_hit=plan.verified_hit,
                signature=plan.signature, prefix_signature=plan.prefix_signature,
                created_at="2026-09-29T00:00:00Z",
            )["reserved"] is True
        assert plans[0].prefix_signature != plans[1].prefix_signature


# ---------- (d) 受控链路 dry-run（临时 sqlite，不触碰生产库） ----------


def test_control_plan_reserves_one_prefix_per_site_for_modes_9_and_88(tmp_path):
    """本地 sqlite 干跑：两条 mode 的受控计划都能命中目标方向并记账。"""
    db_path = str(tmp_path / "number-set-control.sqlite3")
    ensure_admin_tables(db_path)

    for key, mode_id, baseline, hit_target, miss_target in (
        ("title_9", 9, _FROZEN_16, True, False),
        ("title_88", 88, _FROZEN_7, True, False),
    ):
        config = _dynamic_config(key)
        with connect(db_path) as conn:
            hit_plan = _plan_persisted_future_control(
                conn=conn, config=config, lottery_type=3, site_id=6, site_web_id=6,
                draw={"year": 2026, "term": 271}, truth=_truth("27"),
                simulation_config=SimulationConfig(target_hit_rate=1.0),
                mechanism_key=key, predicted_labels=baseline,
            )
            assert hit_plan is not None, key
            assert hit_plan.target_hit is hit_target
            assert hit_plan.verified_hit is True
            assert hit_plan.prefix_signature == hit_plan.labels[:2]

            assert reserve_control(
                conn, lottery_type_id=3, year=2026, term=271, mode_id=mode_id, web_id=6,
                rule_id=hit_plan.rule_id, rule_revision=hit_plan.rule_revision,
                target_hit=hit_plan.target_hit, verified_hit=hit_plan.verified_hit,
                signature=hit_plan.signature, prefix_signature=hit_plan.prefix_signature,
                created_at="2026-09-29T00:00:00Z",
            )["reserved"] is True

            # 同一期另一个站点：前缀不得与已预约站点相同（前缀空间可满足）
            other_site = _plan_persisted_future_control(
                conn=conn, config=config, lottery_type=3, site_id=8, site_web_id=8,
                draw={"year": 2026, "term": 271}, truth=_truth("27"),
                simulation_config=SimulationConfig(target_hit_rate=1.0),
                mechanism_key=key, predicted_labels=baseline,
            )
            assert other_site is not None, key
            assert other_site.prefix_signature != hit_plan.prefix_signature

            # 相邻期同站点：完整签名必须不同
            adjacent = _plan_persisted_future_control(
                conn=conn, config=config, lottery_type=3, site_id=6, site_web_id=6,
                draw={"year": 2026, "term": 272}, truth=_truth("27"),
                simulation_config=SimulationConfig(target_hit_rate=1.0),
                mechanism_key=key, predicted_labels=baseline,
            )
            assert adjacent is not None, key
            assert adjacent.signature != hit_plan.signature

            # 明确要求不中：命中类玩法必须剔掉特码，杀号类必须把特码写进候选
            miss_plan = _plan_persisted_future_control(
                conn=conn, config=config, lottery_type=3, site_id=9, site_web_id=9,
                draw={"year": 2026, "term": 273}, truth=_truth("27"),
                simulation_config=SimulationConfig(target_hit_rate=0.0),
                mechanism_key=key, predicted_labels=baseline,
            )
            assert miss_plan is not None, key
            assert miss_plan.target_hit is miss_target
            assert miss_plan.verified_hit is False
            if get_generation_rule(config).rule_id == "number":
                assert "27" not in miss_plan.labels
            else:
                assert "27" in miss_plan.labels


def test_modes_9_and_88_are_display_order_immaterial():
    """两条 mode 都是号码集合玩法：展示置换不改变命中结论。"""
    from predict.common import contains_hit, excludes_hit
    from prediction_generation import diversity

    assert diversity.is_unordered_number_set_mode(9) is True
    assert diversity.is_unordered_number_set_mode(88) is True

    for mode_id, content, checker in (
        (9, ",".join(_FROZEN_16), contains_hit),
        (88, ",".join(_FROZEN_7), excludes_hit),
    ):
        row = {"content": content, "year": "2026", "term": "271", "web": "6"}
        permuted = diversity.enforce_prediction_diversity(mode_id=mode_id, row_data=row)["content"]
        assert sorted(permuted.split(",")) == sorted(content.split(","))
        before = tuple(content.split(","))
        after = tuple(permuted.split(","))
        for special in (f"{number:02d}" for number in range(1, 50)):
            assert checker(special, before) == checker(special, after), (mode_id, special)
