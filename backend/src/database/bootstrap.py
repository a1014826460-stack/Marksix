"""数据库初始化总入口。

编排 schema 创建、轻量迁移、索引创建、默认数据播种。
可安全重复调用——同一 db_path 后续调用直接返回。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from database.connection import connect, utc_now, auto_increment_primary_key
from database.migrations import add_column_if_missing
from database.seed import seed_bootstrap_data
from database.schema.auth import ensure_auth_tables
from database.schema.lottery import ensure_lottery_tables
from database.schema.sites import ensure_site_tables
from database.schema.prediction import ensure_prediction_tables
from database.schema.scheduler import ensure_scheduler_tables
from database.schema.logs import ensure_log_tables
from database.schema.config import ensure_config_history_tables
from database.schema.audit import ensure_audit_tables
from database.schema.legacy import ensure_legacy_asset_tables
from database.schema.indexes import ensure_indexes
from runtime_config import ensure_system_config_table, seed_system_config_defaults

# 按 db_target 维度记录已完成的初始化
_initialized_targets: set[str] = set()


def _sync_legacy_image_assets(conn: Any) -> None:
    """旧版图片资产同步（受配置控制，默认跳过）。

    仅当 legacy.sync_images_on_bootstrap 配置为 true 时执行，
    避免非旧版部署在启动时产生不必要的 I/O。
    """
    import mimetypes
    from pathlib import Path as _Path

    from runtime_config import get_bootstrap_config_value

    BACKEND_ROOT = _Path(__file__).resolve().parents[2]
    LEGACY_IMAGES_DIR = BACKEND_ROOT / str(
        get_bootstrap_config_value("legacy.images_dir", "data/Images")
    )
    LEGACY_IMAGES_UPLOAD_BUCKET = str(
        get_bootstrap_config_value("legacy.images_upload_bucket", "20250322")
    )
    LEGACY_IMAGES_UPLOAD_PREFIX = f"/uploads/image/{LEGACY_IMAGES_UPLOAD_BUCKET}"
    LEGACY_POST_LIST_PC = int(get_bootstrap_config_value("legacy.post_list_pc", 305))
    LEGACY_POST_LIST_WEB = int(get_bootstrap_config_value("legacy.post_list_web", 4))
    LEGACY_POST_LIST_TYPE = int(get_bootstrap_config_value("legacy.post_list_type", 3))

    if not get_bootstrap_config_value("legacy.sync_images_on_bootstrap", False):
        return
    if not LEGACY_IMAGES_DIR.exists():
        return

    now = utc_now()
    for sort_order, file_path in enumerate(
        sorted(LEGACY_IMAGES_DIR.iterdir()), start=1
    ):
        if not file_path.is_file():
            continue

        storage_path = file_path.relative_to(BACKEND_ROOT).as_posix()
        legacy_upload_path = f"{LEGACY_IMAGES_UPLOAD_PREFIX}/{file_path.name}"
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        file_size = int(file_path.stat().st_size)
        existing = conn.execute(
            """
            SELECT id
            FROM legacy_image_assets
            WHERE file_name = ?
            """,
            (file_path.name,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE legacy_image_assets
                SET source_key = ?,
                    source_pc = ?,
                    source_web = ?,
                    source_type = ?,
                    storage_path = ?,
                    legacy_upload_path = ?,
                    cover_image = ?,
                    mime_type = ?,
                    file_size = ?,
                    sort_order = ?,
                    enabled = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    "legacy-post-list",
                    LEGACY_POST_LIST_PC,
                    LEGACY_POST_LIST_WEB,
                    LEGACY_POST_LIST_TYPE,
                    storage_path,
                    legacy_upload_path,
                    legacy_upload_path,
                    mime_type,
                    file_size,
                    sort_order,
                    now,
                    existing["id"],
                ),
            )
            continue

        conn.execute(
            """
            INSERT INTO legacy_image_assets (
                source_key,
                source_pc,
                source_web,
                source_type,
                file_name,
                storage_path,
                legacy_upload_path,
                cover_image,
                mime_type,
                file_size,
                sort_order,
                enabled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                "legacy-post-list",
                LEGACY_POST_LIST_PC,
                LEGACY_POST_LIST_WEB,
                LEGACY_POST_LIST_TYPE,
                file_path.name,
                storage_path,
                legacy_upload_path,
                legacy_upload_path,
                mime_type,
                file_size,
                sort_order,
                now,
                now,
            ),
        )


def ensure_admin_tables(db_path: str | Path) -> None:
    """确保所有管理表、索引和引导数据存在。

    编排 schema 创建、轻量迁移、索引创建和默认数据播种。
    同一 db_path 可安全重复调用——后续调用直接返回。
    """
    global _initialized_targets

    target_key = str(db_path)
    if target_key in _initialized_targets:
        return

    now = utc_now()
    with connect(db_path) as conn:
        # ── 1. 系统配置表（最先创建，后续播种依赖它） ──
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now=now)

        pk_sql = auto_increment_primary_key("id", conn.engine)

        # ── 2. 各业务表组（按依赖顺序） ──
        ensure_auth_tables(conn, pk_sql)
        ensure_lottery_tables(conn, pk_sql)
        ensure_site_tables(conn, pk_sql)
        ensure_scheduler_tables(conn, pk_sql)
        ensure_prediction_tables(conn, pk_sql)
        ensure_legacy_asset_tables(conn, pk_sql)
        ensure_audit_tables(conn, pk_sql)
        ensure_log_tables(conn, pk_sql)
        ensure_config_history_tables(conn, pk_sql)

        # ── 3. 索引（表就绪后创建） ──
        ensure_indexes(conn)

        # ── 4. Legacy 图片同步（受配置控制） ──
        _sync_legacy_image_assets(conn)

        # ── 5. 播种引导数据 ──
        seed_bootstrap_data(conn, now=now)

    # 只有全部成功后才标记该 target 已初始化
    _initialized_targets.add(target_key)
