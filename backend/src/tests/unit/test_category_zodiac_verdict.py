"""判定口径契约：「特肖所属分类」类玩法（红蓝绿肖 / 肉菜草肖 / 四季生肖…）的 is_correct 复算。

背景（2026-09-28 线上实测 + 本地复算）
------------------------------------
twbst528(web 10) 的 ``hllx``「红蓝绿肖（3选2）」(mode 8) 本地 6/6 期、线上 6/6 期
``is_correct`` 恒为 ``False``，页面恒显示「错」。

根因（逐期实测，见 ``.codex-temp/hllx_evidence.txt``）::

    行正文   = ["红肖|马,兔,鼠,鸡", "蓝肖|蛇,虎,猪,猴"]
    候选标签 = ('红肖', '蓝肖')                      # parse_pipe_label_content
    复合串   = 双数|大数|双|大|2头|2头双|6尾|6|蓝波|蓝双|合双|合数大|野兽|蛇|26|金|琴|4段
    contains_hit 的实际比较 = any(label in outcome)   # 子串判定
    → '红肖' / '蓝肖' 都不是复合串的原子 → 恒 False

口径（钉死）：**特肖所属分类 ∈ 预测的分类集合即命中**（红蓝绿肖 3选2 与
``backend/docs/prediction-module-rules.md`` 的 「特码生肖所属分类落入预测分类则命中」一致）。

修法：``public/api.py::_compute_outcome_from_row`` 补上「特肖所属分类」原子，
分类取自**该行正文自己声明的生肖分组**（``predict.common.zodiac_category_labels``），
与机制 ``outcome_loader``（``make_pipe_category_outcome`` / ``make_dynamic_pipe_outcome``）
和 ``scripts/audit-verdict-truth.py`` 的真值模型同源。

同族 mode（同一类缺陷，本文件一并锁定）：mode 3 肉菜草肖（3选2）、mode 61 四季生肖（4选3）。
"""
from __future__ import annotations

import pytest

from predict.common import zodiac_category_labels
from predict.mechanisms import PREDICTION_CONFIGS
from public.api import _compute_outcome_from_row, serialize_public_history_row

# ── 独立真值表（测试自带，不读库、不借用被测实现）──────────────────

#: 与 ``public.fixed_data`` sign='生肖' 一致的号码 → 生肖（2026 台湾彩口径）。
ZODIAC_CODES: dict[str, str] = {
    "马": "01,13,25,37,49",
    "蛇": "02,14,26,38",
    "龙": "03,15,27,39",
    "兔": "04,16,28,40",
    "虎": "05,17,29,41",
    "牛": "06,18,30,42",
    "鼠": "07,19,31,43",
    "猪": "08,20,32,44",
    "狗": "09,21,33,45",
    "鸡": "10,22,34,46",
    "猴": "11,23,35,47",
    "羊": "12,24,36,48",
}

#: 与 ``public.fixed_data`` 一致的分类分组（status=1）。
FIXED_GROUPS: dict[str, dict[str, str]] = {
    "红蓝绿肖": {"红肖": "马,兔,鼠,鸡", "蓝肖": "蛇,虎,猪,猴", "绿肖": "羊,龙,牛,狗"},
    "肉菜草肖": {"肉肖": "虎,蛇,龙,狗", "菜肖": "猪,鼠,鸡,猴", "草肖": "牛,羊,马,兔"},
    "四季肖": {"春肖": "兔,虎,龙", "夏肖": "羊,蛇,马", "秋肖": "狗,鸡,猴", "冬肖": "猪,牛,鼠"},
}


def code_to_zodiac() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for zodiac, codes in ZODIAC_CODES.items():
        for code in codes.split(","):
            mapping[code] = zodiac
    return mapping


CODE_TO_ZODIAC = code_to_zodiac()


def expected_group(sign: str, code: str) -> str:
    """独立复算：特码号码 → 生肖 → 该分类体系下的分类名。"""
    zodiac = CODE_TO_ZODIAC[code]
    for label, members in FIXED_GROUPS[sign].items():
        if zodiac in members.split(","):
            return label
    raise AssertionError(f"{sign} 未覆盖生肖 {zodiac}")


