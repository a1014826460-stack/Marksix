"""开奖号码的服务端分片揭示。

背景
----
``/api/public/latest-draw`` 过去在 ``is_opened=1`` 的那一刻把 6 个平码 + 特码一次性
下发；站点面板上「每 25 秒多一个球」只是**前端定时器动画**，任何直接请求接口、
查看 DevTools Network 或抓包的人都能立刻拿到全部号码。

这里把节奏搬到服务端：台湾号码从 ``max(reveal_start, draw_time)`` 起，
按每 25 秒一个的节拍逐个对外可用。``reveal_start`` 来自开盘写定的
``opened_at``；只有缺失或空值才退回 ``draw_time``，非空坏锚点关闭揭示。
响应中的 ``reveal_start`` 是实际使用的锚点，完整缓存保留原载荷。

节奏约定
--------
- 第 1 球：``reveal_start`` 当刻即可见。
- 第 N 球：``reveal_start + (N-1) * 25s``。
- 第 7 球（特码）：``reveal_start + 150s``；此后 ``is_complete=True``。
- ``reveal_start`` 之前（例如补偿写入的未来时间行）：``revealed_count=0``，不下发号码。

边界
----
- **只有台湾彩（lottery_type=3）走节拍**：它的 7 个号码是提前写入库的未来真值，不按节拍放行
  就等于开盘瞬间把全部号码交给任何请求接口的人。港彩源站逐个补全、澳门彩源站一次给全，
  两者本来就是公开数据，拿到几个就返回几个，不再人为拖 150 秒。
- 节拍彩种：可见数量 = `min(连续有效源站球数, floor(已过秒/25)+1)`；
  只接受前六个普通球的连续前缀，特码固定第七槽，缺普通球不能前移特码。
- 非节拍彩种：可见数量 = `源站已入库球数`（`is_complete` 仍按 7 个判断，未齐时 `next_reveal_at`
  为空串，前端按 5 秒轮询补齐）。
- 台湾彩有期号或号码但缺少有效锚点时不开放任何号码；无开奖数据的空载荷与
  港澳彩缺锚点的旧载荷保持原样。
- 本模块只做纯计算，不碰数据库、不写缓存；缓存里始终保留**完整**载荷，分片只发生在
  对外响应的边界上，因此读取方任何时刻看到的号码数都只由「服务器时间 - 锚点」决定。
"""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Mapping

from core.time_utils import BEIJING_TZ, beijing_now
from domains.lottery.draw_time import parse_draw_datetime

#: 一期开奖号码总数（6 个平码 + 1 个特码）。
DRAW_BALL_COUNT = 7
#: 相邻两个号码的开放间隔（秒）。
REVEAL_INTERVAL_SECONDS = 25

#: 需要服务端控节奏的彩种：只有台湾彩。
#: 台湾彩的号码是**提前入库的未来真值**，必须由服务端逐个放行；
#: 港澳彩源站本来就公开号码，拿到即全开（2026-10-05 用户口径）。
PACED_REVEAL_LOTTERY_TYPES = frozenset({3})


def is_paced_lottery_type(lottery_type_id: Any) -> bool:
    """该彩种是否走「25 秒一球」的服务端节拍。

    无法识别的彩种按**节拍**处理（fail-safe）：漏传彩种只会多一段节拍，
    绝不会把本该逐球开放的号码一次性放出去。
    """
    if lottery_type_id in (None, ""):
        return True
    try:
        return int(lottery_type_id) in PACED_REVEAL_LOTTERY_TYPES
    except (TypeError, ValueError):
        return True


def _parse_reveal_datetime(value: Any) -> datetime | None:
    """台湾揭示只接受完整、规范且日历有效的北京时间；与公开面板同门。"""
    text = str(value or "").strip()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}", text):
        return None
    anchor = parse_draw_datetime(text.replace("T", " "))
    return anchor if anchor is not None and anchor.timestamp() > 0 else None


def reveal_anchor(payload: Mapping[str, Any], *, paced: bool = True) -> datetime | None:
    """台湾必须有有效排期；非空坏 preferred 关闭揭示，空值才回退排期。"""
    if not paced:
        for key in ("reveal_start", "draw_time"):
            anchor = parse_draw_datetime(str(payload.get(key) or "").strip())
            if anchor is not None:
                return anchor
        return None

    preferred_text = str(payload.get("reveal_start") or "").strip()
    planned = _parse_reveal_datetime(payload.get("draw_time"))
    if planned is None:
        return None
    if not preferred_text:
        return planned
    preferred = _parse_reveal_datetime(preferred_text)
    if preferred is None:
        return None
    return max(preferred, planned)


