from __future__ import annotations

from db import connect
from domains.prediction.accuracy_plan import AccuracyPolicy, validate_rolling_hit_rate
from domains.prediction.generation_control_repository import reserve_control
from domains.prediction.models import DrawTruth
from domains.prediction.simulation_service import SimulationConfig
from prediction_generation import service
from prediction_generation.service import _build_future_draws, _plan_persisted_future_control
from predict.mechanisms import PREDICTION_CONFIGS
from tables import ensure_admin_tables


def _truth(zodiac: str = "虎") -> DrawTruth:
    return DrawTruth(
        ("01", "02", "03", "04", "05", "06", "27"),
        "27",
        zodiac,
        "绿波",
    )


def _reserve(conn, plan, *, term: int, web_id: int) -> None:
    result = reserve_control(
        conn,
        lottery_type_id=3,
        year=2026,
        term=term,
        mode_id=470,
        web_id=web_id,
        rule_id=plan.rule_id,
        rule_revision=plan.rule_revision,
        target_hit=plan.target_hit,
        verified_hit=plan.verified_hit,
        signature=plan.signature,
        prefix_signature=plan.prefix_signature,
        created_at="2026-07-18T00:00:00Z",
    )
    assert result["reserved"] is True


def test_control_plan_guarantees_sixty_percent_across_two_generation_batches(tmp_path):
    db_path = str(tmp_path / "controlled-generation.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]
    outcomes: list[bool] = []

    with connect(db_path) as conn:
        for term in range(101, 121):
            plan = _plan_persisted_future_control(
                conn=conn,
                config=config,
                lottery_type=3,
                site_id=7,
                site_web_id=4,
                draw={"year": 2026, "term": term},
                truth=_truth(),
                simulation_config=SimulationConfig(target_hit_rate=0.6),
                mechanism_key="pt3xiao",
                predicted_labels=("鼠", "猪", "羊"),
            )
            assert plan is not None
            _reserve(conn, plan, term=term, web_id=4)
            outcomes.append(plan.verified_hit)

    assert validate_rolling_hit_rate(outcomes, policy=AccuracyPolicy()) == []


def test_batch_generation_includes_requested_next_issue_when_using_previous_draw_as_reference(monkeypatch):
    """A next-issue-only request must reach modules with its target future draw."""
    captured: list[list[dict]] = []

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(service, "ensure_prediction_configs_loaded", lambda *_args: None)
    monkeypatch.setattr(service, "_resolve_generation_context", lambda *_args: (4, "测试站点"))
    monkeypatch.setattr(service, "connect", lambda *_args: _Connection())
    monkeypatch.setattr(service, "load_fixed_data_maps", lambda *_args: ({}, {}))
    monkeypatch.setattr(service, "_default_target_hit_rate", lambda *_args: 0.65)
    monkeypatch.setattr(service, "_simulation_config", lambda *_args: SimulationConfig())
    monkeypatch.setattr(service, "_max_terms_per_year", lambda *_args: 365)
    monkeypatch.setattr(
        service.generation_repository,
        "list_enabled_site_prediction_modules",
        lambda *_args, **_kwargs: [{"id": 1, "mechanism_key": "daxiao", "mode_id": 57}],
    )
    monkeypatch.setattr(service, "list_opened_draws_in_issue_range", lambda *_args: [])
    monkeypatch.setattr(
        service,
        "find_latest_opened_draw_before_issue",
        lambda *_args: {"year": 2026, "term": 176, "numbers_str": "07,41,15,49,12,34,32"},
    )
    monkeypatch.setattr(service, "_build_safety_draw_map", lambda *_args: {})
    monkeypatch.setattr(service, "_log_module_result", lambda **_kwargs: None)
    monkeypatch.setattr(
        service,
        "_process_single_module",
        lambda **kwargs: captured.append(kwargs["future_draws"]) or {
            "inserted": 1,
            "updated": 0,
            "skipped_existing": 0,
            "errors": 0,
        },
    )

    result = service.generate_prediction_batch(
        "fake-db",
        site_id=4,
        lottery_type=3,
        start_issue=(2026, 177),
        end_issue=(2026, 177),
        mechanism_keys=["daxiao"],
        future_periods=1,
        future_only=True,
        trigger="test",
        sync_site_modules=lambda *_args: None,
        resolve_prediction_table_for_mode=lambda *_args: "mode_payload_57",
        build_generated_prediction_row_data=lambda **kwargs: kwargs,
    )

    assert [[(draw["year"], draw["term"]) for draw in draws] for draws in captured] == [[(2026, 177)]]
    assert result["inserted"] == 1


def test_batch_generation_reaches_a_requested_future_issue_beyond_precreated_draws(monkeypatch):
    """The requested target, not only the next offset, determines future generation."""
    captured: list[list[dict]] = []

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(service, "ensure_prediction_configs_loaded", lambda *_args: None)
    monkeypatch.setattr(service, "_resolve_generation_context", lambda *_args: (5, "台湾彩霸王"))
    monkeypatch.setattr(service, "connect", lambda *_args: _Connection())
    monkeypatch.setattr(service, "load_fixed_data_maps", lambda *_args: ({}, {}))
    monkeypatch.setattr(service, "_default_target_hit_rate", lambda *_args: 0.65)
    monkeypatch.setattr(service, "_simulation_config", lambda *_args: SimulationConfig())
    monkeypatch.setattr(service, "_max_terms_per_year", lambda *_args: 365)
    monkeypatch.setattr(
        service.generation_repository,
        "list_enabled_site_prediction_modules",
        lambda *_args, **_kwargs: [{"id": 1, "mechanism_key": "daxiao", "mode_id": 57}],
    )
    monkeypatch.setattr(service, "list_opened_draws_in_issue_range", lambda *_args: [])
    monkeypatch.setattr(
        service,
        "find_latest_opened_draw_before_issue",
        lambda *_args: {"year": 2026, "term": 208, "numbers_str": "07,41,15,49,12,34,32"},
    )
    monkeypatch.setattr(service, "_build_safety_draw_map", lambda *_args: {})
    monkeypatch.setattr(service, "_log_module_result", lambda **_kwargs: None)
    monkeypatch.setattr(
        service,
        "_process_single_module",
        lambda **kwargs: captured.append(kwargs["future_draws"]) or {
            "inserted": 1,
            "updated": 0,
            "skipped_existing": 0,
            "errors": 0,
        },
    )

    service.generate_prediction_batch(
        "fake-db",
        site_id=5,
        lottery_type=3,
        start_issue=(2026, 218),
        end_issue=(2026, 218),
        mechanism_keys=["daxiao"],
        future_periods=1,
        future_only=True,
        trigger="test",
        sync_site_modules=lambda *_args: None,
        resolve_prediction_table_for_mode=lambda *_args: "mode_payload_57",
        build_generated_prediction_row_data=lambda **kwargs: kwargs,
    )

    assert [[(draw["year"], draw["term"]) for draw in draws] for draws in captured] == [[(2026, 218)]]


def test_control_plan_forces_cross_site_prefix_and_same_site_adjacent_difference(tmp_path):
    db_path = str(tmp_path / "controlled-diversity.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]

    with connect(db_path) as conn:
        first = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=7, site_web_id=4,
            draw={"year": 2026, "term": 198}, truth=_truth(),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="pt3xiao", predicted_labels=("虎", "猪", "羊"),
        )
        assert first is not None
        _reserve(conn, first, term=198, web_id=4)

        adjacent = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=7, site_web_id=4,
            draw={"year": 2026, "term": 199}, truth=_truth(),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="pt3xiao", predicted_labels=("虎", "猪", "羊"),
        )
        assert adjacent is not None
        _reserve(conn, adjacent, term=199, web_id=4)

        other_site = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=8, site_web_id=5,
            draw={"year": 2026, "term": 199}, truth=_truth(),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="pt3xiao", predicted_labels=("虎", "猪", "羊"),
        )

    assert adjacent.signature != first.signature
    assert other_site is not None
    assert other_site.prefix_signature != adjacent.prefix_signature


