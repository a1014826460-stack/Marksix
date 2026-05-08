"""从原始 app.py 重新提取所有模块函数。"""
from pathlib import Path
import re

SRC = Path(__file__).resolve().parent

with open(SRC / '_app_original.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

func_info = {}
for i, line in enumerate(lines):
    m = re.match(r'^(def |class )', line)
    if m:
        name = line.split('(')[0].replace('def ','').replace('class ','').strip()
        func_info[name] = i

func_names = list(func_info.keys())

def get_code(name):
    if name not in func_info:
        return None
    start = func_info[name]
    idx = func_names.index(name)
    end = func_info[func_names[idx+1]] if idx+1 < len(func_names) else len(lines)
    return ''.join(lines[start:end])

# ============== admin/crud.py ==============
CRUD_FUNCS = [
    'list_users', 'save_user', 'delete_user',
    'public_site', 'list_sites', 'get_site', 'save_site', 'delete_site',
    'list_lottery_types', 'save_lottery_type', 'delete_lottery_type',
    'list_draws', 'save_draw', 'delete_draw',
    'list_numbers', 'update_number', 'create_number', 'delete_number',
    'list_site_prediction_modules', 'add_site_prediction_module',
    'update_site_prediction_module', 'delete_site_prediction_module',
    'run_site_prediction_module',
]

CRUD_HEADER = '''"""Admin CRUD 操作 — 用户/站点/彩种/开奖/号码/预测模块管理。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config as app_config
from auth import hash_password
from common import DEFAULT_TARGET_HIT_RATE, predict
from db import connect as db_connect, quote_identifier
from helpers import parse_bool, row_to_dict
from mechanisms import get_prediction_config
from tables import ensure_admin_tables

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)

'''

with open(SRC / 'admin' / 'crud.py', 'w', encoding='utf-8') as f:
    f.write(CRUD_HEADER)
    for name in CRUD_FUNCS:
        code = get_code(name)
        if code:
            f.write('\n')
            f.write(code)
        else:
            print(f"  MISSING crud: {name}")
print(f"crud.py: {sum(1 for n in CRUD_FUNCS if get_code(n))} functions")

# ============== admin/prediction.py ==============
PRED_FUNCS = [
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

PRED_HEADER = '''"""Admin 预测管理 — 模块同步/生成/批量操作/安全控制。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PREDICT_ROOT = Path(__file__).resolve().parents[1] / "predict"
_UTILS_ROOT = Path(__file__).resolve().parents[1] / "utils"
for _p in (_PREDICT_ROOT, _UTILS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from common import DEFAULT_TARGET_HIT_RATE, predict  # noqa: E402
from db import connect as db_connect, quote_identifier
from helpers import (
    apply_lottery_draw_overlay, load_fixed_data_maps, normalize_issue_part,
    parse_issue_int, split_csv,
)
from mechanisms import get_prediction_config, list_prediction_configs  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
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

with open(SRC / 'admin' / 'prediction.py', 'w', encoding='utf-8') as f:
    f.write(PRED_HEADER)
    for name in PRED_FUNCS:
        code = get_code(name)
        if code:
            f.write('\n')
            f.write(code)
        else:
            print(f"  MISSING pred: {name}")
print(f"prediction.py: {sum(1 for n in PRED_FUNCS if get_code(n))} functions")