def _row(code: str, content: str, *, opened: bool = True) -> dict[str, object]:
    zodiac = CODE_TO_ZODIAC.get(code, "")
    others = [value for value in "鼠牛虎兔龙蛇马羊猴鸡狗猪" if value != zodiac][:6]
    return {
        "year": "2026",
        "term": "222",
        "res_code": ",".join(["01"] * 6 + [code]) if opened else "",
        "res_sx": ",".join(others + [zodiac]) if opened else "",
        "res_color": "red,red,red,red,red,red,blue" if opened else "",
        "draw_is_opened": 1 if opened else 0,
        "content": content,
    }


HLLX_CONTENT = '["红肖|马,兔,鼠,鸡", "蓝肖|蛇,虎,猪,猴"]'
RCCA_CONTENT = '["草肖|牛,羊,马,兔", "肉肖|虎,蛇,龙,狗"]'
SIJI3_CONTENT = '["春肖|兔,虎,龙", "夏肖|羊,蛇,马", "冬肖|猪,牛,鼠"]'


# ── 复合 outcome 原子 ────────────────────────────────────────────


def test_outcome_carries_special_zodiac_category_atom():
    """特肖所属分类必须是复合串的原子（旧实现缺失 → 子串判定恒 False）。"""
    atoms = _compute_outcome_from_row(_row("26", HLLX_CONTENT)).split("|")

    # 26 → 蛇 → 蓝肖（候选里只有 红肖/蓝肖）
    assert "蓝肖" in atoms
    assert "红肖" not in atoms
    assert "绿肖" not in atoms
    # 原有原子一个都不能少
    for atom in ("双数", "大数", "双", "大", "2头", "2头双", "6尾", "6", "蓝波", "蓝双",
                 "合双", "合数大", "野兽", "蛇", "26", "金", "琴", "4段"):
        assert atom in atoms, f"缺少既有原子 {atom}"


def test_category_atom_never_comes_from_number_group_content():
    """成员是号码的分组（土|05,06,… / 小单|01,03,…）不能被当成特肖分类。"""
    atoms = _compute_outcome_from_row(_row("26", '["土|05,06,19,20,27"]')).split("|")
    assert "金" in atoms  # 五行原子照旧（26 → 金），号码分组不参与
    assert "土" not in atoms
    atoms = _compute_outcome_from_row(_row("26", '["小单|01,03,05,07,09,11"]')).split("|")
    assert not any(atom.startswith("小单") for atom in atoms)

    # 连号码带生肖的混合分组（mode_payload_161 形状）同样不参与
    mixed = '["家禽|01,05,06,牛,牛|07,狗"]'
    assert zodiac_category_labels(mixed, "马") == ()
    assert zodiac_category_labels(mixed, "牛") == ()


def test_zodiac_category_labels_helper_contract():
    content = '["红肖|马,兔,鼠,鸡", "蓝肖|蛇,虎,猪,猴", "绿肖|羊,龙,牛,狗"]'
    assert zodiac_category_labels(content, "马") == ("红肖",)
    assert zodiac_category_labels(content, "蛇") == ("蓝肖",)
    assert zodiac_category_labels(content, "牛") == ("绿肖",)
    # 普通串（非 JSON 数组）整体当一个分组，不能按逗号拆
    assert zodiac_category_labels("草肖|牛,羊,马,兔", "马") == ("草肖",)
    # 繁体生肖归一化后同样命中
    assert zodiac_category_labels('["红肖|馬,兔,鼠,雞"]', "马") == ("红肖",)
    # 未开奖 / 未知生肖
    assert zodiac_category_labels(content, "") == ()
    assert zodiac_category_labels("", "马") == ()


# ── hllx（mode 8，红蓝绿肖 3选2）─────────────────────────────────


