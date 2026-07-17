from __future__ import annotations

from predict.common import PredictionConfig, contains_hit
from prediction_generation import service
from domains.prediction.models import DrawTruth, PredictionCategory
from domains.prediction.simulation_service import SimulationConfig, SimulationState


def _format_labels(labels: tuple[str, ...], _conn):
    return ",".join(labels)


def _config() -> PredictionConfig:
    return PredictionConfig(
        key="pt3xiao",
        title="pt3xiao",
        default_table="mode_payload_43",
        default_modes_id=43,
        labels=("rat", "ox", "tiger"),
        label_count=2,
        outcome_loader=lambda row, conn: "",
        content_loader=lambda row: "",
        content_parser=lambda content: tuple(item for item in str(content).split(",") if item),
        content_formatter=_format_labels,
        hit_checker=contains_hit,
        explanation=(),
    )


def test_default_future_taiwan_row_applies_simulation_hit_without_exposing_res_code(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "labels": ["ox", "tiger"],
                "content": "ox,tiger",
            }
        },
    )
    monkeypatch.setattr(
        service,
        "classify_prediction_config",
        lambda config: PredictionCategory.ZODIAC,
    )

    row_data = service._generate_default_mode_row(
        draw={"year": 2026, "term": 131},
        is_future=True,
        safe_res_code=None,
        config=_config(),
        table_name="mode_payload_43",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        build_row=lambda **kwargs: {
            "year": kwargs["year"],
            "term": kwargs["term"],
            "web": kwargs["web_value"],
            "content": kwargs["generated_content"],
            "res_code": kwargs["res_code"],
        },
        lottery_type=3,
        site_web_id=6,
        conn=object(),
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "07"),
            special_code="07",
            special_zodiac="rat",
            special_color="red",
        ),
        simulation_config=SimulationConfig(target_hit_rate=1.0),
        simulation_state=SimulationState(),
        site_id=7,
        mechanism_key="pt3xiao",
    )

    assert row_data["content"].split(",")[0] == "rat"
    assert row_data["res_code"] == ""
    assert "07" not in row_data["content"]


def test_default_future_taiwan_row_forces_miss_when_target_hit_rate_is_zero(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "labels": ["rat", "ox"],
                "content": "rat,ox",
            },
            "mode": {
                "resolved_labels": ["rat", "ox", "tiger"],
            },
        },
    )
    monkeypatch.setattr(
        service,
        "classify_prediction_config",
        lambda config: PredictionCategory.ZODIAC,
    )

    row_data = service._generate_default_mode_row(
        draw={"year": 2026, "term": 131},
        is_future=True,
        safe_res_code=None,
        config=_config(),
        table_name="mode_payload_43",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        build_row=lambda **kwargs: {
            "content": kwargs["generated_content"],
            "res_code": kwargs["res_code"],
        },
        lottery_type=3,
        site_web_id=6,
        conn=object(),
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "07"),
            special_code="07",
            special_zodiac="rat",
            special_color="red",
        ),
        simulation_config=SimulationConfig(target_hit_rate=0.0),
        simulation_state=SimulationState(),
        site_id=7,
        mechanism_key="pt3xiao",
    )

    assert "rat" not in row_data["content"].split(",")
    assert row_data["res_code"] == ""


def test_default_future_taiwan_row_reverses_after_consecutive_hit_limit(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "labels": ["ox", "tiger"],
                "content": "ox,tiger",
            },
            "mode": {
                "resolved_labels": ["rat", "ox", "tiger"],
            },
        },
    )
    monkeypatch.setattr(
        service,
        "classify_prediction_config",
        lambda config: PredictionCategory.ZODIAC,
    )

    row_data = service._generate_default_mode_row(
        draw={"year": 2026, "term": 132},
        is_future=True,
        safe_res_code=None,
        config=_config(),
        table_name="mode_payload_43",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        build_row=lambda **kwargs: {
            "content": kwargs["generated_content"],
            "res_code": kwargs["res_code"],
        },
        lottery_type=3,
        site_web_id=6,
        conn=object(),
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "07"),
            special_code="07",
            special_zodiac="rat",
            special_color="red",
        ),
        simulation_config=SimulationConfig(target_hit_rate=1.0, max_consecutive_hits=1),
        simulation_state=SimulationState(consecutive_hits=1),
        site_id=7,
        mechanism_key="pt3xiao",
    )

    assert "rat" not in row_data["content"].split(",")
    assert row_data["_simulation_should_hit"] is False


