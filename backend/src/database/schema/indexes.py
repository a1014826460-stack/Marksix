"""性能关键索引的创建（幂等，IF NOT EXISTS）。"""

from __future__ import annotations

from typing import Any


def ensure_indexes(conn: Any) -> None:
    """创建所有性能关键索引，每个语句均为幂等（IF NOT EXISTS）。

    在 ``ensure_admin_tables`` 中所有表就绪后调用。
    """
    _idx_sql = "CREATE INDEX IF NOT EXISTS"

    # ── 开奖数据 ──
    conn.execute(
        f"""{_idx_sql} idx_lottery_draws_type_opened_issue
           ON lottery_draws (lottery_type_id, is_opened, year DESC, term DESC)"""
    )

    # ── 托管站点 ──
    conn.execute(
        f"""{_idx_sql} idx_managed_sites_domain
           ON managed_sites (domain)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_managed_sites_enabled
           ON managed_sites (enabled)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_managed_sites_web_id
           ON managed_sites (web_id)"""
    )

    # ── 站点预测模块 ──
    conn.execute(
        f"""{_idx_sql} idx_site_prediction_modules_site_status_sort
           ON site_prediction_modules (site_id, status, sort_order)"""
    )

    # ── 调度器任务 ──
    conn.execute(
        f"""{_idx_sql} idx_scheduler_tasks_status_run_at
           ON scheduler_tasks (status, run_at)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_scheduler_tasks_scope_status_run_at
           ON scheduler_tasks (schedule_scope, status, run_at)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_scheduler_tasks_business_ctx
           ON scheduler_tasks (site_id, web_id, lottery_type_id, year, term)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_scheduler_task_runs_task_id
           ON scheduler_task_runs (task_id, id DESC)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_scheduler_task_runs_type_status_started
           ON scheduler_task_runs (task_type, status, started_at DESC)"""
    )

    # ── 错误日志 ──
    conn.execute(
        f"""{_idx_sql} idx_error_logs_created_level_module
           ON error_logs (created_at DESC, level, module)"""
    )
    conn.execute(
        f"""{_idx_sql} idx_error_logs_business_ctx
           ON error_logs (site_id, web_id, lottery_type_id, year, term)"""
    )

    # ── 配置变更历史 ──
    conn.execute(
        f"""{_idx_sql} idx_system_config_history_key_changed
           ON system_config_history (config_key, changed_at DESC)"""
    )
