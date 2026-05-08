"""最终清理脚本：从 app.py 移除已迁移的函数定义，添加模块导入。"""
from pathlib import Path
import re

SRC = Path(__file__).resolve().parent

# 所有已从 app.py 移走的函数名
EXTRACTED_FUNCS = {
    # helpers.py
    'split_csv', 'normalize_issue_part', 'parse_issue_int', 'sql_safe_int_expr',
    'build_mode_payload_order_clause', 'build_mode_payload_filters',
    'load_fixed_data_maps', 'build_draw_result_payload', 'load_lottery_draw_map',
    'apply_lottery_draw_overlay', 'build_mode_payload_row_key',
    'merge_preferred_mode_payload_rows', 'load_mode_payload_rows_from_source',
    'color_name_to_key', 'row_to_dict', 'parse_bool',
    # auth.py
    'hash_password', 'verify_password', 'public_user', 'login_user',
    'auth_user_from_token', 'ensure_generation_permission', 'logout_user',
    # tables.py
    'default_db_target', 'connect', 'ensure_column', 'ensure_admin_tables',
    'sync_legacy_image_assets', 'database_summary',
    # admin/crud.py
    'public_site', 'list_sites', 'get_site', 'save_site', 'delete_site',
    'list_users', 'save_user', 'delete_user', 'list_lottery_types',
    'save_lottery_type', 'delete_lottery_type', 'list_draws', 'save_draw',
    'delete_draw', 'list_numbers', 'update_number', 'create_number',
    'delete_number', 'list_site_prediction_modules', 'add_site_prediction_module',
    'update_site_prediction_module', 'delete_site_prediction_module',
    'run_site_prediction_module',
    # admin/prediction.py
    'get_site_prediction_module_blueprints', 'get_site_prediction_module_blueprint_by_key',
    'sync_site_prediction_modules', 'build_generated_prediction_row_data',
    'normalize_prediction_display_text', 'lookup_draw_visibility',
    'redact_prediction_result_fields', 'apply_prediction_row_safety',
    'resolve_prediction_request_safety', 'build_prediction_api_response',
    'parse_issue_range_value', 'list_opened_draws_in_issue_range',
    'bulk_generate_site_prediction_data', 'regenerate_payload_data',
    # admin/payload.py
    'validate_mode_payload_table', 'normalize_mode_payload_source',
    'mode_payload_table_exists', 'mode_payload_table_columns',
    'build_admin_mode_payload_filters', 'sort_mode_payload_rows',
    'fetch_mode_payload_source_rows', 'normalize_mode_payload_row_id',
    'list_mode_payload_rows', 'update_mode_payload_row', 'delete_mode_payload_row',
    # public/api.py
    'extract_special_result', 'summarize_prediction_text',
    '_check_prediction_correct', 'serialize_public_history_row',
    'load_public_module_history', 'resolve_public_site',
    'load_public_draw_snapshot', 'get_public_site_page_data', 'get_public_latest_draw',
    # legacy/api.py
    'list_legacy_post_images', 'get_legacy_current_term', 'load_legacy_mode_rows',
}

with open(SRC / 'app.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Find all function boundaries
func_starts = {}  # name -> line index (0-based)
for i, line in enumerate(lines):
    m = re.match(r'^(def |class )', line)
    if m:
        name = line.split('(')[0].replace('def ','').replace('class ','').strip()
        func_starts[name] = i

func_names = list(func_starts.keys())

# Build ranges to remove
ranges_to_remove = []
for name in EXTRACTED_FUNCS:
    if name in func_starts:
        start = func_starts[name]
        idx = func_names.index(name)
        end = func_starts[func_names[idx+1]] if idx+1 < len(func_names) else len(lines)
        ranges_to_remove.append((start, end))

# Sort by start position descending to remove from bottom up
ranges_to_remove.sort(key=lambda x: -x[0])

# Remove blocks
for start, end in ranges_to_remove:
    del lines[start:end]

# Rebuild content
content = '\n'.join(lines)

# Remove multiple blank lines
content = re.sub(r'\n{3,}', '\n\n', content)

with open(SRC / 'app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Removed {len(ranges_to_remove)} function blocks")
print(f"Remaining lines: {len(lines)}")

# Check which extracted funcs were NOT found
not_found = [n for n in EXTRACTED_FUNCS if n not in func_starts]
if not_found:
    print(f"NOT FOUND (may already be removed): {not_found}")
