"""10码中特（mode 116 / `title_116`）接入受控未来期生成规则。

背景（2026-09-29）：
- mode 116 的表 `mode_payload_116.content` 是 10 个逗号分隔号码（`01,17,42,...`），
  口径是**特码号码落入候选号码集合即命中**；
- 登记前 `_RULE_BY_MODE_ID` 里没有 116，`get_generation_rule()` 返回
  `blocked_pending_rule`，未来期只走 silent fallback（纯随机 10/49、无规则校验、
  无滚动窗口控制），线上 262-270 连 9 期未中即该表现；
- 该 mode 的动态配置由 `_make_number_config` 生成，已经具备
  `outcome_loader=special_number_from_row` / `content_parser=parse_number_content` /
  `hit_checker=contains_hit` / `label_count=10`，所以只需登记规则。
- 该 mode 同时在 `prediction_generation.diversity.UNORDERED_NUMBER_SET_MODE_IDS`
  白名单里（展示顺序按期号置换，成员不变）。本文件同时锁定「展示置换不参与落库顺序」。
"""

from __future__ import annotations

from db import connect
from domains.prediction.candidate_control import _candidate_sequences, choose_controlled_labels
from domains.prediction.generation_rules import get_generation_rule
from domains.prediction.models import DrawTruth
from domains.prediction.simulation_service import SimulationConfig
from prediction_generation import diversity
from prediction_generation.service import _plan_persisted_future_control
from predict.categories.number import format_24_numbers
from predict.common import contains_hit
from predict.mechanisms import build_title_prediction_configs
from tables import ensure_admin_tables

#: 与仓库其它 PostgreSQL 用例一致：本地开发库 DSN。
_DSN = "postgresql://postgres:2225427@127.0.0.1:5432/liuhecai"

#: 厂商热度排序的典型冻结前缀（线上实测位置 1/2 恒为 01/17），不含特码 27。
_FROZEN_BASELINE = ("01", "17", "42", "02", "23", "15", "03", "07", "39", "38")

#: 同一条候选，把最后一个号码换成特码 27：用于「命中」方向。
_HIT_BASELINE = (*_FROZEN_BASELINE[:9], "27")


