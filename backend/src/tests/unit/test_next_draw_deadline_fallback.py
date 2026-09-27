"""港澳"下次开奖"倒计时回归测试（2026-09-26 空 next_time 导致面板 --:--:--）。

故障链：
1. 新期（香港 104 / 澳门 269）由**备用源**（api.csjid.com / macaumarksix.com）开盘，
   这些源的响应里没有 ``next_time`` 字段 → ``lottery_draws.next_time`` 为空；
2. ``sync_lottery_type_next_time_from_latest_draw`` 直接把空值写进
   ``lottery_types.next_time`` 与 ``system_config.lottery.*_next_time``；
3. ``/api/next-draw-deadline`` 返回 ``next_time: null`` → 面板倒计时 ``--:--:--``。

修复：永不空值覆盖；确实缺失时按开奖排期推导（香港周二/四/六、澳门每日）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from db import connect
from helpers import (
    compute_next_draw_time_ms,
    get_effective_next_draw_payload,
    resolve_next_time_ms,
    sync_lottery_type_next_time_from_latest_draw,
)
from public.api import get_public_next_draw_deadline

HK = 1
MACAU = 2
TAIWAN = 3

_BEIJING = timezone.utc


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """北京时间 → UTC（测试内统一用北京钟点表达，便于对照开奖时间）。"""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc) - __import__(
        "datetime"
    ).timedelta(hours=8)


def _ms(value: datetime) -> str:
    return str(int(value.timestamp() * 1000))


def _beijing_ms(year: int, month: int, day: int, hour: int, minute: int) -> str:
    from datetime import timedelta

    return _ms(datetime(year, month, day, hour, minute, tzinfo=timezone.utc) - timedelta(hours=8))


def _setup(tmp_path, name: str):
    db_path = tmp_path / f"{name}.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type_id INTEGER, year INTEGER, term INTEGER,
                numbers TEXT, draw_time TEXT, status INTEGER,
                is_opened INTEGER DEFAULT 0, next_term INTEGER, next_time TEXT,
                created_at TEXT, updated_at TEXT,
                UNIQUE(lottery_type_id, year, term)
            )
            """
        )
        conn.execute(
            "CREATE TABLE lottery_types (id INTEGER PRIMARY KEY, name TEXT, collect_url TEXT, "
            "draw_time TEXT, next_time TEXT, updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE system_config (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, "
            "value_text TEXT, value_type TEXT, description TEXT, is_secret INTEGER DEFAULT 0, "
            "created_at TEXT, updated_at TEXT)"
        )
        for lt_id, name_cn, clock in ((HK, "香港彩", "21:30"), (MACAU, "澳门彩", "21:32"),
                                      (TAIWAN, "台湾彩", "22:32")):
            conn.execute(
                "INSERT INTO lottery_types (id, name, collect_url, draw_time, next_time, updated_at) "
                "VALUES (?, ?, '', ?, '', '2026-09-27T00:00:00+00:00')",
                (lt_id, name_cn, clock),
            )
        # 与生产一致的计划钟点配置（runtime_config 里澳门的登记默认是 21:30，
        # 生产库为 21:32；测试按生产值写入，避免依赖登记默认值）
        for key, value in (
            ("draw.hk_default_draw_time", "21:30"),
            ("draw.macau_default_draw_time", "21:32"),
            ("draw.taiwan_default_draw_time", "22:32"),
        ):
            conn.execute(
                "INSERT INTO system_config (key, value_text, value_type, description, is_secret, "
                "created_at, updated_at) VALUES (?, ?, 'string', '', 0, ?, ?)",
                (key, value, "2026-09-27T00:00:00+00:00", "2026-09-27T00:00:00+00:00"),
            )
    return db_path


def _insert_opened_draw(db_path, lt_id: int, year: int, term: int, draw_time: str,
                        next_time: str = "") -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO lottery_draws (lottery_type_id, year, term, numbers, draw_time, status, "
            "is_opened, next_term, next_time, created_at, updated_at) "
            "VALUES (?, ?, ?, '01,02,03,04,05,06,07', ?, 1, 1, ?, ?, ?, ?)",
            (lt_id, year, term, draw_time, term + 1, next_time,
             "2026-09-26T13:34:31+00:00", "2026-09-26T13:34:31+00:00"),
        )


