"""
Admin CRUD 操作模块 —— 托管站点、管理员用户、彩种、开奖记录、号码数据的增删改查。

从 app.py 中提取，将 HTTP 路由与数据访问逻辑分离。所有函数保持原有的
签名、函数体和文档字符串不变，仅新增规范的中文注释（含 param / return / raises）。

Extracted from app.py to provide a clean separation between HTTP routing
and data-access logic. All functions preserve their original signatures,
bodies, and docstrings exactly as they appear in app.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from auth import hash_password, public_user
from predict.common import predict
from db import connect, utc_now
from helpers import parse_bool
from predict.mechanisms import get_prediction_config, list_prediction_configs
from runtime_config import get_config
from tables import ensure_admin_tables
from utils.data_fetch import MODES_DATA_URL, WEB_MANAGE_URL_TEMPLATE
from admin.prediction import sync_site_prediction_modules


# ─────────────────────────────────────────────────────────────────
#  站点 CRUD / Site CRUD
# ─────────────────────────────────────────────────────────────────

def public_site(row: Any) -> dict[str, Any]:
    """将数据库中的站点行转换为对外安全的字典（隐藏完整 token，增加预览信息）。

    :param row: 数据库查询返回的站点行对象（通常为 sqlite3.Row 或字典）
    :return: 处理后的站点字典，包含 ``token_present``（布尔值）和
             ``token_preview``（token 前 8 位预览）等字段，不暴露完整 token
    """
    data = dict(row)
    token = data.pop("token", "") or ""
    data["enabled"] = bool(data["enabled"])
    data["token_present"] = bool(token)
    data["token_preview"] = f"{token[:8]}..." if token else ""
    return data


def list_sites(db_path: str | Path) -> list[dict[str, Any]]:
    """获取所有托管站点列表，关联彩种名称，按启用状态降序、ID 升序排列。

    :param db_path: SQLite 数据库文件路径
    :return: 处理后的站点字典列表（已脱敏 token）
    """
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

    :param db_path: SQLite 数据库文件路径
    :param site_id: 站点 ID
    :param include_secret: 是否返回包含完整 token 的原始数据，默认 False（脱敏）
    :return: 站点字典（include_secret=True 时包含完整 token，否则使用 public_site 脱敏）
    :raises KeyError: 当 site_id 对应的站点不存在时抛出
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
            raise KeyError(f"site_id={site_id} 不存在")
        data = dict(row) if include_secret else public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def save_site(db_path: str | Path, payload: dict[str, Any], site_id: int | None = None) -> dict[str, Any]:
    """创建或更新托管站点。

    当 site_id 为 None 时创建新站点，并从模板站点（site 1）复制预测模块配置；
    否则更新已有站点。创建和更新时均会对字段进行校验。

    :param db_path: SQLite 数据库文件路径
    :param payload: 站点字段字典，可包含 name、domain、lottery_type_id、enabled、
                    start_web_id、end_web_id、manage_url_template、modes_data_url、
                    token、request_limit、request_delay、announcement、notes 等字段
    :param site_id: 可选，要更新的站点 ID；为 None 时表示新建
    :return: 创建或更新后的站点字典（已脱敏）
    :raises ValueError: 当站点名称为空、start_web_id > end_web_id，
                        或 manage_url_template 缺少 {web_id}/{id} 占位符时抛出
    :raises KeyError: 当 site_id 对应的站点不存在（更新场景）时抛出
    """
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
            or get_config(db_path, "site.manage_url_template", WEB_MANAGE_URL_TEMPLATE)
        ).strip(),
        "modes_data_url": str(
            payload.get("modes_data_url")
            or get_config(db_path, "site.modes_data_url", MODES_DATA_URL)
        ).strip(),
        "request_limit": int(payload.get("request_limit") or get_config(db_path, "site.request_limit", 250)),
        "request_delay": float(payload.get("request_delay") or get_config(db_path, "site.request_delay", 0.5)),
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
    """删除指定 ID 的托管站点。

    :param db_path: SQLite 数据库文件路径
    :param site_id: 要删除的站点 ID
    :raises KeyError: 当 site_id 对应的站点不存在时抛出
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM managed_sites WHERE id = ?", (site_id,))
        if cur.rowcount == 0:
            raise KeyError(f"site_id={site_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  管理员用户 CRUD / User CRUD
# ─────────────────────────────────────────────────────────────────

def list_users(db_path: str | Path) -> list[dict[str, Any]]:
    """获取所有管理员用户列表，按 ID 升序排列。

    :param db_path: SQLite 数据库文件路径
    :return: 脱敏后的管理员用户字典列表（已移除密码哈希等敏感字段）
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
        return [public_user(row) for row in rows]


def save_user(db_path: str | Path, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    """创建或更新管理员用户。

    当 user_id 为 None 时创建新用户（必须提供密码）；否则更新已有用户，
    密码为空时保留原密码不变。

    :param db_path: SQLite 数据库文件路径
    :param payload: 用户字段字典，可包含 username、display_name、role、status、password 等字段
    :param user_id: 可选，要更新的用户 ID；为 None 时表示新建
    :return: 创建或更新后的管理员用户字典（已脱敏）
    :raises ValueError: 当用户名为空或新增用户未设置密码时抛出
    :raises KeyError: 当 user_id 对应的用户不存在（更新场景）时抛出
    """
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
                (username, display_name, hash_password(password, db_path=db_path), role, status, now, now),
            ).fetchone()
            return public_user(row)

        existing = conn.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise KeyError(f"user_id={user_id} 不存在")
        password_hash = hash_password(password, db_path=db_path) if password else existing["password_hash"]
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
    """删除指定 ID 的管理员用户。

    删除前会校验至少保留一个可登录（status=1）的管理员，防止全部删除。

    :param db_path: SQLite 数据库文件路径
    :param user_id: 要删除的用户 ID
    :raises KeyError: 当 user_id 对应的用户不存在时抛出
    :raises ValueError: 当系统中仅剩一个可登录管理员且尝试删除该用户时抛出
    """
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
#  彩种 CRUD / Lottery Type CRUD
# ─────────────────────────────────────────────────────────────────

def list_lottery_types(db_path: str | Path) -> list[dict[str, Any]]:
    """获取所有彩种列表，按启用状态降序、ID 升序排列。

    当 lottery_types.next_time 为空时，从 lottery_draws 中取该彩种最新的
    next_time 作为兜底值，确保管理页面始终能展示下次开奖时间。
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM lottery_types ORDER BY status DESC, id").fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            d: dict[str, Any] = dict(row) | {"status": bool(row["status"])}
            if not d.get("next_time"):
                ld_row = conn.execute(
                    """SELECT next_time FROM lottery_draws
                       WHERE lottery_type_id = ? AND next_time IS NOT NULL AND next_time != ''
                       ORDER BY year DESC, term DESC LIMIT 1""",
                    (d["id"],),
                ).fetchone()
                if ld_row:
                    d["next_time"] = ld_row["next_time"]
                    # 回填 lottery_types，保持数据一致
                    conn.execute(
                        "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = ?",
                        (ld_row["next_time"], utc_now(), d["id"]),
                    )
            result.append(d)
        return result


def save_lottery_type(db_path: str | Path, payload: dict[str, Any], lottery_id: int | None = None) -> dict[str, Any]:
    """创建或更新彩种信息。

    当 lottery_id 为 None 时创建新彩种；否则更新已有彩种。

    :param db_path: SQLite 数据库文件路径
    :param payload: 彩种字段字典，可包含 name、draw_time、collect_url、next_time、status 等字段
    :param lottery_id: 可选，要更新的彩种 ID；为 None 时表示新建
    :return: 创建或更新后的彩种字典，其中 ``status`` 字段已转换为布尔值
    :raises ValueError: 当彩种名称为空时抛出
    :raises KeyError: 当 lottery_id 对应的彩种不存在（更新场景）时抛出
    """
    ensure_admin_tables(db_path)
    now = utc_now()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("彩种名称不能为空")
    draw_time = str(payload.get("draw_time") or "").strip()
    collect_url = str(payload.get("collect_url") or "").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0

    # next_time 始终从 lottery_draws 最新一期推导，不接受前端直接修改
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

        # 从 lottery_draws 获取该彩种最新一期的 next_time 回填
        ld_row = conn.execute(
            """SELECT next_time FROM lottery_draws
               WHERE lottery_type_id = ? AND next_time IS NOT NULL AND next_time != ''
               ORDER BY year DESC, term DESC LIMIT 1""",
            (effective_lottery_id,),
        ).fetchone()
        derived_next_time = str(ld_row["next_time"]) if ld_row else ""
        if derived_next_time:
            conn.execute(
                "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = ?",
                (derived_next_time, now, effective_lottery_id),
            )

        # 重新读取以获取最终状态
        final_row = conn.execute(
            "SELECT * FROM lottery_types WHERE id = ?", (effective_lottery_id,)
        ).fetchone()
        return dict(final_row) | {"status": bool(final_row["status"])}


def delete_lottery_type(db_path: str | Path, lottery_id: int) -> None:
    """删除指定 ID 的彩种。

    :param db_path: SQLite 数据库文件路径
    :param lottery_id: 要删除的彩种 ID
    :raises KeyError: 当 lottery_id 对应的彩种不存在时抛出
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM lottery_types WHERE id = ? RETURNING id", (lottery_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"lottery_id={lottery_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  开奖记录 CRUD / Draw CRUD
# ─────────────────────────────────────────────────────────────────

def list_draws(db_path: str | Path, limit: int = 200) -> list[dict[str, Any]]:
    """获取开奖记录列表，关联彩种名称，按年份降序、期号降序、ID 降序排列。

    :param db_path: SQLite 数据库文件路径
    :param limit: 返回记录的最大条数，默认 200
    :return: 开奖记录字典列表，其中 ``status`` 和 ``is_opened`` 字段已转换为布尔值
    """
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
    """创建或更新开奖记录。

    当 draw_id 为 None 时创建新记录；否则更新已有记录。创建或更新时会对号码进行校验：
    必须恰好 7 个号码，每个号码为 01~49 之间的两位数。

    :param db_path: SQLite 数据库文件路径
    :param payload: 开奖字段字典，可包含 lottery_type_id、year、term、numbers、
                    draw_time、status、is_opened、next_term 等字段
    :param draw_id: 可选，要更新的开奖记录 ID；为 None 时表示新建
    :return: 创建或更新后的开奖记录字典，其中 ``status`` 和 ``is_opened`` 已转换为布尔值
    :raises ValueError: 当号码为空、号码数量不为 7、或号码不在 01~49 范围内时抛出
    :raises KeyError: 当 draw_id 对应的记录不存在（更新场景）时抛出
    """
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
    # 台湾彩自动推算开奖时间：时间取自 lottery_types.draw_time
    if fields["lottery_type_id"] == 3 and not fields["draw_time"]:
        from calendar import timegm

        with connect(db_path) as conn:
            # 获取 lottery_types 中 id=3 的 draw_time（如 "22:30"）
            lt_row = conn.execute("SELECT draw_time FROM lottery_types WHERE id = 3").fetchone()
            lt_time = str(lt_row["draw_time"]).strip() if lt_row and lt_row["draw_time"] else "22:30:00"
            lt_parts = lt_time.split(":")
            lt_h = int(lt_parts[0]) if len(lt_parts) >= 1 else 22
            lt_m = int(lt_parts[1]) if len(lt_parts) >= 2 else 30
            lt_s = int(lt_parts[2]) if len(lt_parts) >= 3 else 0

            prev = conn.execute(
                """SELECT draw_time FROM lottery_draws
                   WHERE lottery_type_id = 3 ORDER BY year DESC, term DESC LIMIT 1"""
            ).fetchone()
            if prev and prev.get("draw_time"):
                try:
                    prev_dt = datetime.strptime(str(prev["draw_time"]).strip(), "%Y-%m-%d %H:%M:%S")
                    next_dt = prev_dt.replace(
                        day=prev_dt.day + 1, hour=lt_h, minute=lt_m, second=lt_s, microsecond=0
                    )
                    fields["draw_time"] = next_dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, OverflowError):
                    pass
            if not fields["draw_time"]:
                beijing_now = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
                fields["draw_time"] = beijing_now.replace(
                    hour=lt_h, minute=lt_m, second=lt_s, microsecond=0
                ).strftime("%Y-%m-%d %H:%M:%S")

        # type=3 的 next_time：下一期 draw_time 的毫秒级时间戳
        # 若无下一期数据，退化为当期 draw_time 的毫秒时间戳
        if fields["draw_time"]:
            try:
                draw_dt = datetime.strptime(fields["draw_time"].strip(), "%Y-%m-%d %H:%M:%S")
                # 优先取下一期（+1天）；若解析失败则回退到当期时间
                try:
                    next_dt = draw_dt + timedelta(days=1)
                    utc_dt = next_dt - timedelta(hours=8)
                    fields["next_time"] = str(int(timegm(utc_dt.timetuple()) * 1000))
                except (ValueError, OverflowError):
                    utc_dt = draw_dt - timedelta(hours=8)
                    fields["next_time"] = str(int(timegm(utc_dt.timetuple()) * 1000))
            except (ValueError, OverflowError):
                pass

    # 开奖时间已过：自动标记为已开奖（draw_time 为北京时间，须与北京时间比较）
    if fields["draw_time"] and not fields["is_opened"]:
        try:
            draw_dt = datetime.strptime(fields["draw_time"].strip(), "%Y-%m-%d %H:%M:%S")
            beijing_now = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
            if draw_dt <= beijing_now:
                fields["is_opened"] = 1
        except ValueError:
            pass  # 只包含日期的格式，不做自动判断

    if not fields["numbers"]:
        raise ValueError("开奖号码不能为空")
    # 验证恰好 7 个号码，每个 01-49
    num_list = [n.strip() for n in fields["numbers"].split(",") if n.strip()]
    if len(num_list) != 7:
        raise ValueError(f"开奖号码必须恰好 7 个，当前 {len(num_list)} 个")
    for n in num_list:
        if not n.isdigit() or int(n) < 1 or int(n) > 49:
            raise ValueError(f"无效号码: {n}，每个号码必须为 01-49")
    with connect(db_path) as conn:
        if draw_id is None:
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
        return dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}


def delete_draw(db_path: str | Path, draw_id: int) -> None:
    """删除指定 ID 的开奖记录。

    :param db_path: SQLite 数据库文件路径
    :param draw_id: 要删除的开奖记录 ID
    :raises KeyError: 当 draw_id 对应的记录不存在时抛出
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM lottery_draws WHERE id = ?", (draw_id,))
        if cur.rowcount == 0:
            raise KeyError(f"draw_id={draw_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  号码 CRUD（操作 fixed_data 表）
#  Number CRUD (operates on fixed_data)
# ─────────────────────────────────────────────────────────────────

def list_numbers(db_path: str | Path, limit: int = 300, keyword: str = "") -> list[dict[str, Any]]:
    """获取号码列表，直接读取 fixed_data 表，保持与预测映射同源。

    支持按关键字模糊搜索（匹配 name、sign、code 字段）。

    :param db_path: SQLite 数据库文件路径
    :param limit: 返回记录的最大条数，默认 300
    :param keyword: 可选，搜索关键字，用于模糊匹配 name、sign 或 code 字段
    :return: 号码字典列表，其中 ``status`` 字段已转换为布尔值
    """
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
    """更新 fixed_data 表中指定 ID 的号码记录。

    :param db_path: SQLite 数据库文件路径
    :param number_id: 要更新的号码 ID
    :param payload: 号码字段字典，可包含 name、code、category_key（或 sign）、year、status 等字段
    :return: 更新后的号码字典，其中 ``status`` 字段已转换为布尔值
    :raises KeyError: 当 number_id 对应的号码不存在时抛出
    """
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
    """在 fixed_data 表中创建一条新的号码记录。

    :param db_path: SQLite 数据库文件路径
    :param payload: 号码字段字典，可包含 name、code、category_key（或 sign）、year、status、type、xu 等字段
    :return: 新创建的号码字典，其中 ``status`` 字段已转换为布尔值
    """
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
    """从 fixed_data 表中删除指定 ID 的号码记录。

    :param db_path: SQLite 数据库文件路径
    :param number_id: 要删除的号码 ID
    :raises KeyError: 当 number_id 对应的号码不存在时抛出
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM fixed_data WHERE id = ? RETURNING id", (number_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")


# ─────────────────────────────────────────────────────────────────
#  站点预测模块 CRUD / Site prediction module CRUD
# ─────────────────────────────────────────────────────────────────

def list_site_prediction_modules(db_path: str | Path, site_id: int) -> dict[str, Any]:
    """获取指定站点的预测模块列表，同时返回站点信息与可用机制清单。

    模块列表中会补充 ``display_title``、``resolved_mode_id`` 等前端渲染所需字段。
    可用机制清单中标记每个机制是否已配置。

    :param db_path: SQLite 数据库文件路径
    :param site_id: 站点 ID
    :return: 字典，包含三个键：
             - ``site``: 站点信息字典
             - ``modules``: 该站点的预测模块列表
             - ``available_mechanisms``: 可用预测机制列表，每个元素含 key、title、configured 等字段
    """
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
    """为指定站点添加一个新的预测模块。

    :param db_path: SQLite 数据库文件路径
    :param site_id: 站点 ID
    :param payload: 模块字段字典，可包含 mechanism_key、mode_id、status、sort_order 等字段
    :return: 新创建的预测模块字典
    :raises ValueError: 当 mechanism_key 为空时抛出
    """
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
    """更新指定站点下的某个预测模块。

    :param db_path: SQLite 数据库文件路径
    :param site_id: 站点 ID
    :param module_id: 要更新的模块 ID
    :param payload: 模块字段字典，可包含 mechanism_key、mode_id、status、sort_order 等字段
    :return: 更新后的预测模块字典
    :raises KeyError: 当 module_id 在指定 site_id 下不存在时抛出
    """
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
    """删除指定站点下的某个预测模块。

    :param db_path: SQLite 数据库文件路径
    :param site_id: 站点 ID
    :param module_id: 要删除的模块 ID
    :raises KeyError: 当 module_id 在指定 site_id 下不存在时抛出
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM site_prediction_modules WHERE id = ? AND site_id = ? RETURNING id",
            (module_id, site_id),
        ).fetchone()
        if not row:
            raise KeyError(f"module_id={module_id} 在 site_id={site_id} 下不存在")


def run_site_prediction_module(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """执行一次站点预测模块的预测运算。

    :param db_path: SQLite 数据库文件路径
    :param site_id: 站点 ID（保留参数，当前实现中未直接使用，通过预测配置间接关联）
    :param payload: 预测参数字典，可包含 mechanism_key、res_code、content、
                    source_table、target_hit_rate 等字段
    :return: 预测结果字典，结构与 ``predict`` 函数的返回值一致
    :raises ValueError: 当 mechanism_key 为空时抛出
    """
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
        target_hit_rate=float(
            payload.get("target_hit_rate")
            or get_config(db_path, "prediction.default_target_hit_rate", 0.65)
        ),
    )
