"""Thread-safe in-process cache for Windows development and tests."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable

from cache.contracts import CacheUnavailable


@dataclass(frozen=True)
class _Entry:
    value: bytes
    expires_at: float


class MemoryCacheStore:
    """Local TTL store; publication holds one lock so readers see complete versions."""

    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, _Entry] = {}
        self._lock = RLock()

    def get(self, key: str) -> bytes | None:
        try:
            with self._lock:
                entry = self._entries.get(key)
                if entry is None:
                    return None
                if entry.expires_at <= self._clock():
                    self._entries.pop(key, None)
                    return None
                return entry.value
        except CacheUnavailable:
            raise
        except Exception as exc:
            raise CacheUnavailable(str(exc)) from exc

    def _write(self, key: str, value: bytes, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._entries[key] = _Entry(bytes(value), self._clock() + ttl_seconds)

    def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        try:
            with self._lock:
                self._write(key, value, ttl_seconds)
        except CacheUnavailable:
            raise
        except Exception as exc:
            raise CacheUnavailable(str(exc)) from exc

    def delete(self, key: str) -> None:
        try:
            with self._lock:
                self._entries.pop(key, None)
        except Exception as exc:
            raise CacheUnavailable(str(exc)) from exc

    def publish_versioned(
        self,
        pointer_key: str,
        version_key: str,
        value: bytes,
        *,
        ttl_seconds: int,
    ) -> None:
        try:
            with self._lock:
                # The version is durable in the adapter before readers can see its pointer.
                self._write(version_key, value, ttl_seconds)
                self._write(pointer_key, version_key.encode("utf-8"), ttl_seconds)
        except CacheUnavailable:
            raise
        except Exception as exc:
            raise CacheUnavailable(str(exc)) from exc

    def get_versioned(self, pointer_key: str) -> bytes | None:
        pointer = self.get(pointer_key)
        if pointer is None:
            return None
        try:
            version_key = pointer.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return self.get(version_key)
