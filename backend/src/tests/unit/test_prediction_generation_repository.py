from __future__ import annotations

from db import connect
from domains.prediction import generation_repository


def test_generation_repository_loads_opened_draws_and_future_truth_without_exposing_it_by_default(tmp_path):
    db_path = tmp_path / "generation_repository.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                numbers TEXT,
                is_opened INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (lottery_type_id, year, term, numbers, is_opened)
            VALUES
                (3, 2026, 130, '01,02,03,04,05,06,07', 1),
                (3, 2026, 131, '08,09,10,11,12,13,14', 0)
            """
        )

        opened = generation_repository.list_opened_draws_in_issue_range(
            conn,
            lottery_type_id=3,
            start_issue=(2026, 129),
            end_issue=(2026, 130),
        )
        truth = generation_repository.get_future_draw_truth(
            conn,
            lottery_type_id=3,
            year=2026,
            term=131,
            zodiac_map={"14": "rabbit"},
            color_map={"14": "blue"},
        )

    assert opened == [{"year": 2026, "term": 130, "numbers_str": "01,02,03,04,05,06,07"}]
    assert truth is not None
    assert truth.special_code == "14"
    assert truth.special_zodiac == "rabbit"
    assert truth.special_color == "blue"
    assert truth.to_safe_dict() == {"has_truth": True}


def test_generation_repository_loads_enabled_site_modules_with_requested_filter(tmp_path):
    db_path = tmp_path / "generation_modules.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY,
                site_id INTEGER,
                mechanism_key TEXT,
                mode_id INTEGER,
                status INTEGER,
                sort_order INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (site_id, mechanism_key, mode_id, status, sort_order)
            VALUES
                (7, 'pt3xiao', 43, 1, 20),
                (7, 'daxiao', 57, 1, 10),
                (7, 'disabled', 99, 0, 30)
            """
        )

        rows = generation_repository.list_enabled_site_prediction_modules(
            conn,
            site_id=7,
            mechanism_keys=["pt3xiao"],
        )

    assert rows == [
        {
            "id": 1,
            "mechanism_key": "pt3xiao",
            "mode_id": 43,
            "status": 1,
            "sort_order": 20,
        }
    ]


class _FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return list(self._rows)


class _FakeConn:
    """Minimal connection double: records SQL, returns canned rows."""

    def __init__(self, rows):
        self.rows = rows
        self.sql = ""

    def execute(self, sql, params=None):
        self.sql = str(sql)
        return _FakeCursor(self.rows)

    def rollback(self):
        return None


def test_load_recent_created_rows_reads_title_only_tables(monkeypatch):
    """mode 52 四字玄机所在的 created 表只有 title/jiexi，没有 content。

    旧实现硬性要求 `content` 列存在，否则返回空历史。结果是
    `_load_three_period_history_rows` 永远拿不到行，`enforce_three_period_uniqueness(52)`
    在 `len(recent_tokens) < required_recent` 处直接返回原值，mode 52 的「相邻五期展示值
    不得相同」从未生效（线上实测 web_id=5 连续四期 title 都是「黯然無光」）。
    """
    monkeypatch.setattr(
        generation_repository,
        "table_column_names",
        lambda conn, schema, table: ("id", "web", "type", "year", "term", "title", "jiexi"),
    )
    conn = _FakeConn(
        [
            {"title": "黯然無光", "jiexi": "虎马兔龙牛羊狗"},
            {"title": "黯然無光", "jiexi": "鸡蛇马鼠虎猪羊"},
        ]
    )

    rows = generation_repository.load_recent_created_rows(
        conn,
        table_name="mode_payload_52",
        lottery_type=3,
        site_web_id=5,
        mode_id=52,
        limit=8,
    )

    assert rows == [
        {"title": "黯然無光", "jiexi": "虎马兔龙牛羊狗"},
        {"title": "黯然無光", "jiexi": "鸡蛇马鼠虎猪羊"},
    ]
    # 只 select 实际存在的展示列，绝不 select 不存在的 content
    assert "content" not in conn.sql
    assert '"title"' in conn.sql
    assert '"jiexi"' in conn.sql


def test_load_recent_created_rows_returns_empty_without_display_columns(monkeypatch):
    """既没有 content 也没有 title/jiexi 的表不参与唯一性判定，返回空列表而不是抛错。"""
    monkeypatch.setattr(
        generation_repository,
        "table_column_names",
        lambda conn, schema, table: ("id", "web", "type", "year", "term"),
    )
    conn = _FakeConn([{"title": "unused"}])

    rows = generation_repository.load_recent_created_rows(
        conn,
        table_name="mode_payload_x",
        lottery_type=3,
        site_web_id=5,
        mode_id=52,
    )

    assert rows == []
    assert conn.sql == ""