# ── 1. 排期推导 ──────────────────────────────────────────────────────


def test_macau_fallback_is_daily_2132(tmp_path):
    db_path = _setup(tmp_path, "countdown-macau-fallback")
    with connect(db_path) as conn:
        # 2026-09-27（周日）12:00 北京 → 当天 21:32
        value = compute_next_draw_time_ms(conn, MACAU, now_utc=_utc(2026, 9, 27, 12, 0))
        assert value == _beijing_ms(2026, 9, 27, 21, 32)
        # 当天 22:00 北京（已过钟点）→ 次日 21:32
        value2 = compute_next_draw_time_ms(conn, MACAU, now_utc=_utc(2026, 9, 27, 22, 0))
        assert value2 == _beijing_ms(2026, 9, 28, 21, 32)


def test_hk_fallback_uses_tue_thu_sat(tmp_path):
    db_path = _setup(tmp_path, "countdown-hk-fallback")
    with connect(db_path) as conn:
        # 2026-09-26 是周六；周六 22:00 北京（开奖后）→ 下一个周二 09-29 21:30
        sat_after = compute_next_draw_time_ms(conn, HK, now_utc=_utc(2026, 9, 26, 22, 0))
        assert sat_after == _beijing_ms(2026, 9, 29, 21, 30)
        # 2026-09-27（周日）→ 仍是周二 09-29（跳过周日/周一）
        sunday = compute_next_draw_time_ms(conn, HK, now_utc=_utc(2026, 9, 27, 12, 0))
        assert sunday == _beijing_ms(2026, 9, 29, 21, 30)
        # 2026-09-29（周二）20:00 → 当天 21:30
        tue_before = compute_next_draw_time_ms(conn, HK, now_utc=_utc(2026, 9, 29, 20, 0))
        assert tue_before == _beijing_ms(2026, 9, 29, 21, 30)
        # 2026-09-29（周二）22:00 → 周四 10-01
        tue_after = compute_next_draw_time_ms(conn, HK, now_utc=_utc(2026, 9, 29, 22, 0))
        assert tue_after == _beijing_ms(2026, 10, 1, 21, 30)


def test_taiwan_fallback_is_never_derived(tmp_path):
    """台湾彩必须保持原有推导路径（未来期行），不得套用港澳排期。"""
    db_path = _setup(tmp_path, "countdown-taiwan")
    with connect(db_path) as conn:
        assert compute_next_draw_time_ms(conn, TAIWAN, now_utc=_utc(2026, 9, 27, 12, 0)) == ""


# ── 2. 解析优先级：源站 → 仍在未来的已存值 → 排期推导 ────────────────


def test_resolve_prefers_source_then_future_stored_then_schedule(tmp_path):
    db_path = _setup(tmp_path, "countdown-resolve")
    now = _utc(2026, 9, 27, 12, 0)
    future = _beijing_ms(2026, 9, 28, 21, 32)
    past = _beijing_ms(2026, 9, 26, 21, 32)
    with connect(db_path) as conn:
        assert resolve_next_time_ms(conn, MACAU, source_next_time=future, now_utc=now) == future
        assert resolve_next_time_ms(conn, MACAU, stored_next_time=future, now_utc=now) == future
        # 已存值已在过去 → 推导（不得原样返回过去时间）
        assert resolve_next_time_ms(conn, MACAU, stored_next_time=past, now_utc=now) == \
            _beijing_ms(2026, 9, 27, 21, 32)
        # 两者都为空 → 推导
        assert resolve_next_time_ms(conn, MACAU, now_utc=now) == _beijing_ms(2026, 9, 27, 21, 32)


# ── 3. 同步：绝不空值覆盖 ────────────────────────────────────────────


