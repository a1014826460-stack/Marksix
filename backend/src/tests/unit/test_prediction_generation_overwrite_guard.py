from __future__ import annotations

import json
import re

from utils import created_prediction_store
from prediction_generation import service


def test_persist_generated_row_skips_existing_when_overwrite_disabled(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "find_existing_created_row",
        lambda conn, table_name, row_data: {"id": "c7", "created_at": "2026-05-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda conn, table_name, row_data, *, commit=True: calls.append("upsert") or {"action": "updated"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "old"},
        allow_overwrite=False,
    )

    assert result["action"] == "skipped_existing"
    assert result["id"] == "c7"
    assert calls == []


def test_persist_generated_row_allows_admin_overwrite(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "find_existing_created_row",
        lambda conn, table_name, row_data: {"id": "c7", "created_at": "2026-05-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda conn, table_name, row_data, *, commit=True: calls.append("upsert") or {"action": "updated"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "new"},
        allow_overwrite=True,
    )

    assert result["action"] == "updated"
    assert calls == ["upsert"]


def test_persist_generated_row_can_defer_created_store_commit(monkeypatch):
    commit_flags: list[bool] = []

    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda _conn, _table_name, _row_data, *, commit: commit_flags.append(commit) or {"action": "inserted"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "new"},
        allow_overwrite=True,
        commit=False,
    )

    assert result["action"] == "inserted"
    assert commit_flags == [False]


def test_created_table_bootstrap_can_defer_commit(monkeypatch):
    commit_calls: list[str] = []

    class _Conn:
        def commit(self):
            commit_calls.append("commit")

    monkeypatch.setattr(created_prediction_store, "ensure_postgres_connection", lambda _conn: None)
    monkeypatch.setattr(created_prediction_store, "validate_mode_payload_table_name", lambda _name: "mode_payload_44")
    monkeypatch.setattr(created_prediction_store, "table_column_names", lambda *_args: {"id", "created_at", "mode_id"})
    monkeypatch.setattr(created_prediction_store, "list_table_columns", lambda *_args: [])
    monkeypatch.setattr(created_prediction_store, "schema_table_exists", lambda *_args: True)
    monkeypatch.setattr(created_prediction_store, "ensure_created_schema", lambda *_args: None)

    # The implementation's SQL work is irrelevant here; the regression is that
    # the explicit deferred mode must not commit it before its caller finishes.
    monkeypatch.setattr(_Conn, "execute", lambda *_args, **_kwargs: None, raising=False)

    created_prediction_store.ensure_created_prediction_table(_Conn(), "mode_payload_44", commit=False)

    assert commit_calls == []


def test_runtime_created_row_write_rejects_missing_table_without_schema_ddl(monkeypatch):
    class _Conn:
        engine = "postgres"

    monkeypatch.setattr(created_prediction_store, "schema_table_exists", lambda *_args: False)
    monkeypatch.setattr(
        created_prediction_store,
        "ensure_created_prediction_table",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runtime write must not execute DDL")),
    )

    try:
        created_prediction_store.upsert_created_prediction_row(
            _Conn(),
            "mode_payload_44",
            {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "value"},
        )
    except RuntimeError as error:
        assert "database.versioned_migrations" in str(error)
    else:
        raise AssertionError("missing created table must require an explicit migration")


def test_generate_mode_331_row_persists_x7m14(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "labels": ["06", "18", "21", "09", "44", "20", "12", "24", "01", "49", "43", "19", "39", "03"],
                "content": {"title": "示例标题", "content": "示例内容"},
            }
        },
    )

    row_data = service._generate_mode_331_row(
        draw={"year": 2026, "term": 131},
        is_future=False,
        safe_res_code="01,02,03,04,05,06,07",
        lottery_type=3,
        site_web_id=4,
        config=object(),
        table_name="mode_payload_331",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        zodiac_map={
            "01": "马", "03": "龙", "06": "牛", "09": "狗", "12": "羊", "18": "牛", "19": "鼠",
            "20": "猪", "21": "狗", "24": "羊", "39": "龙", "43": "鼠", "44": "猪", "49": "马",
            "02": "蛇", "04": "兔", "05": "虎", "07": "鼠", "08": "猪", "10": "鸡", "11": "猴",
            "13": "马", "14": "蛇", "15": "龙", "16": "兔", "17": "虎", "22": "鸡", "23": "猴",
            "25": "马", "26": "蛇", "27": "龙", "28": "兔", "29": "虎", "30": "牛", "31": "鼠",
            "32": "猪", "33": "狗", "34": "鸡", "35": "猴", "36": "羊", "37": "马", "38": "蛇",
            "40": "兔", "41": "虎", "42": "牛", "45": "狗", "46": "鸡", "47": "猴", "48": "羊",
        },
        build_row=lambda **kwargs: {
            "type": kwargs["lottery_type"],
            "year": kwargs["year"],
            "term": kwargs["term"],
            "web": kwargs["web_value"],
            **dict(kwargs["generated_content"]),
        },
    )

    parsed = json.loads(row_data["x7m14"])
    assert len(parsed) == 7
    assert all(
        re.fullmatch(r"(鼠|牛|虎|兔|龙|蛇|马|羊|猴|鸡|狗|猪)\|\d{2},\d{2}", item)
        for item in parsed
    )


