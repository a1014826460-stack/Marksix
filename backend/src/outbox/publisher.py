"""Consume authoritative draw Outbox events into safe public snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any, Callable

from cache.public_snapshots import PublicDrawSnapshots
from db import connect
from outbox.repository import claim_due_events, mark_published, mark_retry
from public.api import get_current_period, get_public_latest_draw


_DRAW_EVENTS = frozenset({"draw.published", "draw.refresh"})
_DRAW_EVENT_KEY = re.compile(r"^draw-(?:published|refresh):(\d+):(\d+):(\d+)(?::\d+)?$")


class DrawPublicationPublisher:
    """Publish claimed Draw events; the database row, not event payload, is authoritative."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        snapshots: PublicDrawSnapshots,
        owner: str,
        now: Callable[[], datetime] | None = None,
        lease_seconds: int = 30,
        retry_seconds: int = 5,
    ) -> None:
        if not owner:
            raise ValueError("owner must not be empty")
        self._db_path = db_path
        self._snapshots = snapshots
        self._owner = owner
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lease_seconds = lease_seconds
        self._retry_seconds = retry_seconds

    def drain(self, *, limit: int = 20) -> dict[str, int]:
        """Claim and publish a bounded batch; every failure remains retryable."""
        now = self._timestamp()
        lease_until = self._timestamp_after(self._lease_seconds)
        with connect(self._db_path) as conn:
            events = claim_due_events(
                conn, owner=self._owner, now=now, lease_until=lease_until, limit=limit,
            )

        result = {"published": 0, "retried": 0}
        for event in events:
            try:
                self._publish_event(event)
            except Exception as exc:
                if self._retry(event, str(exc)):
                    result["retried"] += 1
            else:
                if self._complete(event):
                    result["published"] += 1
        return result

    def _publish_event(self, event: dict[str, Any]) -> None:
        if str(event.get("event_type")) not in _DRAW_EVENTS:
            raise ValueError(f"unsupported publication event type: {event.get('event_type')}")
        lottery_type_id, year, term = self._draw_identity(event)
        with connect(self._db_path) as conn:
            draw = conn.execute(
                """
                SELECT is_opened FROM lottery_draws
                WHERE lottery_type_id = ? AND year = ? AND term = ?
                """,
                (lottery_type_id, year, term),
            ).fetchone()
        if not draw or int(draw["is_opened"] or 0) != 1:
            raise ValueError("authoritative draw is not opened")

        # Existing public API builders apply their established output shaping.
        latest_draw = get_public_latest_draw(self._db_path, lottery_type_id)
        current_period = get_current_period(self._db_path, lottery_type_id)
        version = f"{year}-{term}"
        self._snapshots.publish_latest_draw(
            lottery_type_id, latest_draw, version=version, is_opened=True,
        )
        self._snapshots.publish_current_period(
            lottery_type_id, current_period, version=version, is_opened=True,
        )

    def _complete(self, event: dict[str, Any]) -> bool:
        with connect(self._db_path) as conn:
            return mark_published(
                conn, event_id=int(event["id"]), owner=self._owner, now=self._timestamp(),
            )

    def _retry(self, event: dict[str, Any], error: str) -> bool:
        with connect(self._db_path) as conn:
            return mark_retry(
                conn,
                event_id=int(event["id"]),
                owner=self._owner,
                available_at=self._timestamp_after(self._retry_seconds),
                error=error[:1000],
                now=self._timestamp(),
            )

    @staticmethod
    def _draw_identity(event: dict[str, Any]) -> tuple[int, int, int]:
        """Use the immutable event key; payloads are only diagnostic metadata."""
        match = _DRAW_EVENT_KEY.fullmatch(str(event.get("event_key") or ""))
        if not match:
            raise ValueError("draw publication event key has no draw identity")
        return tuple(int(value) for value in match.groups())

    def _timestamp(self) -> str:
        return self._now().astimezone(timezone.utc).isoformat()

    def _timestamp_after(self, seconds: int) -> str:
        return (self._now().astimezone(timezone.utc) + timedelta(seconds=seconds)).isoformat()
