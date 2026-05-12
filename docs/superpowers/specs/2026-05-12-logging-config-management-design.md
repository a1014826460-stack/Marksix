# 日志管理 & 配置信息管理 — 设计文档

2026-05-12

## 概述

在现有彩票后台管理系统中，以增量方式新增两个管理板块：
1. **日志管理** — 统一查看、筛选、导出系统日志
2. **配置信息管理** — 统一查看、修改、记录系统配置变更

严格遵循现有项目架构，不进行大规模重构。

---

## 一、日志管理设计

### 1.1 数据源

- **主数据源**: `error_logs` 表（`logger.py:DatabaseLogHandler` 已实现 ERROR 级别入库）
- **文件日志**: `backend/data/logs/app.log`（JSON 格式，RotatingFileHandler）
- **日志统计**: `logger.py:get_log_stats()` 已提供

### 1.2 后端增强

#### 1.2.1 扩展 `error_logs` 表字段（`tables.py`）

需要添加以下列以支持业务维度筛选：
```
site_id, web_id, lottery_type_id, year, term,
task_key, task_type, request_path, request_method
```

使用 `ensure_column()` 轻量迁移模式，保证兼容旧数据。

#### 1.2.2 增强 `query_error_logs()` 筛选参数（`logger.py`）

新增 query 参数支持：
```
user_id, site_id, web_id, lottery_type_id, year, term,
task_type, task_key, path (请求路径)
```

返回结构保持不变但增加 `available_levels` 和 `available_modules`。

#### 1.2.3 新增 API

```
GET /api/admin/logs/modules   → 返回所有已记录的模块名列表
GET /api/admin/logs/levels    → 返回所有已记录的日志等级列表
```

现有 API 不变，仅在 query 参数上扩展。

### 1.3 前端页面

文件: `backend/app/logs/page.tsx`

页面结构：
- 筛选区（等级、模块、时间范围、关键词、用户ID、站点ID、彩种ID）
- 日志表格（时间、等级、模块、消息、用户、站点、彩种、期号、任务、耗时）
- 分页
- 详情抽屉/弹窗（完整 message、stack trace、原始 JSON）
- 导出按钮

组件位置: `@/components/admin/management-pages` 中新增 `LogsPageClient`

### 1.4 核心模块日志增强

检查并在关键路径（爬虫、调度器、预测生成）中增加结构化日志，确保 `module`、`task_key`、`site_id` 等上下文字段完整。

---

## 二、配置信息管理设计

### 2.1 配置来源及优先级

1. **环境变量** — 部署环境敏感配置（数据库DSN等）
2. **数据库 system_config 表** — 运行时可修改配置（管理员通过后台修改）
3. **config.yaml** — 默认值和初始化兜底

页面展示时标注 `source` 字段：`database` | `config.yaml` | `environment` | `computed`

### 2.2 后端增强

#### 2.2.1 新增 `system_config_history` 表（`tables.py`）

```sql
CREATE TABLE system_config_history (
    id SERIAL PRIMARY KEY,
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TEXT NOT NULL,
    change_reason TEXT,
    source TEXT DEFAULT 'admin'
)
```

#### 2.2.2 增强 `upsert_system_config()` — 自动记录变更历史

修改配置时记录 old_value → new_value 到 `system_config_history`。

#### 2.2.3 新增 API

```
GET  /api/admin/configs/groups           → 返回配置分组列表
GET  /api/admin/configs/effective        → 返回运行中实际生效的配置值
POST /api/admin/configs/batch-update     → 批量更新配置
POST /api/admin/configs/{key}/reset      → 恢复单个配置为默认值
GET  /api/admin/configs/{key}/history    → 查看单个配置的变更历史
GET  /api/admin/configs/history          → 查看所有配置变更历史
```

#### 2.2.4 配置值校验

- `int`: 必须是整数，部分需要正整数
- `float`: 必须是浮点数
- `bool`: 只能是 true/false
- `string`: 任意字符串
- `json`: 合法 JSON
- `time`: HH:mm 格式
- `duration_seconds`: 正整数秒数

### 2.3 配置分组

| 分组 | 配置项前缀 | 说明 |
|------|-----------|------|
| lottery | draw.* | 彩种开奖时间、采集URL |
| scheduler | crawler.auto_*, crawler.task_* | 调度器循环时间 |
| prediction | prediction.* | 预测资料生成 |
| site | site.* | 站点默认配置 |
| logging | logging.* | 日志保留、轮转 |
| auth | auth.* | 认证配置 |
| system | admin.*, legacy.* | 系统级配置 |

### 2.4 前端页面

文件: `backend/app/configs/page.tsx`

页面结构：
- 配置分组 Tabs
- 搜索框 + 来源筛选
- 配置表格（配置项、当前值、默认值、类型、来源、说明、可编辑、需重启、最后修改时间）
- 编辑弹窗（根据类型使用不同输入控件）
- 批量保存 / 恢复默认
- 变更历史入口

组件位置: `@/components/admin/management-pages` 中新增 `ConfigsPageClient`

---

## 三、侧边栏更新

在 `admin-shell.tsx` 的 `menuItems` 中添加：
- `{ icon: FileText, label: "日志管理", href: "/logs" }`
- `{ icon: Settings, label: "配置管理", href: "/configs" }`

---

## 四、不做的范围

- 不修改 config.yaml 的结构和字段
- 不修改 `lottery_draws` 表结构
- 不修改预测生成逻辑
- 不修改现有爬虫逻辑
- 不增加第三方依赖

---

## 五、文件清单

### 后端修改
| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/src/tables.py` | 修改 | 新增 `system_config_history` 表，扩展 `error_logs` 字段 |
| `backend/src/logger.py` | 修改 | 增强 `query_error_logs()` 筛选，新增辅助查询函数 |
| `backend/src/runtime_config.py` | 修改 | 增强 `upsert_system_config()` 记录历史，新增配置 API 函数 |
| `backend/src/app.py` | 修改 | 新增日志和配置相关 API 路由 |

### 前端新增/修改
| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/components/admin/admin-shell.tsx` | 修改 | 添加菜单项 |
| `backend/components/admin/management-pages.tsx` | 修改 | 新增 `LogsPageClient` 和 `ConfigsPageClient` |
| `backend/app/logs/page.tsx` | 新增 | 日志管理页面 |
| `backend/app/configs/page.tsx` | 新增 | 配置管理页面 |

### 文档更新
| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/README_CN.md` | 修改 | 新增日志/配置板块说明 |
