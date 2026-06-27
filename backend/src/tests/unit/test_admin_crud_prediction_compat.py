from __future__ import annotations

from pathlib import Path

from admin import crud


def test_prediction_module_crud_compat_delegates_to_domain_service(monkeypatch):
    calls: list[tuple[str, tuple[object, ...]]] = []

    def _delegate(name: str, result):
        def _impl(*args):
            calls.append((name, args))
            return result

        return _impl

    monkeypatch.setattr(
        "domains.prediction.service.list_site_prediction_modules",
        _delegate("list", {"modules": []}),
    )
    monkeypatch.setattr(
        "domains.prediction.service.add_site_prediction_module",
        _delegate("add", {"id": 1}),
    )
    monkeypatch.setattr(
        "domains.prediction.service.update_site_prediction_module",
        _delegate("update", {"id": 2}),
    )
    monkeypatch.setattr(
        "domains.prediction.service.delete_site_prediction_module",
        _delegate("delete", None),
    )
    monkeypatch.setattr(
        "domains.prediction.service.run_prediction",
        _delegate("run", {"ok": True}),
    )

    db_path = Path("test.sqlite3")
    assert crud.list_site_prediction_modules(db_path, 5) == {"modules": []}
    assert crud.add_site_prediction_module(db_path, 5, {"mechanism_key": "m"}) == {"id": 1}
    assert crud.update_site_prediction_module(db_path, 5, 9, {"status": 0}) == {"id": 2}
    assert crud.delete_site_prediction_module(db_path, 5, 9) is None
    assert crud.run_site_prediction_module(db_path, 5, {"mechanism_key": "m"}) == {"ok": True}

    assert calls == [
        ("list", (db_path, 5)),
        ("add", (db_path, 5, {"mechanism_key": "m"})),
        ("update", (db_path, 5, 9, {"status": 0})),
        ("delete", (db_path, 5, 9)),
        ("run", (db_path, 5, {"mechanism_key": "m"})),
    ]
