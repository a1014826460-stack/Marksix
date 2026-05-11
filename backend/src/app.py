"""Lightweight backend API and CMS for lottery data management.

本服务只依赖 Python 标准库，直接复用现有预测、抓取、归一化和文本映射模块。
适合当前项目这种强依赖本地 SQLite 的业务形态，避免为了简单后台管理额外引入
一整套通用 CMS 框架。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = Path(__file__).resolve().parent
PREDICT_ROOT = SRC_ROOT / "predict"
UTILS_ROOT = SRC_ROOT / "utils"
CRAWLER_ROOT = SRC_ROOT / "crawler"
DEFAULT_SQLITE_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"

# Load configuration from config.yaml
import config as app_config  # noqa: E402
_cfg_defaults = app_config.load_config()
_cfg_db = _cfg_defaults.get("database", {})
_cfg_site = _cfg_defaults.get("site", {})
_cfg_legacy = _cfg_defaults.get("legacy", {})

DEFAULT_POSTGRES_DSN = _cfg_db.get("default_postgres_dsn",
    "postgresql://postgres:2225427@localhost:5432/liuhecai")
LEGACY_IMAGES_DIR = BACKEND_ROOT / _cfg_legacy.get("images_dir", "data/Images")
LEGACY_IMAGES_UPLOAD_BUCKET = _cfg_legacy.get("images_upload_bucket", "20250322")
LEGACY_IMAGES_UPLOAD_PREFIX = f"/uploads/image/{LEGACY_IMAGES_UPLOAD_BUCKET}"
LEGACY_POST_LIST_PC = _cfg_legacy.get("post_list_pc", 305)
LEGACY_POST_LIST_WEB = _cfg_legacy.get("post_list_web", 4)
LEGACY_POST_LIST_TYPE = _cfg_legacy.get("post_list_type", 3)

for path in (PREDICT_ROOT, UTILS_ROOT, CRAWLER_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from common import predict  # noqa: E402
from data_fetch import (  # noqa: E402
    DEFAULT_TOKEN,
    MODES_DATA_URL,
    WEB_MANAGE_URL_TEMPLATE,
    ensure_fetch_tables,
    fetch_all_data_for_mode,
    fetch_web_id_list,
    save_mode_all_data,
)
from mechanisms import ensure_prediction_configs_loaded, get_prediction_config, list_prediction_configs  # noqa: E402
from logger import (
    export_error_logs, get_error_log_detail, get_log_stats,
    init_logging, query_error_logs, trigger_cleanup,
)  # noqa: E402
from normalize_sqlite import normalize_payload_tables  # noqa: E402
from build_text_history_mappings import build_text_history_mappings  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
    CREATED_SCHEMA_NAME,
    created_table_exists,
    normalize_color_label,
    quote_qualified_identifier as quote_schema_table,
    schema_table_exists,
    table_column_names,
    upsert_created_prediction_row,
)
from db import auto_increment_primary_key, connect, detect_database_engine, quote_identifier, utc_now  # noqa: E402
from auth import (  # noqa: E402
    auth_user_from_token,
    ensure_generation_permission,
    login_user,
    logout_user,
)
from admin.crud import (  # noqa: E402
    add_site_prediction_module,
    create_number,
    delete_draw,
    delete_lottery_type,
    delete_number,
    delete_site,
    delete_site_prediction_module,
    delete_user,
    get_site,
    list_draws,
    list_lottery_types,
    list_numbers,
    list_site_prediction_modules,
    list_sites,
    list_users,
    public_site,
    run_site_prediction_module,
    save_draw,
    save_lottery_type,
    save_site,
    save_user,
    update_number,
    update_site_prediction_module,
)
from admin.payload import (  # noqa: E402
    delete_mode_payload_row,
    list_mode_payload_rows,
    update_mode_payload_row,
    validate_mode_payload_table,
)
from admin.prediction import (  # noqa: E402
    build_generated_prediction_row_data,
    build_prediction_api_response,
    bulk_generate_site_prediction_data,
    get_site_prediction_module_blueprint_by_key,
    regenerate_payload_data,
    resolve_prediction_request_safety,
)
from helpers import (  # noqa: E402
    apply_lottery_draw_overlay,
    build_draw_result_payload,
    build_mode_payload_filters,
    build_mode_payload_order_clause,
    build_mode_payload_row_key,
    color_name_to_key,
    load_fixed_data_maps,
    load_lottery_draw_map,
    load_mode_payload_rows_from_source,
    merge_preferred_mode_payload_rows,
    normalize_issue_part,
    parse_bool,
    parse_issue_int,
    row_to_dict,
    split_csv,
    sql_safe_int_expr,
)
from legacy.api import (  # noqa: E402
    get_legacy_current_term,
    list_legacy_post_images,
    load_legacy_mode_rows,
)
from public.api import (  # noqa: E402
    get_draw_history,
    get_public_latest_draw,
    get_public_site_page_data,
)
from tables import (  # noqa: E402
    database_summary,
    default_db_target,
    ensure_admin_tables,
    sync_legacy_image_assets,
)
from crawler_service import (  # noqa: E402
    CrawlerScheduler,
    crawl_and_generate_for_type,
    import_taiwan_json,
    run_crawl_only,
    run_hk_crawler,
    run_macau_crawler,
)
from runtime_config import list_system_configs, upsert_system_config, get_config  # noqa: E402

# ── 后台异步任务 ─────────────────────────────────────────
_background_jobs: dict[str, dict[str, Any]] = {}
_background_jobs_lock = threading.Lock()


def _start_background_job(target, *args, **kwargs) -> str:
    """在后台线程中执行任务，返回 job_id。"""
    job_id = secrets.token_hex(8)
    with _background_jobs_lock:
        _background_jobs[job_id] = {"status": "running", "started_at": utc_now(), "result": None}

    def _run():
        try:
            result = target(*args, **kwargs)
            with _background_jobs_lock:
                _background_jobs[job_id]["status"] = "done"
                _background_jobs[job_id]["result"] = result
        except Exception as exc:
            with _background_jobs_lock:
                _background_jobs[job_id]["status"] = "error"
                _background_jobs[job_id]["error"] = str(exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return job_id


def _get_background_job(job_id: str) -> dict[str, Any] | None:
    with _background_jobs_lock:
        return dict(_background_jobs.get(job_id) or {}) or None


def _crawl_and_generate(db_path: str, lottery_type_id: int) -> dict[str, Any]:
    """爬取指定彩种的开奖数据，然后自动生成所有启用站点的预测资料。

    委托给 crawler_service.crawl_and_generate_for_type 执行实际逻辑。
    """
    return crawl_and_generate_for_type(db_path, lottery_type_id)

def create_fetch_run(db_path: str | Path, site_id: int) -> int:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO site_fetch_runs (site_id, status, message, started_at)
            VALUES (?, 'running', '', ?)
            RETURNING id
            """,
            (site_id, utc_now()),
        ).fetchone()
        return int(row["id"])

