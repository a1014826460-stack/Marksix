"""Verified future-generation rules for prediction modules.

Rules keep future truth inside the generation domain and convert it into the
single outcome label that each configured module actually evaluates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import DrawTruth

TruthOutcome = Callable[[DrawTruth, Any], str]


def _normalized_code(truth: DrawTruth) -> int:
    return int(str(truth.special_code or "0"))


def _special_zodiac(truth: DrawTruth, _conn: Any) -> str:
    return str(truth.special_zodiac or "").strip()


def _flat_zodiacs(truth: DrawTruth, conn: Any) -> str:
    """平特口径：开奖 7 个号码对应的生肖集合（逗号分隔）。

    平特一肖只要任一开奖号码的生肖命中预测生肖即算命中，因此真实目标不是特码生肖。
    `draw_zodiacs` 缺失时用号码 -> 生肖映射补齐（受控生成必须能算出真实目标，
    否则会把所有候选都判为“不中”）。
    """
    zodiacs = tuple(
        str(zodiac).strip() for zodiac in (getattr(truth, "draw_zodiacs", ()) or ()) if str(zodiac).strip()
    )
    if not zodiacs and conn is not None:
        try:
            from predict.common import fixed_label_for_value

            zodiacs = tuple(
                label
                for label in (
                    fixed_label_for_value(conn, "生肖", str(code)) for code in truth.numbers
                )
                if label
            )
        except Exception:  # noqa: BLE001 - 缺失 fixed_data 时退化为特码口径
            zodiacs = ()
    if zodiacs:
        return ",".join(zodiacs)
    return str(truth.special_zodiac or "").strip()


def _flat_tails(truth: DrawTruth, _conn: Any) -> str:
    """平特尾口径：开奖 7 个号码对应的尾数集合（逗号分隔）。"""
    tails = tuple(
        str(tail).strip() for tail in (getattr(truth, "draw_tails", ()) or ()) if str(tail).strip()
    )
    if tails:
        return ",".join(tails)
    return ",".join(f"{int(code) % 10}尾" for code in truth.numbers if str(code).isdigit())


def _special_number(truth: DrawTruth, _conn: Any) -> str:
    return str(truth.special_code or "").strip()


def _special_head(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    return "0头" if number < 10 else f"{number // 10}头"


def _special_tail(truth: DrawTruth, _conn: Any) -> str:
    return f"{_normalized_code(truth) % 10}尾"


def _special_parity(truth: DrawTruth, _conn: Any) -> str:
    return "双" if _normalized_code(truth) % 2 == 0 else "单"


def _special_size(truth: DrawTruth, _conn: Any) -> str:
    return "大" if _normalized_code(truth) >= 25 else "小"


def _special_wave(truth: DrawTruth, _conn: Any) -> str:
    raw = str(truth.special_color or "").strip()
    return {"red": "红波", "blue": "蓝波", "green": "绿波"}.get(raw, raw)


def _special_half_wave(truth: DrawTruth, _conn: Any) -> str:
    wave = _special_wave(truth, _conn).removesuffix("波")
    parity = _special_parity(truth, _conn)
    return f"{wave}{parity}" if wave and parity else ""


def _special_head_parity(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    head = "0头" if number < 10 else f"{number // 10}头"
    return head + ("双" if number % 2 == 0 else "单")


def _combined_parity(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    return "合单" if ((number // 10) + (number % 10)) % 2 else "合双"


def _combined_size(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    return "合数大" if (number // 10) + (number % 10) >= 7 else "合数小"


@dataclass(frozen=True)
class PredictionGenerationRule:
    rule_id: str
    rule_revision: int
    supported: bool
    block_reason: str
    cross_site_prefix_width: int
    truth_outcome: TruthOutcome | None = None

    def verify_hit(
        self,
        config: Any,
        labels: tuple[str, ...],
        truth: DrawTruth,
        *,
        conn: Any,
    ) -> bool:
        if not self.supported or self.truth_outcome is None:
            return False
        outcome = self.truth_outcome(truth, conn)
        hit_checker = getattr(config, "hit_checker", None)
        return bool(outcome and callable(hit_checker) and hit_checker(outcome, tuple(labels)))

    def signature(self, labels: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(str(label).strip() for label in labels if str(label).strip())

    def prefix_signature(self, labels: tuple[str, ...]) -> tuple[str, ...]:
        return self.signature(labels)[: max(1, int(self.cross_site_prefix_width))]


_BLOCKED_RULE = PredictionGenerationRule(
    rule_id="blocked_pending_rule",
    rule_revision=1,
    supported=False,
    block_reason="missing_verified_rule",
    cross_site_prefix_width=1,
)


def _rule(
    rule_id: str,
    truth_outcome: TruthOutcome,
    *,
    prefix_width: int = 1,
    revision: int = 1,
) -> PredictionGenerationRule:
    return PredictionGenerationRule(
        rule_id=rule_id,
        rule_revision=revision,
        supported=True,
        block_reason="",
        cross_site_prefix_width=prefix_width,
        truth_outcome=truth_outcome,
    )


_RULE_BY_MODE_ID: dict[int, PredictionGenerationRule] = {
    # Ordered zodiac candidates, including normal and exclusion variants.
    31: _rule("zodiac", _special_zodiac, prefix_width=2),
    42: _rule("zodiac_exclusion", _special_zodiac),
    # 平特二肖
    43: _rule("zodiac_flat", _flat_zodiacs),
    44: _rule("zodiac", _special_zodiac, prefix_width=2),
    45: _rule("zodiac", _special_zodiac, prefix_width=2),
    46: _rule("zodiac", _special_zodiac, prefix_width=2),
    47: _rule("zodiac", _special_zodiac),
    48: _rule("zodiac", _special_zodiac, prefix_width=2),
    49: _rule("zodiac", _special_zodiac, prefix_width=3),
    51: _rule("zodiac", _special_zodiac),
    # 平特一肖（mode 56）、厂商「三期平特1肖」（mode 103）、平特3肖（mode 470）
    # 与「平特1尾2码」（mode 173）按平特口径判定：
    # 开奖 7 个号码的任一肖/尾命中预测即算命中。
    56: _rule("zodiac_flat", _flat_zodiacs),
    103: _rule("zodiac_flat", _flat_zodiacs),
    60: _rule("zodiac", _special_zodiac, prefix_width=3),
    69: _rule("zodiac", _special_zodiac),
    72: _rule("zodiac", _special_zodiac),
    78: _rule("zodiac", _special_zodiac),
    117: _rule("zodiac", _special_zodiac),
    197: _rule("zodiac", _special_zodiac),
    219: _rule("zodiac", _special_zodiac),
    470: _rule("zodiac_flat", _flat_zodiacs),
    472: _rule("zodiac_exclusion", _special_zodiac),
    473: _rule("zodiac_exclusion", _special_zodiac),
    484: _rule("zodiac", _special_zodiac, prefix_width=2),
    # Number, head, tail, and basic classification candidates.
    12: _rule("head", _special_head),
    20: _rule("tail_exclusion", _special_tail),
    28: _rule("parity", _special_parity),
    34: _rule("number", _special_number, prefix_width=3),
    38: _rule("wave", _special_wave),
    # 平特1尾（mode 54）与「平特1尾2码」（mode 173）按平特尾口径判定。
    54: _rule("tail_flat", _flat_tails),
    173: _rule("tail_flat", _flat_tails),
    57: _rule("size", _special_size),
    58: _rule("half_wave_exclusion", _special_half_wave),
    # 单双各4尾（mode 30，前台 `003ds4w.js` / getDsWei）：候选是**尾数**，不是号码。
    # `dan` 列 = 4 个单尾（只能取 {1,3,5,7,9}），`shuang` 列 = 4 个双尾（只能取 {0,2,4,6,8}）。
    # 登记为受控规则后，未来期候选改由 `candidate_control` 在分组候选域内枚举，
    # 即使命中目标要求替换某个尾数，也不会把偶尾写进单尾。
    # 2026-09-28 之前该 mode 无规则（silent fallback），实测出现 `dan=3,9,7,0`（184 期）、
    # `dan=0,9,5,1`（166 期）、`shuang=7,...`（179/208/213 期）等越界值。
    30: _rule("tail", _special_tail),
    66: _rule("tail", _special_tail),
    74: _rule("tail", _special_tail, prefix_width=2),
    77: _rule("number", _special_number, prefix_width=2),
    # 10码中特（mode 116 / 表 `mode_payload_116` / 动态 key `title_116` / 站点 twsaimahui）。
    # 口径：`content` 是 10 个逗号分隔号码（`01,17,42,...`），**特码号码落入候选集合即命中**，
    # 所以 truth 目标是特码号码（`_special_number`），不是生肖/尾数/号码外排除。
    # 该 mode 的动态配置已经具备受控所需的一切（由 `_make_number_config` 生成）：
    # `outcome_loader=special_number_from_row`、`content_parser=parse_number_content`、
    # `hit_checker=contains_hit`、`label_count=10`，因此只需在此登记规则即可放行受控链路。
    # 登记前 `get_generation_rule()` 返回 `blocked_pending_rule`：未来期走 silent fallback
    # （纯随机 10/49 + 无规则校验 + 无滚动窗口控制），线上 262-270 连 9 期未中就是该表现。
    # 登记日期 2026-09-29。
    #
    # `prefix_width=2` 的依据（跨站前缀签名 = 前 N 个号码，用于同一期不同站点之间
    # “前 N 位不得雷同”的预约校验）：
    #   1. 同表结构同玩法族对照：mode 34（24码）取 3，mode 77（14码中特）取 2。
    #      mode 116（10码）候选宽度最小，取 2 与 mode 77 一致，绝不会比它更宽；
    #   2. 前缀空间：10 个号码的有序前两位 = 10*9 = 90 种。台湾彩每期启用该模块的站点数为
    #      个位数（同一期每站一条预约），90 > 站数，所以“跨站前二不同”是**可满足**约束，
    #      不需要像二元玩法（大/小，mode 57）那样退化为允许重复前缀；
    #   3. 取 1 会太松（同一期多站共用首位号码时几乎无区分度），取 3 会把前缀空间缩到
    #      10*9*8=720 但也同时收紧相邻期签名比较，而 mode 116 的候选全域只有 10 个号码，
    #      收紧收益有限，取 2 与同族 mode 77 保持一致更便于审阅。
    116: _rule("number", _special_number, prefix_width=2),
    81: _rule("tail", _special_tail),
    123: _rule("tail", _special_tail),
    132: _rule("combined_parity", _combined_parity),
    143: _rule("wave", _special_wave),
    279: _rule("combined_size", _combined_size),
    471: _rule("head", _special_head),
    481: _rule("number_exclusion", _special_number, prefix_width=2),
    483: _rule("head", _special_head),
    485: _rule("number_exclusion", _special_number, prefix_width=2),
    486: _rule("zodiac", _special_zodiac),
    487: _rule("tail", _special_tail),
    488: _rule("head_parity", _special_head_parity),
    489: _rule("zodiac", _special_zodiac),
    490: _rule("half_wave_exclusion", _special_half_wave),
    491: _rule("tail", _special_tail),
    # 三头四尾 (mode 492)：MIXED 任一维度命中口径。2026-09-28 之前
    # ``three_head_four_tail_hit`` 要求头与尾同时命中，与「MIXED 任一维度命中」的项目约束
    # 及供应商样本口径不一致；语义修正后 rule_revision 从 1 升到 2，
    # 让 ``prediction_generation_controls`` 里旧版本的验证结果可以被区分出来。
    492: _rule(
        "head_tail",
        lambda truth, _conn: f"头:{_special_head(truth, _conn)}|尾:{_special_tail(truth, _conn)}",
        revision=2,
    ),
    493: _rule("number", _special_number, prefix_width=3),
    494: _rule("number_exclusion", _special_number, prefix_width=2),
}

#: 只读别名：受控能力审计（规则文档 / 站点清单 assurance）需要按 mode_id 直接查询登记表。
#: 该映射本身不得在运行时被改写；受控链路仍然只通过 `get_generation_rule()` 读取。
RULE_BY_MODE_ID: dict[int, PredictionGenerationRule] = _RULE_BY_MODE_ID


def get_generation_rule(config: Any) -> PredictionGenerationRule:
    """Return the verified future-control rule for a prediction config."""
    try:
        mode_id = int(getattr(config, "default_modes_id", 0) or 0)
    except (TypeError, ValueError):
        return _BLOCKED_RULE
    return _RULE_BY_MODE_ID.get(mode_id, _BLOCKED_RULE)
