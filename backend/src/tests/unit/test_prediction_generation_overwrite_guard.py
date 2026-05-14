from __future__ import annotations

from prediction_generation import service


def test_persist_generated_row_skips_existing_when_overwrite_disabled(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "find_existing_created_row",
        lambda conn, table_name, row_data: {"id": "c7", "created_at": "2026-05-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda conn, table_name, row_data: calls.append("upsert") or {"action": "updated"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "old"},
        allow_overwrite=False,
    )

    assert result["action"] == "skipped_existing"
    assert result["id"] == "c7"
    assert calls == []


def test_persist_generated_row_allows_admin_overwrite(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "find_existing_created_row",
        lambda conn, table_name, row_data: {"id": "c7", "created_at": "2026-05-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda conn, table_name, row_data: calls.append("upsert") or {"action": "updated"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "new"},
        allow_overwrite=True,
    )

    assert result["action"] == "updated"
    assert calls == ["upsert"]
