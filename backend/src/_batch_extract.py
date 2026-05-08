"""批量从 app.py 提取函数到目标模块。使用方式: python _batch_extract.py"""
from pathlib import Path
import re

SRC = Path(__file__).resolve().parent

with open(SRC / 'app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all function boundaries
func_info = {}
for i, line in enumerate(lines):
    m = re.match(r'^(def |class )', line)
    if m:
        name = line.split('(')[0].replace('def ','').replace('class ','').strip()
        func_info[name] = i

func_names = list(func_info.keys())

def get_func_range(name):
    if name not in func_info:
        return None, None
    start = func_info[name]
    idx = func_names.index(name)
    end = func_info[func_names[idx+1]] if idx+1 < len(func_names) else len(lines)
    return start, end

def get_func_code(name):
    s, e = get_func_range(name)
    if s is None:
        return None
    return ''.join(lines[s:e])

# ===========================================
# admin/crud.py
# ===========================================
crud_funcs = [
    'public_site', 'list_sites', 'get_site', 'save_site', 'delete_site',
    'list_users', 'save_user', 'delete_user',
    'list_lottery_types', 'save_lottery_type', 'delete_lottery_type',
    'list_draws', 'save_draw', 'delete_draw',
    'list_numbers', 'update_number', 'create_number', 'delete_number',
    'list_site_prediction_modules', 'add_site_prediction_module',
    'update_site_prediction_module', 'delete_site_prediction_module',
    'run_site_prediction_module',
]

crud_header = '''"""Admin CRUD 操作 — 用户/站点/彩种/开奖/号码/预测模块管理。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db import connect as db_connect, quote_identifier
from helpers import parse_bool, row_to_dict

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)

'''

# ===========================================
# admin/prediction.py
# ===========================================
pred_funcs = [
    'get_site_prediction_module_blueprints',
    'get_site_prediction_module_blueprint_by_key',
    'sync_site_prediction_modules',
    'build_generated_prediction_row_data',
    'normalize_prediction_display_text',
    'lookup_draw_visibility',
    'redact_prediction_result_fields',
    'apply_prediction_row_safety',
    'resolve_prediction_request_safety',
    'build_prediction_api_response',
    'parse_issue_range_value',
    'list_opened_draws_in_issue_range',
    'bulk_generate_site_prediction_data',
    'regenerate_payload_data',
]

pred_header = '''"""Admin 预测管理 — 模块同步/生成/批量操作/安全控制。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import DEFAULT_TARGET_HIT_RATE, predict
from db import connect as db_connect, quote_identifier
from helpers import (
    apply_lottery_draw_overlay, load_fixed_data_maps, normalize_issue_part,
    parse_issue_int, split_csv,
)
from mechanisms import get_prediction_config, list_prediction_configs
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME, created_table_exists, normalize_color_label,
    quote_qualified_identifier as quote_schema_table,
    schema_table_exists, table_column_names, upsert_created_prediction_row,
)

REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12, 20, 28, 31, 34, 38, 42, 43,
    44, 45, 46, 49, 50, 51, 52, 53, 54, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66,
    67, 68, 69, 151, 197,
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)

'''

# ===========================================
# public/api.py
# ===========================================
public_funcs = [
    'extract_special_result',
    'summarize_prediction_text',
    '_check_prediction_correct',
    'serialize_public_history_row',
    'load_public_module_history',
    'resolve_public_site',
    'load_public_draw_snapshot',
    'get_public_site_page_data',
    'get_public_latest_draw',
]

# ===========================================
# legacy/api.py
# ===========================================
legacy_funcs = [
    'list_legacy_post_images',
    'get_legacy_current_term',
    'load_legacy_mode_rows',
]

# ===========================================
# crawler functions (keep in tables.py or app.py)
# ===========================================
crawler_funcs = [
    'create_fetch_run', 'finish_fetch_run', 'fetch_site_data', 'list_fetch_runs',
]

print("Functions available:", len(func_names))
for name in crud_funcs:
    if name not in func_info:
        print(f"  MISSING CRUD: {name}")
for name in pred_funcs:
    if name not in func_info:
        print(f"  MISSING PRED: {name}")
for name in public_funcs:
    if name not in func_info:
        print(f"  MISSING PUBLIC: {name}")
for name in legacy_funcs:
    if name not in func_info:
        print(f"  MISSING LEGACY: {name}")

# Write crud.py
with open(SRC / 'admin' / 'crud.py', 'w', encoding='utf-8') as f:
    f.write(crud_header)
    for name in crud_funcs:
        code = get_func_code(name)
        if code:
            f.write(code)
    print(f"crud.py written")

# Write prediction.py
with open(SRC / 'admin' / 'prediction.py', 'w', encoding='utf-8') as f:
    f.write(pred_header)
    for name in pred_funcs:
        code = get_func_code(name)
        if code:
            f.write(code)
    print(f"prediction.py written")

print("Done")