def test_control_plan_reuses_prefix_when_binary_future_mode_is_exhausted(monkeypatch, tmp_path):
    """A diversity preference must not prevent all sites from generating a future row."""
    db_path = str(tmp_path / "binary-prefix-fallback.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["daxiao"]
    monkeypatch.setattr(service, "choose_target_hit", lambda *_args, **_kwargs: True)

    with connect(db_path) as conn:
        first = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=4, site_web_id=4,
            draw={"year": 2026, "term": 177}, truth=_truth(),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="daxiao", predicted_labels=("大",),
        )
        assert first is not None
        first_reservation = reserve_control(
            conn,
            lottery_type_id=3,
            year=2026,
            term=177,
            mode_id=57,
            web_id=4,
            rule_id=first.rule_id,
            rule_revision=first.rule_revision,
            target_hit=first.target_hit,
            verified_hit=first.verified_hit,
            signature=first.signature,
            prefix_signature=first.prefix_signature,
            created_at="2026-07-27T00:00:00Z",
        )
        assert first_reservation["reserved"] is True

        second = _plan_persisted_future_control(
            conn=conn, config=config, lottery_type=3, site_id=5, site_web_id=5,
            draw={"year": 2026, "term": 177}, truth=_truth(),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            mechanism_key="daxiao", predicted_labels=("大",),
        )

    assert second is not None
    assert second.prefix_signature == first.prefix_signature


