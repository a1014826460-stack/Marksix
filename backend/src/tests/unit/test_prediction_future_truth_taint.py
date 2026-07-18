from __future__ import annotations

from db import connect
from domains.prediction.models import DrawTruth
from domains.prediction.simulation_service import SimulationConfig
from legacy.frontend_compat import _format_rows
from prediction_generation import service
from predict.mechanisms import PREDICTION_CONFIGS
from public.api import serialize_public_history_row
from tables import ensure_admin_tables


def test_full_future_draw_never_enters_controlled_row_or_internal_plan(tmp_path, monkeypatch):
    db_path = str(tmp_path / "future-truth-taint.sqlite3")
    ensure_admin_tables(db_path)
    truth_csv = "01,02,03,04,05,06,49"
    truth = DrawTruth(
        tuple(truth_csv.split(",")),
        "49",
        "虎",
        "绿波",
    )
    config = PREDICTION_CONFIGS["pt3xiao"]
    monkeypatch.setattr(
        service,
        "predict",
        lambda **_kwargs: {
            "prediction": {"labels": ["鼠", "猪", "羊"], "content": "鼠,猪,羊"},
            "mode": {"resolved_labels": list(config.labels)},
        },
    )

    with connect(db_path) as conn:
        row_data = service._generate_default_mode_row(
            draw={"year": 2026, "term": 131},
            is_future=True,
            safe_res_code=None,
            config=config,
            table_name="mode_payload_470",
            db_path=db_path,
            default_target_hit_rate=0.65,
            build_row=lambda **kwargs: {
                "content": kwargs["generated_content"],
                "res_code": kwargs["res_code"],
                "res_sx": "",
                "res_color": "",
            },
            lottery_type=3,
            site_web_id=4,
            conn=conn,
            truth=truth,
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            simulation_state=None,
            site_id=7,
            mechanism_key="pt3xiao",
        )

    control = row_data.pop("_generation_control")
    row_data.pop("_simulation_should_hit")
    assert truth_csv not in repr(row_data)
    assert truth_csv not in repr(control.__dict__)
    assert row_data["res_code"] == ""
    assert row_data["res_sx"] == ""
    assert row_data["res_color"] == ""


def test_future_control_keeps_full_truth_out_of_persisted_and_public_history_rows(tmp_path, monkeypatch):
    db_path = str(tmp_path / "future-truth-history-taint.sqlite3")
    ensure_admin_tables(db_path)
    truth_csv = "01,02,03,04,05,06,49"
    truth = DrawTruth(tuple(truth_csv.split(",")), "49", "虎", "绿波")
    config = PREDICTION_CONFIGS["pt3xiao"]
    persisted_rows: list[dict] = []

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: truth,
    )
    monkeypatch.setattr(
        service,
        "predict",
        lambda **_kwargs: {
            "prediction": {"labels": ["鼠", "猪", "羊"], "content": "鼠,猪,羊"},
            "mode": {"resolved_labels": list(config.labels)},
        },
    )
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda _conn, _table, row_data, allow_overwrite, *, commit=True: persisted_rows.append(dict(row_data)) or {"action": "inserted"},
    )

    with connect(db_path) as conn:
        report = service._process_single_module(
            conn=conn,
            module_row={"id": 1, "mechanism_key": "pt3xiao", "mode_id": 470},
            draws=[],
            future_draws=[{"year": 2026, "term": 131, "numbers_str": "", "_future": True}],
            future_only=True,
            safety_draw_map={(2026, 131): True},
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            db_path=db_path,
            default_target_hit_rate=0.65,
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            zodiac_map={"49": "虎"},
            color_map={"49": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: {
                "year": kwargs["year"],
                "term": kwargs["term"],
                "content": kwargs["generated_content"],
                "res_code": kwargs["res_code"],
                "res_sx": "",
                "res_color": "",
                "draw_is_opened": False,
            },
        )

    persisted = persisted_rows[0]
    public_payload = serialize_public_history_row(persisted)
    legacy_payload = _format_rows([persisted], "getPtWei")
    for value in (report, persisted, public_payload, legacy_payload):
        assert truth_csv not in repr(value)
    assert persisted["res_code"] == ""
    assert persisted["res_sx"] == ""
    assert persisted["res_color"] == ""
    assert "_generation_control" not in persisted
