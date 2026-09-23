"""预测资料不可变合同：自动流程不得改写或删除已生成的预测资料。

业务要求（2026-09-24）：
- 预测资料一旦生成，除管理员手动更改/删除外，任何自动流程（定时生成、开奖后补跑、
  缺口回填、结果回填）都不得改写其正文，也不得删除既有行；
- 自动流程只允许"补缺失行"和"回填空的结果字段"；
- 覆盖既有正文必须由管理台路由显式授权（``allow_overwrite=True``）。

这些用例是防回归护栏：任何把缺省值改回"默认覆盖"、或让自动路径隐式继承覆盖权限的改动，
都会在这里失败。
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

from db import connect
from domains.prediction import backfill_repository, service as prediction_service
from prediction_generation import service as generation_service
from routes import admin_lottery_routes_extra, admin_site_routes
from tests.helpers.api_contract import make_ctx, response_json

_SRC_ROOT = Path(__file__).resolve().parents[2]


def _read_source(relative_path: str) -> str:
    return (_SRC_ROOT / relative_path).read_text(encoding="utf-8")


# ── 1. 缺省值必须是不覆盖 ──────────────────────────────────────────


def test_generate_prediction_batch_defaults_to_no_overwrite():
    """批量生成编排入口缺省不得覆盖既有预测正文。"""
    parameter = inspect.signature(generation_service.generate_prediction_batch).parameters[
        "allow_overwrite"
    ]
    assert parameter.default is False


def test_bulk_generate_defaults_to_no_overwrite_and_requires_explicit_opt_in():
    """站点批量生成缺省 allow_overwrite=False，只有显式传 True 才允许覆盖。"""
    captured: list[dict] = []

    def _fake_batch(_db_path, **kwargs):
        captured.append(kwargs)
        return {"inserted": 0, "updated": 0, "skipped_existing": 0, "errors": 0, "modules": []}

    payload = {"lottery_type": 3, "start_issue": "2026001", "end_issue": "2026001"}
    with patch.object(prediction_service, "ensure_prediction_configs_loaded"), \
         patch("domains.sites.service.get_site", return_value={"id": 7, "lottery_type_id": 3}), \
         patch(
             "prediction_generation.service.generate_prediction_batch",
             side_effect=_fake_batch,
         ):
        prediction_service.bulk_generate_site_predictions("fake-db", 7, dict(payload))
        prediction_service.bulk_generate_site_predictions(
            "fake-db",
            7,
            dict(payload, trigger="admin_generate_all", allow_overwrite=True),
        )

    assert captured[0]["allow_overwrite"] is False
    assert captured[0]["trigger"] == "unspecified"
    assert captured[1]["allow_overwrite"] is True


def test_admin_generate_all_route_explicitly_authorizes_overwrite():
    """管理台 generate-all 是"管理员手动更改"入口，必须显式授权覆盖。"""
    ctx = make_ctx(
        "/api/admin/sites/7/prediction-modules/generate-all",
        method="POST",
        payload={"lottery_type": "3", "start_issue": "2026001", "end_issue": "2026001"},
    )
    site = type("Site", (), {"site_id": 7, "web_id": 6, "lottery_type_id": 3})()

    with patch("routes.admin_site_routes.parse_site_route_context") as parse_context, \
         patch("routes.admin_site_routes.resolve_site_context", return_value=site), \
         patch("routes.admin_site_routes.validate_web_matches_site"), \
         patch("routes.admin_site_routes.require_site_generation_access"), \
         patch("domains.sites.permissions.can_access_site", return_value=True), \
         patch("routes.admin_site_routes.enqueue_manual_job", return_value="job-1") as enqueue:
        parse_context.return_value.parts = [
            "", "api", "admin", "sites", "7", "prediction-modules", "generate-all",
        ]
        parse_context.return_value.site_id = 7
        admin_site_routes.site_detail(ctx)

    options = enqueue.call_args.kwargs["payload"]["options"]
    assert options["allow_overwrite"] is True
    assert options["trigger"] == "admin_generate_all"
    assert response_json(ctx)["job_id"] == "job-1"


# ── 2. 自动路径必须显式声明不覆盖 ──────────────────────────────────


def test_scheduler_automatic_paths_declare_no_overwrite():
    """调度器自动生成（每日预测、近期待补）必须显式传 allow_overwrite=False。"""
    source = _read_source("crawler/scheduler.py")
    call_sites = [index for index in range(len(source)) if source.startswith("_bulk_gen(", index)]
    assert call_sites, "期望在调度器中找到自动生成调用点"

    for index in call_sites:
        block = source[index: index + 800]
        assert '"allow_overwrite": False' in block, (
            "自动生成调用必须显式声明 allow_overwrite=False，避免继承任何覆盖缺省值"
        )


def test_crawl_and_generate_is_an_explicit_admin_action():
    """抓取并生成只能由管理台手动任务触发，必须显式声明管理员来源与覆盖授权。"""
    source = _read_source("crawler/collectors.py")
    assert '"trigger": "admin_crawl_and_generate"' in source
    assert '"allow_overwrite": True' in source


# ── 3. 自动结果回填只填空白列 ─────────────────────────────────────


def _create_result_table(conn) -> None:  # noqa: ANN001 - 测试内联建表
    conn.execute(
        "CREATE TABLE mode_payload_43 ("
        "id INTEGER PRIMARY KEY, type TEXT, year TEXT, term TEXT, "
        "content TEXT, res_code TEXT, res_sx TEXT, res_color TEXT)"
    )
    rows = [
        # 全空：应当被完整回填
        (1, "3", "2026", "266", "auto-content", "", "", ""),
        # res_code 已有：只补 res_sx/res_color，res_code 与正文保持不变
        (2, "3", "2026", "266", "auto-content", "01,02,03", "", ""),
        # 管理员手工填过 res_sx/res_color：只补 res_code，手工值不得被覆盖
        (3, "3", "2026", "266", "admin-edited-content", "", "ADMIN-SX", "ADMIN-COLOR"),
        # 已完整：完全不动
        (4, "3", "2026", "266", "auto-content", "OLD", "OLD-SX", "OLD-COLOR"),
        # 其它期号：不受影响
        (5, "3", "2026", "265", "auto-content", "", "", ""),
        # 其它彩种：不受影响
        (6, "2", "2026", "266", "auto-content", "", "", ""),
    ]
    conn.executemany(
        "INSERT INTO mode_payload_43 "
        "(id, type, year, term, content, res_code, res_sx, res_color) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def _select_result_rows(conn, *ids: int) -> dict[int, tuple]:
    marks = ", ".join(["?"] * len(ids))
    rows = conn.execute(
        f"SELECT id, content, res_code, res_sx, res_color FROM mode_payload_43 "
        f"WHERE id IN ({marks}) ORDER BY id",
        list(ids),
    ).fetchall()
    return {int(row["id"]): (row["content"], row["res_code"], row["res_sx"], row["res_color"]) for row in rows}


def test_auto_result_backfill_fills_only_empty_columns(tmp_path):
    db_path = tmp_path / "prediction-material-immutability.sqlite3"
    with connect(db_path) as conn:
        _create_result_table(conn)
        affected = backfill_repository.fill_missing_created_prediction_result_fields(
            conn,
            qualified_table="mode_payload_43",
            lottery_type_id=3,
            year=2026,
            term=266,
            numbers="01,02,03,04,05,06,07",
            res_sx="鼠,牛,虎,兔,龙,蛇,马",
            res_color="红,蓝,绿,红,蓝,绿,红",
        )
        rows = _select_result_rows(conn, 1, 2, 3, 4, 5, 6)

    assert affected == 3
    # 全空行被完整回填，正文不变
    assert rows[1] == ("auto-content", "01,02,03,04,05,06,07", "鼠,牛,虎,兔,龙,蛇,马", "红,蓝,绿,红,蓝,绿,红")
    # res_code 已存在时不覆盖，空列被补齐
    assert rows[2] == ("auto-content", "01,02,03", "鼠,牛,虎,兔,龙,蛇,马", "红,蓝,绿,红,蓝,绿,红")
    # 管理员手工填写的 res_sx/res_color 保持不变，只补 res_code
    assert rows[3] == ("admin-edited-content", "01,02,03,04,05,06,07", "ADMIN-SX", "ADMIN-COLOR")
    # 已完整的行完全不动
    assert rows[4] == ("auto-content", "OLD", "OLD-SX", "OLD-COLOR")
    # 其它期号 / 其它彩种不动
    assert rows[5] == ("auto-content", "", "", "")
    assert rows[6] == ("auto-content", "", "", "")


def test_auto_result_backfill_is_a_noop_when_nothing_is_missing(tmp_path):
    """结果字段已完整的行不产生任何写入，也不改正文。"""
    db_path = tmp_path / "prediction-material-immutability-full.sqlite3"
    with connect(db_path) as conn:
        _create_result_table(conn)
        conn.execute(
            "UPDATE mode_payload_43 SET res_code = ?, res_sx = ?, res_color = ?",
            ("OLD", "OLD-SX", "OLD-COLOR"),
        )
        affected = backfill_repository.fill_missing_created_prediction_result_fields(
            conn,
            qualified_table="mode_payload_43",
            lottery_type_id=3,
            year=2026,
            term=266,
            numbers="01,02,03,04,05,06,07",
            res_sx="鼠,牛,虎,兔,龙,蛇,马",
            res_color="红,蓝,绿,红,蓝,绿,红",
        )
        untouched = _select_result_rows(conn, 1, 2, 3, 4)

    assert affected == 0
    assert untouched[1] == ("auto-content", "OLD", "OLD-SX", "OLD-COLOR")
    assert untouched[3] == ("admin-edited-content", "OLD", "OLD-SX", "OLD-COLOR")


def test_admin_manual_backfill_keeps_the_right_to_correct_results(tmp_path):
    """管理员手动回填仍可改写结果字段（预测资料例外条款只对管理员开放）。"""
    db_path = tmp_path / "prediction-material-admin-backfill.sqlite3"
    with connect(db_path) as conn:
        _create_result_table(conn)
        affected = backfill_repository.update_created_prediction_result_fields(
            conn,
            qualified_table="mode_payload_43",
            lottery_type_id=3,
            year=2026,
            term=266,
            numbers="11,12",
            res_sx="CORRECTED-SX",
            res_color="CORRECTED-COLOR",
        )
        rows = _select_result_rows(conn, 3, 4)

    # 只有"至少一个结果字段为空"的行会被管理员回填命中；已完整的行不动。
    assert affected == 3
    assert rows[3] == ("admin-edited-content", "11,12", "CORRECTED-SX", "CORRECTED-COLOR")
    assert rows[4] == ("auto-content", "OLD", "OLD-SX", "OLD-COLOR")


# ── 4. 自动回填必须逐表容错（PostgreSQL 事务中止不得拖垮整次回填） ────


def test_result_backfill_skips_tables_without_result_columns(tmp_path, monkeypatch):
    """缺 res_* 列的表（线上 mode_payload_273/335）必须跳过，且不影响其它表。"""
    db_path = tmp_path / "prediction-result-backfill-columns.sqlite3"
    columns_by_table = {
        "mode_payload_273": ("id", "content"),
        "mode_payload_43": ("id", "type", "year", "term", "content", "res_code", "res_sx", "res_color"),
    }
    monkeypatch.setattr(
        backfill_repository,
        "table_column_names",
        lambda _conn, _schema, name: columns_by_table.get(name, ()),
    )
    # sqlite 里 `created`.`mode_payload_x` 会指向未 attach 的 schema，测试中退化为裸表名。
    monkeypatch.setattr(
        backfill_repository, "quote_qualified_identifier", lambda _schema, name: name
    )
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_273 (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO mode_payload_273 (id, content) VALUES (1, 'no-result-columns')")
        _create_result_table(conn)
        filled = backfill_repository.backfill_created_result_fields(
            conn,
            table_names=["mode_payload_273", "mode_payload_43"],
            lottery_type_id=3,
            year=2026,
            term=266,
            numbers="01,02,03,04,05,06,07",
            res_sx="鼠,牛,虎,兔,龙,蛇,马",
            res_color="红,蓝,绿,红,蓝,绿,红",
            overwrite=False,
        )
        rows = _select_result_rows(conn, 1)

    assert sorted(filled) == ["mode_payload_43"]
    assert rows[1] == ("auto-content", "01,02,03,04,05,06,07", "鼠,牛,虎,兔,龙,蛇,马", "红,蓝,绿,红,蓝,绿,红")


def test_result_backfill_contains_per_table_failures(tmp_path, monkeypatch):
    """单表 SQL 失败必须回滚到 SAVEPOINT 并继续，后续表仍然完成回填。"""
    db_path = tmp_path / "prediction-result-backfill-savepoint.sqlite3"
    monkeypatch.setattr(
        backfill_repository,
        "table_column_names",
        lambda _conn, _schema, _name: ("id", "content", "res_code", "res_sx", "res_color"),
    )
    monkeypatch.setattr(
        backfill_repository, "quote_qualified_identifier", lambda _schema, name: name
    )
    with connect(db_path) as conn:
        # 缺 type/year/term 列 → 该表 UPDATE 必然失败
        conn.execute("CREATE TABLE mode_payload_999 (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO mode_payload_999 (id, content) VALUES (1, 'broken')")
        _create_result_table(conn)
        filled = backfill_repository.backfill_created_result_fields(
            conn,
            table_names=["mode_payload_999", "mode_payload_43"],
            lottery_type_id=3,
            year=2026,
            term=266,
            numbers="01,02,03,04,05,06,07",
            res_sx="鼠,牛,虎,兔,龙,蛇,马",
            res_color="红,蓝,绿,红,蓝,绿,红",
            overwrite=False,
        )
        rows = _select_result_rows(conn, 1)
        broken = conn.execute("SELECT content FROM mode_payload_999 WHERE id = 1").fetchone()

    assert sorted(filled) == ["mode_payload_43"]
    assert broken["content"] == "broken"
    assert rows[1][1] == "01,02,03,04,05,06,07"


def test_admin_result_backfill_loop_can_overwrite_and_isolates_failures(tmp_path, monkeypatch):
    """管理台手动回填走同一个逐表循环：overwrite=True 时允许纠错并覆盖既有值。"""
    db_path = tmp_path / "prediction-result-backfill-admin.sqlite3"
    monkeypatch.setattr(
        backfill_repository,
        "table_column_names",
        lambda _conn, _schema, _name: ("id", "content", "res_code", "res_sx", "res_color"),
    )
    monkeypatch.setattr(
        backfill_repository, "quote_qualified_identifier", lambda _schema, name: name
    )
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_999 (id INTEGER PRIMARY KEY, content TEXT)")
        _create_result_table(conn)
        conn.execute(
            "UPDATE mode_payload_43 SET res_code = ?, res_sx = ?, res_color = ? WHERE id = 4",
            ("OLD", "OLD-SX", "OLD-COLOR"),
        )
        filled = backfill_repository.backfill_created_result_fields(
            conn,
            table_names=["mode_payload_999", "mode_payload_43"],
            lottery_type_id=3,
            year=2026,
            term=266,
            numbers="11,12",
            res_sx="CORRECTED-SX",
            res_color="CORRECTED-COLOR",
            overwrite=True,
        )
        rows = _select_result_rows(conn, 1, 4)

    assert sorted(filled) == ["mode_payload_43"]
    # 管理台回填命中"至少一个结果字段为空"的行，整行改写为纠正值
    assert filled["mode_payload_43"] == 3
    assert rows[1] == ("auto-content", "11,12", "CORRECTED-SX", "CORRECTED-COLOR")
    # 结果字段已完整的行不会被这条 SQL 命中（管理台要改这类行请用行编辑接口）
    assert rows[4] == ("auto-content", "OLD", "OLD-SX", "OLD-COLOR")


# ── 5. 管理员全量改写后必须立即失效快照 ────────────────────────────


@pytest.mark.parametrize("builder_name", ["normalize_payload_tables", "build_text_history_mappings"])
def test_admin_bulk_rewrite_routes_invalidate_prediction_snapshots(builder_name):
    route = (
        admin_lottery_routes_extra.normalize
        if builder_name == "normalize_payload_tables"
        else admin_lottery_routes_extra.text_mappings
    )
    ctx = make_ctx("/api/admin/normalize", method="POST")

    with patch.object(admin_lottery_routes_extra, builder_name, return_value={}), \
         patch("cache.prediction_snapshots.invalidate_lottery_type") as invalidate:
        route(ctx)

    assert [call.args[1] for call in invalidate.call_args_list] == [1, 2, 3]