def test_process_module_persists_binary_future_rows_for_multiple_sites(monkeypatch, tmp_path):
    """Every site must receive a future row even when its prefix repeats."""
    db_path = str(tmp_path / "binary-multiple-sites.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["daxiao"]
    persisted_rows: list[dict] = []

    monkeypatch.setattr(service, "_resolve_prediction_config_with_mode_fallback", lambda *_args: (config, "daxiao", False))
    monkeypatch.setattr(service.generation_repository, "get_future_draw_truth", lambda *_args, **_kwargs: _truth())
    monkeypatch.setattr(service, "choose_target_hit", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        service,
        "predict",
        lambda **_kwargs: {
            "prediction": {"labels": ["大"], "content": "大"},
            "mode": {"resolved_labels": list(config.labels)},
        },
    )
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda _conn, _table, row_data, allow_overwrite, *, commit=True:
            persisted_rows.append(dict(row_data)) or {"action": "inserted"},
    )

    reports: list[dict] = []
    with connect(db_path) as conn:
        for site_id, web_id in ((4, 4), (5, 5)):
            reports.append(service._process_single_module(
                conn=conn,
                module_row={"id": site_id, "mechanism_key": "daxiao", "mode_id": 57},
                draws=[], future_draws=[{"year": 2026, "term": 177, "numbers_str": "", "_future": True}],
                future_only=True, safety_draw_map={(2026, 177): True}, lottery_type=3,
                site_id=site_id, site_web_id=web_id, db_path=db_path, default_target_hit_rate=0.65,
                simulation_config=SimulationConfig(target_hit_rate=1.0), zodiac_map={"27": "虎"},
                color_map={"27": "绿波"}, trigger="test", allow_overwrite=True,
                resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_57",
                build_generated_prediction_row_data=lambda **kwargs: kwargs,
            ))

    assert [report["inserted"] for report in reports] == [1, 1]
    assert [report["errors"] for report in reports] == [0, 0]
    assert len(persisted_rows) == 2


def test_default_future_row_carries_an_internal_control_plan_without_result_fields(monkeypatch, tmp_path):
    db_path = str(tmp_path / "controlled-default-row.sqlite3")
    ensure_admin_tables(db_path)
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
        row = service._generate_default_mode_row(
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
            },
            lottery_type=3,
            site_web_id=4,
            conn=conn,
            truth=_truth(),
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            simulation_state=None,
            site_id=7,
            mechanism_key="pt3xiao",
        )

    assert "虎" in row["content"].split(",")
    assert row["res_code"] == ""
    assert row["_simulation_should_hit"] is True
    assert row["_generation_control"].verified_hit is True


def test_process_module_reserves_control_before_persisting_and_removes_private_plan(monkeypatch, tmp_path):
    db_path = str(tmp_path / "process-control.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]
    persisted_rows: list[dict] = []
    commit_values: list[bool] = []

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )

    def generate(**kwargs):
        control = _plan_persisted_future_control(
            conn=kwargs["conn"],
            config=config,
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            draw=kwargs["draw"],
            truth=kwargs["truth"],
            simulation_config=kwargs["simulation_config"],
            mechanism_key="pt3xiao",
            predicted_labels=("鼠", "猪", "羊"),
        )
        return {
            "type": "3",
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": "4",
            "content": ",".join(control.labels),
            "res_code": "",
            "_simulation_should_hit": control.verified_hit,
            "_generation_control": control,
        }

    monkeypatch.setattr(service, "_generate_single_draw_row", generate)
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda _conn, _table, row_data, allow_overwrite, *, commit=True: (
            commit_values.append(commit) or persisted_rows.append(dict(row_data)) or {"action": "inserted"}
        ),
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
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )
        controls = conn.execute(
            "SELECT target_hit, verified_hit FROM prediction_generation_controls"
        ).fetchall()

    assert report["inserted"] == 1
    assert len(controls) == 1
    assert persisted_rows[0]["res_code"] == ""
    assert "_generation_control" not in persisted_rows[0]
    assert commit_values == [False]


