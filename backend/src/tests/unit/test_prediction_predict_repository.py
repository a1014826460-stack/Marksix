from __future__ import annotations

from db import connect
from domains.prediction import predict_repository


def test_predict_repository_gets_table_title_and_recent_rows(tmp_path):
    db_path = tmp_path / "predict_repository.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER,
                title TEXT,
                table_name TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_43 (
                id INTEGER PRIMARY KEY,
                year TEXT,
                term TEXT,
                res_code TEXT,
                content TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, title, table_name) VALUES (43, 'pt3xiao', 'mode_payload_43')"
        )
        for term in range(1, 13):
            conn.execute(
                "INSERT INTO mode_payload_43 (year, term, res_code, content) VALUES (?, ?, ?, ?)",
                ("2026", str(term), "01,02,03,04,05,06,07", f"row-{term}"),
            )
        conn.execute(
            "INSERT INTO mode_payload_43 (year, term, res_code, content) VALUES (?, ?, ?, ?)",
            ("2026", "13", "", "ignored-empty-result"),
        )

        title = predict_repository.get_mode_payload_table_title(conn, "mode_payload_43")
        rows = predict_repository.load_recent_result_rows(conn, "mode_payload_43", limit=10)

    assert title == (43, "pt3xiao")
    assert [row["content"] for row in rows] == [f"row-{term}" for term in range(3, 13)]


def test_predict_repository_returns_empty_title_for_missing_table():
    class FakeConn:
        def execute(self, *_args, **_kwargs):
            class Cursor:
                def fetchone(self):
                    return None

            return Cursor()

    assert predict_repository.get_mode_payload_table_title(FakeConn(), "missing") == (None, None)


def test_predict_repository_samples_column_values(tmp_path):
    db_path = tmp_path / "predict_repository_samples.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_43 (
                id INTEGER PRIMARY KEY,
                content TEXT,
                xiao TEXT
            )
            """
        )
        conn.execute("INSERT INTO mode_payload_43 (content, xiao) VALUES ('', '')")
        conn.execute("INSERT INTO mode_payload_43 (content, xiao) VALUES ('sample-content', 'rat')")

        assert predict_repository.sample_column_value(conn, "mode_payload_43", "xiao") == "rat"
        assert predict_repository.sample_content(conn, "mode_payload_43") == "sample-content"
        assert predict_repository.sample_column_value(conn, "mode_payload_43", "missing") == ""


def test_predict_repository_loads_fixed_data_rows(tmp_path):
    db_path = tmp_path / "predict_repository_fixed_data.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE fixed_data (
                id INTEGER PRIMARY KEY,
                name TEXT,
                code TEXT,
                sign TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO fixed_data (id, name, code, sign) VALUES (2, 'ox', '02,14', '生肖')"
        )
        conn.execute(
            "INSERT INTO fixed_data (id, name, code, sign) VALUES (1, 'rat', '01,13', '生肖')"
        )
        conn.execute(
            "INSERT INTO fixed_data (id, name, code, sign) VALUES (3, 'red', '01,02', '波色')"
        )

        rows = predict_repository.load_fixed_data_rows(conn, "生肖")

    assert [dict(row) for row in rows] == [
        {"id": 1, "name": "rat", "code": "01,13"},
        {"id": 2, "name": "ox", "code": "02,14"},
    ]


def test_predict_repository_loads_fixed_data_sign_names(tmp_path):
    db_path = tmp_path / "predict_repository_fixed_signs.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE fixed_data (
                id INTEGER PRIMARY KEY,
                name TEXT,
                code TEXT,
                sign TEXT
            )
            """
        )
        conn.execute("INSERT INTO fixed_data (id, name, code, sign) VALUES (2, 'ox', '', 'zodiac')")
        conn.execute("INSERT INTO fixed_data (id, name, code, sign) VALUES (1, 'rat', '', 'zodiac')")
        conn.execute("INSERT INTO fixed_data (id, name, code, sign) VALUES (3, '', '', 'zodiac')")
        conn.execute("INSERT INTO fixed_data (id, name, code, sign) VALUES (4, 'red', '', 'wave')")

        rows = predict_repository.load_fixed_data_sign_names(conn)

    assert [dict(row) for row in rows] == [
        {"sign": "wave", "name": "red"},
        {"sign": "zodiac", "name": "rat"},
        {"sign": "zodiac", "name": "ox"},
    ]


