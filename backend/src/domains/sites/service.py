"""站点领域业务逻辑层（Service）。

职责：业务校验、数据转换、流程编排。
数据库访问委托给 domains/sites/repository.py。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import NotFoundError, ValidationError
from db import connect, utc_now
from helpers import parse_bool
from runtime_config import get_config
from tables import ensure_admin_tables

from .repository import (
    delete_site_by_id,
    find_site_by_id,
    get_site_web_id,
    insert_site,
    list_all_sites,
    update_site,
)


def public_site(row: Any) -> dict[str, Any]:
    """将数据库中的站点行转换为对外安全的字典（隐藏完整 token）。"""
    data = dict(row)
    token = data.pop("token", "") or ""
    data["enabled"] = bool(data["enabled"])
    data["token_present"] = bool(token)
    data["token_preview"] = f"{token[:8]}..." if token else ""
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
    """创建或更新托管站点。

    当 site_id 为 None 时创建新站点，并从模板站点（site 1）复制预测模块配置；
    否则更新已有站点。
    """
    from domains.prediction.generation_service import sync_site_prediction_modules

    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "name": str(payload.get("name") or "").strip(),
        "domain": str(payload.get("domain") or "").strip(),
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "enabled": 1 if parse_bool(payload.get("enabled"), True) else 0,
        "start_web_id": int(payload.get("start_web_id") or 1),
        "end_web_id": int(payload.get("end_web_id") or payload.get("start_web_id") or 10),
        "manage_url_template": str(
            payload.get("manage_url_template")
            or get_config(db_path, "site.manage_url_template", "")
        ).strip(),
        "modes_data_url": str(
            payload.get("modes_data_url")
            or get_config(db_path, "site.modes_data_url", "")
        ).strip(),
        "request_limit": int(payload.get("request_limit") or get_config(db_path, "site.request_limit", 250)),
        "request_delay": float(payload.get("request_delay") or get_config(db_path, "site.request_delay", 0.5)),
        "announcement": str(payload.get("announcement") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }
    token = payload.get("token")
    if site_id is None:
        fields["web_id"] = fields["start_web_id"]

    if not fields["name"]:
        raise ValidationError("站点名称不能为空")
    if fields["start_web_id"] > fields["end_web_id"]:
        raise ValidationError("start_web_id 不能大于 end_web_id")
    if "{web_id}" not in fields["manage_url_template"] and "{id}" not in fields["manage_url_template"]:
        raise ValidationError("manage_url_template 必须包含 {web_id} 或 {id}")

    if site_id is not None:
        fields["token"] = ""  # 更新时在 conn 内处理 token 回退

    with connect(db_path) as conn:
        if site_id is None:
            fields["token"] = str(token or "")
            row = insert_site(conn, fields, now)
            new_site_id = int(row["id"])

            template_modules = conn.execute(
                """
                SELECT mechanism_key, mode_id, status, sort_order
                FROM site_prediction_modules
                WHERE site_id = 1
                ORDER BY sort_order, id
                """
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
                            new_site_id, tm["mechanism_key"], tm["mode_id"],
                            tm["status"], tm["sort_order"], now, now,
                        ),
                    )
                sync_site_prediction_modules(conn, site_id=new_site_id)
                conn.commit()
            return public_site(row)

        # 更新已有站点
        existing = conn.execute(
            "SELECT token FROM managed_sites WHERE id = ?", (site_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError(f"site_id={site_id} 不存在")
        resolved_token = str(token) if token not in (None, "") else str(existing["token"] or "")
        fields["token"] = resolved_token
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