def test_process_module_discards_control_when_created_row_is_skipped(monkeypatch, tmp_path):
    db_path = str(tmp_path / "skipped-created-row-control.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )

    def generate(**kwargs):
        control = _plan_persisted_future_control(
            conn=kwargs["conn"],
            config=config,
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            draw=kwargs["draw"],
            truth=kwargs["truth"],
            simulation_config=kwargs["simulation_config"],
            mechanism_key="pt3xiao",
            predicted_labels=("鼠", "猪", "羊"),
        )
        return {
            "type": "3",
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": "4",
            "content": ",".join(control.labels),
            "res_code": "",
            "_simulation_should_hit": control.verified_hit,
            "_generation_control": control,
        }

    monkeypatch.setattr(service, "_generate_single_draw_row", generate)
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda *_args, **_kwargs: {"action": "skipped_existing"},
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
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=False,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )
        control_count = conn.execute(
            "SELECT COUNT(*) AS count FROM prediction_generation_controls"
        ).fetchone()["count"]

    assert report["skipped_existing"] == 1
    assert report["simulation"]["hits"] == 0
    assert control_count == 0


def test_process_module_reports_existing_future_row_without_control_conflict_error(monkeypatch, tmp_path):
    """A repeat future-generation request must recognize its persisted row first."""
    db_path = str(tmp_path / "existing-future-row-control.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )
    monkeypatch.setattr(
        service,
        "_find_existing_future_row",
        lambda *_args, **_kwargs: {"id": "c42", "created_at": "2026-07-27T04:00:00+00:00"},
    )
    generate_calls: list[str] = []
    monkeypatch.setattr(
        service,
        "_generate_single_draw_row",
        lambda **_kwargs: generate_calls.append("generated"),
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
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="admin_generate_all",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )

    assert report["inserted"] == 0
    assert report["updated"] == 0
    assert report["skipped_existing"] == 1
    assert report["errors"] == 0
    assert generate_calls == []


def test_process_module_rolls_back_control_when_created_row_persistence_fails(monkeypatch, tmp_path):
    db_path = str(tmp_path / "failed-created-row-control.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )

    def generate(**kwargs):
        control = _plan_persisted_future_control(
            conn=kwargs["conn"],
            config=config,
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            draw=kwargs["draw"],
            truth=kwargs["truth"],
            simulation_config=kwargs["simulation_config"],
            mechanism_key="pt3xiao",
            predicted_labels=("鼠", "猪", "羊"),
        )
        return {
            "type": "3",
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": "4",
            "content": ",".join(control.labels),
            "res_code": "",
            "_simulation_should_hit": control.verified_hit,
            "_generation_control": control,
        }

    monkeypatch.setattr(service, "_generate_single_draw_row", generate)
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("created row write failed")),
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
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )
        control_count = conn.execute(
            "SELECT COUNT(*) AS count FROM prediction_generation_controls"
        ).fetchone()["count"]

    assert report["errors"] == 1
    assert control_count == 0


def test_process_module_keeps_prior_control_when_a_later_created_row_write_fails(monkeypatch, tmp_path):
    db_path = str(tmp_path / "later-failed-created-row-control.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]
    persist_calls = 0

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )

    def generate(**kwargs):
        control = _plan_persisted_future_control(
            conn=kwargs["conn"],
            config=config,
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            draw=kwargs["draw"],
            truth=kwargs["truth"],
            simulation_config=kwargs["simulation_config"],
            mechanism_key="pt3xiao",
            predicted_labels=("鼠", "猪", "羊"),
        )
        return {
            "type": "3",
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": "4",
            "content": ",".join(control.labels),
            "res_code": "",
            "_simulation_should_hit": control.verified_hit,
            "_generation_control": control,
        }

    def persist_second_row_fails(*_args, **_kwargs):
        nonlocal persist_calls
        persist_calls += 1
        if persist_calls == 2:
            raise RuntimeError("second created row write failed")
        return {"action": "inserted"}

    monkeypatch.setattr(service, "_generate_single_draw_row", generate)
    monkeypatch.setattr(service, "_persist_generated_row", persist_second_row_fails)

    with connect(db_path) as conn:
        report = service._process_single_module(
            conn=conn,
            module_row={"id": 1, "mechanism_key": "pt3xiao", "mode_id": 470},
            draws=[],
            future_draws=[
                {"year": 2026, "term": 131, "numbers_str": "", "_future": True},
                {"year": 2026, "term": 132, "numbers_str": "", "_future": True},
            ],
            future_only=True,
            safety_draw_map={(2026, 131): True, (2026, 132): True},
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            db_path=db_path,
            default_target_hit_rate=0.65,
            simulation_config=SimulationConfig(target_hit_rate=1.0),
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )
        rows = conn.execute(
            "SELECT term FROM prediction_generation_controls ORDER BY term"
        ).fetchall()

    assert report["inserted"] == 1
    assert report["errors"] == 1
    assert [row["term"] for row in rows] == [131]