def test_predict_repository_loads_non_empty_column_values(tmp_path):
    db_path = tmp_path / "predict_repository_column_values.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_43 (
                id INTEGER PRIMARY KEY,
                content TEXT,
                title TEXT
            )
            """
        )
        conn.execute("INSERT INTO mode_payload_43 (content, title) VALUES ('rat|01,13', 'a')")
        conn.execute("INSERT INTO mode_payload_43 (content, title) VALUES ('', 'ignored')")
        conn.execute("INSERT INTO mode_payload_43 (content, title) VALUES (NULL, 'ignored')")
        conn.execute("INSERT INTO mode_payload_43 (content, title) VALUES ('ox|02,14', 'b')")

        values = predict_repository.load_non_empty_column_values(conn, "mode_payload_43", "content")

    assert values == ["rat|01,13", "ox|02,14"]


def test_predict_repository_loads_distinct_column_values_by_frequency(tmp_path):
    db_path = tmp_path / "predict_repository_distinct_values.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_43 (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
            """
        )
        conn.execute("INSERT INTO mode_payload_43 (content) VALUES ('b')")
        conn.execute("INSERT INTO mode_payload_43 (content) VALUES ('a')")
        conn.execute("INSERT INTO mode_payload_43 (content) VALUES ('b')")
        conn.execute("INSERT INTO mode_payload_43 (content) VALUES ('')")

        values = predict_repository.load_distinct_non_empty_column_values_by_frequency(
            conn, "mode_payload_43", "content"
        )

    assert values == ["b", "a"]


def test_predict_repository_loads_qinqi_history_rows(tmp_path):
    db_path = tmp_path / "predict_repository_qinqi.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_26 (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT
            )
            """
        )
        conn.execute("INSERT INTO mode_payload_26 (title, content) VALUES ('qin,qi', 'rat,ox')")
        conn.execute("INSERT INTO mode_payload_26 (title, content) VALUES ('', 'ignored')")
        conn.execute("INSERT INTO mode_payload_26 (title, content) VALUES ('ignored', '')")

        rows = predict_repository.load_qinqi_history_rows(conn)

    assert [dict(row) for row in rows] == [{"title": "qin,qi", "content": "rat,ox"}]


def test_predict_repository_detects_non_empty_text_history_column(tmp_path):
    db_path = tmp_path / "predict_repository_text_history_column.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE text_history_mappings (
                id INTEGER PRIMARY KEY,
                mode_id INTEGER,
                content TEXT,
                jiexi TEXT
            )
            """
        )
        conn.execute("INSERT INTO text_history_mappings (mode_id, content, jiexi) VALUES (52, '', '')")
        conn.execute("INSERT INTO text_history_mappings (mode_id, content, jiexi) VALUES (52, 'text', '')")
        conn.execute("INSERT INTO text_history_mappings (mode_id, content, jiexi) VALUES (53, '', 'other')")

        assert predict_repository.has_text_history_column_value(
            conn,
            "text_history_mappings",
            "content",
            mode_column="mode_id",
            modes_id=52,
        )
        assert not predict_repository.has_text_history_column_value(
            conn,
            "text_history_mappings",
            "jiexi",
            mode_column="mode_id",
            modes_id=52,
        )


def test_predict_repository_loads_random_text_history_row(tmp_path):
    db_path = tmp_path / "predict_repository_text_history_row.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE text_history_mappings (
                id INTEGER PRIMARY KEY,
                mode_id INTEGER,
                title TEXT,
                content TEXT,
                payload_json TEXT,
                text_content TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO text_history_mappings (mode_id, title, content, payload_json, text_content) "
            "VALUES (52, 'ignored-empty', '', '', '')"
        )
        conn.execute(
            "INSERT INTO text_history_mappings (mode_id, title, content, payload_json, text_content) "
            "VALUES (52, 'target', 'body', '', '')"
        )

        row = predict_repository.load_random_text_history_row(
            conn,
            "text_history_mappings",
            mode_column="mode_id",
            modes_id=52,
            non_empty_columns=("content",),
        )

    assert row is not None
    assert row["title"] == "target"
    assert row["content"] == "body"