def public_balls(payload: Mapping[str, Any], *, paced: bool = True) -> list[dict[str, Any]]:
    """台湾只取连续平码前缀，特码固定第七槽；港澳保留既有源站口径。"""
    if paced:
        regular = payload.get("result_balls")
        if not isinstance(regular, list):
            return []
        prefix: list[dict[str, Any]] = []
        for ball in regular[: DRAW_BALL_COUNT - 1]:
            if not isinstance(ball, dict) or not str(ball.get("value") or "").strip():
                return prefix
            prefix.append(ball)
        special = payload.get("special_ball")
        if len(prefix) == DRAW_BALL_COUNT - 1 and isinstance(special, dict) and str(special.get("value") or "").strip():
            prefix.append(special)
        return prefix

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
    # The public Taiwan clock is fixed; compatibility arguments cannot accelerate it.
    time_count = int(elapsed_seconds // REVEAL_INTERVAL_SECONDS) + 1
    return max(0, min(capped_available, time_count))


def is_full_draw_released(
    draw_row: Mapping[str, Any],
    *,
    lottery_type_id: Any = None,
    now: datetime | None = None,
) -> bool:
    """Whether an authoritative row may expose its complete result publicly.

    Taiwan history and derived results must wait for the same seventh slot as
    the live response, even when the configurable history delay is zero.
    """
    if str(draw_row.get("is_opened") or "").strip() not in {"1", "True"}:
        return False
    effective_type = lottery_type_id if lottery_type_id not in (None, "") else draw_row.get("lottery_type_id")
    if not is_paced_lottery_type(effective_type):
        return True

    planned = _parse_reveal_datetime(draw_row.get("draw_time"))
    if planned is None:
        return False
    anchor_payload = {
        "draw_time": draw_row.get("draw_time"),
        "reveal_start": draw_row.get("opened_at") if "opened_at" in draw_row else draw_row.get("reveal_start"),
    }
    anchor = reveal_anchor(anchor_payload)
    if anchor is None:
        return False

    if "numbers" in draw_row:
        codes = str(draw_row.get("numbers") or "").split(",")
        if len(codes) != DRAW_BALL_COUNT or any(
            not code.strip().isdigit() or not 1 <= int(code.strip()) <= 49 for code in codes
        ):
            return False
        available = DRAW_BALL_COUNT
    else:
        available = len(public_balls(draw_row))
    return reveal_count(anchor=anchor, available=available, now=now) == DRAW_BALL_COUNT


def _beijing_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")


def apply_reveal_slice(
    payload: Mapping[str, Any] | None,
    *,
    lottery_type_id: Any = None,
    now: datetime | None = None,
    interval_seconds: int = REVEAL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    """按彩种口径裁掉尚未开放的号码，并补充揭示进度字段。

    - 节拍彩种（台湾彩）：从锚点起每 ``interval_seconds`` 放行一个号码。
    - 非节拍彩种（港澳彩）：已入库多少就下发多少，`next_reveal_at` 为空串。

    返回新字典；入参不会被修改。台湾彩缺锚点时关闭揭示；空载荷保持原样。
    """
    result: dict[str, Any] = dict(payload or {})
    if not result:
        return result

    paced = is_paced_lottery_type(lottery_type_id)
    if paced:
        interval_seconds = REVEAL_INTERVAL_SECONDS
    anchor = reveal_anchor(result, paced=paced)
    available = public_balls(result, paced=paced)
    if anchor is None and (
        not paced or (not result.get("current_issue") and not result.get("result_balls") and not result.get("special_ball"))
    ):
        return result

    current = now or beijing_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=BEIJING_TZ)
    issue = str(result.get("current_issue") or "").strip()
    valid_issue = bool(re.fullmatch(r"[0-9]{5,7}", issue)) and int(issue[4:] or 0) > 0
    if anchor is None or (paced and not valid_issue):
        count = 0
    elif paced:
        count = reveal_count(
            anchor=anchor,
            available=len(available),
            now=current,
            interval_seconds=interval_seconds,
        )
    else:
        count = min(len(available), DRAW_BALL_COUNT)

    revealed = available[:count]
    is_complete = count >= DRAW_BALL_COUNT

    result["result_balls"] = revealed[: DRAW_BALL_COUNT - 1]
    result["special_ball"] = revealed[DRAW_BALL_COUNT - 1] if is_complete else None
    result["revealed_count"] = count
    result["total_balls"] = DRAW_BALL_COUNT
    result["reveal_interval_seconds"] = int(interval_seconds)
    result["is_complete"] = is_complete
    result["server_now"] = int(current.timestamp())
    result["server_now_ms"] = int(current.timestamp() * 1000)
    if paced and anchor is not None:
        # 所有读取方使用响应的实际锚点；完整缓存里的 raw opened_at 不受影响。
        result["reveal_start"] = _beijing_text(anchor)
    result["next_reveal_at"] = (
        ""
        if anchor is None or (paced and not valid_issue) or is_complete or not paced
        else _beijing_text(anchor + timedelta(seconds=int(interval_seconds) * count))
    )
    return result
