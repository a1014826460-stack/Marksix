"""全局常量集中定义。

把散落在各模块中的常量统一放在这里，
避免重复定义和冲突。
"""

from __future__ import annotations

# ── 分页默认值 ──────────────────────────────────────
DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 500

# ── 时区 ────────────────────────────────────────────
# 北京时区标识，供需要字符串引用的场景使用
BEIJING_TIMEZONE_NAME = "Asia/Shanghai"

# ── 数据库 schema 名称 ──────────────────────────────
CREATED_SCHEMA_NAME = "created"
PUBLIC_SCHEMA_NAME = "public"

# ── 预测相关常量 ────────────────────────────────────
# 三肖三色特殊模式 ID（三期特殊号处理）
THREE_PERIOD_SPECIAL_MODE_ID = 197

# 前端需要的站点预测模块 mode_id 清单，按展示顺序排列
REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12, 20, 28, 31, 34, 38, 42, 43,
    44, 45, 46, 49, 50, 51, 52, 53, 54, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66,
    67, 68, 69, 108, 151, 197,
)

# ── 数据表名称 ──────────────────────────────────────
CONFIG_TABLE_NAME = "system_config"

# ── 彩种 ID ─────────────────────────────────────────
LOTTERY_TYPE_HK = 1      # 香港彩
LOTTERY_TYPE_MACAU = 2   # 澳门彩
LOTTERY_TYPE_TAIWAN = 3  # 台湾彩

# ── 默认开奖时间 ────────────────────────────────────
DEFAULT_HK_DRAW_TIME = "21:30"
DEFAULT_MACAU_DRAW_TIME = "21:30"
DEFAULT_TAIWAN_DRAW_TIME = "22:30"
