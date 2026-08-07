"""Atomic public-publication event creation for authoritative lottery draws."""

from __future__ import annotations

from typing import Any, Mapping

from outbox.repository import enqueue_event

_PUBLIC_DRAW_FIELDS = (
    "lottery_type_id", "year", "term", "numbers", "draw_time", "next_time",
    "status", "is_opened", "next_term",
)


def enqueue_draw_publication(
    conn: Any,
    *,
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    now: str | None = None,
) -> str | None:
    """Enqueue an authoritative public event in the caller's draw transaction.

    The initial transition to an Opened Draw is keyed once.  Later changes to
    public data of an already opened draw receive sequential refresh keys, so a
    consumer cannot remain stale after a correction.
    """
    previous = dict(previous) if previous is not None else None
    current = dict(current)
    if not _is_opened(current):
        return None

    lottery_type_id, year, term = _identity(current)
    payload = _payload(current)
    if previous is None or not _is_opened(previous):
        enqueue_event(
            conn,
            event_key=f"draw-published:{lottery_type_id}:{year}:{term}",
            event_type="draw.published",
            payload=payload,
            now=now,
        )
        return "draw.published"

    if _payload(previous) == payload:
        return None

    prefix = f"draw-refresh:{lottery_type_id}:{year}:{term}:"
    row = conn.execute(
        "SELECT event_key FROM publication_outbox WHERE event_key LIKE ? "
        "ORDER BY id DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    version = _refresh_version(row["event_key"] if row else "", prefix) + 1
    enqueue_event(
        conn,
        event_key=f"{prefix}{version}",
        event_type="draw.refresh",
        payload=payload,
        now=now,
    )
    return "draw.refresh"


def enqueue_opened_draw_publication(conn: Any, draw: Mapping[str, Any], *, now: str | None = None) -> str | None:
    """Enqueue an initial event for rows atomically opened by a scheduler."""
    return enqueue_draw_publication(conn, previous={**draw, "is_opened": 0}, current=draw, now=now)


def _is_opened(draw: Mapping[str, Any]) -> bool:
    return bool(int(draw.get("is_opened") or 0))


def _identity(draw: Mapping[str, Any]) -> tuple[int, int, int]:
    return int(draw["lottery_type_id"]), int(draw["year"]), int(draw["term"])


def _payload(draw: Mapping[str, Any]) -> dict[str, Any]:
    # Never use a generic row dump: it risks leaking internal/future-only data.
    return {key: draw.get(key) for key in _PUBLIC_DRAW_FIELDS}


def _refresh_version(event_key: str, prefix: str) -> int:
    try:
        return int(str(event_key).removeprefix(prefix))
    except ValueError:
        return 0
