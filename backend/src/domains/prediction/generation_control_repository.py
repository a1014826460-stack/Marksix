"""Internal persistence for future-generation accuracy and diversity controls."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from .accuracy_plan import AccuracyPolicy, validate_rolling_hit_rate


def _signature_hash(values: Iterable[str]) -> str:
    payload = json.dumps([str(value) for value in values], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def acquire_issue_mode_lock(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
    mode_id: int,
) -> None:
    """Serialize PostgreSQL reservations for one issue/mode; SQLite tests need no lock."""
    if getattr(conn, "engine", "") != "postgres":
        return
    material = f"prediction-control:{lottery_type_id}:{year}:{term}:{mode_id}"
    lock_key = int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:15], 16)
    conn.execute("SELECT pg_advisory_xact_lock(?)", (lock_key,))


def reserve_control(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
    mode_id: int,
    web_id: int,
    rule_id: str,
    rule_revision: int,
    target_hit: bool,
    verified_hit: bool,
    signature: tuple[str, ...],
    prefix_signature: tuple[str, ...],
    created_at: str,
) -> dict[str, Any]:
    """Reserve a site candidate without exposing its raw signature to callers."""
    signature_hash = _signature_hash(signature)
    prefix_hash = _signature_hash(prefix_signature)
    existing_site = conn.execute(
        """
        SELECT 1
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND year = ? AND term = ? AND mode_id = ? AND web_id = ?
        LIMIT 1
        """,
        (int(lottery_type_id), int(year), int(term), int(mode_id), int(web_id)),
    ).fetchone()
    if existing_site:
        return {"reserved": False, "reason": "site_issue_already_reserved"}

    cursor = conn.execute(
        """
        INSERT INTO prediction_generation_controls (
            lottery_type_id, year, term, mode_id, web_id, rule_id, rule_revision,
            target_hit, verified_hit, signature_hash, prefix_hash, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
        """,
        (
            int(lottery_type_id), int(year), int(term), int(mode_id), int(web_id),
            str(rule_id), int(rule_revision), int(bool(target_hit)), int(bool(verified_hit)),
            signature_hash, prefix_hash, str(created_at), str(created_at),
        ),
    )
    if cursor.rowcount == 1:
        return {"reserved": True, "reason": ""}
    return {"reserved": False, "reason": "reservation_conflict"}


def load_adjacent_controls(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
    mode_id: int,
    web_id: int,
) -> list[dict[str, Any]]:
    """Return only non-sensitive hashes from the nearest issue on either side."""
    previous = conn.execute(
        """
        SELECT year, term, signature_hash
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND mode_id = ? AND web_id = ?
          AND (year < ? OR (year = ? AND term < ?))
        ORDER BY year DESC, term DESC
        LIMIT 1
        """,
        (
            int(lottery_type_id), int(mode_id), int(web_id),
            int(year), int(year), int(term),
        ),
    ).fetchone()
    following = conn.execute(
        """
        SELECT year, term, signature_hash
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND mode_id = ? AND web_id = ?
          AND (year > ? OR (year = ? AND term > ?))
        ORDER BY year ASC, term ASC
        LIMIT 1
        """,
        (
            int(lottery_type_id), int(mode_id), int(web_id),
            int(year), int(year), int(term),
        ),
    ).fetchone()
    rows = [row for row in (previous, following) if row]
    return [
        {"year": int(row["year"]), "term": int(row["term"]), "signature_hash": str(row["signature_hash"])}
        for row in rows
    ]


def list_recent_verified_outcomes(
    conn: Any,
    *,
    lottery_type_id: int,
    mode_id: int,
    web_id: int,
    before_issue: tuple[int, int],
    limit: int,
) -> list[bool]:
    rows = conn.execute(
        """
        SELECT verified_hit
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND mode_id = ? AND web_id = ?
          AND (year < ? OR (year = ? AND term < ?))
        ORDER BY year DESC, term DESC
        LIMIT ?
        """,
        (
            int(lottery_type_id), int(mode_id), int(web_id),
            int(before_issue[0]), int(before_issue[0]), int(before_issue[1]), int(limit),
        ),
    ).fetchall()
    return [bool(row["verified_hit"]) for row in reversed(rows)]


def load_controls_for_issue(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
    mode_id: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT web_id, prefix_hash
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND year = ? AND term = ? AND mode_id = ?
        """,
        (int(lottery_type_id), int(year), int(term), int(mode_id)),
    ).fetchall()
    return [{"web_id": int(row["web_id"]), "prefix_hash": str(row["prefix_hash"])} for row in rows]


def validate_affected_windows(
    conn: Any,
    *,
    lottery_type_id: int,
    mode_id: int,
    web_id: int,
    policy: AccuracyPolicy,
) -> list[tuple[int, int, int, int]]:
    rows = conn.execute(
        """
        SELECT verified_hit
        FROM prediction_generation_controls
        WHERE lottery_type_id = ? AND mode_id = ? AND web_id = ?
        ORDER BY year ASC, term ASC
        """,
        (int(lottery_type_id), int(mode_id), int(web_id)),
    ).fetchall()
    return validate_rolling_hit_rate([bool(row["verified_hit"]) for row in rows], policy=policy)
