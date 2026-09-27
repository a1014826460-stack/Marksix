"""mode 38（双波中特）：波色标签正文必须能解析并算出 True/False，不能恒为 None。

回归背景：`shuangbo` 的 `content_parser` 原先误用 `parse_zodiac_content`
（只识别生肖字），而历史正文是波色**标签**（`蓝波,绿波` / `["蓝波|03,04…","绿波|05,06…"]`），
解析结果恒为空 tuple → `public.api._check_correct_by_mechanism` 直接返回 `None`
→ 前端拿不到对/错，命中也不显示判定（twcf888 `#pred-amgst-38`/`#pred-jhq-38`、
twwanli `#hblvxiao`、twsyw `#shuangbo`/`#hblvxiao` 共用后端）。

命中口径（与 `backend/docs/prediction-module-rules.md`、`title_143` 一波中特一致）：
**特码所属波色 ∈ 预测的两个波色 → 命中**。
波色取值口径复用仓库既有实现：`predict.categories.size_parity.special_wave_from_row`
（`res_color` 末位 red/blue/green）与 `public.api._compute_outcome_from_row`
中的 `{"red": "红波", "blue": "蓝波", "green": "绿波"}` 映射。
"""

from __future__ import annotations

from predict.categories import content_columns
from predict.common import parse_zodiac_content
from predict.mechanisms import PREDICTION_CONFIGS
from public.api import _check_correct_by_mechanism


def _row(code: str, color: str, zodiac: str = "马") -> dict[str, str]:
    """构造与 public.api 入参同形的历史行：res_code / res_sx / res_color 都是逗号串。"""
    return {
        "res_code": f"01,02,03,04,05,06,{code}",
        "res_sx": f"鼠,牛,虎,兔,龙,蛇,{zodiac}",
        "res_color": f"red,red,red,red,red,red,{color}",
    }


def _config():
    return PREDICTION_CONFIGS["shuangbo"]


def test_shuangbo_uses_literal_label_parser_not_zodiac_parser():
    """解析器必须认波色标签；修复前的生肖解析器对同一正文恒为空。"""
    config = _config()

    assert config.content_parser is content_columns.parse_literal_label_content
    assert config.content_parser("蓝波,绿波") == ("蓝波", "绿波")
    # 修复前的解析器对波色标签恒为空 —— 这正是 is_correct 恒为 None 的根因
    assert parse_zodiac_content("蓝波,绿波") == ()


def test_shuangbo_parser_accepts_json_and_pipe_shapes():
    config = _config()

    assert config.content_parser('["蓝波|03,04,09","绿波|05,06,11"]') == ("蓝波", "绿波")
    assert config.content_parser("红波,蓝波") == ("红波", "蓝波")


def test_shuangbo_hit_when_special_wave_in_prediction():
    """特码波色落在预测的两个波色里 → 命中。"""
    config = _config()

    # 190 期：预测 红波,绿波；特码 45 是红波 → 命中
    assert _check_correct_by_mechanism("红波,绿波", _row("45", "red"), config) is True
    # 189 期：预测 蓝波,红波；特码 09 是蓝波 → 命中
    assert _check_correct_by_mechanism("蓝波,红波", _row("09", "blue"), config) is True
    # 188 期：预测 绿波,红波；特码 38 是绿波 → 命中
    assert _check_correct_by_mechanism("绿波,红波", _row("38", "green"), config) is True


def test_shuangbo_miss_when_special_wave_outside_prediction():
    """特码波色不在预测的两个波色里 → 未命中（False，而不是 None）。"""
    config = _config()

    # 186 期：预测 绿波,红波；特码 42 是蓝波 → 未命中
    assert _check_correct_by_mechanism("绿波,红波", _row("42", "blue"), config) is False
    # 182 期：预测 蓝波,绿波；特码 12 是红波 → 未命中
    assert _check_correct_by_mechanism("蓝波,绿波", _row("12", "red"), config) is False


def test_shuangbo_pending_period_stays_none():
    """未开奖（无 res_code）仍然必须是 None，不能因为解析器变好就给出判定。"""
    config = _config()
    pending = {"res_code": "", "res_sx": "", "res_color": ""}

    assert _check_correct_by_mechanism("红波,蓝波", pending, config) is None


def test_shuangbo_formatter_keeps_history_shape():
    """正文格式保持 `红波,蓝波`，不得改动对外形状。"""
    formatter = _config().content_formatter
    assert formatter(("红波", "蓝波"), None) == "红波,蓝波"
