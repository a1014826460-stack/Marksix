"""Versioned public snapshots for prediction payloads.

预测资料（`/api/kaijiang/*`、`/api/vendor/homepage-modules`、站点资料聚合）每次请求都要
重新聚合，实测单次回源 2.7～6.3 秒。这里复用开奖快照的"内容寻址版本 + 指针"机制，把
**已经被公开 HTTP 端点返回过的 JSON** 缓存下来，命中时只需一次 KV 读。

安全边界与 `cache.public_snapshots` 一致：
- 只存公开响应本身，不存数据库行；
- 载荷递归拒绝内部标记（例如未来期受控生成用的 ``_simulation_should_hit``）；
- 版本键内容不可变（哈希寻址），重复发布幂等，指针 TTL 决定最长陈旧时间；
- 任何缓存异常都必须由调用方回落数据库，本模块只抛 ``CacheUnavailable``/``ValueError``。
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import math
import os
import re
from time import perf_counter, time
from typing import Any, Callable, Mapping

from cache.contracts import CacheUnavailable, CacheStore


logger = logging.getLogger("cache.prediction_snapshots")

_ENABLED_ENV = "PREDICTION_SNAPSHOT_ENABLED"
_ENABLED_CONFIG_KEY = "prediction.snapshot.enabled"
_ENABLED_CACHE_TTL_SECONDS = 5.0
_DISABLED_VALUES = frozenset({"0", "false", "no", "off", ""})
_enabled_cache: tuple[float, bool] | None = None


_KEY_VERSION = "v1"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_FORBIDDEN_KEYS = frozenset(
    {
        # 未来期受控生成的内部标记，任何公开载荷都不应出现；命中即拒绝发布。
        "_simulation_should_hit",
        "simulation_should_hit",
        "should_hit",
        "truth_source",
        "future_truth",
    }
)
_MAX_PAYLOAD_BYTES = 2 * 1024 * 1024

KIND_LEGACY = "legacy"
KIND_LEGACY_ROWS = "legacy-rows"
KIND_SITE = "site"
KIND_HOMEPAGE = "homepage"
SUPPORTED_KINDS = frozenset({KIND_LEGACY, KIND_LEGACY_ROWS, KIND_SITE, KIND_HOMEPAGE})

# 代际计数：读路径把 "彩种代际.站点代际" 并入指针键，事件里把对应计数 +1 即可让
# 该彩种（或该站+该彩种）的全部快照立刻失效，无需按前缀 SCAN（CacheStore 契约没有 SCAN）。
GENERATION_TTL_SECONDS = 7 * 24 * 3600
_GENERATION_PREFIX = f"public:prediction-snapshot:{_KEY_VERSION}:generation"


@dataclass(frozen=True)
class SnapshotKeys:
    """Immutable version entry plus the mutable pointer that selects it."""

    pointer_key: str
    version_key: str


def snapshot_keys(
    kind: str,
    site_ref: str,
    lottery_type_id: int,
    selector: str,
    version: str,
    generation: str = "0.0",
) -> SnapshotKeys:
    """Return stable keys for one prediction snapshot entry."""
    kind_value = _validate_token(kind, "kind")
    if kind_value not in SUPPORTED_KINDS:
        raise ValueError(f"unsupported prediction snapshot kind: {kind}")
    site_token = _validate_token(site_ref, "site_ref")
    lottery_type = _validate_lottery_type(lottery_type_id)
    selector_token = _validate_token(selector, "selector")
    version_token = _validate_token(version, "version")
    generation_token = _validate_token(generation, "generation")
    base = (
        f"public:prediction-snapshot:{_KEY_VERSION}:{kind_value}:{site_token}"
        f":lottery:{lottery_type}:{selector_token}:g{generation_token}"
    )
    return SnapshotKeys(
        pointer_key=f"{base}:pointer",
        version_key=f"{base}:version:{version_token}",
    )


def generation_key_for_lottery_type(lottery_type_id: int) -> str:
    """Generation counter shared by every site for one lottery type."""
    lottery_type = _validate_lottery_type(lottery_type_id)
    return f"{_GENERATION_PREFIX}:lottery:{lottery_type}"


def generation_keys(site_ref: str, lottery_type_id: int) -> tuple[str, str]:
    """Return (per lottery type, per site+type) generation counter keys."""
    site_token = _validate_token(site_ref, "site_ref")
    return (
        generation_key_for_lottery_type(lottery_type_id),
        f"{_GENERATION_PREFIX}:{site_token}:lottery:{_validate_lottery_type(lottery_type_id)}",
    )


def _parse_generation(raw: bytes | None) -> int:
    if raw is None:
        return 0
    try:
        value = int(raw.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError):
        return 0
    return value if value >= 0 else 0


def snapshot_version(payload: Mapping[str, Any]) -> str:
    """Content-addressed version: identical payloads are idempotent to publish."""
    encoded = _encode_payload(payload)
    return hashlib.sha256(encoded).hexdigest()[:16]


def payload_is_cacheable(kind: str, payload: Any) -> bool:
    """Reject empty results so authorization/生成 changes are never cached."""
    if not isinstance(payload, Mapping):
        return False
    if kind == KIND_LEGACY:
        data = payload.get("data")
        return isinstance(data, (list, dict)) and len(data) > 0
    if kind == KIND_LEGACY_ROWS:
        rows = payload.get("rows")
        return isinstance(rows, list) and len(rows) > 0
    if "data" not in payload:
        return True
    return bool(payload.get("data"))


def invalidate_lottery_type(cache: CacheStore | None, lottery_type_id: int) -> None:
    """Best-effort generation bump for callers that only hold a raw cache store.

    管理台改写开奖号码、预测生成完成等场景调用它，让该彩种的预测资料快照立即失效；
    缓存不可用只记录告警，绝不影响主流程。
    """
    if cache is None:
        return
    try:
        PublicPredictionSnapshots(cache, ttl_seconds=300).bump_lottery_type(lottery_type_id)
    except Exception as exc:  # noqa: BLE001 - 缓存问题不能影响业务写入
        logger.warning(
            "prediction snapshot invalidation failed lottery_type_id=%s error=%s",
            lottery_type_id,
            type(exc).__name__,
        )


def invalidate_all_lottery_types(
    cache: CacheStore | None,
    lottery_type_ids: tuple[int, ...] = (1, 2, 3),
) -> None:
    """Best-effort generation bump for every lottery type.

    管理台的全量改写入口（开奖号码增删改、payload 行增删改、``/api/admin/normalize``、
    ``/api/admin/text-mappings``）无法预知被影响的行属于哪个彩种，而这些入口调用频率极低，
    因此统一对三个彩种做粗粒度失效；缓存不可用只记录告警，绝不影响业务写入。
    """
    for lottery_type_id in lottery_type_ids:
        invalidate_lottery_type(cache, lottery_type_id)


def invalidate_site(cache: CacheStore | None, site_ref: str, lottery_type_id: int) -> None:
    """Best-effort generation bump for one site (后台改该站资料)。"""
    if cache is None:
        return
    try:
        PublicPredictionSnapshots(cache, ttl_seconds=300).bump_site(site_ref, lottery_type_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "prediction snapshot site invalidation failed site=%s lottery_type_id=%s error=%s",
            site_ref,
            lottery_type_id,
            type(exc).__name__,
        )


def read_through(
    snapshots: Any | None,
    *,
    kind: str,
    site_ref: str,
    lottery_type_id: int,
    selector: str,
    builder: Callable[[], dict[str, Any]],
    db_path: str | None = None,
) -> dict[str, Any]:
    """Snapshot-first read with unconditional fallback to ``builder``.

    ``enabled`` stays a runtime decision (环境变量 + ``system_config`` 覆盖，5 秒进程内缓存)，
    因此线上可以随时关停而不需要改代码或重启。
    """
    enabled = snapshot_enabled(db_path)
    if not enabled or snapshots is None:
        return builder()

    try:
        cached = snapshots.get(kind, site_ref, lottery_type_id, selector)
    except (CacheUnavailable, ValueError):
        cached = None
    if cached is not None:
        logger.debug(
            "prediction snapshot hit kind=%s site=%s lottery_type_id=%s selector=%s",
            kind,
            site_ref,
            lottery_type_id,
            selector,
        )
        return cached

    started = perf_counter()
    payload = builder()
    build_ms = int((perf_counter() - started) * 1000)
    try:
        published = snapshots.publish(kind, site_ref, lottery_type_id, selector, payload)
    except (CacheUnavailable, ValueError) as exc:
        published = False
        logger.warning(
            "prediction snapshot publish failed kind=%s site=%s lottery_type_id=%s selector=%s error=%s",
            kind,
            site_ref,
            lottery_type_id,
            selector,
            type(exc).__name__,
        )
    if published:
        logger.info(
            "prediction snapshot miss kind=%s site=%s lottery_type_id=%s selector=%s build_ms=%s",
            kind,
            site_ref,
            lottery_type_id,
            selector,
            build_ms,
        )
    return payload


def snapshot_enabled(db_path: str | None = None) -> bool:
    """Return whether prediction snapshots may be read/written in this process."""
    global _enabled_cache
    now = time()
    if _enabled_cache is not None and now - _enabled_cache[0] <= _ENABLED_CACHE_TTL_SECONDS:
        return _enabled_cache[1]

    enabled = _env_enabled()
    if enabled and db_path:
        override = _config_override(db_path)
        if override is not None:
            enabled = override
    _enabled_cache = (now, enabled)
    return enabled


def reset_enabled_cache() -> None:
    """Test helper: forget the cached enable-flag decision."""
    global _enabled_cache
    _enabled_cache = None


def _env_enabled() -> bool:
    return os.getenv(_ENABLED_ENV, "1").strip().lower() not in _DISABLED_VALUES


def _config_override(db_path: str) -> bool | None:
    try:
        from runtime_config import get_config

        value = get_config(db_path, _ENABLED_CONFIG_KEY, None)
    except Exception as exc:  # noqa: BLE001 - 配置读取失败不能影响响应
        logger.debug("prediction snapshot config lookup failed error=%s", type(exc).__name__)
        return None
    if value is None:
        return None
    return str(value).strip().lower() not in _DISABLED_VALUES


class PublicPredictionSnapshots:
    """Publish and read validated prediction JSON through immutable versions."""

    def __init__(
        self,
        cache: CacheStore,
        *,
        ttl_seconds: int = 300,
        clock: Callable[[], float] = time,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def publish(
        self,
        kind: str,
        site_ref: str,
        lottery_type_id: int,
        selector: str,
        payload: Mapping[str, Any],
    ) -> bool:
        """Publish one payload; returns False when the payload is refused."""
        if not payload_is_cacheable(kind, payload):
            return False
        public_payload = _validate_payload(kind, payload, lottery_type_id)
        version = snapshot_version(public_payload)
        generation = self._read_generation(site_ref, lottery_type_id)
        keys = snapshot_keys(kind, site_ref, lottery_type_id, selector, version, generation)
        envelope = {
            "schema_version": 1,
            "kind": kind,
            "site_ref": site_ref,
            "lottery_type_id": int(lottery_type_id),
            "selector": selector,
            "published_at": self._clock(),
            "payload": public_payload,
        }
        encoded = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._cache.publish_versioned(
            keys.pointer_key,
            keys.version_key,
            encoded,
            ttl_seconds=self._ttl_seconds,
        )
        return True

    def get(
        self,
        kind: str,
        site_ref: str,
        lottery_type_id: int,
        selector: str,
    ) -> dict[str, Any] | None:
        """Return the published payload, or None for miss/invalid entry."""
        generation = self._read_generation(site_ref, lottery_type_id)
        probe = snapshot_keys(kind, site_ref, lottery_type_id, selector, "0", generation)
        pointer = self._cache.get(probe.pointer_key)
        if pointer is None:
            return None
        try:
            version_key = pointer.decode("utf-8")
        except UnicodeDecodeError:
            return None
        prefix = probe.version_key.rsplit(":", 1)[0] + ":"
        if not version_key.startswith(prefix):
            return None
        version = version_key.removeprefix(prefix)
        try:
            _validate_token(version, "version")
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
            or envelope.get("kind") != kind
            or envelope.get("site_ref") != site_ref
            or envelope.get("lottery_type_id") != int(lottery_type_id)
            or envelope.get("selector") != selector
            or not _is_finite_number(envelope.get("published_at"))
        ):
            return None
        try:
            return _validate_payload(kind, envelope.get("payload"), lottery_type_id)
        except ValueError:
            return None

    def invalidate(
        self,
        kind: str,
        site_ref: str,
        lottery_type_id: int,
        selector: str,
    ) -> None:
        """Drop the pointer so the next request rebuilds (versions expire by TTL)."""
        generation = self._read_generation(site_ref, lottery_type_id)
        probe = snapshot_keys(kind, site_ref, lottery_type_id, selector, "0", generation)
        self._cache.delete(probe.pointer_key)

    def bump_lottery_type(self, lottery_type_id: int) -> None:
        """Invalidate every site's snapshots for one lottery type (开奖/生成事件)."""
        self._bump(generation_key_for_lottery_type(lottery_type_id))

    def bump_site(self, site_ref: str, lottery_type_id: int) -> None:
        """Invalidate one site's snapshots for one lottery type (后台改资料)."""
        _type_key, site_key = generation_keys(site_ref, lottery_type_id)
        self._bump(site_key)

    def _bump(self, key: str) -> int:
        current = _parse_generation(self._cache.get(key))
        updated = current + 1
        self._cache.set(key, str(updated).encode("ascii"), ttl_seconds=GENERATION_TTL_SECONDS)
        return updated

    def _read_generation(self, site_ref: str, lottery_type_id: int) -> str:
        type_key, site_key = generation_keys(site_ref, lottery_type_id)
        type_generation = _parse_generation(self._cache.get(type_key))
        site_generation = _parse_generation(self._cache.get(site_key))
        return f"{type_generation}.{site_generation}"


