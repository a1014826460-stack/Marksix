"""Safe, versioned cache snapshots for the public draw read endpoints.

Only endpoint JSON that is already public is stored here.  Database-shaped draw
rows are deliberately rejected so a Future Issue cannot leak through Redis.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from time import time
from typing import Any, Callable, Mapping

from cache.contracts import CacheStore


_KEY_VERSION = "v1"
_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_LATEST_DRAW_FIELDS = frozenset({"current_issue", "draw_time", "result_balls", "special_ball"})
_CURRENT_PERIOD_FIELDS = frozenset(
    {"lottery_type_id", "lottery_name", "current_period", "current_year", "current_term"}
)
_FORBIDDEN_FIELDS = frozenset({"numbers", "res_sx", "res_color", "is_opened"})
_BALL_FIELDS = frozenset({"value", "zodiac", "color"})


@dataclass(frozen=True)
class SnapshotKeys:
    """The immutable entry and mutable pointer for a single public endpoint."""

    pointer_key: str
    version_key: str


def _snapshot_keys(lottery_type_id: int, snapshot_type: str, version: str) -> SnapshotKeys:
    lottery_type = _validate_lottery_type(lottery_type_id)
    version_value = _validate_version(version)
    base = f"public:draw-snapshot:{_KEY_VERSION}:lottery:{lottery_type}:{snapshot_type}"
    return SnapshotKeys(
        pointer_key=f"{base}:pointer",
        version_key=f"{base}:version:{version_value}",
    )


def _version_key_prefix(lottery_type_id: int, snapshot_type: str) -> str:
    lottery_type = _validate_lottery_type(lottery_type_id)
    return f"public:draw-snapshot:{_KEY_VERSION}:lottery:{lottery_type}:{snapshot_type}:version:"


def latest_draw_snapshot_keys(lottery_type_id: int, version: str) -> SnapshotKeys:
    """Return stable keys for a `GET /api/public/latest-draw` snapshot."""
    return _snapshot_keys(lottery_type_id, "latest-draw", version)


def current_period_snapshot_keys(lottery_type_id: int, version: str) -> SnapshotKeys:
    """Return stable keys for a `GET /api/public/current-period` snapshot."""
    return _snapshot_keys(lottery_type_id, "current-period", version)


class PublicDrawSnapshots:
    """Publish and read validated public draw JSON through immutable versions."""

    def __init__(
        self,
        cache: CacheStore,
        *,
        ttl_seconds: int = 120,
        clock: Callable[[], float] = time,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    def publish_latest_draw(
        self,
        lottery_type_id: int,
        payload: Mapping[str, Any],
        *,
        version: str,
        is_opened: bool,
        published_at: float | None = None,
    ) -> bool:
        """Publish an Opened Draw's existing latest-draw response, or do nothing."""
        return self._publish(
            lottery_type_id,
            payload,
            version=version,
            is_opened=is_opened,
            snapshot_type="latest_draw",
            keys=latest_draw_snapshot_keys,
            published_at=published_at,
        )

    def publish_current_period(
        self,
        lottery_type_id: int,
        payload: Mapping[str, Any],
        *,
        version: str,
        is_opened: bool,
        published_at: float | None = None,
    ) -> bool:
        """Publish an Opened Draw's existing current-period response, or do nothing."""
        return self._publish(
            lottery_type_id,
            payload,
            version=version,
            is_opened=is_opened,
            snapshot_type="current_period",
            keys=current_period_snapshot_keys,
            published_at=published_at,
        )

    def get_latest_draw(self, lottery_type_id: int) -> dict[str, Any] | None:
        return self._get(lottery_type_id, "latest_draw")

    def get_current_period(self, lottery_type_id: int) -> dict[str, Any] | None:
        return self._get(lottery_type_id, "current_period")

    def _publish(
        self,
        lottery_type_id: int,
        payload: Mapping[str, Any],
        *,
        version: str,
        is_opened: bool,
        snapshot_type: str,
        keys: Callable[[int, str], SnapshotKeys],
        published_at: float | None,
    ) -> bool:
        lottery_type = _validate_lottery_type(lottery_type_id)
        if not is_opened:
            return False
        public_payload = _validate_payload(snapshot_type, lottery_type, payload)
        snapshot_keys = keys(lottery_type, version)
        envelope = {
            "schema_version": 1,
            "snapshot_type": snapshot_type,
            "lottery_type_id": lottery_type,
            # A retried Outbox event must reproduce its immutable bytes exactly.
            "published_at": self._clock() if published_at is None else published_at,
            "payload": public_payload,
        }
        encoded = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._cache.publish_versioned(
            snapshot_keys.pointer_key,
            snapshot_keys.version_key,
            encoded,
            ttl_seconds=self._ttl_seconds,
        )
        return True

    def _get(self, lottery_type_id: int, snapshot_type: str) -> dict[str, Any] | None:
        lottery_type = _validate_lottery_type(lottery_type_id)
        key_type = snapshot_type.replace("_", "-")
        pointer_key = _snapshot_keys(lottery_type, key_type, "pointer").pointer_key
        pointer = self._cache.get(pointer_key)
        if pointer is None:
            return None
        try:
            version_key = pointer.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if not version_key.startswith(_version_key_prefix(lottery_type, key_type)):
            return None
        version = version_key.removeprefix(_version_key_prefix(lottery_type, key_type))
        try:
            _validate_version(version)
        except ValueError:
            return None
        raw = self._cache.get(version_key)
        if raw is None:
            return None
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(envelope, Mapping):
            return None
        if (
            envelope.get("schema_version") != 1
            or envelope.get("snapshot_type") != snapshot_type
            or envelope.get("lottery_type_id") != lottery_type
            or not _is_finite_number(envelope.get("published_at"))
        ):
            return None
        payload = envelope.get("payload")
        try:
            return _validate_payload(snapshot_type, lottery_type, payload)
        except ValueError:
            return None


