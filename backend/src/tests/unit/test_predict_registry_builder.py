from __future__ import annotations

from dataclasses import dataclass

from db import connect


@dataclass(frozen=True)
class DummyConfig:
    key: str
    title: str
    default_modes_id: int


def test_registry_builder_skips_static_modes_and_delegates_by_table_shape(tmp_path):
    from predict.registry_builder import build_dynamic_prediction_configs

    db_path = tmp_path / "dynamic_registry.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                title TEXT,
                record_count INTEGER
            )
            """
        )
        conn.execute("CREATE TABLE mode_payload_11 (content TEXT)")
        conn.execute("CREATE TABLE mode_payload_12 (content TEXT, xiao TEXT)")
        conn.execute("CREATE TABLE mode_payload_13 (content TEXT)")
        conn.executemany(
            "INSERT INTO mode_payload_tables (modes_id, table_name, title, record_count) VALUES (?, ?, ?, ?)",
            [
                (11, "mode_payload_11", "first", 1),
                (12, "mode_payload_12", "second", 1),
                (13, "mode_payload_13", "static", 1),
            ],
        )
        conn.execute("INSERT INTO mode_payload_11 (content) VALUES ('first-content')")
        conn.execute("INSERT INTO mode_payload_12 (content, xiao) VALUES ('second-content', '鼠')")

    first_stage_calls: list[tuple[str, str, int, str]] = []
    second_stage_calls: list[tuple[str, str, int, tuple[str, ...]]] = []

    def classify_first(title: str, table_name: str, modes_id: int, sample_content: str):
        first_stage_calls.append((title, table_name, modes_id, sample_content))
        return DummyConfig("dynamic_first", title, modes_id)

    def classify_second(conn, title: str, table_name: str, modes_id: int, business_columns: tuple[str, ...]):
        second_stage_calls.append((title, table_name, modes_id, business_columns))
        return DummyConfig("dynamic_second", title, modes_id)

    result = build_dynamic_prediction_configs(
        db_path,
        static_configs={"static": DummyConfig("static", "static", 13)},
        classify_first_stage=classify_first,
        classify_second_stage=classify_second,
    )

    assert tuple(result) == ("dynamic_first", "dynamic_second")
    assert first_stage_calls == [("first", "mode_payload_11", 11, "first-content")]
    assert second_stage_calls == [("second", "mode_payload_12", 12, ("xiao",))]