@pytest.mark.parametrize(
    "content",
    [
        HLLX_CONTENT,                                       # 蓝肖 ∈ 候选
        '["红肖|马,兔,鼠,鸡", "绿肖|羊,龙,牛,狗"]',           # 蓝肖 ∉ 候选
        '["绿肖|羊,龙,牛,狗", "蓝肖|蛇,虎,猪,猴"]',           # 绿肖 ∈ 候选
    ],
)
def test_hllx_verdict_for_every_number(content: str):
    """01-49 逐码复算：特肖分类 ∈ 候选 → 对，否则错（真值由测试自带分组表独立算出）。"""
    config = PREDICTION_CONFIGS["hllx"]
    assert int(config.default_modes_id) == 8

    for code in sorted(CODE_TO_ZODIAC):
        truth = expected_group("红蓝绿肖", code) in content
        serialized = serialize_public_history_row(_row(code, content), config)
        assert serialized["is_correct"] is truth, f"{code} 判定与独立真值不一致"


def test_hllx_verdict_matches_independent_recompute_for_real_periods():
    """本地库 web 10 mode 8 的真实 10 期（候选 + 开奖特码），逐期与独立真值比对。"""
    config = PREDICTION_CONFIGS["hllx"]
    periods = [
        ("222", "26", HLLX_CONTENT, True),
        ("218", "17", '["红肖|马,兔,鼠,鸡", "绿肖|羊,龙,牛,狗"]', False),
        ("217", "26", '["红肖|马,兔,鼠,鸡", "绿肖|羊,龙,牛,狗"]', False),
        ("216", "37", '["红肖|马,兔,鼠,鸡", "绿肖|羊,龙,牛,狗"]', True),
        ("215", "14", '["红肖|马,兔,鼠,鸡", "蓝肖|蛇,虎,猪,猴"]', True),
        ("214", "04", '["蓝肖|蛇,虎,猪,猴", "红肖|马,兔,鼠,鸡"]', True),
        ("213", "35", '["绿肖|羊,龙,牛,狗", "蓝肖|蛇,虎,猪,猴"]', True),
        ("212", "06", '["红肖|马,兔,鼠,鸡", "绿肖|羊,龙,牛,狗"]', True),
        ("211", "01", '["绿肖|羊,龙,牛,狗", "蓝肖|蛇,虎,猪,猴"]', False),
        ("210", "49", '["蓝肖|蛇,虎,猪,猴", "红肖|马,兔,鼠,鸡"]', True),
    ]
    for term, code, content, expect in periods:
        row = _row(code, content)
        row["term"] = term
        # 独立真值：特肖分类 ∈ 候选
        truth = expected_group("红蓝绿肖", code) in content
        assert truth is expect
        assert serialize_public_history_row(row, config)["is_correct"] is expect


def test_hllx_pending_row_has_no_verdict():
    config = PREDICTION_CONFIGS["hllx"]
    serialized = serialize_public_history_row(_row("", HLLX_CONTENT, opened=False), config)
    assert serialized["is_opened"] is False
    assert serialized["is_correct"] is None


# ── 同族 mode：肉菜草肖（3）/ 四季生肖（61）───────────────────────


@pytest.mark.parametrize(
    "key, mode_id, sign, content",
    [
        ("rcca", 3, "肉菜草肖", RCCA_CONTENT),
        ("siji3", 61, "四季肖", SIJI3_CONTENT),
    ],
)
def test_category_family_verdict_for_every_number(key: str, mode_id: int, sign: str, content: str):
    config = PREDICTION_CONFIGS[key]
    assert int(config.default_modes_id) == mode_id

    for code in sorted(CODE_TO_ZODIAC):
        truth = expected_group(sign, code) in content
        serialized = serialize_public_history_row(_row(code, content), config)
        assert serialized["is_correct"] is truth, f"{key} {code} 判定与独立真值不一致"


# ── 共用路径回归：候选是生肖 / 五行原子的玩法不受影响 ─────────────


