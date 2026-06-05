from __future__ import annotations

from database.schema.legacy import ensure_site_specific_prediction_tables
from db import auto_increment_primary_key, connect
from domains.prediction.site_module_blueprints import get_required_mode_ids_for_site
from prediction_generation import service
from prediction_generation.mode_474_image import MODE_474_OUTPUT_DIR
from predict.mechanisms import get_prediction_config


def test_mode_474_table_and_metadata_are_bootstrapped(tmp_path):
    db_path = str(tmp_path / "mode_474_bootstrap.sqlite3")
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

        columns = set(conn.table_columns("mode_payload_474"))
        row = conn.execute(
            "SELECT modes_id, title, table_name, is_image FROM mode_payload_tables WHERE modes_id = ?",
            (474,),
        ).fetchone()

    assert {"title", "content", "image_url", "source_record_id"}.issubset(columns)
    assert row["modes_id"] == 474
    assert row["title"] == "四不像中特图"
    assert row["table_name"] == "mode_payload_474"
    assert int(row["is_image"] or 0) == 1


def test_mode_474_is_registered_in_mechanisms():
    config = get_prediction_config("sxztu")
    assert config.default_modes_id == 474
    assert config.default_table == "mode_payload_474"


def test_mode_474_is_in_default_site_blueprint():
    required = get_required_mode_ids_for_site(None)
    assert 474 in required


def test_generate_mode_474_row_sets_image_url(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "content": "鼠,牛,虎",
            }
        },
    )
    monkeypatch.setattr(
        service,
        "_load_previous_opened_numbers_for_issue",
        lambda *args, **kwargs: "01,02,03,04,05,06,07",
    )
    monkeypatch.setattr(
        service,
        "render_mode_474_prediction_image",
        lambda **kwargs: type(
            "FakeMode474RenderResult",
            (),
            {
                "title": "123期四不像中特图",
                "relative_url": "/data/Images/mode_474/prediction/mode_474_type3_2026123_web4.jpg",
                "source_record_id": "2022_140_amsbx",
            },
        )(),
    )

    row_data = service._generate_single_draw_row(
        draw={"year": 2026, "term": 123},
        mode_id=474,
        is_future=False,
        safe_res_code="01,02,03,04,05,06,07",
        lottery_type=3,
        site_web_id=4,
        config=type("Cfg", (), {"default_modes_id": 474})(),
        table_name="mode_payload_474",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        zodiac_map={},
        build_row=lambda **kwargs: {
            "type": kwargs["lottery_type"],
            "year": kwargs["year"],
            "term": kwargs["term"],
            "web": kwargs["web_value"],
            "content": kwargs["generated_content"],
        },
        conn=object(),
    )

    assert row_data["title"] == "123期四不像中特图"
    assert row_data["content"] == "鼠,牛,虎"
    assert row_data["image_url"] == "/data/Images/mode_474/prediction/mode_474_type3_2026123_web4.jpg"
    assert row_data["source_record_id"] == "2022_140_amsbx"


def test_mode_474_image_output_dir_is_absolute():
    assert MODE_474_OUTPUT_DIR.is_absolute()
