"""版本化缓存的 **envelope 稳定发布时间戳**。

背景（2026-10-05 定位）
--------------------
`publish_versioned` 的版本键是**内容寻址**的（`sha256(载荷)[:16]`），两套缓存实现
（`MemoryCacheStore` / `RedisCacheStore` 的 Lua 脚本）都要求「同一版本键的字节不可变」，
不一致就拒绝发布：
- 内存：抛 `CacheUnavailable("version key is immutable ...")`；
- Redis：脚本返回 0 → 同样抛 `CacheUnavailable`。

但 envelope 里带 `published_at`。若每次都用「当前时钟」，同一载荷在时钟刻度改变后重复发布
就会写出**不同字节**，于是：
1. `test_prediction_snapshots` 出现时钟粒度偶发（Windows `time()` 约 15.6ms 粒度）；
2. 线上「指针已过期、版本键还在」的重建窗口（版本 TTL 比指针多 1 秒）里，重新发布会直接被拒，
   指针反而挂不回去。

`cache/public_snapshots.py` 早就用「outbox 重试时由调用方传入同一个 `published_at`」来保证
逐字节可复现；本模块把同一条约定补到**没有调用方时间戳**的路径上：版本键已存在就复用它的
首次发布时间，重复发布因此是真正的幂等。
"""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Mapping

from cache.contracts import CacheStore, CacheUnavailable


def is_finite_number(value: Any) -> bool:
    """与快照模块的既有校验一致（bool 不算数字，inf/nan 不算有限值）。"""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def stable_published_at(
    cache: CacheStore,
    version_key: str,
    clock: Callable[[], float],
) -> float:
    """版本键已存在时复用其 `published_at`，否则取当前时钟。

    只读一次版本键（发布本来就不在请求热路径上）；缓存不可用/内容损坏时退回当前时钟，
    由 `publish_versioned` 自己的不可变校验决定是否拒绝。
    """
    try:
        raw = cache.get(version_key)
    except CacheUnavailable:
        return clock()
    if not raw:
        return clock()
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return clock()
    if isinstance(envelope, Mapping):
        value = envelope.get("published_at")
        if is_finite_number(value):
            return float(value)
    return clock()
