"""临时：提取 public/api.py 和 legacy/api.py 的函数体。"""
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

def get_func_code(name):
    if name not in func_info:
        return None
    start = func_info[name]
    idx = func_names.index(name)
    end = func_info[func_names[idx+1]] if idx+1 < len(func_names) else len(lines)
    return ''.join(lines[start:end])

# public/api.py functions
public_names = [
    'extract_special_result', 'summarize_prediction_text',
    '_check_prediction_correct', 'serialize_public_history_row',
    'load_public_module_history', 'resolve_public_site',
    'load_public_draw_snapshot', 'get_public_site_page_data',
    'get_public_latest_draw',
]

# Append to public/api.py
with open(SRC / 'public' / 'api.py', 'a', encoding='utf-8') as f:
    for name in public_names:
        code = get_func_code(name)
        if code:
            f.write('\n')
            f.write(code)
            print(f"  + {name}")
        else:
            print(f"  MISSING: {name}")

# Create legacy/api.py
legacy_header = '''"""旧站兼容 API — post-list / current-term / module-rows。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PREDICT_ROOT = Path(__file__).resolve().parents[1] / "predict"
if str(_PREDICT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PREDICT_ROOT))

from helpers import (
    build_mode_payload_filters, build_mode_payload_order_clause, load_fixed_data_maps,
    merge_preferred_mode_payload_rows, load_mode_payload_rows_from_source,
    normalize_issue_part, parse_issue_int, split_csv,
)
from mechanisms import get_prediction_config  # noqa: E402
'''

legacy_names = [
    'list_legacy_post_images', 'get_legacy_current_term', 'load_legacy_mode_rows',
]

with open(SRC / 'legacy' / 'api.py', 'w', encoding='utf-8') as f:
    f.write(legacy_header)
    for name in legacy_names:
        code = get_func_code(name)
        if code:
            f.write('\n')
            f.write(code)
            print(f"  + {name}")
        else:
            print(f"  MISSING: {name}")

print("Done")
