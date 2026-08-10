"""Validation and selection for versioned forced announcements."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from core.errors import ConflictError, NotFoundError, ValidationError
from db import connect, utc_now
from helpers import parse_bool
from tables import ensure_admin_tables


BEIJING_TIMEZONE = timezone(timedelta(hours=8))
_SAVE_LOCK_KEY = 0x46414E4E
_ALLOWED_TAGS = {"p", "br", "strong", "em", "u", "ul", "ol", "li", "a"}
_SUPPRESSED_TAGS = {
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "svg",
    "math",
    "template",
}


class _AnnouncementHtmlSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.suppressed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.suppressed_depth:
            if tag in _SUPPRESSED_TAGS:
                self.suppressed_depth += 1
            return
        if tag in _SUPPRESSED_TAGS:
            self.suppressed_depth = 1
            return
        if tag not in _ALLOWED_TAGS:
            return
        if tag == "a":
            href = next((value for name, value in attrs if name.lower() == "href"), None)
            safe_href = _safe_href(href)
            if safe_href is not None:
                self.parts.append(f'<a href="{escape(safe_href, quote=True)}">')
                return
        self.parts.append(f"<{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.suppressed_depth:
            return
        if tag.lower() == "br":
            self.parts.append("<br>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.suppressed_depth:
            if tag in _SUPPRESSED_TAGS:
                self.suppressed_depth -= 1
            return
        if tag in _ALLOWED_TAGS and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.suppressed_depth:
            self.parts.append(escape(data, quote=False))


def _safe_href(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value or value.startswith("//") or "\\" in value:
        return None
    if any(ord(char) < 32 for char in value):
        return None
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        return None
    return value


def sanitize_announcement_html(raw: Any) -> str:
    sanitizer = _AnnouncementHtmlSanitizer()
    sanitizer.feed(str(raw or ""))
    sanitizer.close()
    return "".join(sanitizer.parts).strip()


def _beijing_datetime(raw: Any, field_name: str) -> datetime:
    if isinstance(raw, datetime):
        value = raw
    else:
        text = str(raw or "").strip()
        if not text:
            raise ValidationError(f"{field_name} 不能为空")
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} 必须是有效日期时间") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TIMEZONE)
    return value.astimezone(BEIJING_TIMEZONE).replace(microsecond=0)


def _optional_beijing_datetime(raw: Any, field_name: str) -> datetime | None:
    if raw is None or str(raw).strip() == "":
        return None
    return _beijing_datetime(raw, field_name)


def _site_ids_for_announcement(conn: Any, announcement_id: int, scope: str) -> set[int]:
    if scope == "all_sites":
        return {
            int(row["id"])
            for row in conn.execute("SELECT id FROM managed_sites").fetchall()
        }
    return {
        int(row["site_id"])
        for row in conn.execute(
            """
            SELECT site_id
            FROM forced_announcement_sites
            WHERE announcement_id = ?
            """,
            (announcement_id,),
        ).fetchall()
    }


def _load_site_ids(conn: Any, announcement_id: int) -> list[int]:
    return [
        int(row["site_id"])
        for row in conn.execute(
            """
            SELECT site_id
            FROM forced_announcement_sites
            WHERE announcement_id = ?
            ORDER BY site_id
            """,
            (announcement_id,),
        ).fetchall()
    ]


def _admin_projection(conn: Any, row: Any) -> dict[str, Any]:
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    data["site_ids"] = _load_site_ids(conn, int(data["id"]))
    return data


def _public_projection(row: Any) -> dict[str, Any]:
    return {
        key: row[key]
        for key in ("id", "version", "title", "html", "starts_at", "ends_at")
    }


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValidationError("公告标题不能为空")

    sanitized_html = sanitize_announcement_html(payload.get("html"))
    if not sanitized_html:
        raise ValidationError("公告内容不能为空")

    scope = str(payload.get("scope") or "").strip()
    if scope not in {"all_sites", "selected_sites"}:
        raise ValidationError("公告范围必须是 all_sites 或 selected_sites")

    raw_site_ids = payload.get("site_ids") or []
    if not isinstance(raw_site_ids, list):
        raise ValidationError("site_ids 必须是数组")
    try:
        site_ids = sorted({int(site_id) for site_id in raw_site_ids})
    except (TypeError, ValueError) as exc:
        raise ValidationError("site_ids 必须只包含站点 ID") from exc
    if any(site_id <= 0 for site_id in site_ids):
        raise ValidationError("site_ids 必须只包含有效站点 ID")
    if scope == "selected_sites" and not site_ids:
        raise ValidationError("指定站点范围至少需要一个站点")
    if scope == "all_sites":
        site_ids = []

    starts_at = _beijing_datetime(payload.get("starts_at"), "starts_at")
    ends_at = _optional_beijing_datetime(payload.get("ends_at"), "ends_at")
    if ends_at is not None and ends_at <= starts_at:
        raise ValidationError("ends_at 必须晚于 starts_at")

    return {
        "title": title,
        "html": sanitized_html,
        "scope": scope,
        "site_ids": site_ids,
        "starts_at": starts_at.isoformat(timespec="seconds"),
        "ends_at": ends_at.isoformat(timespec="seconds") if ends_at else None,
        "enabled": 1 if parse_bool(payload.get("enabled"), True) else 0,
    }


def _lock_announcement_writes(conn: Any) -> None:
    if conn.engine == "postgres":
        conn.execute("SELECT pg_advisory_xact_lock(?)", (_SAVE_LOCK_KEY,))
    else:
        conn.execute("BEGIN IMMEDIATE")


def _validate_sites_exist(conn: Any, site_ids: list[int]) -> None:
    if not site_ids:
        return
    placeholders = ", ".join("?" for _ in site_ids)
    rows = conn.execute(
        f"SELECT id FROM managed_sites WHERE id IN ({placeholders})",
        tuple(site_ids),
    ).fetchall()
    existing = {int(row["id"]) for row in rows}
    missing = sorted(set(site_ids) - existing)
    if missing:
        raise ValidationError(f"站点不存在: {', '.join(str(site_id) for site_id in missing)}")


def _validate_no_overlap(
    conn: Any,
    fields: dict[str, Any],
    *,
    exclude_id: int | None = None,
) -> None:
    if not fields["enabled"]:
        return

    new_site_ids = (
        _site_ids_for_announcement(conn, 0, "all_sites")
        if fields["scope"] == "all_sites"
        else set(fields["site_ids"])
    )
    if not new_site_ids:
        return

    rows = conn.execute(
        """
        SELECT id, scope, starts_at, ends_at
        FROM forced_announcements
        WHERE enabled = 1
          AND (? IS NULL OR id <> ?)
          AND (? IS NULL OR starts_at < ?)
          AND (ends_at IS NULL OR ends_at > ?)
        ORDER BY id
        """,
        (
            exclude_id,
            exclude_id,
            fields["ends_at"],
            fields["ends_at"],
            fields["starts_at"],
        ),
    ).fetchall()
    for row in rows:
        existing_sites = _site_ids_for_announcement(
            conn, int(row["id"]), str(row["scope"])
        )
        conflicts = sorted(new_site_ids & existing_sites)
        if conflicts:
            raise ConflictError(
                "公告有效时段与站点冲突: "
                + ", ".join(str(site_id) for site_id in conflicts)
            )


def _replace_sites(conn: Any, announcement_id: int, site_ids: list[int]) -> None:
    conn.execute(
        "DELETE FROM forced_announcement_sites WHERE announcement_id = ?",
        (announcement_id,),
    )
    if site_ids:
        conn.executemany(
            """
            INSERT INTO forced_announcement_sites (announcement_id, site_id)
            VALUES (?, ?)
            """,
            [(announcement_id, site_id) for site_id in site_ids],
        )


def create_forced_announcement(
    db_path: str | Path, payload: dict[str, Any]
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    fields = _normalized_payload(payload)
    now = utc_now()
    with connect(db_path) as conn:
        _lock_announcement_writes(conn)
        _validate_sites_exist(conn, fields["site_ids"])
        _validate_no_overlap(conn, fields)
        row = conn.execute(
            """
            INSERT INTO forced_announcements (
                version, title, html, scope, starts_at, ends_at, enabled,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                uuid4().hex,
                fields["title"],
                fields["html"],
                fields["scope"],
                fields["starts_at"],
                fields["ends_at"],
                fields["enabled"],
                now,
                now,
            ),
        ).fetchone()
        announcement_id = int(row["id"])
        _replace_sites(conn, announcement_id, fields["site_ids"])
        return _admin_projection(conn, row)