def test_sync_never_wipes_next_time_with_empty_source(tmp_path):
    """新期由备用源开盘（next_time 为空）时，排期不得被清空，而要推导成未来时间。"""
    db_path = _setup(tmp_path, "countdown-sync-no-wipe")
    _insert_opened_draw(db_path, MACAU, 2026, 269, "2026-09-26 21:32:32", next_time="")
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO system_config (key, value_text, value_type, description, is_secret, "
            "created_at, updated_at) VALUES ('lottery.macau_next_time', ?, 'string', '', 0, ?, ?)",
            (_beijing_ms(2026, 9, 26, 21, 32), "2026-09-27T00:00:00+00:00", "2026-09-27T00:00:00+00:00"),
        )

    with connect(db_path) as conn:
        resolved = sync_lottery_type_next_time_from_latest_draw(
            conn, MACAU, updated_at="2026-09-27T04:20:00+00:00", source="test"
        )
        lt_value = conn.execute(
            "SELECT next_time FROM lottery_types WHERE id = ?", (MACAU,)
        ).fetchone()["next_time"]
        cfg_value = conn.execute(
            "SELECT value_text FROM system_config WHERE key = 'lottery.macau_next_time'"
        ).fetchone()["value_text"]

    assert resolved, "排期不得为空"
    assert lt_value == resolved, "lottery_types.next_time 必须落库为解析后的未来时间"
    assert cfg_value == resolved, "system_config 必须与 lottery_types 一致"
    # 推导值必须是未来时间（相对真实当前时刻）
    assert int(resolved) > int(datetime.now(timezone.utc).timestamp() * 1000) - 86_400_000


def test_sync_keeps_source_value_when_present(tmp_path):
    db_path = _setup(tmp_path, "countdown-sync-source")
    source_next = _beijing_ms(2026, 9, 29, 21, 30)
    _insert_opened_draw(db_path, HK, 2026, 104, "2026-09-26 21:35:23", next_time=source_next)
    with connect(db_path) as conn:
        resolved = sync_lottery_type_next_time_from_latest_draw(
            conn, HK, updated_at="2026-09-27T04:20:00+00:00", source="test"
        )
    assert resolved == source_next


# ── 4. 公开接口：倒计时永远拿得到未来时间 ────────────────────────────


def test_public_next_draw_deadline_falls_back_for_hk_macau(tmp_path):
    db_path = _setup(tmp_path, "countdown-api-fallback")
    _insert_opened_draw(db_path, MACAU, 2026, 269, "2026-09-26 21:32:32", next_time="")
    _insert_opened_draw(db_path, HK, 2026, 104, "2026-09-26 21:35:23", next_time="")

    macau = get_public_next_draw_deadline(db_path, MACAU)
    hk = get_public_next_draw_deadline(db_path, HK)

    assert macau["current_issue"] == "2026269"
    assert macau["next_issue"] == "2026270"
    assert macau["next_time"] and int(macau["next_time"]) > 0
    assert hk["next_time"] and int(hk["next_time"]) > 0
    # 香港推导值必须落在周二/四/六
    from datetime import datetime as _dt

    hk_beijing = _dt.fromtimestamp(int(hk["next_time"]) / 1000, tz=timezone.utc)
    hk_local = hk_beijing.astimezone(timezone.utc)
    assert hk_local.hour == 13 and hk_local.minute == 30  # 21:30 北京 = 13:30 UTC


def test_public_next_draw_deadline_keeps_taiwan_payload(tmp_path):
    """台湾彩接口必须与载荷完全一致（不参与港澳兜底推导）。"""
    db_path = _setup(tmp_path, "countdown-api-taiwan")
    taiwan_next = _beijing_ms(2026, 9, 27, 22, 32)
    _insert_opened_draw(db_path, TAIWAN, 2026, 269, "2026-09-27 22:32:00", next_time=taiwan_next)

    payload = get_public_next_draw_deadline(db_path, TAIWAN)
    with connect(db_path) as conn:
        expected = get_effective_next_draw_payload(conn, TAIWAN)

    assert payload["next_time"] == expected["next_time"]
    assert payload["current_issue"] == expected["current_issue"]
    assert payload["next_issue"] == expected["next_issue"]


def test_effective_payload_unchanged_shape(tmp_path):
    """get_effective_next_draw_payload 的返回形状不变（港澳仍以行内 next_time 为准）。"""
    db_path = _setup(tmp_path, "countdown-payload-shape")
    _insert_opened_draw(db_path, MACAU, 2026, 269, "2026-09-26 21:32:32", next_time="")
    with connect(db_path) as conn:
        payload = get_effective_next_draw_payload(conn, MACAU)
    assert set(payload) == {"current_issue", "next_issue", "next_draw_time", "next_time"}
    assert payload["current_issue"] == "2026269"
    assert payload["next_issue"] == "2026270"
