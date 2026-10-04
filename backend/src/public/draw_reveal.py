"""开奖号码的服务端分片揭示。

背景
----
``/api/public/latest-draw`` 过去在 ``is_opened=1`` 的那一刻把 6 个平码 + 特码一次性
下发；站点面板上「每 25 秒多一个球」只是**前端定时器动画**，任何直接请求接口、
查看 DevTools Network 或抓包的人都能立刻拿到全部号码。

这里把节奏搬到服务端：号码从 ``reveal_start``（开盘瞬间写定的 ``opened_at``，
缺失时退回 ``draw_time``）起，按每 25 秒一个的节拍逐个对外可用。

节奏约定
--------
- 第 1 球：``reveal_start`` 当刻即可见。
- 第 N 球：``reveal_start + (N-1) * 25s``。
- 第 7 球（特码）：``reveal_start + 150s``；此后 ``is_complete=True``。
- ``reveal_start`` 之前（例如补偿写入的未来时间行）：``revealed_count=0``，不下发号码。

边界
----
- 所有彩种共用同一条节奏：可见数量 = `min(源站已入库球数, floor(已过秒/25)+1)`。
  香港彩源站逐个补全号码，因此它的可见数量天然受「已入库球数」封顶，但同样不会
  在开盘瞬间把多个号码一次性放出去。
- 没有 ``reveal_start`` / ``draw_time`` 的旧载荷原样返回（兼容旧部署、旧快照与
  无开奖数据的空载荷），不新增任何字段。
- 本模块只做纯计算，不碰数据库、不写缓存；缓存里始终保留**完整**载荷，分片只发生在
  对外响应的边界上，因此读取方任何时刻看到的号码数都只由「服务器时间 - 锚点」决定。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from core.time_utils import BEIJING_TZ, beijing_now
from domains.lottery.draw_time import parse_draw_datetime

#: 一期开奖号码总数（6 个平码 + 1 个特码）。
DRAW_BALL_COUNT = 7
#: 相邻两个号码的开放间隔（秒）。
REVEAL_INTERVAL_SECONDS = 25


def reveal_anchor(payload: Mapping[str, Any]) -> datetime | None:
    """揭示锚点：优先 ``reveal_start``（号码首次对外可用时刻），退回 ``draw_time``。"""
    for key in ("reveal_start", "draw_time"):
        anchor = parse_draw_datetime(str(payload.get(key) or "").strip())
        if anchor is not None:
            return anchor
    return None


def public_balls(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """载荷里的已公开号码（6 平码 + 特码），按顺序最多 7 个。"""
    balls = [
        ball
        for ball in (payload.get("result_balls") or [])
        if isinstance(ball, dict)
    ]
    special_ball = payload.get("special_ball")
    if isinstance(special_ball, dict):
        balls = [*balls, special_ball]
    return [ball for ball in balls if str(ball.get("value") or "").strip()][:DRAW_BALL_COUNT]


def reveal_count(
    *,
    anchor: datetime,
    available: int,
    now: datetime | None = None,
    interval_seconds: int = REVEAL_INTERVAL_SECONDS,
) -> int:
    """此刻允许对外可见的号码个数（0..7）。

    ``available`` 是源站已入库的号码数：揭示只能**延后**，绝不能超过它。
    """
    if available <= 0:
        return 0
    capped_available = min(int(available), DRAW_BALL_COUNT)

    current = now or beijing_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=BEIJING_TZ)
    elapsed_seconds = (current - anchor).total_seconds()
    if elapsed_seconds < 0:
        return 0
    time_count = int(elapsed_seconds // max(1, int(interval_seconds))) + 1
    return max(0, min(capped_available, time_count))


def _beijing_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")


def apply_reveal_slice(
    payload: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    interval_seconds: int = REVEAL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    """按服务器时间裁掉尚未开放的号码，并补充揭示进度字段。

    返回新字典；入参不会被修改。没有锚点的旧载荷原样返回（浅拷贝）。
    """
    result: dict[str, Any] = dict(payload or {})
    if not result:
        return result

    anchor = reveal_anchor(result)
    if anchor is None:
        return result

    available = public_balls(result)
    count = reveal_count(
        anchor=anchor,
        available=len(available),
        now=now,
        interval_seconds=interval_seconds,
    )
    revealed = available[:count]
    is_complete = count >= DRAW_BALL_COUNT

    result["result_balls"] = revealed[: DRAW_BALL_COUNT - 1]
    result["special_ball"] = revealed[DRAW_BALL_COUNT - 1] if is_complete else None
    result["revealed_count"] = count
    result["total_balls"] = DRAW_BALL_COUNT
    result["reveal_interval_seconds"] = int(interval_seconds)
    result["is_complete"] = is_complete
    result["next_reveal_at"] = (
        ""
        if is_complete
        else _beijing_text(anchor + timedelta(seconds=int(interval_seconds) * count))
    )
    return result