def update_forced_announcement(
    db_path: str | Path,
    announcement_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _lock_announcement_writes(conn)
        existing = conn.execute(
            "SELECT * FROM forced_announcements WHERE id = ?",
            (announcement_id,),
        ).fetchone()
        if not existing:
            raise NotFoundError(f"公告 id={announcement_id} 不存在")
        merged = dict(existing)
        merged["site_ids"] = _load_site_ids(conn, announcement_id)
        merged.update(payload)
        fields = _normalized_payload(merged)
        _validate_sites_exist(conn, fields["site_ids"])
        _validate_no_overlap(conn, fields, exclude_id=announcement_id)
        row = conn.execute(
            """
            UPDATE forced_announcements
            SET version = ?, title = ?, html = ?, scope = ?, starts_at = ?,
                ends_at = ?, enabled = ?, updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (
                uuid4().hex,
                fields["title"],
                fields["html"],
                fields["scope"],
                fields["starts_at"],
                fields["ends_at"],
                fields["enabled"],
                utc_now(),
                announcement_id,
            ),
        ).fetchone()
        _replace_sites(conn, announcement_id, fields["site_ids"])
        return _admin_projection(conn, row)


def get_effective_forced_announcement(
    db_path: str | Path,
    *,
    site_id: int,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    ensure_admin_tables(db_path)
    effective_at = _beijing_datetime(
        now or datetime.now(timezone.utc), "now"
    ).isoformat(timespec="seconds")
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT announcement.*
            FROM forced_announcements AS announcement
            WHERE announcement.enabled = 1
              AND announcement.starts_at <= ?
              AND (announcement.ends_at IS NULL OR announcement.ends_at > ?)
              AND (
                    announcement.scope = 'all_sites'
                    OR EXISTS (
                        SELECT 1
                        FROM forced_announcement_sites AS selected
                        WHERE selected.announcement_id = announcement.id
                          AND selected.site_id = ?
                    )
              )
            ORDER BY announcement.starts_at DESC, announcement.id DESC
            LIMIT 1
            """,
            (effective_at, effective_at, site_id),
        ).fetchone()
        return _public_projection(row) if row else None

