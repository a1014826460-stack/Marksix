"""天地生肖（mode 5）受控计划的「相邻连续展示值」约束回归测试。

背景（2026-10-13 用户报障）：twcf888（web 8）279-285 连续 7 期展示「地肖+蛇羊」。
根因不是生成规则错，而是受控计划对**二值玩法**不可达：
`forbidden_signature_hashes` 里含上一期签名（`load_adjacent_controls`），而二选一玩法
在「本期要求未中」时只剩一个候选，两者冲突 → `ControlledCandidateUnavailable`
→ 静默回落到无约束路径 → 同值可以无限连下去。

本文件锁定修复后的两条契约：
1. 「最近 window-1 期同值」时，受控计划必须锁到另一个候选，并按锁定值反解真实方向；
2. 二值展示域不再被上一期签名卡死（否则约束反而失效）。
"""

from __future__ import annotations

from typing import Any

import pytest

from domains.prediction.candidate_control import signature_hash
from domains.prediction.generation_rules import RULE_BY_MODE_ID
from domains.prediction.models import DrawTruth
from domains.prediction.simulation_service import SimulationConfig
from predict.mechanisms import PREDICTION_CONFIGS, format_tiandi_groups
from prediction_generation.service import _plan_persisted_future_control


class _Rows(list):
    def fetchone(self) -> Any:
        return self[0] if self else None

    def fetchall(self) -> list[Any]:
        return list(self)


class _StubConn:
    """最小连接桩：只回答受控计划用到的三类只读查询。"""

    engine = "sqlite"

    def __init__(self, *, verified_hits: list[bool], adjacent: list[dict[str, Any]] | None = None):
        # 仓库函数按「新→旧」取行再 reverse 成时序，因此这里同样按新→旧返回。
        self._verified = list(reversed(verified_hits))
        self._adjacent = list(adjacent or [])

    def execute(self, sql: str, params: Any = ()) -> _Rows:
        text = str(sql)
        if "FROM prediction_generation_controls" in text and "verified_hit" in text:
            return _Rows({"verified_hit": 1 if hit else 0} for hit in self._verified)
        if "FROM prediction_generation_controls" in text and "signature_hash" in text:
            return _Rows(self._adjacent)
        if "FROM prediction_generation_controls" in text:
            return _Rows()
        return _Rows()

    def commit(self) -> None:  # pragma: no cover - 计划阶段不写库
        return None


def _config():
    return PREDICTION_CONFIGS["title_5"]


def _plan(
    conn: _StubConn,
    *,
    truth_zodiac: str,
    recent_tokens: tuple[str, ...],
    term: int = 286,
):
    config = _config()
    return _plan_persisted_future_control(
        conn=conn,
        config=config,
        lottery_type=3,
        site_id=8,
        site_web_id=8,
        draw={"year": "2026", "term": str(term)},
        truth=DrawTruth(numbers=(), special_code="01", special_zodiac=truth_zodiac),
        simulation_config=SimulationConfig(target_hit_rate=0.5),
        mechanism_key="title_5",
        predicted_labels=("地肖",),
        recent_display_tokens=recent_tokens,
    )


def test_plan_flips_label_when_run_reaches_the_display_cap():
    """连续三期「地肖」后（window=4），真实特肖属地肖也必须改判为「天肖」。"""
    conn = _StubConn(verified_hits=[True, True])
    plan = _plan(conn, truth_zodiac="鼠", recent_tokens=("地肖", "地肖", "地肖"))

    assert plan is not None
    assert plan.labels == ("天肖",)
    # 方向必须按锁定后的标签反解：天肖不含鼠 → 台账记录未中，与落库内容一致
    assert plan.target_hit is False
    assert plan.verified_hit is False
    # 落库正文与判定同向
    assert format_tiandi_groups(plan.labels, None)["content"].startswith('["天肖|')


def test_plan_keeps_direction_when_run_is_below_the_cap():
    """连续上限内允许同值：window=4 ⇒ 连续 3 期相同仍允许，第 4 期才强制换值。"""
    conn = _StubConn(verified_hits=[True, True])
    below_cap = _plan(conn, truth_zodiac="鼠", recent_tokens=("地肖", "地肖"))
    assert below_cap is not None
    assert below_cap.labels in {("天肖",), ("地肖",)}

    at_cap = _plan(
        _StubConn(verified_hits=[True, True]),
        truth_zodiac="鼠",
        recent_tokens=("地肖", "地肖", "地肖"),
    )
    assert at_cap is not None
    assert at_cap.labels == ("天肖",)


def test_binary_display_mode_is_not_blocked_by_the_adjacent_signature_ban():
    """上一期签名不再卡死二值玩法（否则计划必然无解并回落成连续同值）。

    构造：最近 9 期有 5 期未中 → `choose_target_hit` 必然要求命中；真实特肖属地肖
    → 唯一命中标签是「地肖」；同时把「地肖」放进相邻签名黑名单。
    修复前：候选「天肖」= 未中 ≠ 要求命中，「地肖」= 被禁 → 计划返回 None（回落）。
    修复后：相邻签名对二值展示域不再生效，计划返回「地肖」。
    """
    conn = _StubConn(
        verified_hits=[False, False, False, False, False, True],
        adjacent=[{"year": 2026, "term": 285, "signature_hash": signature_hash(("地肖",))}],
    )
    plan = _plan(conn, truth_zodiac="鼠", recent_tokens=("天肖", "地肖"))

    assert plan is not None, "二值玩法被相邻签名黑名单卡死 → 会静默回落到无约束路径"
    assert plan.labels == ("地肖",)
    assert plan.target_hit is True
    assert plan.verified_hit is True