def test_process_module_replans_after_one_control_reservation_conflict(monkeypatch, tmp_path):
    db_path = str(tmp_path / "retry-control-reservation.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]
    persisted_rows: list[dict] = []
    original_reserve = service.reserve_control
    reserve_calls = 0

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (config, "pt3xiao", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )

    def generate(**kwargs):
        control = _plan_persisted_future_control(
            conn=kwargs["conn"],
            config=config,
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            draw=kwargs["draw"],
            truth=kwargs["truth"],
            simulation_config=kwargs["simulation_config"],
            mechanism_key="pt3xiao",
            predicted_labels=("鼠", "猪", "羊"),
        )
        return {
            "type": "3",
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": "4",
            "content": ",".join(control.labels),
            "res_code": "",
            "_simulation_should_hit": control.verified_hit,
            "_generation_control": control,
        }

    def reserve_once_then_delegate(*args, **kwargs):
        nonlocal reserve_calls
        reserve_calls += 1
        if reserve_calls == 1:
            return {"reserved": False, "reason": "reservation_conflict"}
        return original_reserve(*args, **kwargs)

    monkeypatch.setattr(service, "_generate_single_draw_row", generate)
    monkeypatch.setattr(service, "reserve_control", reserve_once_then_delegate)
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
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )

    assert reserve_calls == 2
    assert report["errors"] == 0
    assert report["inserted"] == 1
    assert len(persisted_rows) == 1
    assert "_generation_control" not in persisted_rows[0]


