from __future__ import annotations

from db import connect
from domains.prediction.generation_control_repository import (
    load_adjacent_controls,
    reserve_control,
)
from tables import ensure_admin_tables


def _reserve(
    conn,
    *,
    term: int,
    web_id: int,
    signature: tuple[str, ...],
    prefix_signature: tuple[str, ...],
):
    return reserve_control(
        conn,
        lottery_type_id=3,
        year=2026,
        term=term,
        mode_id=470,
        web_id=web_id,
        rule_id="zodiac",
        rule_revision=1,
        target_hit=True,
        verified_hit=True,
        signature=signature,
        prefix_signature=prefix_signature,
        created_at="2026-07-18T00:00:00Z",
    )


def test_cross_site_same_prefix_cannot_be_reserved(tmp_path):
    db_path = str(tmp_path / "controls.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        first = _reserve(
            conn,
            term=131,
            web_id=4,
            signature=("虎", "猪", "羊"),
            prefix_signature=("虎",),
        )
        second = _reserve(
            conn,
            term=131,
            web_id=5,
            signature=("虎", "鼠", "马"),
            prefix_signature=("虎",),
        )
        stored = conn.execute(
            "SELECT signature_hash, prefix_hash FROM prediction_generation_controls"
        ).fetchone()

    assert first == {"reserved": True, "reason": ""}
    assert second == {"reserved": False, "reason": "cross_site_prefix_conflict"}
    assert "虎" not in str(dict(stored))
    assert "猪" not in str(dict(stored))


def test_adjacent_control_lookup_returns_only_signature_hashes(tmp_path):
    db_path = str(tmp_path / "adjacent-controls.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _reserve(
            conn,
            term=198,
            web_id=4,
            signature=("鼠", "猪", "羊"),
            prefix_signature=("鼠",),
        )
        _reserve(
            conn,
            term=200,
            web_id=4,
            signature=("牛", "马", "狗"),
            prefix_signature=("牛",),
        )

        rows = load_adjacent_controls(
            conn,
            lottery_type_id=3,
            year=2026,
            term=199,
            mode_id=470,
            web_id=4,
        )

    assert {row["term"] for row in rows} == {198, 200}
    assert all(set(row) == {"year", "term", "signature_hash"} for row in rows)


def test_adjacent_control_lookup_includes_previous_year_last_issue(tmp_path):
    db_path = str(tmp_path / "cross-year-adjacent-controls.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _reserve(
            conn,
            term=999,
            web_id=4,
            signature=("鼠", "猪", "羊"),
            prefix_signature=("鼠",),
        )
        conn.execute(
            "UPDATE prediction_generation_controls SET year = ? WHERE term = ?",
            (2025, 999),
        )

        rows = load_adjacent_controls(
            conn,
            lottery_type_id=3,
            year=2026,
            term=1,
            mode_id=470,
            web_id=4,
        )

    assert {(row["year"], row["term"]) for row in rows} == {(2025, 999)}
    assert all(set(row) == {"year", "term", "signature_hash"} for row in rows)
