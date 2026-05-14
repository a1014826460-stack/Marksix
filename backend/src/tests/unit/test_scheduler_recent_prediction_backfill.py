from __future__ import annotations

from crawler import scheduler


class _FakeCursorConnection:
    def __init__(self, draws, sites, modules):
        self._draws = draws
        self._sites = sites
        self._modules = modules

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=()):
        normalized = " ".join(str(query).split())
        if "FROM lottery_draws" in normalized:
            return _Rows(self._draws)
        if "FROM managed_sites" in normalized:
            return _Rows(self._sites)
        if "FROM site_prediction_modules" in normalized:
            site_id = int(params[0])
            return _Rows(self._modules.get(site_id, []))
        raise AssertionError(f"Unexpected query: {query}")


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


def test_recent_periods_skip_when_all_enabled_site_modules_already_exist(monkeypatch):
    generated_calls: list[tuple[int, str]] = []
    logged_actions: list[tuple[str, str]] = []

    monkeypatch.setattr(
        scheduler,
        "_cfg",
        lambda _db_path, key, default=None: 1 if key == "prediction.recent_period_count" else default,
    )
    monkeypatch.setattr(
        scheduler,
        "db_connect",
        lambda _db_path: _FakeCursorConnection(
            draws=[{"year": 2026, "term": 133, "numbers": "01,02,03,04,05,06,07"}],
            sites=[{"id": 10, "web_id": 4}],
            modules={10: [{"mechanism_key": "m1", "mode_id": 44}]},
        ),
    )
    monkeypatch.setattr(
        "utils.created_prediction_store.created_prediction_issue_exists",
        lambda conn, table_name, lottery_type, year, term, web_value=None: True,
    )
    monkeypatch.setattr(
        "admin.prediction.bulk_generate_site_prediction_data",
        lambda db_path, site_id, payload: generated_calls.append((site_id, payload["start_issue"])) or {"inserted": 1, "updated": 0, "errors": 0},
    )
    monkeypatch.setattr(
        scheduler,
        "_log_backfill_event",
        lambda db_path, lottery_type_id, period, action, detail="": logged_actions.append((action, detail)),
    )

    report = scheduler._ensure_recent_periods_have_predictions("fake-db", 3, 2026, 133)

    assert report["checked"] == 1
    assert report["missing"] == 0
    assert report["generated"] == 0
    assert report["errors"] == 0
    assert generated_calls == []
    assert report["periods"][0]["action"] == "skipped_existing"
    assert any(action == "skipped_existing" for action, _detail in logged_actions)


def test_recent_periods_generate_only_missing_sites(monkeypatch):
    generated_calls: list[tuple[int, str]] = []

    monkeypatch.setattr(
        scheduler,
        "_cfg",
        lambda _db_path, key, default=None: 1 if key == "prediction.recent_period_count" else default,
    )
    monkeypatch.setattr(
        scheduler,
        "db_connect",
        lambda _db_path: _FakeCursorConnection(
            draws=[{"year": 2026, "term": 133, "numbers": "01,02,03,04,05,06,07"}],
            sites=[{"id": 10, "web_id": 4}, {"id": 20, "web_id": 9}],
            modules={
                10: [{"mechanism_key": "m1", "mode_id": 44}],
                20: [{"mechanism_key": "m1", "mode_id": 44}],
            },
        ),
    )

    def _fake_exists(conn, table_name, lottery_type, year, term, web_value=None):
        return str(web_value) == "4"

    monkeypatch.setattr(
        "utils.created_prediction_store.created_prediction_issue_exists",
        _fake_exists,
    )
    monkeypatch.setattr(
        "admin.prediction.bulk_generate_site_prediction_data",
        lambda db_path, site_id, payload: generated_calls.append((site_id, payload["start_issue"])) or {"inserted": 1, "updated": 0, "errors": 0},
    )
    monkeypatch.setattr(
        scheduler,
        "_log_backfill_event",
        lambda *args, **kwargs: None,
    )

    report = scheduler._ensure_recent_periods_have_predictions("fake-db", 3, 2026, 133)

    assert report["checked"] == 1
    assert report["missing"] == 1
    assert report["generated"] == 1
    assert report["errors"] == 0
    assert generated_calls == [(20, "2026133")]
    assert report["periods"][0]["action"] == "generated"


def test_recent_periods_generate_only_missing_modules(monkeypatch):
    generated_calls: list[tuple[int, str, list[str], bool]] = []

    monkeypatch.setattr(
        scheduler,
        "_cfg",
        lambda _db_path, key, default=None: 1 if key == "prediction.recent_period_count" else default,
    )
    monkeypatch.setattr(
        scheduler,
        "db_connect",
        lambda _db_path: _FakeCursorConnection(
            draws=[{"year": 2026, "term": 133, "numbers": "01,02,03,04,05,06,07"}],
            sites=[{"id": 10, "web_id": 4}],
            modules={
                10: [
                    {"mechanism_key": "existing", "mode_id": 44},
                    {"mechanism_key": "missing", "mode_id": 45},
                ],
            },
        ),
    )

    def _fake_exists(conn, table_name, lottery_type, year, term, web_value=None):
        return table_name == "mode_payload_44"

    monkeypatch.setattr(
        "utils.created_prediction_store.created_prediction_issue_exists",
        _fake_exists,
    )
    monkeypatch.setattr(
        "admin.prediction.bulk_generate_site_prediction_data",
        lambda db_path, site_id, payload: generated_calls.append((
            site_id,
            payload["start_issue"],
            list(payload["mechanism_keys"]),
            bool(payload["allow_overwrite"]),
        )) or {"inserted": 1, "updated": 0, "skipped_existing": 0, "errors": 0},
    )
    monkeypatch.setattr(
        scheduler,
        "_log_backfill_event",
        lambda *args, **kwargs: None,
    )

    report = scheduler._ensure_recent_periods_have_predictions("fake-db", 3, 2026, 133)

    assert report["missing"] == 1
    assert report["generated"] == 1
    assert generated_calls == [(10, "2026133", ["missing"], False)]
