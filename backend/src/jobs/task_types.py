"""后台任务类型常量定义。

所有 job 的 metadata 必须包含：
site_id, web_id, lottery_type_id, year, term, task_type, created_by
"""

from __future__ import annotations

# ── 任务类型常量 ──────────────────────────────────────
TASK_TYPE_CRAWL_HK = "crawl_hk"
TASK_TYPE_CRAWL_MACAU = "crawl_macau"
TASK_TYPE_CRAWL_AND_GENERATE = "crawl_and_generate"
TASK_TYPE_AUTO_OPEN_DRAW = "auto_open_draw"
TASK_TYPE_AUTO_PREDICTION = "auto_prediction"
TASK_TYPE_MANUAL_PREDICTION = "manual_prediction"
TASK_TYPE_SITE_FETCH = "site_fetch"
TASK_TYPE_NORMALIZE_PAYLOAD = "normalize_payload"
TASK_TYPE_BUILD_TEXT_MAPPINGS = "build_text_mappings"

# ── 任务状态常量 ──────────────────────────────────────
TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_DONE = "done"
TASK_STATUS_ERROR = "error"
TASK_STATUS_CANCELLED = "cancelled"

# ── 后台任务 metadata key ────────────────────────────
JOB_METADATA_KEYS = (
    "site_id",
    "web_id",
    "lottery_type_id",
    "year",
    "term",
    "task_type",
    "task_key",
    "created_by",
)
