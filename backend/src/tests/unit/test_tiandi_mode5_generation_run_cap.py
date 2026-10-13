"""天地生肖（mode 5）未来期连续生成的展示值轮换 + 台账一致性（端到端）。

被测改动（`prediction_generation/diversity.py` + `prediction_generation/service.py`）：
1. `THREE_PERIOD_UNIQUE_MODE_IDS` 补入 `5`，新增 `DISPLAY_UNIQUE_WINDOW_BY_MODE[5] = 4`
   （口径：最多允许连续 3 期同值，禁止第 4 期）与纯函数 `display_run_at_cap()`；
2. `_plan_persisted_future_control(..., recent_display_tokens=...)` 在「再写同值就会
   连续 `display_unique_window(5)` 期相同」时把候选锁到另一个分组标签，并按锁定标签
   反解 `target_hit`（台账与落库一致）；二值展示域（候选域 ≤2）不再用上一期签名当黑名单；
3. `_rotate_tiandi_pair()` 仅对 mode 5 未来期按 `term` 轮转两肖槽（判定/台账只看分组标签）；
4. `prediction.simulation.max_consecutive_*` 已接到跨天台账
   （`prediction_generation_controls`），但不许破坏 `AccuracyPolicy` 滚动准率下限。

Harness：复用 `test_prediction_generation_control_integration.py` 的
`ensure_admin_tables(tmp_path/xxx.sqlite3) + domains.prediction.models.DrawTruth 注入 +
prediction_generation_controls 台账`（真实建库、真实受控计划、真实台账 SQL），
入口用真实的 `prediction_generation.service._process_single_module`（不是纯函数替身）。

落库一致性说明：生产的 `created.mode_payload_*` 只允许写 PostgreSQL
（`utils.created_prediction_store.upsert_created_prediction_row` 对非 postgres 连接直接
报错，见 `ensure_postgres_connection`），因此这里在同一个 sqlite 里建一张与
`created.mode_payload_5` 同列的镜像表，把服务交给 `_persist_generated_row` 的行原样
INSERT 进去、再用 SQL 读回来断言——落库内容经真实 SQL 往返，台账则是服务自己写进
`prediction_generation_controls` 的真实行。
"""

from __future__ import annotations

import json

import pytest

from db import connect
from domains.prediction.accuracy_plan import AccuracyPolicy, validate_rolling_hit_rate
from domains.prediction.generation_control_repository import reserve_control
from domains.prediction.generation_service import build_generated_prediction_row_data
from domains.prediction.generation_rules import get_generation_rule
from domains.prediction.models import DrawTruth
from domains.prediction.simulation_service import SimulationConfig
from prediction_generation import diversity, service
from predict.mechanisms import PREDICTION_CONFIGS, TIANDI_LABEL_FALLBACK
from tables import ensure_admin_tables

MODE_ID = 5
MECHANISM_KEY = "title_5"
LOTTERY_TYPE = 3
YEAR = 2026
WEB_ID = 4
TRUTH_ZODIAC = "虎"  # 地肖：线上事故（twcf888 279-285 连续 7 期「地肖+蛇羊」）的特肖形态
TARGET_HIT_RATE = 0.6

#: `created.mode_payload_5` 的落库列（镜像表列，按生产 created 表的业务列裁剪）。
CREATED_COLUMNS = (
    "type",
    "year",
    "term",
    "web",
    "modes_id",
    "content",
    "xiao",
    "res_code",
    "res_sx",
    "res_color",
    "start",
    "end",
)
_MIRROR_TABLE = "created_mode_payload_5"

_PUBLIC_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS mode_payload_{MODE_ID} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    year TEXT,
    term TEXT,
    web TEXT,
    modes_id INTEGER,
    title TEXT,
    content TEXT,
    xiao TEXT,
    res_code TEXT,
    res_sx TEXT,
    res_color TEXT,
    created_at TEXT
)
"""

_CREATED_MIRROR_SQL = f"""
CREATE TABLE IF NOT EXISTS {_MIRROR_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT, year TEXT, term TEXT, web TEXT, modes_id INTEGER,
    content TEXT, xiao TEXT, res_code TEXT, res_sx TEXT, res_color TEXT,
    start TEXT, end TEXT
)
"""


def _truth(zodiac: str = TRUTH_ZODIAC) -> DrawTruth:
    """未来期真值（只经内存 `DrawTruth` 注入，不写日志/响应）。"""
    return DrawTruth(
        ("01", "02", "03", "04", "05", "06", "27"),
        "27",
        zodiac,
        "绿波",
    )


def _prepare_database(db_path: str) -> None:
    """真实建库：sqlite bootstrap + mode 5 公开表 + 历史行 + 落库镜像表。"""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute(_PUBLIC_TABLE_SQL)
        conn.execute(_CREATED_MIRROR_SQL)
        # 历史行让 predict() 有真实回测样本（mode 5 的 outcome_loader 读 res_sx 末项）。
        for index, (zodiac, content) in enumerate(
            (
                ("兔", '["天肖|兔,马,猴,猪,牛,龙"]'),
                ("虎", '["地肖|鼠,虎,蛇,羊,鸡,狗"]'),
            )
            * 5,
            start=1,
        ):
            conn.execute(
                f"""
                INSERT INTO mode_payload_{MODE_ID} (
                    type, year, term, web, modes_id, title, content, xiao,
                    res_code, res_sx, res_color, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(LOTTERY_TYPE),
                    str(YEAR),
                    str(index),
                    str(WEB_ID),
                    MODE_ID,
                    "天地生肖",
                    content,
                    "兔,马" if zodiac == "兔" else "虎,蛇",
                    "01,02,03,04,05,06,27",
                    zodiac,
                    "绿波",
                    "2026-01-01T00:00:00Z",
                ),
            )