def _validate_lottery_type(lottery_type_id: int) -> int:
    if isinstance(lottery_type_id, bool) or not isinstance(lottery_type_id, int) or lottery_type_id <= 0:
        raise ValueError("lottery_type_id must be a positive integer")
    return lottery_type_id


def _validate_version(version: str) -> str:
    if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
        raise ValueError("version must contain only letters, numbers, dot, underscore, or hyphen")
    return version


def _validate_payload(
    snapshot_type: str,
    lottery_type_id: int,
    payload: Any,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("public snapshot payload must be an object")
    fields = set(payload)
    forbidden = fields & _FORBIDDEN_FIELDS
    if forbidden:
        raise ValueError(f"public snapshot field(s) not allowed: {', '.join(sorted(forbidden))}")
    allowed = _LATEST_DRAW_FIELDS if snapshot_type == "latest_draw" else _CURRENT_PERIOD_FIELDS
    if fields != allowed:
        raise ValueError("public snapshot payload fields are not allowed")
    result = dict(payload)
    if snapshot_type == "latest_draw":
        if not isinstance(result["current_issue"], str) or not isinstance(result["draw_time"], str):
            raise ValueError("latest draw issue and time must be strings")
        if not isinstance(result["result_balls"], list):
            raise ValueError("latest draw result_balls must be a list")
        for ball in result["result_balls"]:
            _validate_ball(ball)
        if result["special_ball"] is not None:
            _validate_ball(result["special_ball"])
    else:
        if result["lottery_type_id"] != lottery_type_id:
            raise ValueError("current period lottery_type_id must match cache key")
        if not isinstance(result["lottery_name"], str) or not isinstance(result["current_period"], str):
            raise ValueError("current period names must be strings")
        if isinstance(result["current_year"], bool) or not isinstance(result["current_year"], int):
            raise ValueError("current_year must be an integer")
        if isinstance(result["current_term"], bool) or not isinstance(result["current_term"], int):
            raise ValueError("current_term must be an integer")
    return result


def _validate_ball(ball: Any) -> None:
    if not isinstance(ball, Mapping) or set(ball) != _BALL_FIELDS:
        raise ValueError("latest draw ball fields are not allowed")
    if any(not isinstance(ball[field], str) for field in _BALL_FIELDS):
        raise ValueError("latest draw ball values must be strings")


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)
