"""Lottery domain service layer.

This module owns lottery read behavior. Some write paths still delegate to
``admin.crud`` until they can be moved safely with focused tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db import connect, utc_now
from helpers import (
    draw_time_to_unix_ms,
    get_effective_next_draw_payload,
    parse_bool,
    sync_lottery_type_next_time_from_latest_draw,
)
from tables import ensure_admin_tables


def _load_taiwan_placeholder_previous_draw_ids(
    conn: Any,
    *,
    year: int,
    term: int,
) -> list[int]:
    """Find previous terminal draws whose next_time still points to their own draw_time."""
    rows = conn.execute(
        """
        SELECT d.id, d.draw_time, d.next_time
        FROM lottery_draws d
        WHERE d.lottery_type_id = 3
          AND (d.year < ? OR (d.year = ? AND d.term < ?))
          AND NOT EXISTS (
              SELECT 1
              FROM lottery_draws newer
              WHERE newer.lottery_type_id = d.lottery_type_id
                AND (newer.year > d.year OR (newer.year = d.year AND newer.term > d.term))
                AND (newer.year < ? OR (newer.year = ? AND newer.term < ?))
          )
        """,
        (year, year, term, year, year, term),
    ).fetchall()

    candidate_ids: list[int] = []
    for row in rows:
        draw_time = str(row["draw_time"] or "").strip()
        next_time = str(row["next_time"] or "").strip()
        if not draw_time or not next_time:
            continue
        try:
            if next_time == draw_time_to_unix_ms(draw_time):
                candidate_ids.append(int(row["id"]))
        except ValueError:
            continue
    return candidate_ids


def _update_taiwan_previous_draw_next_time(
    conn: Any,
    *,
    draw_ids: list[int],
    next_draw_time: str,
    updated_at: str,
) -> None:
    """Backfill previous Taiwan draws so their next_time points to the new draw."""
    if not draw_ids or not next_draw_time:
        return
    replacement_next_time = draw_time_to_unix_ms(next_draw_time)
    conn.executemany(
        """
        UPDATE lottery_draws
        SET next_time = ?, updated_at = ?
        WHERE id = ?
        """,
        [(replacement_next_time, updated_at, draw_id) for draw_id in draw_ids],
    )


def _sync_lottery_type_next_time(conn: Any, lottery_type_id: int, updated_at: str) -> None:
    """Keep lottery_types.next_time aligned with the effective next draw payload."""
    sync_lottery_type_next_time_from_latest_draw(
        conn,
        lottery_type_id,
        updated_at=updated_at,
        source="domains.lottery.service",
    )


def list_lottery_types(db_path: str | Path) -> list[dict[str, Any]]:
    """List all lottery types with effective next_time synchronized."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM lottery_types ORDER BY status DESC, id").fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item: dict[str, Any] = dict(row) | {"status": bool(row["status"])}
            stored_next_time = str(item.get("next_time") or "")
            payload = get_effective_next_draw_payload(conn, int(item["id"]))
            effective_next_time = str(payload.get("next_time") or "")
            item["next_time"] = effective_next_time
            if effective_next_time != stored_next_time:
                conn.execute(
                    "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = ?",
                    (effective_next_time, utc_now(), item["id"]),
                )
            result.append(item)
        return result