def test_process_single_module_loads_future_truth_and_tracks_simulation_state(monkeypatch):
    calls: list[dict] = []
    states: list[SimulationState | None] = []

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda mechanism_key, mode_id, db_path: (_config(), mechanism_key, False),
    )
    monkeypatch.setattr(service, "_load_recent_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(service, "enforce_prediction_diversity", lambda **kwargs: kwargs["row_data"])
    monkeypatch.setattr(service, "_repair_text_prediction_diversity", lambda *args, **kwargs: kwargs["row_data"])
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda conn, **kwargs: DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "07"),
            special_code="07",
            special_zodiac="rat",
            special_color="red",
        ),
    )

    def fake_generate(**kwargs):
        states.append(kwargs["simulation_state"])
        row = {
            "type": str(kwargs["lottery_type"]),
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": str(kwargs["site_web_id"]),
            "content": "rat",
            "res_code": kwargs["safe_res_code"] or "",
            "_simulation_should_hit": True,
        }
        return row

    monkeypatch.setattr(service, "_generate_single_draw_row", fake_generate)
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda conn, table_name, row_data, allow_overwrite: calls.append(dict(row_data)) or {"action": "inserted"},
    )

    report = service._process_single_module(
        conn=object(),
        module_row={"id": 1, "mechanism_key": "pt3xiao", "mode_id": 43},
        draws=[],
        future_draws=[
            {"year": 2026, "term": 131, "numbers_str": "", "_future": True},
            {"year": 2026, "term": 132, "numbers_str": "", "_future": True},
        ],
        future_only=True,
        safety_draw_map={(2026, 131): True, (2026, 132): True},
        lottery_type=3,
        site_id=7,
        site_web_id=6,
        db_path="fake-db",
        default_target_hit_rate=0.65,
        simulation_config=SimulationConfig(target_hit_rate=1.0),
        zodiac_map={"07": "rat"},
        color_map={"07": "red"},
        trigger="test",
        allow_overwrite=True,
        resolve_prediction_table_for_mode=lambda conn, mode_id, default_table: default_table,
        build_generated_prediction_row_data=lambda **kwargs: kwargs,
    )

    assert report["inserted"] == 2
    assert states == [
        SimulationState(consecutive_hits=0, consecutive_misses=0),
        SimulationState(consecutive_hits=1, consecutive_misses=0),
    ]
    assert report["simulation"] == {
        "enabled": True,
        "target_hit_rate": 1.0,
        "max_consecutive_hits": 3,
        "max_consecutive_misses": 3,
        "truth_available": 2,
        "truth_missing": 0,
        "hits": 2,
        "misses": 0,
        "reversals": 0,
        "skipped": 0,
        "modes_used": [43],
        "modes_skipped": [],
        "mechanisms_used": ["pt3xiao"],
        "mechanisms_skipped": [],
    }
    assert "01" not in str(report["simulation"])
    assert "07" not in str(report["simulation"])
    assert all(row["res_code"] == "" for row in calls)
    assert all("_simulation_should_hit" not in row for row in calls)