def test_display_window_stays_configurable_per_mode():
    """连续窗口按模式可配：mode 5 用户口径 4 期（连值上限 3），52/62 为 5 期，其余默认 3 期。"""
    from prediction_generation.diversity import display_unique_window

    assert display_unique_window(5) == 4
    assert display_unique_window(52) == 5
    assert display_unique_window(62) == 5
    assert display_unique_window(28) == 3


def test_plan_sequence_never_repeats_the_display_value_four_times():
    """计划级序列模拟：真实特肖一直属地肖（最容易诱导长期同值），连跑 16 期。

    window=4 ⇒ 最多允许连续 3 期相同、禁止第 4 期；同时把「上一期签名」放进相邻黑名单，
    验证二值展示域不再因此无解。
    """
    tokens: list[str] = []
    outcomes: list[bool] = []
    for term in range(286, 302):
        adjacent = (
            [{"year": 2026, "term": term - 1, "signature_hash": signature_hash((tokens[0],))}]
            if tokens
            else []
        )
        conn = _StubConn(verified_hits=outcomes, adjacent=adjacent)
        plan = _plan(conn, truth_zodiac="鼠", recent_tokens=tuple(tokens), term=term)

        assert plan is not None, f"term={term} 受控计划无解"
        label = str(plan.labels[0])
        tokens.insert(0, label)
        outcomes.append(bool(plan.verified_hit))
        assert not (
            len(tokens) >= 4 and len(set(tokens[:4])) == 1
        ), f"term={term} 连续 4 期同值：{tokens[:5]}"
    # 12+ 期里两个分组都必须出现过（不允许再次被单一取值锁死）
    assert set(tokens) == {"天肖", "地肖"}
    # 口径是「上限 3」而不是「上限 2」：序列里应当出现过连续 3 期同值
    assert any(
        len(set(tokens[index:index + 3])) == 1 for index in range(len(tokens) - 2)
    ), f"未出现连续 3 期同值，说明上限被收得比用户口径更严：{tokens}"


def test_pair_rotation_keeps_the_pair_inside_the_group():
    """两肖槽按期轮转：同一分组的相邻期两肖不同，且始终是分组成员。"""
    from predict.mechanisms import TIANDI_LABEL_FALLBACK
    from prediction_generation.service import _rotate_tiandi_pair

    content = '["地肖|蛇,羊,鸡,狗,鼠,虎"]'
    pairs = []
    for term in (286, 287):
        rotated = _rotate_tiandi_pair(
            {"content": content, "xiao": "蛇,羊"}, mode_id=5, term=term
        )
        first, second = str(rotated["xiao"]).split(",")
        assert first in TIANDI_LABEL_FALLBACK["地肖"]
        assert second in TIANDI_LABEL_FALLBACK["地肖"]
        pairs.append(rotated["xiao"])

    assert pairs[0] != pairs[1], "相邻期两肖未轮转"
    # 非 mode 5 原样返回
    untouched = {"content": content, "xiao": "蛇,羊"}
    assert _rotate_tiandi_pair(untouched, mode_id=14, term=286) is untouched


def test_alternative_templates_unwrap_the_dict_formatter_for_mode5():
    """mode 5 的 formatter 返回 `{content, xiao}`；备选模板必须是**字符串正文**。

    线上实测（2026-10-13）：把整个 dict 当模板时 `display_token_for_row` 读不出标签，
    兜底路径换不了分组 → 283-286 连续 4 期「地肖」。
    """
    from predict.mechanisms import PREDICTION_CONFIGS
    from prediction_generation.service import _three_period_alternative_content_templates

    templates = _three_period_alternative_content_templates(
        mode_id=5,
        config=PREDICTION_CONFIGS["title_5"],
        conn=None,
        alternative_tokens=("地肖", "天肖"),
    )
    assert templates, "没有生成任何备选正文模板"
    assert all(isinstance(template, str) for template in templates), templates
    assert any('["天肖|' in template for template in templates), templates
    assert any('["地肖|' in template for template in templates), templates


def test_fallback_path_flips_mode5_after_three_identical_rows():
    """受控计划被跳过时的兜底路径也必须换值（复现线上那次重生成的失败形态）。"""
    from predict.mechanisms import PREDICTION_CONFIGS
    from prediction_generation.diversity import enforce_three_period_uniqueness
    from prediction_generation.service import _three_period_alternative_content_templates

    di_xiao = '["地肖|蛇,羊,鸡,狗,鼠,虎"]'
    templates = _three_period_alternative_content_templates(
        mode_id=5,
        config=PREDICTION_CONFIGS["title_5"],
        conn=None,
        alternative_tokens=("地肖", "天肖"),
    )
    result = enforce_three_period_uniqueness(
        mode_id=5,
        row_data={"content": di_xiao, "xiao": "蛇,羊"},
        recent_rows=[{"content": di_xiao}, {"content": di_xiao}, {"content": di_xiao}],
        alternative_content_templates=templates,
    )

    assert "_diversity_warning" not in result, result
    assert str(result["content"]).startswith('["天肖|'), result["content"]