def test_process_module_blocks_unverified_future_rule_without_persisting(monkeypatch, tmp_path):
    db_path = str(tmp_path / "blocked-control.sqlite3")
    ensure_admin_tables(db_path)
    dynamic_config = type(
        "DynamicConfig",
        (),
        {"key": "title_9999", "default_modes_id": 9999, "default_table": "mode_payload_9999"},
    )()
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda *_args: (dynamic_config, "title_9999", False),
    )
    monkeypatch.setattr(
        service.generation_repository,
        "get_future_draw_truth",
        lambda *_args, **_kwargs: _truth(),
    )
    monkeypatch.setattr(service, "_generate_single_draw_row", lambda **_kwargs: calls.append("generate"))
    monkeypatch.setattr(service, "_persist_generated_row", lambda *_args, **_kwargs: calls.append("persist"))

    with connect(db_path) as conn:
        report = service._process_single_module(
            conn=conn,
            module_row={"id": 1, "mechanism_key": "title_9999", "mode_id": 9999},
            draws=[],
            future_draws=[{"year": 2026, "term": 131, "numbers_str": "", "_future": True}],
            future_only=True,
            safety_draw_map={(2026, 131): True},
            lottery_type=3,
            site_id=7,
            site_web_id=4,
            db_path=db_path,
            default_target_hit_rate=0.65,
            simulation_config=SimulationConfig(target_hit_rate=0.6),
            zodiac_map={"27": "虎"},
            color_map={"27": "绿波"},
            trigger="test",
            allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_9999",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )

    assert report["inserted"] == 0
    assert report["simulation"]["skipped"] == 1
    assert any("unverified rule" in warning for warning in report["warnings"])
    assert calls == []


def test_process_module_does_not_apply_legacy_diversity_after_control_reservation(monkeypatch, tmp_path):
    db_path = str(tmp_path / "controlled-no-legacy-diversity.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]
    persisted_rows: list[dict] = []

    monkeypatch.setattr(service, "_resolve_prediction_config_with_mode_fallback", lambda *_args: (config, "pt3xiao", False))
    monkeypatch.setattr(service.generation_repository, "get_future_draw_truth", lambda *_args, **_kwargs: _truth())
    monkeypatch.setattr(
        service,
        "_generate_single_draw_row",
        lambda **kwargs: {
            "type": "3",
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": "4",
            "content": "虎,猪,羊",
            "res_code": "",
            "_simulation_should_hit": True,
            "_generation_control": _plan_persisted_future_control(
                conn=kwargs["conn"], config=config, lottery_type=3, site_id=7, site_web_id=4,
                draw=kwargs["draw"], truth=kwargs["truth"],
                simulation_config=kwargs["simulation_config"], mechanism_key="pt3xiao",
                predicted_labels=("虎", "猪", "羊"),
            ),
        },
    )
    monkeypatch.setattr(
        service,
        "enforce_prediction_diversity",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy diversity must be bypassed")),
    )
    monkeypatch.setattr(
        service,
        "_repair_text_prediction_diversity",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("text diversity must be bypassed")),
    )
    monkeypatch.setattr(
        service,
        "_persist_generated_row",
        lambda _conn, _table, row_data, allow_overwrite, *, commit=True: persisted_rows.append(dict(row_data)) or {"action": "inserted"},
    )

    with connect(db_path) as conn:
        report = service._process_single_module(
            conn=conn, module_row={"id": 1, "mechanism_key": "pt3xiao", "mode_id": 470},
            draws=[], future_draws=[{"year": 2026, "term": 131, "numbers_str": "", "_future": True}],
            future_only=True, safety_draw_map={(2026, 131): True}, lottery_type=3,
            site_id=7, site_web_id=4, db_path=db_path, default_target_hit_rate=0.65,
            simulation_config=SimulationConfig(target_hit_rate=1.0), zodiac_map={"27": "虎"},
            color_map={"27": "绿波"}, trigger="test", allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )

    assert report["inserted"] == 1
    assert persisted_rows[0]["content"] == "虎,猪,羊"


def test_process_module_refuses_to_persist_when_all_controlled_prefixes_are_reserved(monkeypatch, tmp_path):
    db_path = str(tmp_path / "exhausted-prefixes.sqlite3")
    ensure_admin_tables(db_path)
    config = PREDICTION_CONFIGS["pt3xiao"]
    persisted_rows: list[dict] = []

    monkeypatch.setattr(service, "_resolve_prediction_config_with_mode_fallback", lambda *_args: (config, "pt3xiao", False))
    monkeypatch.setattr(service.generation_repository, "get_future_draw_truth", lambda *_args, **_kwargs: _truth())
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
        lambda _conn, _table, row_data, allow_overwrite: persisted_rows.append(dict(row_data)) or {"action": "inserted"},
    )

    with connect(db_path) as conn:
        for index, zodiac in enumerate(config.labels, start=20):
            reserve_control(
                conn,
                lottery_type_id=3,
                year=2026,
                term=131,
                mode_id=470,
                web_id=index,
                rule_id="zodiac",
                rule_revision=1,
                target_hit=True,
                verified_hit=True,
                signature=(zodiac, "鼠", "牛"),
                prefix_signature=(zodiac,),
                created_at="2026-07-18T00:00:00Z",
            )
        # `_load_recent_rows` safely rolls back when this SQLite fixture has no
        # created-schema table; preserve the pre-existing cross-site controls.
        conn.commit()

        report = service._process_single_module(
            conn=conn, module_row={"id": 1, "mechanism_key": "pt3xiao", "mode_id": 470},
            draws=[], future_draws=[{"year": 2026, "term": 131, "numbers_str": "", "_future": True}],
            future_only=True, safety_draw_map={(2026, 131): True}, lottery_type=3,
            site_id=7, site_web_id=4, db_path=db_path, default_target_hit_rate=0.65,
            simulation_config=SimulationConfig(target_hit_rate=1.0), zodiac_map={"27": "虎"},
            color_map={"27": "绿波"}, trigger="test", allow_overwrite=True,
            resolve_prediction_table_for_mode=lambda _conn, _mode_id, _default: "mode_payload_470",
            build_generated_prediction_row_data=lambda **kwargs: kwargs,
        )

    assert report["inserted"] == 0
    assert report["errors"] == 1
    assert persisted_rows == []