def test_zodiac_and_element_plays_are_unaffected_by_category_atoms():
    """新增分类原子不得改变「候选本身就是生肖 / 五行」的玩法判定。"""
    three_hang = PREDICTION_CONFIGS["3hang"]
    content = '["木|07,08,15,16,23,24,37,38,45,46", "金|03,04,11,12,25,26,33,34,41,42"]'
    # 号码五行取权威分组：26 → 金 ∈ 候选 → 对；25 → 金 ∈ 候选 → 对
    assert serialize_public_history_row(_row("26", content), three_hang)["is_correct"] is True
    assert serialize_public_history_row(_row("25", content), three_hang)["is_correct"] is True
    # 27 → 土 ∉ 候选 → 错；21 → 水 ∉ 候选 → 错
    assert serialize_public_history_row(_row("27", content), three_hang)["is_correct"] is False
    assert serialize_public_history_row(_row("21", content), three_hang)["is_correct"] is False

    three_zxt = PREDICTION_CONFIGS["3zxt"]
    zodiacs = '["蛇","猴","鸡"]'
    assert serialize_public_history_row(_row("26", zodiacs), three_zxt)["is_correct"] is True
    assert serialize_public_history_row(_row("37", zodiacs), three_zxt)["is_correct"] is False

    juesha1wei = PREDICTION_CONFIGS["juesha1wei"]
    # 26 → 6尾；候选只杀 1尾 → 杀中（对）；候选含 6尾 → 杀不中（错）
    assert serialize_public_history_row(_row("26", "1尾"), juesha1wei)["is_correct"] is True
    assert serialize_public_history_row(_row("26", "6尾"), juesha1wei)["is_correct"] is False


def test_no_config_label_still_collides_with_category_atoms():
    """共用 outcome 的影响面守门：任何玩法的候选标签都不得是新增分类原子的**严格子串**。

    ``_check_correct_by_mechanism`` 对标准 contains/excludes 走 ``label in outcome``，
    所以只有当候选标签是某个分类原子的子串时才会被新增原子误命中（相等是本次要修的
    正常情形）。分类原子清单来自各站 mode_payload 里「生肖分组」的标签
    （见 ``docs/prediction-display-standard.md`` 的 hllx 修复记录）。

    原子由**本行 content 自己声明的分组**推出，标签来自本玩法的静态 labels，
    因此只有「同一张表既声明了该分组、候选标签又是它的子串」才会真的误命中。
    经验守门是 ``scripts/audit-verdict-truth.py``：本改动在 29817 行上 0 新增 finding。
    """
    from predict.mechanisms import build_title_prediction_configs

    atoms = {
        "红肖", "蓝肖", "绿肖", "肉肖", "菜肖", "草肖",
        "春肖", "夏肖", "秋肖", "冬肖",
        "阴肖", "阳肖", "文肖", "武肖", "左肖", "右肖", "天肖", "地肖",
        "有肖", "无肖", "肥肖", "瘦肖", "笔肖", "墨肖", "纸肖", "砚肖",
        "凶丑肖", "吉美肖", "凶丑", "吉美", "胆大生肖", "胆小生肖",
        "风", "雨", "雷", "电", "家禽", "野兽",
    }
    #: 结构性可容忍碰撞：标签与原子来自**不同 mode_payload 表**，同一行不可能同时出现
    #: （mode 480 的正文只声明「凶丑 / 吉美」，mode 155 才声明「凶丑肖 / 吉美肖」；
    #: mode 57 / 108 的正文是号码分组，永远推不出「胆大生肖 / 胆小生肖」原子）。
    tolerated = {
        ("xiongjiliuxiao", "凶丑", "凶丑肖"),
        ("xiongjiliuxiao", "吉美", "吉美肖"),
        ("daxiao", "小", "胆小生肖"),
        ("daxiao", "大", "胆大生肖"),
        ("dxztt1", "小", "胆小生肖"),
        ("dxztt1", "大", "胆大生肖"),
    }
    configs = dict(PREDICTION_CONFIGS)
    configs.update({k: v for k, v in build_title_prediction_configs().items() if k not in configs})
    collisions: set[tuple[str, str, str]] = set()
    for key, config in configs.items():
        for raw in tuple(getattr(config, "labels", ()) or ()):
            label = str(raw)
            if not label:
                continue
            for atom in atoms:
                if label != atom and label in atom:
                    collisions.add((key, label, atom))
    assert collisions == tolerated, (
        "候选标签与分类原子的子串碰撞发生变化："
        f"新增 {sorted(collisions - tolerated)}，消失 {sorted(tolerated - collisions)}"
    )
