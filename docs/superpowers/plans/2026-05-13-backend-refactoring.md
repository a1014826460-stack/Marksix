# Backend/src 规范化分层重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持现有功能可用、接口尽量兼容的前提下，将 backend/src 整理成清晰的分层架构。

**Architecture:** 采用分层架构：core(基础设施) → database(数据库) → http(HTTP框架) → routes(路由适配) → domains(业务领域) → predict_engine(预测算法) → jobs(后台任务)。每层有明确职责边界，routes不写SQL，domains封装业务逻辑，repository封装数据访问。

**Tech Stack:** Python stdlib, ThreadingHTTPServer, PostgreSQL (psycopg2), 自定义Router

**关键约束:**
- `db.py` 已存在，因此数据库层使用 `database/` 目录名避免冲突
- 不引入新Web框架，保持当前架构
- `web_id` 是多站点隔离的核心标识
- 禁止硬编码 `web=4`
- predict/mechanisms.py 不大规模拆分

---

## 当前已完成项（不需要重复做）

- `http/router.py` - Router 已存在
- `http/request_context.py` - RequestContext 已存在
- `http/response.py` - ResponseWriter 已存在
- `http/site_context.py` - SiteContext 已存在
- `http/auth.py` - HTTP层鉴权已存在
- `routes/` - 大部分路由模块已存在
- `tables.py` - PostgreSQL-only schema 已存在
- `prediction_generation/service.py` - 预测生成服务已存在

---

### Task 1: 第一阶段 - 完善开发规范文件 (CLAUDE.md)

**Files:**
- Modify: `backend/CLAUDE.md`

- [ ] **Step 1: 更新 CLAUDE.md 包含完整的开发规范**

将现有的简化版 CLAUDE.md 扩展为包含数据库、多站点、路由、业务层、预测、配置、日志、测试等完整规范的版本。按照 Prompt 第四节的模板进行扩展。

---

### Task 2: 第二阶段 - 建立 core/ 层

**Files:**
- Create: `backend/src/core/__init__.py`
- Create: `backend/src/core/errors.py`
- Create: `backend/src/core/time_utils.py`
- Create: `backend/src/core/constants.py`

- [ ] **Step 1: 创建 core/__init__.py**

```python
# core/ 基础设施层：统一异常、时间工具、全局常量
```

- [ ] **Step 2: 创建 core/errors.py - 统一异常类型**

```python
"""统一业务异常类型，后续 routes 和 service 优先抛这些异常。"""

class AppError(Exception):
    """业务异常基类"""
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str = "", status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

class NotFoundError(AppError):
    """资源不存在"""
    status_code = 404
    code = "NOT_FOUND"

class UnauthorizedError(AppError):
    """未认证"""
    status_code = 401
    code = "UNAUTHORIZED"

class ForbiddenError(AppError):
    """无权限"""
    status_code = 403
    code = "FORBIDDEN"

class ValidationError(AppError):
    """参数校验失败"""
    status_code = 400
    code = "VALIDATION_ERROR"

class ConflictError(AppError):
    """资源冲突（如重复创建）"""
    status_code = 409
    code = "CONFLICT"
```

- [ ] **Step 3: 创建 core/time_utils.py - 统一时间工具**

从 `db.py` 中提取 `utc_now()` 逻辑，从 `helpers.py` 中提取开奖时间处理逻辑，统一放在这里。

- [ ] **Step 4: 创建 core/constants.py - 全局常量**

集中定义 `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`, `BEIJING_TIMEZONE`, `CREATED_SCHEMA_NAME` 等常量。

- [ ] **Step 5: 验证 py_compile 通过**

Run: `python -m py_compile backend/src/core/*.py`

---

### Task 3: 第三阶段 - 建立 database/ 层（拆分 tables.py）

**注意:** 使用 `database/` 目录名而非 `db/`，因为 `db.py` 已存在。

**Files:**
- Create: `backend/src/database/__init__.py`
- Create: `backend/src/database/connection.py`
- Create: `backend/src/database/bootstrap.py`
- Create: `backend/src/database/summary.py`
- Create: `backend/src/database/seed.py`
- Create: `backend/src/database/migrations.py`
- Create: `backend/src/database/schema/__init__.py`
- Create: `backend/src/database/schema/auth.py`
- Create: `backend/src/database/schema/lottery.py`
- Create: `backend/src/database/schema/sites.py`
- Create: `backend/src/database/schema/prediction.py`
- Create: `backend/src/database/schema/scheduler.py`
- Create: `backend/src/database/schema/logs.py`
- Create: `backend/src/database/schema/config.py`
- Create: `backend/src/database/schema/legacy.py`
- Create: `backend/src/database/schema/indexes.py`
- Modify: `backend/src/tables.py` (兼容导出入口)