def test_repair_text_prediction_diversity_replaces_adjacent_duplicate(monkeypatch):
    monkeypatch.setattr(
        service,
        "_load_text_history_candidate_payloads",
        lambda conn, mode_id: [
            {"title": "旧标题", "content": "旧内容", "jiexi": "旧解析"},
            {"title": "新标题", "content": "新内容", "jiexi": "新解析"},
        ],
    )

    result = service._repair_text_prediction_diversity(
        object(),
        mode_id=50,
        row_data={"title": "旧标题", "content": "旧内容", "jiexi": "旧解析"},
        recent_rows=[{"title": "旧标题", "content": "旧内容", "jiexi": "旧解析"}],
    )

    assert result["title"] == "新标题"
    assert result["content"] == "新内容"
    assert result["jiexi"] == "新解析"


def test_repair_text_prediction_diversity_keeps_non_duplicate_row(monkeypatch):
    monkeypatch.setattr(
        service,
        "_load_text_history_candidate_payloads",
        lambda conn, mode_id: [{"title": "新标题", "content": "新内容", "jiexi": "新解析"}],
    )

    row_data = {"title": "当前标题", "content": "当前内容", "jiexi": "当前解析"}
    result = service._repair_text_prediction_diversity(
        object(),
        mode_id=50,
        row_data=row_data,
        recent_rows=[{"title": "上期标题", "content": "上期内容", "jiexi": "上期解析"}],
    )

    assert result == row_data


def test_normalize_created_term_three_digit_padding():
    assert created_prediction_store._normalize_created_term("94") == "094"
    assert created_prediction_store._normalize_created_term(94) == "094"
    assert created_prediction_store._normalize_created_term("052") == "052"
    assert created_prediction_store._normalize_created_term("113") == "113"
    assert created_prediction_store._normalize_created_term("") == ""


def test_upsert_created_prediction_row_normalizes_term_to_three_digits(monkeypatch):
    class _Cursor:
        def fetchone(self):
            return None

        def fetchall(self):
            return []

    class _Conn:
        engine = "postgres"

        def execute(self, _sql, _params=None):
            return _Cursor()

        def commit(self):
            pass

    captured: dict[str, object] = {}

    monkeypatch.setattr(created_prediction_store, "schema_table_exists", lambda *_args: True)
    monkeypatch.setattr(
        created_prediction_store,
        "list_table_columns",
        lambda *_args: [type("Col", (), {"name": "term", "sql_type": "text"})()],
    )
    def _capture_normalized(_conn, _table, row):
        captured["term"] = row.get("term")
        return row

    monkeypatch.setattr(
        created_prediction_store,
        "normalize_three_period_special_row",
        _capture_normalized,
    )
    monkeypatch.setattr(created_prediction_store, "enrich_prediction_result_fields", lambda _c, _t, row: row)
    monkeypatch.setattr(created_prediction_store, "normalize_prediction_result_placeholders", lambda row: row)
    monkeypatch.setattr(created_prediction_store, "sanitize_created_prediction_row_data", lambda _t, row, _d: row)
    monkeypatch.setattr(created_prediction_store, "find_existing_created_row", lambda *_args: None)
    monkeypatch.setattr(created_prediction_store, "sync_three_period_special_window_rows", lambda *_args: None)

    created_prediction_store.upsert_created_prediction_row(
        _Conn(),
        "mode_payload_100",
        {"type": "1", "year": "2026", "term": "94", "web": "8", "content": "x"},
    )

    assert captured["term"] == "094"
