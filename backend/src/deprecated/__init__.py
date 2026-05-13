"""deprecated/ — 已废弃的一次性脚本和兼容层。

本目录存放不再需要但保留备查的脚本：
- normalize_sqlite.py: 旧 SQLite 兼容包装（已由 normalize_payload_tables 替代）
- tools/generate_missing_types.py: 一次性 type=1/2 数据生成脚本
- tools/repair_created_mode_payload_197.py: mode_payload_197 一次修复脚本
- tools/fill_empty_mode_payload_tables_from_fetched_records.py: 一次性回填脚本
- tools/fill_missing_type3_web4_samples_from_fetched_records.py: 一次性回填脚本

这些脚本保留仅供历史参考，不应在新代码中引用。
"""