- [ ] **Step 1: 创建 database/__init__.py 和 connection.py**

从 `db.py` 和 `tables.py` 中提取连接相关逻辑：`default_db_target()`, `resolve_database_target()`, `is_postgres_target()`。

- [ ] **Step 2: 创建 database/schema/ 各文件**

将 `tables.py` 中的建表 helper 按领域拆分到对应的 schema 文件：
- `schema/auth.py`: admin_users 表
- `schema/lottery.py`: lottery_types, lottery_draws 表
- `schema/sites.py`: managed_sites, site_prediction_modules 表
- `schema/prediction.py`: created schema 相关
- `schema/scheduler.py`: scheduler_tasks 表
- `schema/logs.py`: error_logs 表
- `schema/config.py`: system_config 表
- `schema/legacy.py`: 旧站兼容表
- `schema/indexes.py`: 索引创建

- [ ] **Step 3: 创建 database/bootstrap.py**

将 `tables.py` 中的 `ensure_admin_tables()` 迁移为调用各 schema 文件的总入口。

- [ ] **Step 4: 创建 database/seed.py**

将 `tables.py` 中的默认数据播种逻辑（默认管理员、默认彩种、默认站点）迁移到 seed.py。

- [ ] **Step 5: 创建 database/summary.py 和 migrations.py**

从 `tables.py` 中提取 `database_summary()` 和 `add_column_if_missing()`。

- [ ] **Step 6: 更新 tables.py 为兼容导出入口**

```python
# tables.py - 兼容导出入口，逐步迁移到 database/ 包
from database.bootstrap import ensure_admin_tables
from database.summary import database_summary
from database.migrations import add_column_if_missing
# ... 其他兼容导出
```

- [ ] **Step 7: 验证 py_compile 通过**

Run: `python -m py_compile backend/src/database/*.py` and `python -m py_compile backend/src/database/schema/*.py`

---

### Task 4: 第四阶段 - 完善 http/ 层

**Files:**
- Modify: `backend/src/http/request_context.py` (确保完整性)
- Modify: `backend/src/http/site_context.py` (完善 resolve/validate 逻辑)
- Modify: `backend/src/http/auth.py` (完善权限分级)

- [ ] **Step 1: 审计并完善 RequestContext**

确保 `RequestContext` 包含 method, path, query, body, db_path, user, request_id, handler 等字段。

- [ ] **Step 2: 审计并完善 SiteContext**

确保 `resolve_site_context_from_request()`, `validate_web_matches_site()`, `require_site_access()` 完整实现。

规则：
1. 路径中的 site_id 是权威来源
2. query/body 中的 web/web_id 必须等于当前站点 web_id
3. 找不到站点时返回明确错误
4. 禁止静默默认 web=4

- [ ] **Step 3: 完善 http/auth.py 权限分级**

实现 `require_admin(ctx)`, `require_generation_permission(ctx)`, `require_site_access(ctx, site_id)` 并预留 site_admin/operator/viewer 角色。

- [ ] **Step 4: 验证 py_compile 通过**

---

### Task 5: 第五阶段 - 审计并规范 routes/ 层

**Files:**
- 审计: 所有 `backend/src/routes/*.py` 文件
- 重点检查: `admin_site_routes.py` 和 `admin_payload_routes.py` 路由冲突

- [ ] **Step 1: 检查所有 routes 文件中是否存在直接写复杂 SQL 的情况**

逐个检查 routes 文件，确保它们只做：解析HTTP参数、鉴权、调用domain service、返回JSON。

- [ ] **Step 2: 检查路由冲突**

检查 `/api/admin/sites/{site_id}/mode-payload/...` 是否会被 `/api/admin/sites/` 大前缀遮挡。

- [ ] **Step 3: 修复发现的问题**

如果发现 SQL 在 routes 中，提取到对应的 admin/ 或 service 模块。
如果发现路由冲突，修复 router 注册顺序或使用更精确的 regex。

---

### Task 6: 第六阶段 - 建立 domains/ 层