def save_lottery_type(
    db_path: str | Path,
    payload: dict[str, Any],
    lottery_id: int | None = None,
) -> dict[str, Any]:
    """Create or update a lottery type."""
    ensure_admin_tables(db_path)
    now = utc_now()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("彩种名称不能为空")

    draw_time = str(payload.get("draw_time") or "").strip()
    collect_url = str(payload.get("collect_url") or "").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0

    effective_lottery_id = lottery_id
    with connect(db_path) as conn:
        if effective_lottery_id is None:
            row = conn.execute(
                """
                INSERT INTO lottery_types (name, draw_time, collect_url, next_time, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (name, draw_time, collect_url, "", status, now, now),
            ).fetchone()
            effective_lottery_id = int(row["id"])
        else:
            row = conn.execute(
                """
                UPDATE lottery_types
                SET name = ?, draw_time = ?, collect_url = ?, status = ?, updated_at = ?
                WHERE id = ?
                RETURNING *
                """,
                (name, draw_time, collect_url, status, now, effective_lottery_id),
            ).fetchone()
            if not row:
                raise KeyError(f"lottery_id={effective_lottery_id} 不存在")

        sync_lottery_type_next_time_from_latest_draw(
            conn,
            int(effective_lottery_id),
            updated_at=now,
            source="domains.lottery.service",
        )

        final_row = conn.execute(
            "SELECT * FROM lottery_types WHERE id = ?",
            (effective_lottery_id,),
        ).fetchone()
        return dict(final_row) | {"status": bool(final_row["status"])}


def delete_lottery_type(db_path: str | Path, lottery_id: int) -> None:
    """Delete a lottery type."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM lottery_types WHERE id = ? RETURNING id",
            (lottery_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"lottery_id={lottery_id} 不存在")


def get_latest_draw(db_path: str | Path, lottery_type_id: int) -> dict[str, Any] | None:
    """Return the latest opened draw for a lottery type."""
    from domains.lottery.repository import find_latest_draw

    with connect(db_path) as conn:
        return find_latest_draw(conn, lottery_type_id)


def list_draws(
    db_path: str | Path,
    limit: int = 200,
    offset: int = 0,
    lottery_type_id: int | None = None,
) -> dict[str, Any]:
    """List draw records using the admin API payload shape."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conditions = []
        params: list[Any] = []

        if lottery_type_id is not None:
            conditions.append("d.lottery_type_id = ?")
            params.append(int(lottery_type_id))

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        total_row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM lottery_draws d {where_clause}",
            params,
        ).fetchone()
        total = int(total_row["cnt"]) if total_row else 0

        rows = conn.execute(
            f"""
            SELECT d.*, l.name AS lottery_name
            FROM lottery_draws d
            JOIN lottery_types l ON l.id = d.lottery_type_id
            {where_clause}
            ORDER BY d.year DESC, d.term DESC, d.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()

        draws = [
            dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}
            for row in rows
        ]

        page = (offset // limit) + 1 if limit > 0 else 1
        return {
            "draws": draws,
            "total": total,
            "page": page,
            "page_size": limit,
            "total_pages": max(1, -(-total // limit)) if limit > 0 else 1,
        }


def save_draw(
    db_path: str | Path,
    payload: dict[str, Any],
    draw_id: int | None = None,
) -> dict[str, Any]:
    """Create or update a draw record."""
    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "year": int(payload.get("year") or datetime.now().year),
        "term": int(payload.get("term") or 1),
        "numbers": str(payload.get("numbers") or "").strip(),
        "draw_time": str(payload.get("draw_time") or "").strip(),
        "next_time": str(payload.get("next_time") or "").strip(),
        "status": 1 if parse_bool(payload.get("status"), True) else 0,
        "is_opened": 1 if parse_bool(payload.get("is_opened"), False) else 0,
        "next_term": int(payload.get("next_term") or (int(payload.get("term") or 1) + 1)),
    }
    if fields["lottery_type_id"] != 3:
        raise ValueError("当前仅允许管理台台湾彩在线记录")

    if fields["lottery_type_id"] == 3 and not fields["draw_time"]:
        from calendar import timegm

        with connect(db_path) as conn:
            lt_row = conn.execute("SELECT draw_time FROM lottery_types WHERE id = 3").fetchone()
            lt_time = str(lt_row["draw_time"]).strip() if lt_row and lt_row["draw_time"] else "22:30:00"
            lt_parts = lt_time.split(":")
            lt_h = int(lt_parts[0]) if len(lt_parts) >= 1 else 22
            lt_m = int(lt_parts[1]) if len(lt_parts) >= 2 else 30
            lt_s = int(lt_parts[2]) if len(lt_parts) >= 3 else 0

            prev = conn.execute(
                """
                SELECT draw_time FROM lottery_draws
                WHERE lottery_type_id = 3
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if prev and prev.get("draw_time"):
                try:
                    prev_dt = datetime.strptime(str(prev["draw_time"]).strip(), "%Y-%m-%d %H:%M:%S")
                    next_dt = (prev_dt + timedelta(days=1)).replace(
                        hour=lt_h, minute=lt_m, second=lt_s, microsecond=0
                    )
                    fields["draw_time"] = next_dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, OverflowError):
                    pass
            if not fields["draw_time"]:
                beijing_now = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
                fields["draw_time"] = beijing_now.replace(
                    hour=lt_h, minute=lt_m, second=lt_s, microsecond=0
                ).strftime("%Y-%m-%d %H:%M:%S")

        if fields["draw_time"]:
            try:
                draw_dt = datetime.strptime(fields["draw_time"].strip(), "%Y-%m-%d %H:%M:%S")
                try:
                    next_dt = draw_dt + timedelta(days=1)
                    utc_dt = next_dt - timedelta(hours=8)
                    fields["next_time"] = str(int(timegm(utc_dt.timetuple()) * 1000))
                except (ValueError, OverflowError):
                    utc_dt = draw_dt - timedelta(hours=8)
                    fields["next_time"] = str(int(timegm(utc_dt.timetuple()) * 1000))
            except (ValueError, OverflowError):
                pass

    if fields["draw_time"] and not fields["is_opened"]:
        try:
            draw_dt = datetime.strptime(fields["draw_time"].strip(), "%Y-%m-%d %H:%M:%S")
            beijing_now = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
            if draw_dt <= beijing_now:
                fields["is_opened"] = 1
        except ValueError:
            pass

    if fields["draw_time"] and fields["is_opened"]:
        try:
            draw_dt = datetime.strptime(fields["draw_time"].strip(), "%Y-%m-%d %H:%M:%S")
            beijing_now = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
            if draw_dt > beijing_now:
                raise ValueError("当前期开奖时间尚未到达，不能提前设置为已开奖")
        except ValueError as exc:
            if str(exc) == "当前期开奖时间尚未到达，不能提前设置为已开奖":
                raise

    if not fields["numbers"]:
        raise ValueError("开奖号码不能为空")

    num_list = [n.strip() for n in fields["numbers"].split(",") if n.strip()]
    if len(num_list) != 7:
        raise ValueError(f"开奖号码必须恰好 7 个，当前 {len(num_list)} 个")
    for n in num_list:
        if not n.isdigit() or int(n) < 1 or int(n) > 49:
            raise ValueError(f"无效号码: {n}，每个号码必须为 01-49")

    with connect(db_path) as conn:
        duplicate = (
            conn.execute(
                """
                SELECT id FROM lottery_draws
                WHERE lottery_type_id = ? AND year = ? AND term = ?
                LIMIT 1
                """,
                (
                    fields["lottery_type_id"],
                    fields["year"],
                    fields["term"],
                ),
            ).fetchone()
            if draw_id is None
            else conn.execute(
                """
                SELECT id FROM lottery_draws
                WHERE lottery_type_id = ? AND year = ? AND term = ? AND id <> ?
                LIMIT 1
                """,
                (
                    fields["lottery_type_id"],
                    fields["year"],
                    fields["term"],
                    draw_id,
                ),
            ).fetchone()
        )
        if duplicate:
            raise ValueError(
                f"该彩种的 {fields['year']} 年第 {fields['term']} 期已存在，请检查期数或改为编辑现有记录"
            )

        duplicate_draw_date = (
            conn.execute(
                """
                SELECT id FROM lottery_draws
                WHERE lottery_type_id = ? AND substr(draw_time, 1, 10) = substr(?, 1, 10)
                LIMIT 1
                """,
                (
                    fields["lottery_type_id"],
                    fields["draw_time"],
                ),
            ).fetchone()
            if draw_id is None
            else conn.execute(
                """
                SELECT id FROM lottery_draws
                WHERE lottery_type_id = ? AND substr(draw_time, 1, 10) = substr(?, 1, 10) AND id <> ?
                LIMIT 1
                """,
                (
                    fields["lottery_type_id"],
                    fields["draw_time"],
                    draw_id,
                ),
            ).fetchone()
        )
        if duplicate_draw_date:
            raise ValueError(f"开奖日期 {fields['draw_time'][:10]} 已存在，请检查后再提交")

        if draw_id is None:
            previous_placeholder_ids = _load_taiwan_placeholder_previous_draw_ids(
                conn,
                year=fields["year"],
                term=fields["term"],
            )
            row = conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, next_time, status,
                    is_opened, next_term, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (*fields.values(), now, now),
            ).fetchone()
            _update_taiwan_previous_draw_next_time(
                conn,
                draw_ids=previous_placeholder_ids,
                next_draw_time=fields["draw_time"],
                updated_at=now,
            )
            _sync_lottery_type_next_time(conn, fields["lottery_type_id"], now)
        else:
            row = conn.execute(
                """
                UPDATE lottery_draws
                SET lottery_type_id = ?, year = ?, term = ?, numbers = ?, draw_time = ?,
                    next_time = ?, status = ?, is_opened = ?, next_term = ?, updated_at = ?
                WHERE id = ?
                RETURNING *
                """,
                (*fields.values(), now, draw_id),
            ).fetchone()
            if not row:
                raise KeyError(f"draw_id={draw_id} 不存在")
            _sync_lottery_type_next_time(conn, fields["lottery_type_id"], now)

        return dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}


def delete_draw(db_path: str | Path, draw_id: int) -> None:
    """Delete a draw record."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM lottery_draws WHERE id = ?", (draw_id,))
        if cur.rowcount == 0:
            raise KeyError(f"draw_id={draw_id} 不存在")
