"""Admin CRUD operations for managed sites, users, lottery types, draws, and numbers.

Extracted from app.py to provide a clean separation between HTTP routing
and data-access logic. All functions preserve their original signatures,
bodies, and docstrings exactly as they appear in app.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auth import hash_password, public_user
from predict.common import DEFAULT_TARGET_HIT_RATE, predict
from db import connect as db_connect
from helpers import parse_bool
from predict.mechanisms import get_prediction_config, list_prediction_configs
from tables import ensure_admin_tables
from utils.data_fetch import MODES_DATA_URL, WEB_MANAGE_URL_TEMPLATE

REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12, 20, 28, 31, 34, 38, 42, 43,
    44, 45, 46, 49, 50, 51, 52, 53, 54, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66,
    67, 68, 69, 151, 197,
)


# ─────────────────────────────────────────────────────────────────
#  Local utility helpers
# ─────────────────────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)


# ─────────────────────────────────────────────────────────────────
#  Sync helpers (dependency of save_site — originally in admin.prediction)
# ─────────────────────────────────────────────────────────────────

def get_site_prediction_module_blueprints() -> list[dict[str, Any]]:
    """返回站点预测模块的标准配置清单，并按前端要求的 mode_id 顺序输出。"""
    configs_by_mode_id: dict[int, dict[str, Any]] = {}
    for item in list_prediction_configs():
        try:
            configs_by_mode_id[int(item["default_modes_id"])] = item
        except (TypeError, ValueError):
            continue

    missing = [mode_id for mode_id in REQUIRED_SITE_PREDICTION_MODE_IDS if mode_id not in configs_by_mode_id]
    if missing:
        raise ValueError(f"以下 mode_id 缺少预测配置，无法同步站点模块: {missing}")

    blueprints: list[dict[str, Any]] = []
    for index, mode_id in enumerate(REQUIRED_SITE_PREDICTION_MODE_IDS):
        item = dict(configs_by_mode_id[mode_id])
        item["mode_id"] = int(mode_id)
        item["sort_order"] = index * 10
        blueprints.append(item)
    return blueprints


def sync_site_prediction_modules(conn: Any, site_id: int | None = None) -> None:
    """将 site_prediction_modules 与前端站点模块清单保持同步。"""
    blueprints = get_site_prediction_module_blueprints()
    allowed_keys = tuple(str(item["key"]) for item in blueprints)
    now = utc_now()

    site_query = "SELECT id FROM managed_sites"
    site_params: tuple[Any, ...] = ()
    if site_id is not None:
        site_query += " WHERE id = ?"
        site_params = (int(site_id),)
    site_rows = conn.execute(site_query, site_params).fetchall()

    for site_row in site_rows:
        current_site_id = int(site_row["id"])
        existing_rows = conn.execute(
            """
            SELECT mechanism_key, status, created_at
            FROM site_prediction_modules
            WHERE site_id = ?
            """,
            (current_site_id,),
        ).fetchall()
        existing_by_key = {str(row["mechanism_key"]): dict(row) for row in existing_rows}

        for item in blueprints:
            existing = existing_by_key.get(str(item["key"]))
            if existing:
                # 已有记录则 UPDATE，避免 INSERT ... ON CONFLICT 消耗序列值
                conn.execute(
                    """
                    UPDATE site_prediction_modules
                    SET mode_id = ?, sort_order = ?, updated_at = ?
                    WHERE site_id = ? AND mechanism_key = ?
                    """,
                    (
                        int(item["mode_id"]),
                        int(item["sort_order"]),
                        now,
                        current_site_id,
                        str(item["key"]),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO site_prediction_modules (
                        site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        current_site_id,
                        str(item["key"]),
                        int(item["mode_id"]),
                        1,
                        int(item["sort_order"]),
                        now,
                        now,
                    ),
                )



# ─────────────────────────────────────────────────────────────────
#  Site CRUD
# ─────────────────────────────────────────────────────────────────

def public_site(row: Any) -> dict[str, Any]:
    data = dict(row)
    token = data.pop("token", "") or ""
    data["enabled"] = bool(data["enabled"])
    data["token_present"] = bool(token)
    data["token_preview"] = f"{token[:8]}..." if token else ""
    return data


def list_sites(db_path: str | Path) -> list[dict[str, Any]]:
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
            raise KeyError(f"site_id={site_id} 不存在")
        data = dict(row) if include_secret else public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def save_site(db_path: str | Path, payload: dict[str, Any], site_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "name": str(payload.get("name") or "").strip(),
        "domain": str(payload.get("domain") or "").strip(),
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "enabled": 1 if parse_bool(payload.get("enabled"), True) else 0,
        "start_web_id": int(payload.get("start_web_id") or 1),
        "end_web_id": int(payload.get("end_web_id") or payload.get("start_web_id") or 10),
        "manage_url_template": str(payload.get("manage_url_template") or WEB_MANAGE_URL_TEMPLATE).strip(),
        "modes_data_url": str(payload.get("modes_data_url") or MODES_DATA_URL).strip(),
        "request_limit": int(payload.get("request_limit") or 250),
        "request_delay": float(payload.get("request_delay") or 0.5),
        "announcement": str(payload.get("announcement") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }
    token = payload.get("token")
    if not fields["name"]:
        raise ValueError("站点名称不能为空")
    if fields["start_web_id"] > fields["end_web_id"]:
        raise ValueError("start_web_id 不能大于 end_web_id")
    if "{web_id}" not in fields["manage_url_template"] and "{id}" not in fields["manage_url_template"]:
        raise ValueError("manage_url_template 必须包含 {web_id} 或 {id}")

    with connect(db_path) as conn:
        if site_id is None:
            row = conn.execute(
                """
                INSERT INTO managed_sites (
                    name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
                    manage_url_template, modes_data_url, token, request_limit,
                    request_delay, announcement, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
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
                "SELECT mechanism_key, mode_id, status, sort_order FROM site_prediction_modules WHERE site_id = 1 ORDER BY sort_order, id"
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
                sync_site_prediction_modules(conn, site_id=new_site_id)
                conn.commit()

            return new_site

        existing = conn.execute("SELECT token FROM managed_sites WHERE id = ?", (site_id,)).fetchone()
        if not existing:
            raise KeyError(f"site_id={site_id} 不存在")
        resolved_token = str(token) if token not in (None, "") else str(existing["token"] or "")
        row = conn.execute(
            """
            UPDATE managed_sites
            SET name = ?,
                domain = ?,
                lottery_type_id = ?,
                enabled = ?,
                start_web_id = ?,
                end_web_id = ?,
                manage_url_template = ?,
                modes_data_url = ?,
                token = ?,
                request_limit = ?,
                request_delay = ?,
                announcement = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (
                fields["name"],
                fields["domain"],
                fields["lottery_type_id"],
                fields["enabled"],
                fields["start_web_id"],
                fields["end_web_id"],
                fields["manage_url_template"],
                fields["modes_data_url"],
                resolved_token,
                fields["request_limit"],
                fields["request_delay"],
                fields["announcement"],
                fields["notes"],
                now,
                site_id,
            ),
        ).fetchone()
        return public_site(row)


def delete_site(db_path: str | Path, site_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM managed_sites WHERE id = ?", (site_id,))
        if cur.rowcount == 0:
            raise KeyError(f"site_id={site_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  User CRUD
# ─────────────────────────────────────────────────────────────────

def list_users(db_path: str | Path) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
        return [public_user(row) for row in rows]


def save_user(db_path: str | Path, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    username = str(payload.get("username") or "").strip()
    display_name = str(payload.get("display_name") or username).strip()
    role = str(payload.get("role") or "admin").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0
    password = str(payload.get("password") or "")
    if not username:
        raise ValueError("管理员用户名不能为空")

    with connect(db_path) as conn:
        if user_id is None:
            if not password:
                raise ValueError("新增管理员必须设置密码")
            row = conn.execute(
                """
                INSERT INTO admin_users (
                    username, display_name, password_hash, role, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (username, display_name, hash_password(password), role, status, now, now),
            ).fetchone()
            return public_user(row)

        existing = conn.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise KeyError(f"user_id={user_id} 不存在")
        password_hash = hash_password(password) if password else existing["password_hash"]
        row = conn.execute(
            """
            UPDATE admin_users
            SET username = ?,
                display_name = ?,
                password_hash = ?,
                role = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (username, display_name, password_hash, role, status, now, user_id),
        ).fetchone()
        return public_user(row)


def delete_user(db_path: str | Path, user_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        total = int(
            conn.execute("SELECT COUNT(*) AS total FROM admin_users WHERE status = 1").fetchone()["total"]
            or 0
        )
        target = conn.execute("SELECT status FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise KeyError(f"user_id={user_id} 不存在")
        if total <= 1 and int(target["status"] or 0) == 1:
            raise ValueError("至少保留一个可登录管理员")
        conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))


# ─────────────────────────────────────────────────────────────────
#  Lottery Type CRUD
# ─────────────────────────────────────────────────────────────────

def list_lottery_types(db_path: str | Path) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM lottery_types ORDER BY status DESC, id").fetchall()
        return [dict(row) | {"status": bool(row["status"])} for row in rows]


def save_lottery_type(db_path: str | Path, payload: dict[str, Any], lottery_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("彩种名称不能为空")
    draw_time = str(payload.get("draw_time") or "").strip()
    collect_url = str(payload.get("collect_url") or "").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0
    with connect(db_path) as conn:
        if lottery_id is None:
            row = conn.execute(
                """
                INSERT INTO lottery_types (name, draw_time, collect_url, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (name, draw_time, collect_url, status, now, now),
            ).fetchone()
        else:
            row = conn.execute(
                """
                UPDATE lottery_types
                SET name = ?, draw_time = ?, collect_url = ?, status = ?, updated_at = ?
                WHERE id = ?
                RETURNING *
                """,
                (name, draw_time, collect_url, status, now, lottery_id),
            ).fetchone()
            if not row:
                raise KeyError(f"lottery_id={lottery_id} 不存在")
        return dict(row) | {"status": bool(row["status"])}


def delete_lottery_type(db_path: str | Path, lottery_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM lottery_types WHERE id = ? RETURNING id", (lottery_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"lottery_id={lottery_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  Draw CRUD
# ─────────────────────────────────────────────────────────────────

def list_draws(db_path: str | Path, limit: int = 200) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT d.*, l.name AS lottery_name
            FROM lottery_draws d
            JOIN lottery_types l ON l.id = d.lottery_type_id
            ORDER BY d.year DESC, d.term DESC, d.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}
            for row in rows
        ]


def save_draw(db_path: str | Path, payload: dict[str, Any], draw_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "year": int(payload.get("year") or datetime.now().year),
        "term": int(payload.get("term") or 1),
        "numbers": str(payload.get("numbers") or "").strip(),
        "draw_time": str(payload.get("draw_time") or "").strip(),
        "status": 1 if parse_bool(payload.get("status"), True) else 0,
        "is_opened": 1 if parse_bool(payload.get("is_opened"), False) else 0,
        "next_term": int(payload.get("next_term") or (int(payload.get("term") or 1) + 1)),
    }
    if not fields["numbers"]:
        raise ValueError("开奖号码不能为空")
    with connect(db_path) as conn:
        if draw_id is None:
            row = conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, status,
                    is_opened, next_term, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (*fields.values(), now, now),
            ).fetchone()
        else:
            row = conn.execute(
                """
                UPDATE lottery_draws
                SET lottery_type_id = ?, year = ?, term = ?, numbers = ?, draw_time = ?,
                    status = ?, is_opened = ?, next_term = ?, updated_at = ?
                WHERE id = ?
                RETURNING *
                """,
                (*fields.values(), now, draw_id),
            ).fetchone()
            if not row:
                raise KeyError(f"draw_id={draw_id} 不存在")
        return dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}


def delete_draw(db_path: str | Path, draw_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM lottery_draws WHERE id = ?", (draw_id,))
        if cur.rowcount == 0:
            raise KeyError(f"draw_id={draw_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  Number CRUD (operates on fixed_data)
# ─────────────────────────────────────────────────────────────────

def list_numbers(db_path: str | Path, limit: int = 300, keyword: str = "") -> list[dict[str, Any]]:
    """号码管理直接读取 fixed_data 单表，保持和预测映射同源。"""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        params: list[Any] = []
        where = ""
        if keyword:
            where = "WHERE name LIKE ? OR sign LIKE ? OR code LIKE ?"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        rows = conn.execute(
            f"""
            SELECT id, name, code, sign AS category_key, year, status, type, xu
            FROM fixed_data
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) | {"status": bool(row["status"])} for row in rows]


def update_number(db_path: str | Path, number_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            UPDATE fixed_data
            SET name = ?,
                code = ?,
                sign = ?,
                year = ?,
                status = ?
            WHERE id = ?
            RETURNING id, name, code, sign AS category_key, year, status, type, xu
            """,
            (
                str(payload.get("name") or "").strip(),
                str(payload.get("code") or "").strip(),
                str(payload.get("category_key") or payload.get("sign") or "").strip(),
                str(payload.get("year") or "").strip(),
                1 if parse_bool(payload.get("status"), True) else 0,
                number_id,
            ),
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")
        return dict(row) | {"status": bool(row["status"])}


def create_number(db_path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO fixed_data (name, code, sign, year, status, type, xu)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id, name, code, sign AS category_key, year, status, type, xu
            """,
            (
                str(payload.get("name") or "").strip(),
                str(payload.get("code") or "").strip(),
                str(payload.get("category_key") or payload.get("sign") or "").strip(),
                str(payload.get("year") or "").strip(),
                1 if parse_bool(payload.get("status"), True) else 0,
                int(payload.get("type", 0)),
                int(payload.get("xu", 0)),
            ),
        ).fetchone()
        return dict(row) | {"status": bool(row["status"])}


def delete_number(db_path: str | Path, number_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM fixed_data WHERE id = ? RETURNING id", (number_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  Site prediction module CRUD
# ─────────────────────────────────────────────────────────────────

def list_site_prediction_modules(db_path: str | Path, site_id: int) -> dict[str, Any]:
    from predict.mechanisms import ensure_prediction_configs_loaded as _ensure_loaded
    _ensure_loaded(db_path)
    ensure_admin_tables(db_path)
    site = get_site(db_path, site_id)
    with connect(db_path) as conn:
        # 读取 mode_payload_tables 的 modes_id → title 映射
        mode_titles: dict[int, str] = {}
        if conn.table_exists("mode_payload_tables"):
            title_rows = conn.execute(
                "SELECT modes_id, title FROM mode_payload_tables"
            ).fetchall()
            for tr in title_rows:
                try:
                    mode_titles[int(tr["modes_id"])] = str(tr["title"] or "")
                except (TypeError, ValueError):
                    continue

        rows = conn.execute(
            """
            SELECT id, site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
            FROM site_prediction_modules
            WHERE site_id = ?
            ORDER BY sort_order, id
            """,
            (site_id,),
        ).fetchall()
        modules = [dict(row) for row in rows]
        for m in modules:
            mechanism_key = str(m.get("mechanism_key") or "").strip()
            try:
                config = get_prediction_config(mechanism_key)
            except ValueError:
                config = None
            if config is not None:
                m["default_modes_id"] = int(config.default_modes_id or 0)
                m["default_table"] = str(config.default_table or "")
            try:
                resolved_mode_id = int(m.get("mode_id") or 0)
            except (TypeError, ValueError):
                resolved_mode_id = 0
            if resolved_mode_id <= 0 and config is not None:
                resolved_mode_id = int(config.default_modes_id or 0)
            fallback_title = str(config.title or "") if config is not None else ""
            resolved_title = mode_titles.get(resolved_mode_id, fallback_title)
            if resolved_title:
                m["display_title"] = resolved_title
                m["tables_title"] = resolved_title
                m["title"] = resolved_title
            if resolved_mode_id > 0:
                m["resolved_mode_id"] = resolved_mode_id
        configured_keys = {str(m["mechanism_key"]) for m in modules}

        # 构建可用机制列表（title 优先使用 mode_payload_tables 的）
        available_mechanisms: list[dict[str, Any]] = []
        for item in list_prediction_configs():
            key = str(item["key"])
            mid = item["default_modes_id"]
            available_mechanisms.append({
                "key": key,
                "title": mode_titles.get(mid, item["title"]),
                "default_modes_id": mid,
                "default_table": item["default_table"],
                "configured": key in configured_keys,
            })

        return {
            "site": site,
            "modules": modules,
            "available_mechanisms": available_mechanisms,
        }


def add_site_prediction_module(
    db_path: str | Path, site_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    from predict.mechanisms import ensure_prediction_configs_loaded as _ensure_loaded
    _ensure_loaded(db_path)
    ensure_admin_tables(db_path)
    now = utc_now()
    mechanism_key = str(payload.get("mechanism_key") or "").strip()
    if not mechanism_key:
        raise ValueError("mechanism_key 不能为空")
    config = get_prediction_config(mechanism_key)
    mode_id = int(payload.get("mode_id") or 0)
    if mode_id <= 0:
        mode_id = int(config.default_modes_id or 0)
    status = 1 if parse_bool(payload.get("status"), True) else 0
    sort_order = int(payload.get("sort_order") or 0)

    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO site_prediction_modules (
                site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (site_id, mechanism_key, mode_id, status, sort_order, now, now),
        ).fetchone()
        return dict(row)


def update_site_prediction_module(
    db_path: str | Path, site_id: int, module_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()

    with connect(db_path) as conn:
        existing = conn.execute(
            "SELECT * FROM site_prediction_modules WHERE id = ? AND site_id = ?",
            (module_id, site_id),
        ).fetchone()
        if not existing:
            raise KeyError(f"module_id={module_id} 在 site_id={site_id} 下不存在")

        mechanism_key = str(payload.get("mechanism_key") or existing["mechanism_key"]).strip()
        config = get_prediction_config(mechanism_key)
        mode_id = int(payload.get("mode_id") or existing.get("mode_id") or 0)
        if mode_id <= 0:
            mode_id = int(config.default_modes_id or 0)
        status = 1 if parse_bool(payload.get("status"), bool(existing.get("status"))) else 0
        sort_order = int(payload.get("sort_order") or existing.get("sort_order") or 0)

        row = conn.execute(
            """
            UPDATE site_prediction_modules
            SET mechanism_key = ?, mode_id = ?, status = ?, sort_order = ?, updated_at = ?
            WHERE id = ? AND site_id = ?
            RETURNING *
            """,
            (mechanism_key, mode_id, status, sort_order, now, module_id, site_id),
        ).fetchone()
        return dict(row)


def delete_site_prediction_module(db_path: str | Path, site_id: int, module_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM site_prediction_modules WHERE id = ? AND site_id = ? RETURNING id",
            (module_id, site_id),
        ).fetchone()
        if not row:
            raise KeyError(f"module_id={module_id} 在 site_id={site_id} 下不存在")


def run_site_prediction_module(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    mechanism_key = str(payload.get("mechanism_key") or "").strip()
    if not mechanism_key:
        raise ValueError("mechanism_key 不能为空")
    config = get_prediction_config(mechanism_key)
    return predict(
        config=config,
        res_code=str(payload.get("res_code") or "").strip() or None,
        content=str(payload.get("content") or "").strip() or None,
        source_table=str(payload.get("source_table") or "").strip() or None,
        db_path=db_path,
        target_hit_rate=float(payload.get("target_hit_rate") or DEFAULT_TARGET_HIT_RATE),
    )
