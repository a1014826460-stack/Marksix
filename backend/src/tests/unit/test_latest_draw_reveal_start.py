"""开奖揭示锚点（reveal_start / lottery_draws.opened_at）契约测试。

锚点语义：reveal_start = 该期号码首次对外可用的时刻（opened_at，开盘瞬间
写一次、之后不漂移）。共享开奖面板与预测遮罩门都以它为全局时间线起点：
刷新不从头重放、不同浏览器同一时刻进度一致；历史行没有 opened_at 时
退回 draw_time，行为与改造前一致。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from database.bootstrap import ensure_admin_tables
from crawler.scheduler import CrawlerScheduler
from db import connect
from public.api import get_public_latest_draw


def _setup(tmp_path, name: str) -> str:
    db_path = str(tmp_path / f"{name}.sqlite3")
    ensure_admin_tables(db_path)
    return db_path


def _insert_draw(
    db_path: str,
    *,
    term: int,
    is_opened: int = 1,
    opened_at: str | None = None,
    draw_time: str = "2026-09-01 22:32:00",
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status,
                is_opened, next_term, opened_at, created_at, updated_at
            ) VALUES (3, 2026, ?, '01,02,03,04,05,06,07', ?, 1, ?, 272, ?, ?, ?)
            """,
            (term, draw_time, is_opened, opened_at, "2026-09-01T14:00:00", "2026-09-01T14:00:00"),
        )


def _read_opened_at(db_path: str, term: int = 271) -> str:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT opened_at FROM lottery_draws WHERE lottery_type_id = 3 AND term = ?",
            (term,),
        ).fetchone()
    return str(row["opened_at"] or "") if row else ""


def test_reveal_start_uses_opened_at_when_present(tmp_path):
    db_path = _setup(tmp_path, "reveal-opened-at")
    _insert_draw(db_path, term=271, opened_at="2026-09-01 22:32:05")

    payload = get_public_latest_draw(db_path, 3)

    assert payload["current_issue"] == "2026271"
    assert payload["draw_time"] == "2026-09-01 22:32:00"
    assert payload["reveal_start"] == "2026-09-01 22:32:05"


def test_reveal_start_falls_back_to_draw_time_for_legacy_rows(tmp_path):
    db_path = _setup(tmp_path, "reveal-fallback")
    _insert_draw(db_path, term=271, opened_at=None)

    payload = get_public_latest_draw(db_path, 3)

    assert payload["reveal_start"] == "2026-09-01 22:32:00"


def test_reveal_start_empty_when_no_opened_draw(tmp_path):
    db_path = _setup(tmp_path, "reveal-empty")

    payload = get_public_latest_draw(db_path, 3)

    assert payload == {
        "current_issue": "",
        "draw_time": "",
        "reveal_start": "",
        "result_balls": [],
        "special_ball": None,
    }


def test_precise_open_writes_stable_opened_at(tmp_path):
    """台湾精准开盘写 opened_at（北京时间），重复执行不得漂移。"""
    db_path = _setup(tmp_path, "reveal-precise-open")
    _insert_draw(db_path, term=271, is_opened=0, opened_at=None)
    scheduler = CrawlerScheduler(db_path)

    assert scheduler._open_taiwan_draws_and_update_next_time() == 1
    first = _read_opened_at(db_path)
    assert first
    datetime.strptime(first, "%Y-%m-%d %H:%M:%S")

    # 已开盘行不会被再次触碰；即便重跑开盘任务 opened_at 保持首写值
    assert scheduler._open_taiwan_draws_and_update_next_time() == 0
    assert _read_opened_at(db_path) == first


def test_precise_open_anchor_is_close_to_real_publish_time_not_draw_time(tmp_path):
    """锚点是真实开盘时刻：人为把 draw_time 配错（提前一天）也不影响锚点。"""
    db_path = _setup(tmp_path, "reveal-anchor-real-time")
    _insert_draw(db_path, term=271, is_opened=0, opened_at=None, draw_time="2026-09-01 22:32:00")
    before = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)

    assert CrawlerScheduler(db_path)._open_taiwan_draws_and_update_next_time() == 1

    opened_at = datetime.strptime(_read_opened_at(db_path), "%Y-%m-%d %H:%M:%S")
    after = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
    # opened_at 秒级截断，可比 before 晚约 1 秒内
    assert before - timedelta(seconds=1) <= opened_at <= after + timedelta(seconds=5)
