from __future__ import annotations

from contextlib import contextmanager

from db import connect
from helpers import sql_safe_int_expr
from public import api


class _Connection:
    engine = "postgres"

    def table_exists(self, _table_name: str) -> bool:
        return True


def _payload(term: int) -> dict[str, object]:
    return {
        "id": term,
        "type": 3,
        "year": 2026,
        "term": term,
        "web_id": 9,
        "content": f"row-{term}",
    }


def test_postgres_safe_int_expression_rejects_nonnumeric_seed_rows_before_cast():
    expression = sql_safe_int_expr("type", engine="postgres")

    assert "CASE WHEN" in expression
    assert "~ '^[0-9]+$'" in expression
    assert "THEN CAST" in expression


def test_public_history_reads_fallback_when_preferred_window_has_duplicate_issues(monkeypatch):
    """A full raw created window is not sufficient when it has only one issue."""

    @contextmanager
    def fake_connect(_db_path):
        yield _Connection()

    calls: list[dict[str, object]] = []

    def fake_load(_conn, *, schema_name=None, **kwargs):
        calls.append({"schema_name": schema_name, **kwargs})
        if schema_name == "created":
            return [_payload(175) for _ in range(100)]
        return [_payload(term) for term in range(174, 166, -1)]

    monkeypatch.setattr(api, "connect", fake_connect)
    monkeypatch.setattr(api, "created_table_exists", lambda *_args: True)
    monkeypatch.setattr(api, "resolve_prediction_table_for_mode", lambda *_args: "mode_payload_54")
    monkeypatch.setattr(api, "load_mode_payload_rows_from_source", fake_load)
    monkeypatch.setattr(api, "apply_lottery_draw_overlay", lambda _conn, rows, **_kwargs: rows)

    result = api.load_public_module_history(
        "postgresql://example.invalid/test",
        "pt1wei",
        8,
        lottery_type_id=3,
    )

    assert [row["term"] for row in result["history"]] == [str(term) for term in range(175, 167, -1)]
    assert any(call["schema_name"] is None for call in calls)


def test_public_history_marks_domestic_wild_result_from_fixed_data_mapping():
    rows = [
        {"res_code": "01,03", "res_sx": "马,龙"},
        {"res_code": "01,02", "res_sx": "马,牛"},
        {"res_code": "", "res_sx": ""},
    ]

    annotated = api.attach_domestic_wild_result_category(
        rows,
        {"牛": "家禽", "龙": "野兽"},
    )

    assert annotated[0]["domestic_wild_category"] == "野兽"
    assert annotated[1]["domestic_wild_category"] == "家禽"
    assert "domestic_wild_category" not in annotated[2]


def test_public_history_attaches_qinqi_reference_from_fixed_data_mapping():
    rows = [{"title": "画,琴,棋"}]

    annotated = api.attach_qinqi_reference(
        rows,
        {
            "琴": ("兔", "蛇", "鸡"),
            "棋": ("鼠", "牛", "狗"),
            "书": ("虎", "龙", "马"),
            "画": ("羊", "猴", "猪"),
        },
    )

    assert annotated[0]["qinqi_reference"] == "琴:兔蛇鸡　棋:鼠牛狗\n书:虎龙马　画:羊猴猪"


def test_public_site_ten_history_filters_to_its_own_web_id(tmp_path):
    """Site ten may not expose prediction rows generated for another site."""
    from tables import ensure_admin_tables
    from domains.prediction.generation_service import sync_site_prediction_modules

    db_path = str(tmp_path / "twbst528_public_history.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            ) VALUES (10, 10, '台湾百事通', 'www.twbst528.com', 3, 1, 'twbst528', '', '', 'now', 'now')
            """
        )
        sync_site_prediction_modules(conn, site_id=10)
        conn.execute(
            """
            INSERT INTO mode_payload_50 (year, term, web, type, content)
            VALUES
                ('2026', '201', 9, 3, 'other-site-row'),
                ('2026', '201', 10, 3, 'twbst528-row')
            """
        )

    result = api.get_public_site_page_data(
        db_path,
        site_id=10,
        lottery_type_id=3,
        history_limit=1,
    )
    module = next(item for item in result["modules"] if item["mechanism_key"] == "yijuzhenyan")

    assert len(module["history"]) == 1
    assert module["history"][0]["prediction_text"] == "twbst528-row"
    assert int(module["history"][0]["raw"]["web"]) == 10