def test_process_single_module_reports_missing_future_truth_as_skipped_simulation(monkeypatch):
    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda mechanism_key, mode_id, db_path: (_config(), mechanism_key, False),
    )
    monkeypatch.setattr(service, "_load_recent_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(service, "enforce_prediction_diversity", lambda **kwargs: kwargs["row_data"])
    monkeypatch.setattr(service, "_repair_text_prediction_diversity", lambda *args, **kwargs: kwargs["row_data"])
    monkeypatch.setattr(service.generation_repository, "get_future_draw_truth", lambda conn, **kwargs: None)
    monkeypatch.setattr(
        service,
        "_generate_single_draw_row",
        lambda **kwargs: {
            "type": str(kwargs["lottery_type"]),
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": str(kwargs["site_web_id"]),
            "content": "rat",
            "res_code": kwargs["safe_res_code"] or "",
        },
    )
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda conn, table_name, row_data, allow_overwrite: {"action": "inserted"},
    )

    report = service._process_single_module(
        conn=object(),
        module_row={"id": 1, "mechanism_key": "pt3xiao", "mode_id": 43},
        draws=[],
        future_draws=[{"year": 2026, "term": 131, "numbers_str": "", "_future": True}],
        future_only=True,
        safety_draw_map={(2026, 131): True},
        lottery_type=3,
        site_id=7,
        site_web_id=6,
        db_path="fake-db",
        default_target_hit_rate=0.65,
        simulation_config=SimulationConfig(target_hit_rate=0.5),
        zodiac_map={},
        color_map={},
        trigger="test",
        allow_overwrite=True,
        resolve_prediction_table_for_mode=lambda conn, mode_id, default_table: default_table,
        build_generated_prediction_row_data=lambda **kwargs: kwargs,
    )

    assert report["simulation"]["truth_available"] == 0
    assert report["simulation"]["truth_missing"] == 1
    assert report["simulation"]["hits"] == 0
    assert report["simulation"]["misses"] == 0
    assert report["simulation"]["modes_used"] == []
    assert report["simulation"]["modes_skipped"] == [43]
    assert report["simulation"]["mechanisms_used"] == []
    assert report["simulation"]["mechanisms_skipped"] == ["pt3xiao"]


def test_mode_65_future_taiwan_simulation_forces_matching_number_segment():
    row_data = service._generate_mode_65_row(
        draw={"year": 2026, "term": 131},
        is_future=True,
        lottery_type=3,
        site_web_id=6,
        build_row=lambda **kwargs: {
            "content": kwargs["generated_content"],
            "res_code": kwargs["res_code"],
        },
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "27"),
            special_code="27",
            special_zodiac="rabbit",
            special_color="red",
        ),
        simulation_config=SimulationConfig(target_hit_rate=1.0),
        simulation_state=SimulationState(),
        site_id=7,
        mechanism_key="mode65",
    )

    assert row_data["content"] == ",".join(f"{i:02d}" for i in range(25, 37))
    assert row_data["res_code"] == ""
    assert row_data["_simulation_should_hit"] is True


def test_mode_108_future_taiwan_simulation_forces_matching_size_group(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "labels": ["small"],
                "content": "small",
            }
        },
    )

    row_data = service._generate_mode_108_row(
        draw={"year": 2026, "term": 131},
        is_future=True,
        safe_res_code=None,
        lottery_type=3,
        site_web_id=6,
        config=_config(),
        table_name="mode_payload_108",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        build_row=lambda **kwargs: {
            "content": kwargs["generated_content"]["content"],
            "tou": kwargs["generated_content"]["tou"],
            "res_code": kwargs["res_code"],
        },
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "27"),
            special_code="27",
            special_zodiac="rabbit",
            special_color="red",
        ),
        simulation_config=SimulationConfig(target_hit_rate=1.0),
        simulation_state=SimulationState(),
        site_id=7,
        mechanism_key="mode108",
    )

    assert row_data["content"][0].split("|", 1)[0]
    assert row_data["content"][0].endswith("27")
    assert row_data["tou"] == ["2tou"]
    assert row_data["res_code"] == ""
    assert row_data["_simulation_should_hit"] is True