def _encode_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _validate_payload(kind: str, payload: Any, lottery_type_id: int) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("prediction snapshot payload must be an object")
    encoded = _encode_payload(payload)
    if len(encoded) > _MAX_PAYLOAD_BYTES:
        raise ValueError("prediction snapshot payload is too large")
    _reject_forbidden_keys(payload, path="")
    # 公开载荷的真实形状：旧站 {"data":[...]}；vendor 首页 {"ok","site","data"}；
    # 站点资料聚合 {"site","draw","modules"}（没有 data 键）。
    if kind == KIND_LEGACY and "data" not in payload:
        raise ValueError("legacy prediction snapshot payload must contain data")
    if kind == KIND_LEGACY_ROWS:
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ValueError("legacy rows snapshot payload must contain a rows list")
    if kind == KIND_HOMEPAGE and "data" not in payload:
        raise ValueError("homepage prediction snapshot payload must contain data")
    if kind == KIND_SITE and not {"data", "modules", "site"} & set(payload):
        raise ValueError("site prediction snapshot payload has no known top-level key")
    try:
        json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        raise ValueError("prediction snapshot payload is not serialisable") from exc
    if _validate_lottery_type(lottery_type_id) != int(lottery_type_id):  # pragma: no cover
        raise ValueError("lottery_type_id must match the snapshot key")
    return dict(payload)


def _reject_forbidden_keys(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_KEYS:
                raise ValueError(f"prediction snapshot field is not allowed: {key_text}")
            _reject_forbidden_keys(item, path=f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_forbidden_keys(item, path=f"{path}[{index}]")


def _validate_token(value: str, label: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or hyphen")
    return value


def _validate_lottery_type(lottery_type_id: int) -> int:
    if isinstance(lottery_type_id, bool) or not isinstance(lottery_type_id, int) or lottery_type_id <= 0:
        raise ValueError("lottery_type_id must be a positive integer")
    return lottery_type_id


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)
