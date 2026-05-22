from __future__ import annotations

from database.schema.legacy import ensure_site_specific_prediction_tables
from db import auto_increment_primary_key, connect
from domains.prediction.site_module_blueprints import get_required_mode_ids_for_site
from prediction_generation import service
from prediction_generation.brain_teaser import (
    build_brain_teaser_generated_content,
    format_brain_teaser_issue_text,
)
from prediction_generation.brain_teaser_image import DEFAULT_OUTPUT_DIR
from predict.mechanisms import get_prediction_config


def test_mode_475_table_and_metadata_are_bootstrapped(tmp_path):
    db_path = str(tmp_path / "mode_475_bootstrap.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                filename TEXT,
                title TEXT,
                table_name TEXT,
                record_count INTEGER,
                is_image INTEGER,
                is_text INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        ensure_site_specific_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))

        columns = set(conn.table_columns("mode_payload_475"))
        row = conn.execute(
            "SELECT modes_id, title, table_name FROM mode_payload_tables WHERE modes_id = ?",
            (475,),
        ).fetchone()

    assert {"title", "content", "image_url", "answer", "tips", "jiexi", "source_record_id"}.issubset(columns)
    assert row["modes_id"] == 475
    assert row["title"] == "脑筋急转弯"
    assert row["table_name"] == "mode_payload_475"


def test_mode_475_is_registered_in_mechanisms():
    config = get_prediction_config("brainteaser")
    assert config.default_modes_id == 475
    assert config.default_table == "mode_payload_475"


def test_mode_475_is_in_default_site_blueprint():
    required = get_required_mode_ids_for_site(None)
    assert 475 in required


def test_generate_mode_475_row_uses_static_mapping_content(monkeypatch):
    monkeypatch.setattr(
        service,
        "build_brain_teaser_generated_content",
        lambda conn, year, term, site_web_id: {
            "title": "脑筋急转弯",
            "content": "123期：谁越擦越亮？",
            "answer": "镜子",
            "tips": "反光",
            "jiexi": "共19划",
            "source_record_id": "64",
        },
    )
    monkeypatch.setattr(
        service,
        "_generate_mode_475_image_url",
        lambda conn, lottery_type, year, term, site_web_id:
        "/data/Images/mode_475/prediction/brain_teaser_type3_2026123_web4.jpg",
    )

    row_data = service._generate_single_draw_row(
        draw={"year": 2026, "term": 123},
        mode_id=475,
        is_future=False,
        safe_res_code="",
        lottery_type=3,
        site_web_id=4,
        config=object(),
        table_name="mode_payload_475",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        zodiac_map={},
        build_row=lambda **kwargs: {
            "type": kwargs["lottery_type"],
            "year": kwargs["year"],
            "term": kwargs["term"],
            "web": kwargs["web_value"],
            **dict(kwargs["generated_content"]),
        },
        conn=object(),
    )

    assert row_data["title"] == "脑筋急转弯"
    assert row_data["content"] == "123期：谁越擦越亮？"
    assert row_data["image_url"] == "/data/Images/mode_475/prediction/brain_teaser_type3_2026123_web4.jpg"
    assert row_data["answer"] == "镜子"
    assert row_data["tips"] == "反光"
    assert row_data["jiexi"] == "共19划"
    assert row_data["source_record_id"] == "64"


def test_build_brain_teaser_generated_content_is_deterministic():
    class _Cursor:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class FakeConn:
        def execute(self, sql, params=None):
            normalized = " ".join(str(sql).split())
            if "COUNT(*) AS total" in normalized:
                return _Cursor({"total": 2})
            if "OFFSET ? LIMIT 1" in normalized:
                offset = int(params[0])
                rows = [
                    {
                        "id": 63,
                        "question": "谁越打越开心？",
                        "answer": "篮球",
                        "tips": "运动",
                        "analysis": "共27划",
                        "mapping_path": "json_data/brain_test/63",
                    },
                    {
                        "id": 64,
                        "question": "谁越擦越亮？",
                        "answer": "镜子",
                        "tips": "反光",
                        "analysis": "共19划",
                        "mapping_path": "json_data/brain_test/64",
                    },
                ]
                return _Cursor(rows[offset % 2])
            raise AssertionError(f"unexpected sql: {sql}")

    conn = FakeConn()
    first = build_brain_teaser_generated_content(conn, year=2026, term=123, site_web_id=4)
    second = build_brain_teaser_generated_content(conn, year=2026, term=123, site_web_id=4)

    assert first == second
    assert first["title"] == "脑筋急转弯"
    assert first["content"].startswith("123期：")
    assert first["source_record_id"] in {"63", "64"}


def test_mode_475_image_output_dir_is_absolute():
    assert DEFAULT_OUTPUT_DIR.is_absolute()


def test_format_brain_teaser_issue_text():
    assert format_brain_teaser_issue_text(54) == "054期："
