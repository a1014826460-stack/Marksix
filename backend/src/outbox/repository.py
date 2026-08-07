"""Portable persistence primitives for the authoritative draw Outbox."""

from __future__ import annotations

import json
from typing import Any, Mapping

from database.connection import utc_now
from database.schema.outbox import PUBLICATION_OUTBOX_TABLE


def enqueue_event(
    conn: Any,
    *,
    event_key: str,
    event_type: str,
    payload: Mapping[str, Any] | str,
    now: str | None = None,
) -> bool:
    """Append an event in the caller's transaction, once per business key.

    No commit is performed here: an Outbox event becomes visible exactly when
    the draw state transaction that called this function commits.
    """
    created_at = now or utc_now()
    payload_json = _payload_json(payload)
    cursor = conn.execute(
        f"""
        INSERT INTO {PUBLICATION_OUTBOX_TABLE} (
            event_key, event_type, payload_json, status, available_at,
            attempts, created_at, updated_at
        ) VALUES (?, ?, ?, 'pending', ?, 0, ?, ?)
        ON CONFLICT(event_key) DO NOTHING
        """,
        (event_key, event_type, payload_json, created_at, created_at, created_at),
    )
    return cursor.rowcount == 1


def claim_due_events(
    conn: Any,
    *,
    owner: str,
    now: str | None = None,
    lease_until: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Claim currently due events, including events abandoned by an expired lease.

    Each candidate is conditionally updated so competing worker processes can
    select the same row but only one can own it.  This works with both SQLite
    and PostgreSQL without database-specific `SKIP LOCKED` syntax.
    """
    if not owner:
        raise ValueError("owner must not be empty")
    if limit <= 0:
        return []
    claimed_at = now or utc_now()
    candidates = conn.execute(
        f"""
        SELECT id
        FROM {PUBLICATION_OUTBOX_TABLE}
        WHERE (status = 'pending' AND available_at <= ?)
           OR (status = 'processing' AND lease_until IS NOT NULL AND lease_until <= ?)
        ORDER BY available_at ASC, id ASC
        LIMIT ?
        """,
        (claimed_at, claimed_at, limit),
    ).fetchall()
    claimed: list[dict[str, Any]] = []
    for candidate in candidates:
        event_id = int(candidate["id"])
        updated = conn.execute(
            f"""
            UPDATE {PUBLICATION_OUTBOX_TABLE}
            SET status = 'processing', lease_owner = ?, lease_until = ?,
                attempts = attempts + 1, updated_at = ?
            WHERE id = ?
              AND (
                    (status = 'pending' AND available_at <= ?)
                    OR (status = 'processing' AND lease_until IS NOT NULL AND lease_until <= ?)
                  )
            """,
            (owner, lease_until, claimed_at, event_id, claimed_at, claimed_at),
        )
        if updated.rowcount != 1:
            continue
        row = conn.execute(
            f"""
            SELECT id, event_key, event_type, payload_json, status, available_at,
                   lease_owner, lease_until, attempts, last_error, published_at,
                   created_at, updated_at
            FROM {PUBLICATION_OUTBOX_TABLE}
            WHERE id = ? AND status = 'processing' AND lease_owner = ?
            """,
            (event_id, owner),
        ).fetchone()
        if row:
            claimed.append(dict(row))
    return claimed


def mark_retry(
    conn: Any,
    *,
    event_id: int,
    owner: str,
    available_at: str,
    error: str,
    now: str | None = None,
) -> bool:
    """Release an owned event for a later retry without changing its attempts."""
    updated_at = now or utc_now()
    cursor = conn.execute(
        f"""
        UPDATE {PUBLICATION_OUTBOX_TABLE}
        SET status = 'pending', available_at = ?, lease_owner = NULL,
            lease_until = NULL, last_error = ?, updated_at = ?
        WHERE id = ? AND status = 'processing' AND lease_owner = ?
          AND lease_until > ?
        """,
        (available_at, error, updated_at, event_id, owner, updated_at),
    )
    return cursor.rowcount == 1


def mark_published(
    conn: Any,
    *,
    event_id: int,
    owner: str,
    now: str | None = None,
) -> bool:
    """Complete an event only while the calling worker still owns its lease."""
    published_at = now or utc_now()
    cursor = conn.execute(
        f"""
        UPDATE {PUBLICATION_OUTBOX_TABLE}
        SET status = 'published', lease_owner = NULL, lease_until = NULL,
            last_error = NULL, published_at = ?, updated_at = ?
        WHERE id = ? AND status = 'processing' AND lease_owner = ?
          AND lease_until > ?
        """,
        (published_at, published_at, event_id, owner, published_at),
    )
    return cursor.rowcount == 1


def _payload_json(payload: Mapping[str, Any] | str) -> str:
    if isinstance(payload, str):
        # Validate caller-supplied JSON so workers never discover malformed data.
        parsed = json.loads(payload)
        if not isinstance(parsed, Mapping):
            raise ValueError("outbox payload must be a JSON object")
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if not isinstance(payload, Mapping):
        raise ValueError("outbox payload must be an object")
    return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
