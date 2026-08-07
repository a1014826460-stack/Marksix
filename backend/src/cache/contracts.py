"""Small cache contract shared by local and Redis adapters."""

from __future__ import annotations

from typing import Protocol


class CacheUnavailable(RuntimeError):
    """The cache backend could not complete a bounded operation."""


class CacheStore(Protocol):
    """A byte-oriented cache with an atomic version pointer publication step."""

    def get(self, key: str) -> bytes | None: ...

    def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...

    def publish_versioned(
        self,
        pointer_key: str,
        version_key: str,
        value: bytes,
        *,
        ttl_seconds: int,
    ) -> None: ...

    def get_versioned(self, pointer_key: str) -> bytes | None: ...
