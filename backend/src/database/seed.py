"""默认数据播种：管理员、彩种、站点、预测模块同步。

将 tables.py 中的 _seed_bootstrap_data 和 seed_default_lottery_types
迁移到此文件，表结构与默认数据分离。
"""

from __future__ import annotations

from typing import Any

from database.connection import connect, utc_now
from runtime_config import (
    get_bootstrap_config_value,
    ensure_system_config_table,
    seed_system_config_defaults,
)

# 彩种名称常量
HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"
TAIWAN_NAME = "台湾彩"


def seed_default_lottery_types(conn: Any, *, now: str) -> None:
    """插入三个默认彩种（香港/澳门/台湾），缺失时自动创建。

    所有默认值（开奖时间、采集 URL）均从运行时配置系统读取，
    确保 config.yaml 和 system_config 表是唯一可信源。
    """
    # 历史数据兼容：将 "六肖彩" 统一更名为 "香港彩"
    conn.execute(
        "UPDATE lottery_types SET name = ? WHERE name = ?",
        (HK_NAMES[0], HK_NAMES[1]),
    )
    defaults = [
        (
            HK_NAMES[0],
            str(get_bootstrap_config_value("draw.hk_default_draw_time", "21:30")),
            str(get_bootstrap_config_value("draw.hk_default_collect_url", "https://www.lnlllt.com/api.php")),
        ),
        (
            MACAU_NAME,
            str(get_bootstrap_config_value("draw.macau_default_draw_time", "21:30")),
            str(get_bootstrap_config_value("draw.macau_default_collect_url", "https://www.lnlllt.com/api.php")),
        ),
        (
            TAIWAN_NAME,
            str(get_bootstrap_config_value("draw.taiwan_default_draw_time", "22:30")),
            "",
        ),
    ]
    for lottery_name, draw_time, collect_url in defaults:
        exists = conn.execute(
            "SELECT COUNT(*) AS total FROM lottery_types WHERE name = ?",
            (lottery_name,),
        ).fetchone()["total"]
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO lottery_types
                (name, draw_time, collect_url, status, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (lottery_name, draw_time, collect_url, now, now),
        )


def seed_bootstrap_data(conn: Any, now: str) -> None:
    """播种引导数据：默认管理员、默认站点。

    所有默认值均从运行时配置系统读取，不硬编码回退值。
    """
    from auth import hash_password as _hash_password
    from admin.prediction import sync_site_prediction_modules as _sync_modules

    # ── 默认管理员 ──
    if (
        int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM admin_users"
            ).fetchone()["total"]
            or 0
        )
        == 0
    ):
        _admin_user = str(get_bootstrap_config_value("admin.username", "admin"))
        _admin_display = str(get_bootstrap_config_value("admin.display_name", "系统管理员"))
        _admin_pass = str(get_bootstrap_config_value("admin.password", "admin123"))
        _admin_role = str(get_bootstrap_config_value("admin.role", "super_admin"))
        conn.execute(
            """
            INSERT INTO admin_users (
                username, display_name, password_hash, role, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (
                _admin_user,
                _admin_display,
                _hash_password(_admin_pass),
                _admin_role,
                now,
                now,
            ),
        )

    # ── 播种彩种 ──
    seed_default_lottery_types(conn, now=now)

    # ── 默认托管站点 ──
    default_lottery_id = conn.execute(
        "SELECT id FROM lottery_types ORDER BY id LIMIT 1"
    ).fetchone()["id"]

    existing = int(
        conn.execute(
            "SELECT COUNT(*) AS total FROM managed_sites"
        ).fetchone()["total"]
        or 0
    )
    if existing == 0:
        _site_name = str(get_bootstrap_config_value("site.default_site_name", "默认盛世站点"))
        _site_domain = str(get_bootstrap_config_value("site.default_domain", "admin.shengshi8800.com"))
        _site_url = str(get_bootstrap_config_value("site.manage_url_template", ""))
        _site_data_url = str(get_bootstrap_config_value("site.modes_data_url", ""))
        _site_token = str(get_bootstrap_config_value("site.default_token", ""))
        _site_req_limit = int(get_bootstrap_config_value("site.request_limit", 250))
        _site_req_delay = float(get_bootstrap_config_value("site.request_delay", 0.5))
        _site_announcement = str(get_bootstrap_config_value("site.default_announcement", ""))
        _site_notes = str(get_bootstrap_config_value("site.default_notes", ""))
        _site_start = int(get_bootstrap_config_value("site.start_web_id", 1))
        _site_end = int(get_bootstrap_config_value("site.end_web_id", 10))
        conn.execute(
            """
            INSERT INTO managed_sites (
                web_id, name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
                manage_url_template, modes_data_url, token, request_limit, request_delay,
                announcement, notes,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _site_start,  # web_id 默认为 start_web_id
                _site_name,
                _site_domain,
                default_lottery_id,
                _site_start,
                _site_end,
                _site_url,
                _site_data_url,
                _site_token,
                _site_req_limit,
                _site_req_delay,
                _site_announcement,
                _site_notes,
                now,
                now,
            ),
        )
    else:
        conn.execute(
            "UPDATE managed_sites SET lottery_type_id = COALESCE(lottery_type_id, ?)",
            (default_lottery_id,),
        )
        # 回填已有站点的 web_id
        conn.execute(
            "UPDATE managed_sites SET web_id = start_web_id WHERE web_id IS NULL"
        )

    # 同步站点预测模块（站点创建后执行）
    _sync_modules(conn)