def _install_created_mirror(monkeypatch) -> None:
    """把 `_persist_generated_row` 换成「原样落库到镜像表」的双写点。

    只替代持久化落地动作（真实 created schema 仅接受 PostgreSQL 连接），
    行内容、列裁剪、调用时机全部仍由服务的真实代码路径决定。
    """

    def fake_persist(conn, table_name, row_data, allow_overwrite, *, commit=True):
        row = dict(row_data)
        conn.execute(
            f"""
            INSERT INTO {_MIRROR_TABLE} ({", ".join(CREATED_COLUMNS)})
            VALUES ({", ".join("?" for _ in CREATED_COLUMNS)})
            """,
            tuple(row.get(column) for column in CREATED_COLUMNS),
        )
        return {"action": "inserted"}

    monkeypatch.setattr(service, "_persist_generated_row", fake_persist)


def _build_row(**kwargs):
    """复用生产行构造器（`build_generated_prediction_row_data`），只补 db_path。"""
    return build_generated_prediction_row_data(**kwargs)


def _generated_rows(conn) -> list[dict]:
    """用 SQL 读回落库镜像表（按真实期号顺序）。"""
    rows = conn.execute(
        f"""
        SELECT {", ".join(CREATED_COLUMNS)}
        FROM {_MIRROR_TABLE}
        ORDER BY CAST(term AS INTEGER)
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _ledger_rows(conn) -> dict[int, dict]:
    rows = conn.execute(
        """
        SELECT term, target_hit, verified_hit
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND mode_id = ? AND web_id = ?
        ORDER BY CAST(term AS INTEGER)
        """,
        (LOTTERY_TYPE, MODE_ID, WEB_ID),
    ).fetchall()
    return {int(row["term"]): dict(row) for row in rows}


def _tokens(rows: list[dict]) -> list[str]:
    return [diversity.display_token_for_row(MODE_ID, row) for row in rows]


def _longest_run(tokens: list[str]) -> int:
    longest = 0
    current = 0
    previous = object()
    for token in tokens:
        current = current + 1 if token == previous else 1
        previous = token
        longest = max(longest, current)
    return longest


def _content_members(row: dict) -> list[str]:
    """从落库 content（`["分组名|成员,成员"]`）解析分组成员。"""
    items = json.loads(row["content"])
    assert len(items) == 1, row["content"]
    assert "|" in items[0], row["content"]
    label, members_text = items[0].split("|", 1)
    assert label == diversity.display_token_for_row(MODE_ID, row)
    return [member for member in members_text.split(",") if member]


@pytest.fixture()
def mode5_env(monkeypatch, tmp_path):
    """mode 5 端到端环境：真实建库 + 真值注入 + 落库镜像。"""
    db_path = str(tmp_path / "tiandi-mode5.sqlite3")
    _prepare_database(db_path)
    _install_created_mirror(monkeypatch)
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda _conn, *, year, term, **kwargs: _truth(),
    )
    return {
        "db_path": db_path,
        "config": PREDICTION_CONFIGS[MECHANISM_KEY],
    }


def _process_future_terms(env, terms: list[int]) -> dict:
    """按真实服务入口连续生成未来期（同一站点、同一批次）。"""
    with connect(env["db_path"]) as conn:
        report = service._process_single_module(
            conn=conn,
            module_row={"id": 1, "mechanism_key": MECHANISM_KEY, "mode_id": MODE_ID},
            draws=[],
            future_draws=[
                {"year": YEAR, "term": term, "numbers_str": "", "_future": True}
                for term in terms
            ],
            future_only=True,
            safety_draw_map={(YEAR, term): True for term in terms},
            lottery_type=LOTTERY_TYPE,
            site_id=WEB_ID,
            site_web_id=WEB_ID,
            db_path=env["db_path"],
            default_target_hit_rate=TARGET_HIT_RATE,
            simulation_config=SimulationConfig(target_hit_rate=TARGET_HIT_RATE),
            zodiac_map={"27": TRUTH_ZODIAC},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, mode_id, _fallback: f"mode_payload_{mode_id}",
            build_generated_prediction_row_data=_build_row,
        )
        report["_rows"] = _generated_rows(conn)
        report["_ledger"] = _ledger_rows(conn)
    return report


def test_mode_5_future_rows_never_reach_four_identical_display_tokens(mode5_env):
    """连续 12 期未来 mode 5 行：展示值最多连续 3 期相同，禁止第 4 期；内容/台账互相一致。

    真值固定为「虎」（地肖），即线上连值事故的形态：命中偏好与「换展示值」直接冲突，
    必须由 `display_run_at_cap` 在受控计划里把候选锁到另一分组来化解。
    """
    terms = list(range(301, 313))
    report = _process_future_terms(mode5_env, terms)

    assert report["errors"] == 0, report
    assert report["inserted"] == len(terms), report
    assert report["warnings"] == [], report["warnings"]

    rows = report["_rows"]
    assert [int(row["term"]) for row in rows] == terms
    assert [row["type"] for row in rows] == [str(LOTTERY_TYPE)] * len(terms)
    assert [row["web"] for row in rows] == [str(WEB_ID)] * len(terms)
    assert [int(row["modes_id"]) for row in rows] == [MODE_ID] * len(terms)

    # 未来期不得携带任何开奖结果字段。
    assert [row["res_code"] for row in rows] == [""] * len(terms)
    assert [row["res_sx"] for row in rows] == [""] * len(terms)
    assert [row["res_color"] for row in rows] == [""] * len(terms)

    tokens = _tokens(rows)
    assert all(tokens), tokens
    assert len(set(tokens)) == 2, tokens
    # mode 5 口径：window=4 ⇒ 允许连续 3 期同值，禁止第 4 期。
    window = diversity.display_unique_window(MODE_ID)
    assert window == 4
    cap = window - 1
    assert cap == 3
    assert diversity.display_run_at_cap(MODE_ID, ("地肖", "地肖")) is False
    assert diversity.display_run_at_cap(MODE_ID, ("地肖", "地肖", "地肖")) is True
    assert _longest_run(tokens) <= cap, f"展示值出现连续 {_longest_run(tokens)} 期相同: {tokens}"

    # 上限真的被触发过：出现过「连续 3 期同值」，且紧接着的第 4 期必须换值
    # （若受控计划没读到 `recent_display_tokens`，第 4 期会继续同值）。
    enforced = [
        index
        for index in range(3, len(tokens))
        if tokens[index - 3] == tokens[index - 2] == tokens[index - 1]
        and tokens[index] != tokens[index - 1]
    ]
    assert enforced, f"未观察到「连续 3 期同值后第 4 期强制换值」的受控轮换: {tokens}"

    for row in rows:
        members = _content_members(row)
        xiao = [item for item in str(row["xiao"]).split(",") if item]
        # 两肖槽必须落在本行分组成员内（面板与判定同向）。
        assert len(xiao) == 2, row
        assert set(xiao) <= set(members), row
        assert set(members) == set(TIANDI_LABEL_FALLBACK[diversity.display_token_for_row(MODE_ID, row)])

    # 同分组相邻期的两肖组合必须不同（线上「地肖+蛇羊」连值的那条缺陷）。
    for previous, current in zip(rows, rows[1:]):
        if diversity.display_token_for_row(MODE_ID, previous) == diversity.display_token_for_row(MODE_ID, current):
            assert previous["xiao"] != current["xiao"], (previous, current)

    # 台账与落库内容一致：verified_hit == (真值分组 == 落库分组) == (target == verified)。
    ledger = report["_ledger"]
    assert sorted(ledger) == terms
    hits: list[bool] = []
    for row in rows:
        term = int(row["term"])
        expected_hit = TRUTH_ZODIAC in _content_members(row)
        entry = ledger[term]
        assert bool(entry["verified_hit"]) == expected_hit, (term, entry, row)
        assert bool(entry["target_hit"]) == bool(entry["verified_hit"]), (term, entry)
        hits.append(bool(entry["verified_hit"]))
    assert any(hits) and not all(hits), hits

    assert validate_rolling_hit_rate(hits, policy=AccuracyPolicy(minimum_hit_rate=TARGET_HIT_RATE)) == []


def test_mode_5_miss_cap_forces_a_verified_hit_from_the_cross_day_ledger(mode5_env):
    """连续未中达 `max_consecutive_misses` 时，下一期必须是命中（台账驱动，非内存态）。"""
    term = 401
    simulation_config = SimulationConfig(target_hit_rate=TARGET_HIT_RATE)
    assert simulation_config.normalized().max_consecutive_misses == 3
    plan_kwargs = {
        "config": mode5_env["config"],
        "lottery_type": LOTTERY_TYPE,
        "site_id": WEB_ID,
        "site_web_id": WEB_ID,
        "draw": {"year": YEAR, "term": term},
        "truth": _truth(),
        "simulation_config": simulation_config,
        "mechanism_key": MECHANISM_KEY,
        "predicted_labels": ("天肖",),
    }

    with connect(mode5_env["db_path"]) as conn:
        baseline = service._plan_persisted_future_control(conn=conn, **plan_kwargs)
        assert baseline is not None
        # 未被连续上限干预时，本期本会是「不中」。
        assert baseline.target_hit is False
        assert baseline.verified_hit is False

        for missed_term in (398, 399, 400):
            reserved = reserve_control(
                conn,
                lottery_type_id=LOTTERY_TYPE,
                year=YEAR,
                term=missed_term,
                mode_id=MODE_ID,
                web_id=WEB_ID,
                rule_id=baseline.rule_id,
                rule_revision=baseline.rule_revision,
                target_hit=False,
                verified_hit=False,
                signature=("天肖",),
                prefix_signature=("天肖",),
                created_at="2026-07-01T00:00:00Z",
            )
            assert reserved["reserved"] is True, reserved

        capped = service._plan_persisted_future_control(conn=conn, **plan_kwargs)
        assert capped is not None
        # 到期必须命中，且候选就是真值所属分组。
        assert capped.target_hit is True
        assert capped.verified_hit is True
        assert capped.labels == ("地肖",)
        # 判定必须来自真实生成规则（内容 / 台账 / 判定三方同源）。
        assert get_generation_rule(mode5_env["config"]).verify_hit(
            mode5_env["config"], capped.labels, _truth(), conn=conn
        ) is True

    outcomes = [False, False, False, bool(capped.verified_hit)]
    assert validate_rolling_hit_rate(
        outcomes, policy=AccuracyPolicy(minimum_hit_rate=TARGET_HIT_RATE)
    ) == []


def test_mode_5_hit_cap_forces_a_verified_miss_while_policy_still_has_room(mode5_env):
    """连续命中达 `max_consecutive_hits` 时下一期必须未中；滚动准率仍有空间才允许。"""
    term = 402
    simulation_config = SimulationConfig(target_hit_rate=TARGET_HIT_RATE)
    assert simulation_config.normalized().max_consecutive_hits == 3
    plan_kwargs = {
        "config": mode5_env["config"],
        "lottery_type": LOTTERY_TYPE,
        "site_id": WEB_ID,
        "site_web_id": WEB_ID,
        "draw": {"year": YEAR, "term": term},
        "truth": _truth(),
        "simulation_config": simulation_config,
        "mechanism_key": MECHANISM_KEY,
        "predicted_labels": ("天肖",),
    }

    with connect(mode5_env["db_path"]) as conn:
        baseline = service._plan_persisted_future_control(conn=conn, **plan_kwargs)
        assert baseline is not None
        assert baseline.target_hit is True

        for hit_term in (399, 400, 401):
            reserved = reserve_control(
                conn,
                lottery_type_id=LOTTERY_TYPE,
                year=YEAR,
                term=hit_term,
                mode_id=MODE_ID,
                web_id=WEB_ID,
                rule_id=baseline.rule_id,
                rule_revision=baseline.rule_revision,
                target_hit=True,
                verified_hit=True,
                signature=("地肖",),
                prefix_signature=("地肖",),
                created_at="2026-07-01T00:00:00Z",
            )
            assert reserved["reserved"] is True, reserved

        capped = service._plan_persisted_future_control(conn=conn, **plan_kwargs)
        assert capped is not None
        assert capped.target_hit is False
        assert capped.verified_hit is False
        assert capped.labels == ("天肖",)
        assert get_generation_rule(mode5_env["config"]).verify_hit(
            mode5_env["config"], capped.labels, _truth(), conn=conn
        ) is False

    # 上限优先不等于可以击穿滚动准率下限：窗口内未中数仍在上限之内。
    policy = AccuracyPolicy(minimum_hit_rate=TARGET_HIT_RATE).normalized()
    window_outcomes = [True, True, True, bool(capped.verified_hit)]
    assert window_outcomes[-policy.window_size:].count(False) < policy.maximum_misses
    assert validate_rolling_hit_rate(
        window_outcomes, policy=AccuracyPolicy(minimum_hit_rate=TARGET_HIT_RATE)
    ) == []
