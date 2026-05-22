from __future__ import annotations

from database.schema.legacy import ensure_site_specific_prediction_tables
from db import auto_increment_primary_key, connect
from domains.prediction.site_module_blueprints import get_required_mode_ids_for_site
from prediction_generation import service
from prediction_generation.mode_478_image import MODE_478_OUTPUT_DIR
from predict.mechanisms import get_prediction_config


def test_mode_478_table_and_metadata_are_bootstrapped(tmp_path):
    db_path = str(tmp_path / "mode_478_bootstrap.sqlite3")
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

        columns = set(conn.table_columns("mode_payload_478"))
        row = conn.execute(
            "SELECT modes_id, title, table_name, is_image FROM mode_payload_tables WHERE modes_id = ?",
            (478,),
        ).fetchone()

    assert {"title", "content", "image_url", "source_record_id"}.issubset(columns)
    assert row["modes_id"] == 478
    assert row["title"] == "台湾跑马图（带图）"
    assert row["table_name"] == "mode_payload_478"
    assert int(row["is_image"] or 0) == 1


def test_mode_478_is_registered_in_mechanisms():
    config = get_prediction_config("tw_pmt_image")
    assert config.default_modes_id == 478
    assert config.default_table == "mode_payload_478"


def test_mode_478_is_in_default_site_blueprint():
    required = get_required_mode_ids_for_site(None)
    assert 478 in required


def test_generate_mode_478_row_sets_image_url(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "content": ["虎|01,13", "兔|02,14"],
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
        "render_mode_478_prediction_image",
        lambda **kwargs: type(
            "FakeMode478RenderResult",
            (),
            {
                "relative_url": "/data/Images/mode_478/prediction/mode_478_type3_2026123_web4.jpg",
                "source_record_id": "001_ampm",
            },
        )(),
    )

    row_data = service._generate_single_draw_row(
        draw={"year": 2026, "term": 123},
        mode_id=478,
        is_future=False,
        safe_res_code="01,02,03,04,05,06,07",
        lottery_type=3,
        site_web_id=4,
        config=type("Cfg", (), {"default_modes_id": 478})(),
        table_name="mode_payload_478",
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

    assert row_data["title"] == "台湾跑马图（带图）"
    assert row_data["content"] == ["虎|01,13", "兔|02,14"]
    assert row_data["image_url"] == "/data/Images/mode_478/prediction/mode_478_type3_2026123_web4.jpg"
    assert row_data["source_record_id"] == "001_ampm"


def test_mode_478_image_output_dir_is_absolute():
    assert MODE_478_OUTPUT_DIR.is_absolute()