def test_predict_repository_loads_latest_window_metadata(tmp_path):
    db_path = tmp_path / "predict_repository_window_metadata.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_250 (
                id INTEGER PRIMARY KEY,
                year TEXT,
                term TEXT,
                start TEXT,
                end TEXT,
                image_url TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_250 (year, term, start, end, image_url) "
            "VALUES ('2026', '1', 'old-start', 'old-end', 'old.png')"
        )
        conn.execute(
            "INSERT INTO mode_payload_250 (year, term, start, end, image_url) "
            "VALUES ('2026', '2', 'new-start', 'new-end', 'new.png')"
        )

        row = predict_repository.load_latest_columns_by_issue(
            conn,
            "mode_payload_250",
            columns=("start", "end", "image_url"),
        )

    assert dict(row) == {"start": "new-start", "end": "new-end", "image_url": "new.png"}


def test_predict_repository_latest_columns_prefers_source_record_id_when_issue_ties(tmp_path):
    db_path = tmp_path / "predict_repository_window_source_record.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_250 (
                id INTEGER PRIMARY KEY,
                year TEXT,
                term TEXT,
                source_record_id TEXT,
                start TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_250 (year, term, source_record_id, start) "
            "VALUES ('2026', '2', '10', 'old-source')"
        )
        conn.execute(
            "INSERT INTO mode_payload_250 (year, term, source_record_id, start) "
            "VALUES ('2026', '2', '11', 'new-source')"
        )

        row = predict_repository.load_latest_columns_by_issue(
            conn,
            "mode_payload_250",
            columns=("start",),
        )

    assert dict(row) == {"start": "new-source"}


def test_predict_repository_loads_random_distinct_text_pool_row(tmp_path):
    db_path = tmp_path / "predict_repository_text_pool.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_52 (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT,
                jiexi TEXT,
                code TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_52 (title, content, jiexi, code) "
            "VALUES ('ignored', '', 'ignored', '00')"
        )
        conn.execute(
            "INSERT INTO mode_payload_52 (title, content, jiexi, code) "
            "VALUES ('target', 'body', 'analysis', '01')"
        )

        row = predict_repository.load_random_distinct_text_pool_row(
            conn,
            "mode_payload_52",
            text_column="content",
            selected_columns=("title", "content", "jiexi", "code"),
        )

    assert row == {"title": "target", "content": "body", "jiexi": "analysis", "code": "01"}


def test_predict_repository_loads_limited_non_empty_column_values(tmp_path):
    db_path = tmp_path / "predict_repository_limited_column_values.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_300 (
                id INTEGER PRIMARY KEY,
                xiao_1 TEXT
            )
            """
        )
        conn.execute("INSERT INTO mode_payload_300 (xiao_1) VALUES ('rat')")
        conn.execute("INSERT INTO mode_payload_300 (xiao_1) VALUES ('')")
        conn.execute("INSERT INTO mode_payload_300 (xiao_1) VALUES ('ox')")
        conn.execute("INSERT INTO mode_payload_300 (xiao_1) VALUES ('tiger')")

        values = predict_repository.load_limited_non_empty_column_values(
            conn,
            "mode_payload_300",
            "xiao_1",
            limit=2,
        )

    assert values == ["rat", "ox"]


def test_predict_repository_loads_rows_with_non_empty_label_column(tmp_path):
    db_path = tmp_path / "predict_repository_label_rows.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_301 (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT
            )
            """
        )
        conn.execute("INSERT INTO mode_payload_301 (title, content) VALUES ('red', '01,02')")
        conn.execute("INSERT INTO mode_payload_301 (title, content) VALUES ('', 'ignored')")
        conn.execute("INSERT INTO mode_payload_301 (title, content) VALUES ('blue', '03,04')")

        rows = predict_repository.load_rows_with_non_empty_label_column(
            conn,
            "mode_payload_301",
            label_column="title",
            selected_columns=("title", "content"),
        )

    assert [dict(row) for row in rows] == [
        {"title": "red", "content": "01,02"},
        {"title": "blue", "content": "03,04"},
    ]


def test_predict_repository_loads_mode_payload_table_rows(tmp_path):
    db_path = tmp_path / "predict_repository_mode_payload_tables.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER,
                title TEXT,
                table_name TEXT,
                record_count INTEGER
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count) "
            "VALUES (2, 'b', 'mode_payload_2', 20)"
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count) "
            "VALUES (1, 'a', 'mode_payload_1', 10)"
        )

        rows = predict_repository.load_mode_payload_table_rows(conn)

    assert [dict(row) for row in rows] == [
        {"modes_id": 1, "title": "a", "table_name": "mode_payload_1", "record_count": 10},
        {"modes_id": 2, "title": "b", "table_name": "mode_payload_2", "record_count": 20},
    ]
