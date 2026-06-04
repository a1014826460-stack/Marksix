"""Managed site service layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import NotFoundError, ValidationError
from db import connect, utc_now
from helpers import parse_bool
from tables import ensure_admin_tables

from .repository import (
    delete_site_by_id,
    find_site_by_id,
    get_site_web_id,
    insert_site,
    list_all_sites,
    update_site,
)

DEFAULT_SITE_BLUEPRINT_NAME = "default"


def public_site(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    return data


def list_sites(db_path: str | Path) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        return [public_site(row) for row in list_all_sites(conn)]


def get_site(db_path: str | Path, site_id: int, include_secret: bool = False) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = find_site_by_id(conn, site_id)
        if not row:
            raise NotFoundError(f"site_id={site_id} 不存在")
        data = dict(row) if include_secret else public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def save_site(db_path: str | Path, payload: dict[str, Any], site_id: int | None = None) -> dict[str, Any]:
    from domains.prediction.generation_service import (
        initialize_site_prediction_modules_from_blueprint,
        sync_site_prediction_modules,
    )

    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "name": str(payload.get("name") or "").strip(),
        "domain": str(payload.get("domain") or "").strip(),
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "enabled": 1 if parse_bool(payload.get("enabled"), True) else 0,
        "web_id": int(payload.get("web_id") or 0),
        "announcement": str(payload.get("announcement") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
        "blueprint_name": str(payload.get("blueprint_name") or "").strip() or DEFAULT_SITE_BLUEPRINT_NAME,
    }
    if not fields["name"]:
        raise ValidationError("站点名称不能为空")
    if fields["web_id"] <= 0:
        raise ValidationError("web_id 不能为空")

    with connect(db_path) as conn:
        if site_id is None:
            existing_web = conn.execute(
                "SELECT id FROM managed_sites WHERE web_id = ? LIMIT 1",
                (fields["web_id"],),
            ).fetchone()
            if existing_web:
                raise ValidationError(f"web_id={fields['web_id']} 已被其他站点占用")
            row = insert_site(conn, fields, now)
            new_site_id = int(row["id"])
            template_site_id = int(payload.get("template_site_id") or 4)
            template_exists = conn.execute(
                "SELECT id FROM managed_sites WHERE id = ?",
                (template_site_id,),
            ).fetchone()
            if not template_exists and template_site_id != 1:
                template_site_id = 1
            template_modules = conn.execute(
                """
                SELECT mechanism_key, mode_id, status, sort_order
                FROM site_prediction_modules
                WHERE site_id = ?
                ORDER BY sort_order, id
                """,
                (template_site_id,),
            ).fetchall()
            if template_modules:
                for tm in template_modules:
                    conn.execute(
                        """
                        INSERT INTO site_prediction_modules (
                            site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(site_id, mechanism_key) DO NOTHING
                        """,
                        (
                            new_site_id,
                            tm["mechanism_key"],
                            tm["mode_id"],
                            tm["status"],
                            tm["sort_order"],
                            now,
                            now,
                        ),
                    )
            new_site = find_site_by_id(conn, new_site_id) or dict(row)
            initialize_site_prediction_modules_from_blueprint(conn, new_site)
            sync_site_prediction_modules(conn, site_id=new_site_id)
            conn.commit()
            return public_site(row)

        existing = conn.execute(
            "SELECT web_id FROM managed_sites WHERE id = ?", (site_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError(f"site_id={site_id} 不存在")
        fields["web_id"] = int(fields["web_id"] or existing["web_id"] or site_id)
        row = update_site(conn, site_id, fields, now)
        if not row:
            raise NotFoundError(f"site_id={site_id} 不存在")
        return public_site(row)


def delete_site(db_path: str | Path, site_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        if not delete_site_by_id(conn, site_id):
            raise NotFoundError(f"site_id={site_id} 不存在")


def resolve_web_id(db_path: str | Path, site_id: int) -> int:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        web_id = get_site_web_id(conn, site_id)
        if web_id is None:
            raise NotFoundError(f"site_id={site_id} 不存在或缺少 web_id 配置")
        return web_id
