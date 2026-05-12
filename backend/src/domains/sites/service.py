"""站点领域业务逻辑层（Service）。

站点查询、创建/更新、启用/停用、web_id 解析。
已从 admin/crud.py 迁移实际实现，不再委托。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import NotFoundError, ValidationError
from db import connect, utc_now
from helpers import parse_bool
from runtime_config import get_config
from tables import ensure_admin_tables


def public_site(row: Any) -> dict[str, Any]:
    """将数据库中的站点行转换为对外安全的字典（隐藏完整 token）。"""
    data = dict(row)
    token = data.pop("token", "") or ""
    data["enabled"] = bool(data["enabled"])
    data["token_present"] = bool(token)
    data["token_preview"] = f"{token[:8]}..." if token else ""
    return data


def list_sites(db_path: str | Path) -> list[dict[str, Any]]:
    """获取所有托管站点列表，关联彩种名称，按启用状态降序、ID 升序排列。"""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            ORDER BY s.enabled DESC, s.id ASC
            """
        ).fetchall()
        return [public_site(row) for row in rows]


def get_site(db_path: str | Path, site_id: int, include_secret: bool = False) -> dict[str, Any]:
    """根据 ID 获取单个托管站点的详细信息。

    Args:
        db_path: 数据库路径
        site_id: 站点 ID
        include_secret: 是否返回包含完整 token 的原始数据

    Raises:
        NotFoundError: 站点不存在
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            WHERE s.id = ?
            """,
            (site_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(f"site_id={site_id} 不存在")
        data = dict(row) if include_secret else public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def save_site(db_path: str | Path, payload: dict[str, Any], site_id: int | None = None) -> dict[str, Any]:
    """创建或更新托管站点。

    当 site_id 为 None 时创建新站点，并从模板站点（site 1）复制预测模块配置；
    否则更新已有站点。

    Raises:
        ValidationError: 名称空、start > end、URL 模板缺少占位符
        NotFoundError: 更新时站点不存在
    """
    from admin.prediction import sync_site_prediction_modules

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
    # web_id: 新建时使用 start_web_id，更新时保持现有值
    if site_id is None:
        fields["web_id"] = fields["start_web_id"]

    if not fields["name"]:
        raise ValidationError("站点名称不能为空")
    if fields["start_web_id"] > fields["end_web_id"]:
        raise ValidationError("start_web_id 不能大于 end_web_id")
    if "{web_id}" not in fields["manage_url_template"] and "{id}" not in fields["manage_url_template"]:
        raise ValidationError("manage_url_template 必须包含 {web_id} 或 {id}")

    with connect(db_path) as conn:
        if site_id is None:
            row = conn.execute(
                """
                INSERT INTO managed_sites (
                    web_id, name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
                    manage_url_template, modes_data_url, token, request_limit,
                    request_delay, announcement, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    fields["web_id"],
                    fields["name"],
                    fields["domain"],
                    fields["lottery_type_id"],
                    fields["enabled"],
                    fields["start_web_id"],
                    fields["end_web_id"],
                    fields["manage_url_template"],
                    fields["modes_data_url"],
                    str(token or ""),
                    fields["request_limit"],
                    fields["request_delay"],
                    fields["announcement"],
                    fields["notes"],
                    now,
                    now,
                ),
            ).fetchone()
            new_site = public_site(row)
            new_site_id = int(new_site["id"])

            # 从模板站点（site 1）复制预测模块配置到新站点
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
            return new_site

        # 更新已有站点
        existing = conn.execute(
            "SELECT token FROM managed_sites WHERE id = ?", (site_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError(f"site_id={site_id} 不存在")
        resolved_token = str(token) if token not in (None, "") else str(existing["token"] or "")
        row = conn.execute(
            """
            UPDATE managed_sites
            SET name = ?, domain = ?, lottery_type_id = ?, enabled = ?,
                start_web_id = ?, end_web_id = ?,
                manage_url_template = ?, modes_data_url = ?, token = ?,
                request_limit = ?, request_delay = ?,
                announcement = ?, notes = ?,
                updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (
                fields["name"], fields["domain"], fields["lottery_type_id"], fields["enabled"],
                fields["start_web_id"], fields["end_web_id"],
                fields["manage_url_template"], fields["modes_data_url"], resolved_token,
                fields["request_limit"], fields["request_delay"],
                fields["announcement"], fields["notes"],
                now, site_id,
            ),
        ).fetchone()
        return public_site(row)


def delete_site(db_path: str | Path, site_id: int) -> None:
    """删除指定 ID 的托管站点。

    Raises:
        NotFoundError: 站点不存在
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM managed_sites WHERE id = ?", (site_id,))
        if cur.rowcount == 0:
            raise NotFoundError(f"site_id={site_id} 不存在")


def resolve_web_id(db_path: str | Path, site_id: int) -> int:
    """解析站点的 web_id。

    Raises:
        NotFoundError: 站点不存在或 web_id 未配置。
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT web_id FROM managed_sites WHERE id = ?", (site_id,)
        ).fetchone()
        if not row or row["web_id"] is None:
            raise NotFoundError(f"site_id={site_id} 不存在或缺少 web_id 配置")
        return int(row["web_id"])