**Files:**
- Create: `backend/src/domains/__init__.py`
- Create: `backend/src/domains/sites/__init__.py`
- Create: `backend/src/domains/sites/models.py`
- Create: `backend/src/domains/sites/repository.py`
- Create: `backend/src/domains/sites/service.py`
- Create: `backend/src/domains/sites/permissions.py`
- Create: `backend/src/domains/lottery/__init__.py`
- Create: `backend/src/domains/lottery/models.py`
- Create: `backend/src/domains/lottery/repository.py`
- Create: `backend/src/domains/lottery/service.py`
- Create: `backend/src/domains/lottery/draw_time.py`
- Create: `backend/src/domains/prediction/__init__.py`
- Create: `backend/src/domains/prediction/models.py`
- Create: `backend/src/domains/prediction/repository.py`
- Create: `backend/src/domains/prediction/service.py`

- [ ] **Step 1: 创建 domains/sites/ 领域**

从 `admin/crud.py` 中提取站点相关函数：`list_sites()`, `get_site()`, `save_site()`, `delete_site()`。
在 repository 中封装站点相关的 SQL 查询。
在 service 中封装站点业务逻辑。
在 permissions 中封装站点权限判断。

- [ ] **Step 2: 创建 domains/lottery/ 领域**

从 `admin/crud.py` 和 `public/api.py` 中提取开奖相关函数。
在 repository 中封装开奖数据的 SQL 查询。
在 service 中封装开奖业务逻辑。
在 draw_time.py 中封装开奖时间计算。

- [ ] **Step 3: 创建 domains/prediction/ 领域**

封装预测模块管理、预测生成等业务逻辑。
调用现有的 `prediction_generation/service.py`。

- [ ] **Step 4: 更新 routes 层调用新的 domains**

将 routes 中的调用从直接调 `admin/crud.py` 逐步改为调 `domains/*/service.py`。

- [ ] **Step 5: 保持旧模块兼容导出**

```python
# admin/crud.py 保留兼容导出
from domains.sites.service import list_sites, get_site, save_site, delete_site
from domains.lottery.service import list_lottery_types, ...
```

---

### Task 7: 第七阶段 - 清理 predict/ 和 prediction_generation/

**Files:**
- Modify: `backend/src/predict/common.py` (print → logger)
- Modify: `backend/src/predict/mechanisms.py` (print → logger, db_path → db_target)
- Modify: `backend/src/prediction_generation/service.py` (消除 web=4 硬编码)

- [ ] **Step 1: 清理 predict/ 中的 print 语句**

将所有 `print()` 改为 `logger.info()` / `logger.debug()`。

- [ ] **Step 2: 清理 SQLite 注释和类型误导**

检查并清理 predict/ 中的 SQLite 相关注释。

- [ ] **Step 3: db_path 命名改为 db_target**

在 predict/ 中统一参数命名。

- [ ] **Step 4: 确保 prediction_generation 不硬编码 web=4**

检查并确保所有 created row 写入使用正确的 SiteContext.web_id。

---

### Task 8: 第八阶段 - 建立 jobs/ 层

**Files:**
- Create: `backend/src/jobs/__init__.py`
- Create: `backend/src/jobs/task_types.py`
- Create: `backend/src/jobs/handlers.py`
- Modify: `backend/src/routes/common.py` (提取后台任务逻辑)

- [ ] **Step 1: 创建 jobs/task_types.py**

定义任务类型枚举和 metadata 结构。

- [ ] **Step 2: 创建 jobs/handlers.py**

从 `routes/common.py` 中提取 `start_background_job()`, `get_background_job()` 等逻辑。

- [ ] **Step 3: 更新 routes/common.py 为兼容导出**

---

### Task 9: 第九阶段 - 测试和验证

**Files:**
- Create: `backend/src/tests/__init__.py`
- Create: `backend/src/tests/unit/__init__.py`
- Create: `backend/src/tests/integration/__init__.py`
- Create: `backend/src/tests/fixtures/__init__.py`
- Create: `backend/src/tests/unit/test_site_context.py`
- Create: `backend/src/tests/unit/test_router.py`
- Create: `backend/src/tests/integration/test_tables_bootstrap.py`

- [ ] **Step 1: 创建 SiteContext 单元测试**
- [ ] **Step 2: 创建 Router 单元测试**
- [ ] **Step 3: 创建 Schema bootstrap 集成测试**
- [ ] **Step 4: 运行全量 py_compile 验证**
- [ ] **Step 5: 手动验证关键 API 端点**
