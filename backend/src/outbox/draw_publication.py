"""Atomic public-publication event creation for authoritative lottery draws."""

from __future__ import annotations

from typing import Any, Mapping

from outbox.repository import enqueue_event

_PUBLIC_DRAW_FIELDS = (
    "lottery_type_id", "year", "term", "numbers", "draw_time", "next_time",
    "status", "is_opened", "next_term",
)

# 香港彩源站按号码逐个补全（先 1 个、再 2 个 ……），因此采用“轮序发布”：
# 只要已有合法号码，就按源站给出的顺序发布当前前缀，每多一个号码刷新一次。
# 澳门彩与台湾彩必须一次性给出完整 7 个号码才允许开盘与发布。
HK_PROGRESSIVE_LOTTERY_TYPE_IDS = frozenset({1})
DRAW_BALL_COUNT = 7
_MIN_BALL = 1
_MAX_BALL = 49


def normalize_draw_numbers(numbers: Any) -> list[str]:
    """把开奖号码文本拆成有序号码列表，保留源站给出的原始顺序。"""
    text = str(numbers or "").replace("，", ",").replace("、", ",")
    return [token.strip() for token in text.split(",") if token.strip()]


def _is_valid_ball(token: str) -> bool:
    return token.isdigit() and _MIN_BALL <= int(token) <= _MAX_BALL


def draw_numbers_are_publishable(lottery_type_id: Any, numbers: Any) -> bool:
    """该期号码是否允许开盘并对公众发布。

    - 香港彩（``HK_PROGRESSIVE_LOTTERY_TYPE_IDS``）：允许 1..7 个合法且不重复的
      号码，按源站顺序轮序发布。
    - 其他彩种：必须刚好 7 个合法且不重复的号码，否则只入库不开盘、不发布。
    """
    tokens = normalize_draw_numbers(numbers)
    if not tokens or len(tokens) > DRAW_BALL_COUNT:
        return False
    if not all(_is_valid_ball(token) for token in tokens):
        return False
    if len({int(token) for token in tokens}) != len(tokens):
        return False
    try:
        lottery_type = int(lottery_type_id)
    except (TypeError, ValueError):
        return False
    if lottery_type in HK_PROGRESSIVE_LOTTERY_TYPE_IDS:
        return True
    return len(tokens) == DRAW_BALL_COUNT


def draw_is_publishable(draw: Mapping[str, Any]) -> bool:
    """按一条开奖记录判断它是否可以被公众看到。"""
    return bool(int(draw.get("is_opened") or 0)) and draw_numbers_are_publishable(
        draw.get("lottery_type_id"), draw.get("numbers")
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
    # 号码不完整（香港彩为“轮序发布”，只要有号码即通过）不得进入公开通道。
    if not draw_numbers_are_publishable(current.get("lottery_type_id"), current.get("numbers")):
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