def finish_fetch_run(
    db_path: str | Path,
    run_id: int,
    status: str,
    message: str,
    modes_count: int,
    records_count: int,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE site_fetch_runs
            SET status = ?,
                message = ?,
                modes_count = ?,
                records_count = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (status, message, modes_count, records_count, utc_now(), run_id),
        )

def fetch_site_data(
    db_path: str | Path,
    site_id: int,
    *,
    normalize_after: bool = True,
    build_text_mappings_after: bool = True,
) -> dict[str, Any]:
    """按 CMS 站点配置抓取数据，并可选执行归一化和文本映射刷新。"""
    ensure_admin_tables(db_path)
    site = get_site(db_path, site_id, include_secret=True)
    if not site["enabled"]:
        raise ValueError("该站点已禁用，不能执行抓取")

    run_id = create_fetch_run(db_path, site_id)
    modes_count = 0
    records_count = 0
    try:
        modes_by_web = fetch_web_id_list(
            start_web_id=int(site["start_web_id"]),
            end_web_id=int(site["end_web_id"]),
            url_template=str(site["manage_url_template"]),
            token=str(site.get("token") or "") or None,
        )
        fetched_at = utc_now()
        with connect(db_path) as conn:
            ensure_fetch_tables(conn)
            for web_id in range(int(site["start_web_id"]), int(site["end_web_id"]) + 1):
                for mode in modes_by_web.get(web_id, []):
                    all_data = fetch_all_data_for_mode(
                        web_id=web_id,
                        modes_id=int(mode["modes_id"]),
                        base_url=str(site["modes_data_url"]),
                        token=str(site.get("token") or "") or None,
                        limit=int(site["request_limit"]),
                        request_delay=float(site["request_delay"]),
                    )
                    save_mode_all_data(conn, web_id, mode, all_data, fetched_at)
                    conn.commit()
                    modes_count += 1
                    records_count += len(all_data)

        post_process: dict[str, Any] = {}
        if normalize_after:
            post_process["normalized_tables"] = len(normalize_payload_tables(db_path))
        if build_text_mappings_after:
            post_process["text_mappings"] = build_text_history_mappings(db_path, rebuild=True)

        message = "抓取完成"
        finish_fetch_run(db_path, run_id, "success", message, modes_count, records_count)
        return {
            "run_id": run_id,
            "status": "success",
            "message": message,
            "modes_count": modes_count,
            "records_count": records_count,
            "post_process": post_process,
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        finish_fetch_run(db_path, run_id, "failed", message, modes_count, records_count)
        raise

def list_fetch_runs(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.*, s.name AS site_name
            FROM site_fetch_runs r
            LEFT JOIN managed_sites s ON s.id = r.site_id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

class ApiHandler(BaseHTTPRequestHandler):
    server_version = "LiuhecaiBackend/1.0"

    @property
    def db_path(self) -> Path:
        return self.server.db_path  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        self.dispatch("GET")

    def do_POST(self) -> None:
        self.dispatch("POST")

    def do_PUT(self) -> None:
        self.dispatch("PUT")

    def do_PATCH(self) -> None:
        self.dispatch("PATCH")

    def do_DELETE(self) -> None:
        self.dispatch("DELETE")

    def dispatch(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)

            if method == "GET" and path == "/":
                self.redirect("/admin")
                return
            if method == "GET" and path == "/admin":
                self.send_html(ADMIN_HTML)
                return
            if method == "GET" and path == "/health":
                self.send_json({"status": "ok", "engine": detect_database_engine(self.db_path)})
                return
            if method == "GET" and path == "/api/health":
                self.send_json({"ok": True, "summary": database_summary(self.db_path)})
                return
            if method == "POST" and path == "/api/auth/login":
                body = self.read_json()
                self.send_json(
                    login_user(
                        self.db_path,
                        str(body.get("username") or ""),
                        str(body.get("password") or ""),
                    )
                )
                return
            if method == "GET" and path == "/api/auth/me":
                user = auth_user_from_token(self.db_path, self.bearer_token())
                if not user:
                    self.send_error_json(HTTPStatus.UNAUTHORIZED, "未登录或登录已失效")
                    return
                self.send_json({"user": user})
                return
            if method == "POST" and path == "/api/auth/logout":
                logout_user(self.db_path, self.bearer_token())
                self.send_json({"ok": True})
                return
            if method == "GET" and path == "/api/predict/mechanisms":
                self.send_json({"mechanisms": list_prediction_configs()})
                return
            if path.startswith("/api/predict/") and method in {"GET", "POST"}:
                mechanism = path.split("/")[-1]
                body = self.read_json() if method == "POST" else {}
                self.handle_prediction(mechanism, body, query)
                return

            if method == "GET" and path == "/api/public/site-page":
                site_id = query.get("site_id", [None])[0]
                history_limit = int(query.get("history_limit", ["8"])[0])
                self.send_json(
                    get_public_site_page_data(
                        self.db_path,
                        site_id=int(site_id) if site_id not in (None, "") else None,
                        domain=query.get("domain", [None])[0],
                        history_limit=history_limit,
                    )
                )
                return

            if method == "GET" and path == "/api/public/latest-draw":
                lottery_type = int(query.get("lottery_type", ["1"])[0] or 1)
                self.send_json(
                    get_public_latest_draw(self.db_path, lottery_type)
                )
                return

            if method == "GET" and path == "/api/public/next-draw-deadline":
                lottery_type = int(query.get("lottery_type", ["3"])[0] or 3)
                next_time: str | None = None
                with connect(self.db_path) as conn:
                    row = conn.execute(
                        "SELECT next_time FROM lottery_draws WHERE lottery_type_id = ? AND next_time IS NOT NULL AND next_time != '' ORDER BY year DESC, term DESC LIMIT 1",
                        (lottery_type,),
                    ).fetchone()
                    if row:
                        next_time = str(row["next_time"])
                    else:
                        # 兜底：从 lottery_types 读取
                        lt_row = conn.execute(
                            "SELECT next_time FROM lottery_types WHERE id = ?",
                            (lottery_type,),
                        ).fetchone()
                        if lt_row and lt_row["next_time"]:
                            next_time = str(lt_row["next_time"])
                    self.send_json({
                        "next_time": next_time,
                        "server_time": str(int(time.time())),
                    })
                return

            if method == "GET" and path == "/api/public/draw-history":
                lottery_type = int(query.get("lottery_type", ["3"])[0] or 3)
                year = int(query.get("year", ["0"])[0] or 0) or None
                sort = query.get("sort", ["l"])[0] or "l"
                self.send_json(
                    get_draw_history(self.db_path, lottery_type, year, sort)
                )
                return

            if method == "GET" and path == "/api/legacy/current-term":
                lottery_type_id = int(query.get("lottery_type_id", ["1"])[0] or 1)
                self.send_json(get_legacy_current_term(self.db_path, lottery_type_id))
                return

            if method == "GET" and path == "/api/legacy/post-list":
                pc_raw = query.get("pc", [str(LEGACY_POST_LIST_PC)])[0]
                web_raw = query.get("web", [str(LEGACY_POST_LIST_WEB)])[0]
                type_raw = query.get("type", [str(LEGACY_POST_LIST_TYPE)])[0]
                limit = int(query.get("limit", ["20"])[0] or 20)
                self.send_json(
                    {
                        "data": list_legacy_post_images(
                            self.db_path,
                            source_pc=int(pc_raw) if pc_raw not in (None, "") else None,
                            source_web=int(web_raw) if web_raw not in (None, "") else None,
                            source_type=int(type_raw) if type_raw not in (None, "") else None,
                            limit=limit,
                        )
                    }
                )
                return

            if method == "GET" and path == "/api/legacy/module-rows":
                modes_id = int(query.get("modes_id", ["0"])[0] or 0)
                if modes_id <= 0:
                    raise ValueError("modes_id 必须为正整数")
                web_value = query.get("web", [None])[0]
                type_raw = query.get("type", [None])[0]
                limit = int(query.get("limit", ["10"])[0] or 10)
                self.send_json(
                    load_legacy_mode_rows(
                        self.db_path,
                        modes_id=modes_id,
                        limit=limit,
                        web=int(web_value) if web_value not in (None, "") else None,
                        type_value=int(type_raw) if type_raw not in (None, "") else None,
                    )
                )
                return

            # ── 静态资源：旧站图片 /uploads/image/{bucket}/{filename} ──
            if method == "GET" and path.startswith("/uploads/"):
                self.serve_upload(path)
                return

            if path.startswith("/api/admin/") and not auth_user_from_token(self.db_path, self.bearer_token()):
                self.send_error_json(HTTPStatus.UNAUTHORIZED, "未登录或登录已失效")
                return

            if method == "GET" and path == "/api/admin/users":
                self.send_json({"users": list_users(self.db_path)})
                return
            if method == "GET" and path == "/api/admin/system-config":
                prefix = query.get("prefix", [""])[0]
                include_secrets = query.get("include_secrets", ["0"])[0] in {"1", "true", "True"}
                self.send_json(
                    {
                        "configs": list_system_configs(
                            self.db_path,
                            prefix=prefix,
                            include_secrets=include_secrets,
                        )
                    }
                )
                return
            if method in {"PUT", "PATCH"} and path.startswith("/api/admin/system-config/"):
                config_key = path.split("/api/admin/system-config/", 1)[1].strip()
                body = self.read_json()
                self.send_json(
                    {
                        "config": upsert_system_config(
                            self.db_path,
                            key=config_key,
                            value=body.get("value"),
                            value_type=str(body.get("value_type") or "") or None,
                            description=str(body.get("description") or "") or None,
                            is_secret=body.get("is_secret"),
                        )
                    }
                )
                return
            if method == "POST" and path == "/api/admin/users":
                self.send_json({"user": save_user(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/users/"):
                user_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"user": save_user(self.db_path, self.read_json(), user_id)})
                    return
                if method == "DELETE":
                    delete_user(self.db_path, user_id)
                    self.send_json({"ok": True})
                    return

            if method == "GET" and path == "/api/admin/lottery-types":
                self.send_json({"lottery_types": list_lottery_types(self.db_path)})
                return
            if method == "POST" and path == "/api/admin/lottery-types":
                self.send_json({"lottery_type": save_lottery_type(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            # 仅爬取开奖数据（不生成预测），爬取成功后自动安排 6h 延迟预测任务
            if method == "POST" and re.match(r"^/api/admin/lottery-types/\d+/crawl-only$", path):
                lt_id = int(path.split("/")[4])
                ensure_generation_permission(auth_user_from_token(self.db_path, self.bearer_token()))
                try:
                    result = run_crawl_only(self.db_path, lt_id)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return
            # 爬取指定彩种开奖数据 + 自动生成预测
            if method == "POST" and re.match(r"^/api/admin/lottery-types/\d+/crawl-and-generate$", path):
                lt_id = int(path.split("/")[4])
                ensure_generation_permission(auth_user_from_token(self.db_path, self.bearer_token()))
                job_id = _start_background_job(_crawl_and_generate, self.db_path, lt_id)
                self.send_json({"ok": True, "job_id": job_id, "message": f"彩种 {lt_id} 爬取+生成已放入后台执行"})
                return
            if path.startswith("/api/admin/lottery-types/"):
                lottery_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"lottery_type": save_lottery_type(self.db_path, self.read_json(), lottery_id)})
                    return
                if method == "DELETE":
                    delete_lottery_type(self.db_path, lottery_id)
                    self.send_json({"ok": True})
                    return

            if method == "GET" and path == "/api/admin/draws":
                limit = int(query.get("limit", ["200"])[0])
                self.send_json({"draws": list_draws(self.db_path, limit)})
                return
            if method == "POST" and path == "/api/admin/draws":
                self.send_json({"draw": save_draw(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/draws/"):
                draw_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"draw": save_draw(self.db_path, self.read_json(), draw_id)})
                    return
                if method == "DELETE":
                    delete_draw(self.db_path, draw_id)
                    self.send_json({"ok": True})
                    return

            if method == "POST" and path == "/api/admin/crawler/run-hk":
                try:
                    result = run_hk_crawler(self.db_path)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return
            if method == "POST" and path == "/api/admin/crawler/run-macau":
                try:
                    result = run_macau_crawler(self.db_path)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return
            if method == "POST" and path == "/api/admin/crawler/run-all":
                errors = []
                results = {}
                for _label, _fn in [("hk", run_hk_crawler), ("macau", run_macau_crawler)]:
                    try:
                        results[_label] = _fn(self.db_path)
                    except Exception as e:
                        errors.append(f"{_label}: {e}")
                # Also import Taiwan JSON if available
                _taiwan_json = BACKEND_ROOT / str(
                    get_config(self.db_path, "draw.taiwan_import_file", "data/lottery_data/lottery_page_1_20260506_194209.json")
                )
                if _taiwan_json.exists():
                    try:
                        results["taiwan"] = import_taiwan_json(self.db_path, _taiwan_json)
                    except Exception as e:
                        errors.append(f"taiwan: {e}")
                self.send_json({"results": results, "errors": errors if errors else None})
                return
            if method == "POST" and path == "/api/admin/crawler/import-taiwan":
                _taiwan_json = BACKEND_ROOT / str(
                    get_config(self.db_path, "draw.taiwan_import_file", "data/lottery_data/lottery_page_1_20260506_194209.json")
                )
                if not _taiwan_json.exists():
                    self.send_error_json(HTTPStatus.NOT_FOUND, "台湾彩 JSON 数据文件不存在")
                    return
                try:
                    result = import_taiwan_json(self.db_path, _taiwan_json)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return

            if method == "GET" and path == "/api/admin/numbers":
                limit = int(query.get("limit", ["300"])[0])
                keyword = query.get("keyword", [""])[0]
                self.send_json({"numbers": list_numbers(self.db_path, limit, keyword)})
                return
            if method == "POST" and path == "/api/admin/numbers":
                self.send_json({"number": create_number(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/numbers/"):
                number_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"number": update_number(self.db_path, number_id, self.read_json())})
                    return
                if method == "DELETE":
                    delete_number(self.db_path, number_id)
                    self.send_json({"ok": True})
                    return

            if method == "GET" and path == "/api/admin/sites":
                self.send_json({"sites": list_sites(self.db_path)})
                return
            if method == "POST" and path == "/api/admin/sites":
                self.send_json({"site": save_site(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if method == "GET" and path == "/api/admin/fetch-runs":
                limit = int(query.get("limit", ["20"])[0])
                self.send_json({"runs": list_fetch_runs(self.db_path, limit)})
                return
            if method == "GET" and path == "/api/admin/legacy-images":
                limit = int(query.get("limit", ["50"])[0] or 50)
                self.send_json(
                    {
                        "images": list_legacy_post_images(
                            self.db_path,
                            source_pc=LEGACY_POST_LIST_PC,
                            source_web=LEGACY_POST_LIST_WEB,
                            source_type=LEGACY_POST_LIST_TYPE,
                            limit=limit,
                        )
                    }
                )
                return
            if method == "POST" and path == "/api/admin/normalize":
                result = normalize_payload_tables(self.db_path)
                self.send_json({"normalized_tables": len(result), "tables": result})
                return
            if method == "POST" and path == "/api/admin/text-mappings":
                result = build_text_history_mappings(self.db_path, rebuild=True)
                self.send_json(result)
                return
            if method == "GET" and path.startswith("/api/admin/jobs/"):
                job_id = path.split("/")[-1]
                job = _get_background_job(job_id)
                if job is None:
                    self.send_error_json(HTTPStatus.NOT_FOUND, f"job_id={job_id} 不存在或已过期")
                else:
                    self.send_json(job)
                return
            if method == "GET" and path == "/api/admin/lottery-draws/latest-term":
                qs = parse_qs(urlparse(self.path).query)
                lt_id = int(qs.get("lottery_type_id", ["1"])[0])
                with connect(self.db_path) as conn:
                    row = conn.execute(
                        "SELECT year, term, draw_time FROM lottery_draws WHERE lottery_type_id = ? AND is_opened = 1 ORDER BY year DESC, term DESC LIMIT 1",
                        (lt_id,),
                    ).fetchone()
                    if row:
                        self.send_json({
                            "year": int(row["year"]),
                            "term": int(row["term"]),
                            "draw_time": str(row["draw_time"] or ""),
                        })
                    else:
                        self.send_json({"year": 0, "term": 0, "draw_time": ""})
                return
            if path.startswith("/api/admin/sites/"):
                self.handle_site_detail(method, path)
                return

            # ── 日志管理 API ──────────────────────────────────
            if path == "/api/admin/logs/stats" and method == "GET":
                self.send_json(get_log_stats(self.db_path))
                return
            if path == "/api/admin/logs/cleanup" and method == "POST":
                result = trigger_cleanup()
                self.send_json({"ok": True, **result})
                return
            if path == "/api/admin/logs/export" and method == "GET":
                qs = parse_qs(urlparse(self.path).query)
                rows = export_error_logs(
                    self.db_path,
                    level=qs.get("level", [""])[0],
                    module=qs.get("module", [""])[0],
                    keyword=qs.get("keyword", [""])[0],
                    date_from=qs.get("date_from", [""])[0],
                    date_to=qs.get("date_to", [""])[0],
                )
                self.send_json({"rows": rows, "total": len(rows)})
                return
            if path.startswith("/api/admin/logs/"):
                log_id_str = path.split("/")[-1]
                if log_id_str.isdigit() and method == "GET":
                    detail = get_error_log_detail(self.db_path, int(log_id_str))
                    if detail:
                        self.send_json(detail)
                    else:
                        self.send_error_json(HTTPStatus.NOT_FOUND, f"log_id={log_id_str} 不存在")
                    return
            if path == "/api/admin/logs" and method == "GET":
                qs = parse_qs(urlparse(self.path).query)
                result = query_error_logs(
                    self.db_path,
                    page=int(qs.get("page", ["1"])[0] or 1),
                    page_size=min(int(qs.get("page_size", ["30"])[0] or 30), 200),
                    level=qs.get("level", [""])[0],
                    module=qs.get("module", [""])[0],
                    keyword=qs.get("keyword", [""])[0],
                    date_from=qs.get("date_from", [""])[0],
                    date_to=qs.get("date_to", [""])[0],
                )
                self.send_json(result)
                return

            self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
        except Exception as exc:
            import logging
            logger = logging.getLogger("app.request")
            logger.exception(
                "Request failed: %s %s — %s",
                self.command,
                self.path,
                exc,
                extra={
                    "user_id": (auth_user_from_token(self.db_path, self.bearer_token()) or {}).get("id", ""),
                },
            )
            status = HTTPStatus.BAD_REQUEST
            if isinstance(exc, KeyError):
                status = HTTPStatus.NOT_FOUND
            elif isinstance(exc, PermissionError):
                status = HTTPStatus.FORBIDDEN
            self.send_error_json(status, str(exc), traceback.format_exc())

    def handle_prediction(self, mechanism: str, body: dict[str, Any], query: dict[str, list[str]]) -> None:
        # Active prediction generation mutates operational state expectations even if
        # it does not persist rows directly, so keep this behind the same admin
        # permission boundary as the site-level "run module" action.
        ensure_generation_permission(
            auth_user_from_token(self.db_path, self.bearer_token())
        )

        def pick(name: str, default: Any = None) -> Any:
            if name in body:
                return body[name]
            snake = name.replace("-", "_")
            if snake in body:
                return body[snake]
            return query.get(snake, [default])[0]

        config = get_prediction_config(mechanism)
        default_target_hit_rate = float(
            get_config(self.db_path, "prediction.default_target_hit_rate", 0.65)
        )
        request_payload = {
            "res_code": pick("res_code"),
            "content": pick("content"),
            "source_table": pick("source_table"),
            "target_hit_rate": float(pick("target_hit_rate", default_target_hit_rate)),
            "lottery_type": pick("lottery_type"),
            "year": pick("year"),
            "term": pick("term"),
            "web": pick("web", "4"),
        }
        safety: dict[str, Any] | None = None
        effective_res_code = request_payload["res_code"]
        if (
            request_payload["lottery_type"] not in (None, "")
            and request_payload["year"] not in (None, "")
            and request_payload["term"] not in (None, "")
        ):
            with connect(self.db_path) as conn:
                effective_res_code, safety = resolve_prediction_request_safety(
                    conn,
                    lottery_type=request_payload["lottery_type"],
                    year=request_payload["year"],
                    term=request_payload["term"],
                    res_code=request_payload["res_code"],
                )
        request_payload["res_code"] = effective_res_code
        result = predict(
            config=config,
            res_code=effective_res_code,
            content=request_payload["content"],
            source_table=request_payload["source_table"],
            db_path=self.db_path,
            target_hit_rate=float(request_payload["target_hit_rate"]),
        )
        self.send_json(
            build_prediction_api_response(
                mechanism_key=mechanism,
                request_payload=request_payload,
                raw_result=result,
                safety=safety,
            )
        )

    def handle_site_detail(self, method: str, path: str) -> None:
        parts = path.split("/")
        if len(parts) < 5:
            self.send_error_json(HTTPStatus.NOT_FOUND, "站点接口不存在")
            return
        site_id = int(parts[4])

        if len(parts) == 5:
            if method == "GET":
                self.send_json({"site": get_site(self.db_path, site_id)})
                return
            if method in {"PUT", "PATCH"}:
                self.send_json({"site": save_site(self.db_path, self.read_json(), site_id)})
                return
            if method == "DELETE":
                delete_site(self.db_path, site_id)
                self.send_json({"ok": True})
                return

        if len(parts) == 6 and parts[5] == "fetch" and method == "POST":
            body = self.read_json()
            result = fetch_site_data(
                self.db_path,
                site_id,
                normalize_after=parse_bool(body.get("normalize"), True),
                build_text_mappings_after=parse_bool(body.get("build_text_mappings"), True),
            )
            self.send_json(result)
            return

        # ── mode_payload 直读/直写 ──
        if len(parts) >= 7 and parts[5] == "mode-payload":
            table_name = str(parts[6])
            # handle_site_detail 内部没有 query 变量，从 self.path 重新解析
            mp_query = parse_qs(urlparse(self.path).query)
            query_source = mp_query.get("source", ["public"])[0]

            # GET /sites/{id}/mode-payload/{table}?type=&page=&page_size=&search=
            if len(parts) == 7 and method == "GET":
                query_type = mp_query.get("type", [""])[0]
                query_web = mp_query.get("web", [""])[0]
                query_page = mp_query.get("page", ["1"])[0]
                query_size = mp_query.get("page_size", ["50"])[0]
                query_search = mp_query.get("search", [""])[0]
                self.send_json(
                    list_mode_payload_rows(
                        self.db_path,
                        table_name,
                        type_filter=query_type,
                        web_filter=query_web,
                        page=int(query_page or 1),
                        page_size=int(query_size or 50),
                        search=query_search,
                        source=query_source,
                    )
                )
                return

            # POST /sites/{id}/mode-payload/{table}/regenerate
            if len(parts) == 8 and parts[7] == "regenerate" and method == "POST":
                ensure_generation_permission(
                    auth_user_from_token(self.db_path, self.bearer_token())
                )
                body = self.read_json()
                self.send_json(
                    regenerate_payload_data(
                        self.db_path,
                        table_name=table_name,
                        mechanism_key=str(body.get("mechanism_key", "")),
                        res_code=str(body.get("res_code", "")),
                        lottery_type=str(body.get("lottery_type", "3")),
                        year=str(body.get("year", "")),
                        term=str(body.get("term", "")),
                    )
                )
                return

            # PUT|PATCH /sites/{id}/mode-payload/{table}/{row_id}
            if len(parts) == 8 and parts[7] != "regenerate" and method in {"PUT", "PATCH"}:
                self.send_json(
                    update_mode_payload_row(
                        self.db_path,
                        table_name,
                        parts[7],
                        self.read_json(),
                        source=query_source,
                    )
                )
                return

            # DELETE /sites/{id}/mode-payload/{table}/{row_id}
            if len(parts) == 8 and parts[7] != "regenerate" and method == "DELETE":
                delete_mode_payload_row(
                    self.db_path,
                    table_name,
                    parts[7],
                    source=query_source,
                )
                self.send_json({"ok": True})
                return

        if len(parts) == 6 and parts[5] == "prediction-modules":
            if method == "GET":
                self.send_json(list_site_prediction_modules(self.db_path, site_id))
                return
            if method == "POST":
                self.send_json(
                    {"module": add_site_prediction_module(self.db_path, site_id, self.read_json())},
                    HTTPStatus.CREATED,
                )
                return

        if len(parts) == 7 and parts[5] == "prediction-modules":
            if parts[6] == "generate-all" and method == "POST":
                ensure_generation_permission(
                    auth_user_from_token(self.db_path, self.bearer_token())
                )
                body = self.read_json()
                job_id = _start_background_job(
                    bulk_generate_site_prediction_data,
                    self.db_path,
                    site_id,
                    body,
                )
                self.send_json({
                    "ok": True,
                    "job_id": job_id,
                    "message": "批量生成已放入后台执行，可通过 /api/admin/jobs/{job_id} 查询进度",
                })
                return
            if parts[6] == "run" and method == "POST":
                ensure_generation_permission(
                    auth_user_from_token(self.db_path, self.bearer_token())
                )
                self.send_json(run_site_prediction_module(self.db_path, site_id, self.read_json()))
                return
            if method in {"PUT", "PATCH"}:
                self.send_json(
                    {
                        "module": update_site_prediction_module(
                            self.db_path,
                            site_id,
                            int(parts[6]),
                            self.read_json(),
                        )
                    }
                )
                return
            if method == "DELETE":
                delete_site_prediction_module(self.db_path, site_id, int(parts[6]))
                self.send_json({"ok": True})
                return

        self.send_error_json(HTTPStatus.NOT_FOUND, "站点接口不存在")

    def bearer_token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            return header.split(" ", 1)[1].strip()
        return None

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON body 必须是对象")
        return data

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str, detail: str | None = None) -> None:
        payload = {"ok": False, "error": message}
        if detail:
            payload["detail"] = detail
        self.send_json(payload, status)

    def serve_upload(self, path: str) -> None:
        """Serve legacy image files from backend/data/Images/."""
        filename = Path(path).name
        if not filename:
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        file_path = LEGACY_IMAGES_DIR / filename
        resolved = file_path.resolve()
        if not resolved.is_file() or not resolved.is_relative_to(LEGACY_IMAGES_DIR.resolve()):
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        mime_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        try:
            data = resolved.read_bytes()
        except OSError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", html.escape(location, quote=True))
        self.end_headers()

def run_server(host: str, port: int, db_path: str | Path) -> None:
    ensure_prediction_configs_loaded(db_path)
    ensure_admin_tables(db_path)
    init_logging(str(db_path))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    server.db_path = db_path  # type: ignore[attr-defined]
    print(f"Backend API running at http://{host}:{port}")
    print(f"CMS admin page: http://{host}:{port}/admin")
    print(f"Database engine: {detect_database_engine(db_path)}")
    print(f"Database target: {db_path}")
    # Start background task scheduler (auto-open draws + auto-prediction timers)
    _scheduler = CrawlerScheduler(db_path)
    _scheduler.start()
    try:
        server.serve_forever()
    finally:
        _scheduler.stop()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Liuhecai backend API and Python CMS.")
    parser.add_argument("--host", default=os.environ.get("LOTTERY_API_HOST", "127.0.0.1"), help="HTTP host.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LOTTERY_API_PORT", "8000")), help="HTTP port.")
    parser.add_argument(
        "--db-path",
        default=default_db_target(),
        help="Database target. Accepts a SQLite path or PostgreSQL DSN.",
    )
    return parser

if __name__ == "__main__":
    args = build_parser().parse_args()
    run_server(args.host, args.port, args.db_path)