def _dynamic_config():
    """`title_116` 是动态发现的配置，必须从本地库构建，不能写死在测试里。"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = build_title_prediction_configs(_DSN).get("title_116")
    assert _CONFIG_CACHE is not None, "mode_payload_tables 缺少 mode 116 或本地库不可用"
    return _CONFIG_CACHE


_CONFIG_CACHE = None


def _truth(*, special: str = "27") -> DrawTruth:
    return DrawTruth(("01", "02", "03", "04", "05", "06", special), special, "虎", "绿波")


# ---------- (a) 规则已登记 ----------


def test_mode_116_is_registered_as_a_supported_number_rule():
    config = _dynamic_config()
    rule = get_generation_rule(config)

    assert rule.supported is True
    assert rule.block_reason == ""
    assert rule.rule_id == "number"
    assert rule.rule_revision == 1
    # 跨站前缀宽度：与同族 14码中特（mode 77）一致取 2，24码（mode 34）取 3。
    assert rule.cross_site_prefix_width == 2


def test_mode_116_prefix_width_is_adjustable_per_sibling_number_modes():
    """登记表里号码类玩法的前缀宽度必须可见，便于审阅跨站前缀契约。"""
    from domains.prediction.generation_rules import RULE_BY_MODE_ID

    widths = {
        mode_id: RULE_BY_MODE_ID[mode_id].cross_site_prefix_width
        for mode_id in (34, 77, 116)
    }
    assert widths == {34: 3, 77: 2, 116: 2}


# ---------- (b) verify_hit 双向 ----------


def test_mode_116_verify_hit_hits_only_when_special_number_is_in_the_candidate():
    config = _dynamic_config()
    rule = get_generation_rule(config)

    # 特码 27 在候选里 -> 命中
    assert rule.verify_hit(config, _HIT_BASELINE, _truth(special="27"), conn=None) is True
    # 特码 27 不在候选里 -> 不中
    assert rule.verify_hit(config, _FROZEN_BASELINE, _truth(special="27"), conn=None) is False
    # 其它特码同理
    assert rule.verify_hit(config, _FROZEN_BASELINE, _truth(special="17"), conn=None) is True
    assert rule.verify_hit(config, _FROZEN_BASELINE, _truth(special="49"), conn=None) is False
    # 候选顺序与命中无关（集合语义）
    reversed_candidates = tuple(reversed(_HIT_BASELINE))
    assert rule.verify_hit(config, reversed_candidates, _truth(special="27"), conn=None) is True


def test_mode_116_prefix_signature_is_the_first_two_labels_in_stored_order():
    config = _dynamic_config()
    rule = get_generation_rule(config)

    assert rule.signature(_FROZEN_BASELINE) == _FROZEN_BASELINE
    assert rule.prefix_signature(_FROZEN_BASELINE) == ("01", "17")


def test_mode_116_formatter_matches_the_persisted_csv_shape():
    """记录 mode 116 的候选宽度与格式化形态，避免后续被误改成其它列语义。"""
    config = _dynamic_config()

    assert config.key == "title_116"
    assert config.title == "10码"
    assert config.default_table == "mode_payload_116"
    assert config.label_count == 10
    assert len(config.labels) == 49
    assert config.labels[0] == "01" and config.labels[-1] == "49"
    assert format_24_numbers(_FROZEN_BASELINE, None) == ",".join(_FROZEN_BASELINE)
    # 落库形态必须是号码集合（不是 `标签|号码` 有序标签序列）
    assert diversity.number_set_members(",".join(_FROZEN_BASELINE)) == list(_FROZEN_BASELINE)


# ---------- (c) 动态配置核查 ----------


def test_mode_116_dynamic_config_declares_number_semantics():
    config = _dynamic_config()

    assert config.outcome_loader is not None
    assert config.content_parser is not None
    assert config.hit_checker is contains_hit
    # 真实目标解析：res_code 最后一个号码是特码。
    assert config.outcome_loader({"res_code": "01,02,03,04,05,06,27"}, None) == "27"
    # content 解析：逗号串里的 10 个号码
    assert config.content_parser("01,17,42,02,23,15,03,07,39,38") == _FROZEN_BASELINE
    # 命中判定：特码是否落在候选集合内
    assert config.hit_checker("27", _HIT_BASELINE) is True
    assert config.hit_checker("27", _FROZEN_BASELINE) is False
    assert config.hit_checker("49", _FROZEN_BASELINE) is False


# ---------- (d) 展示置换不影响落库顺序 / 前缀签名 ----------


def test_mode_116_is_in_the_unordered_number_set_whitelist():
    assert 116 in diversity.UNORDERED_NUMBER_SET_MODE_IDS
    assert diversity.resolve_diversity_policy(116, None) == diversity.UNORDERED_SET_DIVERSITY_POLICY


def test_display_permutation_keeps_members_and_thus_hit_semantics():
    """展示置换只换顺序：成员集合与命中结论逐一等价。"""
    row = {"content": ",".join(_FROZEN_BASELINE), "year": "2026", "term": "271", "web": "6"}
    permuted = diversity.enforce_prediction_diversity(mode_id=116, row_data=row)["content"]

    assert sorted(permuted.split(",")) == sorted(_FROZEN_BASELINE)
    before = tuple(_FROZEN_BASELINE)
    after = tuple(permuted.split(","))
    for special in (f"{number:02d}" for number in range(1, 50)):
        assert contains_hit(special, before) == contains_hit(special, after)


def test_display_permutation_would_change_the_prefix_signature_of_a_controlled_row():
    """论证为什么受控行不能过多样性修复：置换会改动前缀签名的落库顺序。

    `prediction_generation.service` 只在 `control_plan is None`（无规则/非台湾未来期/
    兜底）时调用 `enforce_prediction_diversity`；受控行直接落库，因此预约过的
    `prefix_signature` 与创建行内容的前两位一致。这里锁定这个前提。
    """
    config = _dynamic_config()
    rule = get_generation_rule(config)
    row = {"content": ",".join(_FROZEN_BASELINE), "year": "2026", "term": "271", "web": "6"}

    permuted = diversity.enforce_prediction_diversity(mode_id=116, row_data=row)["content"]
    permuted_prefix = rule.prefix_signature(tuple(permuted.split(",")))

    assert permuted_prefix != rule.prefix_signature(_FROZEN_BASELINE)
    # 因此受控行必须跳过置换（service 的 `if control_plan is None:` 分支），
    # 否则预约哈希会对不上实际落库内容。
    assert rule.prefix_signature(_FROZEN_BASELINE) == ("01", "17")


def test_candidate_enumeration_alone_cannot_reach_the_truth_without_the_directional_fix():
    """锁定根因：高宽度玩法把预算全花在 baseline 排列上，产不出缺的真值。

    mode 116 的宽是 10，`predicted_labels` 恰好也是 10，因此历史实现的前 32768 个
    候选全部是同一组号码的排列——不含特码 27 的数量为 32768。
    """
    config = _dynamic_config()
    pool = tuple(config.labels)
    generator = _candidate_sequences(
        predicted_labels=_FROZEN_BASELINE,
        available_labels=pool,
        width=10,
        seed="mode116-reachability",
    )
    emitted = list(generator)

    assert len(emitted) == 32768
    assert all("27" not in candidate for candidate in emitted)
    assert {tuple(sorted(candidate)) for candidate in emitted} == {tuple(sorted(_FROZEN_BASELINE))}


def test_candidate_control_reaches_the_truth_for_wide_number_modes():
    """修复后必须能产出方向正确的候选（可达性）。"""
    config = _dynamic_config()
    rule = get_generation_rule(config)

    # baseline 不含特码 27，但目标是「命中」：历史实现在这里必然 candidate_space_exhausted
    hit = choose_controlled_labels(
        config=config,
        rule=rule,
        truth=_truth(special="27"),
        predicted_labels=_FROZEN_BASELINE,
        should_hit=True,
        forbidden_prefixes=set(),
        forbidden_signatures=set(),
        seed="mode116-hit",
    )
    assert hit.verified_hit is True
    assert "27" in hit.labels
    assert len(hit.labels) == 10
    # 跨站前缀仍按落库顺序取前两位
    assert hit.prefix_signature == hit.labels[:2]

    # baseline 含特码 27，但目标是「不中」：必须把 27 从候选里剔除
    miss = choose_controlled_labels(
        config=config,
        rule=rule,
        truth=_truth(special="27"),
        predicted_labels=_HIT_BASELINE,
        should_hit=False,
        forbidden_prefixes=set(),
        forbidden_signatures=set(),
        seed="mode116-miss",
    )
    assert miss.verified_hit is False
    assert "27" not in miss.labels
    assert len(miss.labels) == 10


def test_candidate_sequences_sample_is_deterministic_for_mode_116():
    config = _dynamic_config()
    pool = tuple(config.labels)

    def first_n(count: int) -> list[tuple[str, ...]]:
        generator = _candidate_sequences(
            predicted_labels=_FROZEN_BASELINE,
            available_labels=pool,
            width=10,
            seed="mode116-determinism",
        )
        return [next(generator) for _ in range(count)]

    assert first_n(3) == first_n(3)
    assert first_n(1)[0] == _FROZEN_BASELINE


# ---------- 受控链路（本地 dry-run，不写生产库） ----------


def test_control_plan_for_mode_116_hits_and_reserves_one_prefix_per_site(tmp_path):
    """本地 sqlite 干跑：受控计划真的按目标命中率产出「命中/不中」候选并记账。

    只写临时 sqlite 文件（`prediction_generation_controls` 的本地副本），
    不触碰 PostgreSQL 的 `created.mode_payload_*` 或线上控制表。
    """
    from domains.prediction.generation_control_repository import reserve_control

    db_path = str(tmp_path / "mode116-control.sqlite3")
    ensure_admin_tables(db_path)
    config = _dynamic_config()

    with connect(db_path) as conn:
        hit_plan = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=6, site_web_id=6,
            draw={"year": 2026, "term": 271}, truth=_truth(special="27"),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="title_116", predicted_labels=_FROZEN_BASELINE,
        )
        assert hit_plan is not None
        assert hit_plan.rule_id == "number"
        assert hit_plan.target_hit is True
        assert hit_plan.verified_hit is True
        assert "27" in hit_plan.labels
        assert hit_plan.prefix_signature == hit_plan.labels[:2]

        assert reserve_control(
            conn, lottery_type_id=3, year=2026, term=271, mode_id=116, web_id=6,
            rule_id=hit_plan.rule_id, rule_revision=hit_plan.rule_revision,
            target_hit=hit_plan.target_hit, verified_hit=hit_plan.verified_hit,
            signature=hit_plan.signature, prefix_signature=hit_plan.prefix_signature,
            created_at="2026-09-29T00:00:00Z",
        )["reserved"] is True

        # 同一期另一站点：前缀必须与已预约站点不同。
        other_site = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=7, site_web_id=7,
            draw={"year": 2026, "term": 271}, truth=_truth(special="27"),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="title_116", predicted_labels=_FROZEN_BASELINE,
        )
        assert other_site is not None
        assert other_site.prefix_signature != hit_plan.prefix_signature

        # 相邻期同站点：完整签名必须不同（相邻期契约）。
        adjacent = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=6, site_web_id=6,
            draw={"year": 2026, "term": 272}, truth=_truth(special="27"),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="title_116", predicted_labels=_FROZEN_BASELINE,
        )
        assert adjacent is not None
        assert adjacent.signature != hit_plan.signature

        # 目标不中：即使 baseline 里已经带了特码 27，也必须把它剔除。
        miss_plan = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=8, site_web_id=8,
            draw={"year": 2026, "term": 273}, truth=_truth(special="27"),
            simulation_config=SimulationConfig(target_hit_rate=0.0),
            mechanism_key="title_116", predicted_labels=_HIT_BASELINE,
        )
        assert miss_plan is not None
        assert miss_plan.target_hit is False
        assert miss_plan.verified_hit is False
        assert "27" not in miss_plan.labels
