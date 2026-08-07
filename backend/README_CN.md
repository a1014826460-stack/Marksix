# Liuhecai 后端管理系统 README

## 概述

该后端是一个轻量级的管理后台和 API 服务，用于彩票数据管理、开奖数据采集、预测生成、日志记录，以及旧版前端兼容。

当前运行架构使用两层配置：

1. `DATABASE_URL` / 启动参数 / `runtime_config.py` 中的引导默认值  
   作为启动期配置来源，使服务能够启动并连接 PostgreSQL。

2. `system_config` 表  
   作为运行时大多数常量和运维参数的真实配置来源。

运行时会优先读取数据库中的配置；如果某个配置项缺失，或数据库不可用，则回退到 `runtime_config.py` 中的默认值。数据库连接目标本身仍需通过 `DATABASE_URL` 或启动参数提供。

## 高可用数据库端点

本地开发继续只配置 `DATABASE_URL`，读写均回退到该端点。高可用应用节点可由部署平台 Secret 注入：

- `DATABASE_WRITE_URL`：托管 PostgreSQL 的稳定写端点；优先于 `DATABASE_URL`。
- `DATABASE_READ_URL`：托管 PostgreSQL 的稳定只读端点；未配置时回退到写端点。
- `LIUHECAI_DATABASE_MODE=managed`：只允许生产运行时使用非 loopback 的托管端点；默认 `compose` 保持当前 `pgbouncer:6432` 保护。

不要把任何真实 DSN 写入仓库、根 `.env`、日志或健康检查响应。当前阶段只建立端点和健康检查契约；公共读取尚未切换到只读端点。

## Redis 公共读取缓存

公共开奖快照可使用 Redis 作为可丢弃的读取缓存，PostgreSQL 仍是开奖事实源：

- 开发环境未设置 `CACHE_BACKEND` 时使用进程内 `memory` 缓存，无需 Redis。
- 生产环境必须设置 `CACHE_BACKEND=redis` 与由部署 Secret 注入的 `REDIS_URL`；`memory` 会在启动时被拒绝。
- Redis 客户端只在实际读写时连接，并使用短连接/操作超时；故障会以缓存不可用处理，不能影响开奖事实写入。
- 版本化发布先写不可变数据键，再以原子事务更新指针，避免读取到半成品快照。

不要把真实 Redis URL 写入仓库、根 `.env`、日志或健康检查响应。

## 站点预测模块授权

- `site_prediction_modules` 中 `status=1` 的行是站点预测资料的唯一运行时授权来源。
- 站点私有 API 的站点身份由 URL 路径确定，query 中的 `site_id`、`web`、`web_id` 不能跨站覆盖。
- 站点 4-8 的蓝图目标来自 `domains.prediction.site_page_dependencies`：它只收录当前前端可访问页面的精确数据源；注释脚本、孤立静态文件与未调用的旧元数据不会授权生成模块。
- 模块的内部生成保障分为 `controlled_future`（已有已验证命中规则）、`history_only`（可展示历史但未来期不宣称受控正确率）和 `blocked`（没有精确数据源）。这些内部状态不会加入任何 API 响应。
- 站点 4-8 的模块集可用以下命令审计；先执行 PostgreSQL versioned migration，再加 `--apply`。`--apply` 只停用蓝图外行或启用缺失蓝图行，不删除历史数据：

```powershell
Push-Location backend/src
python -m database.versioned_migrations --db-path "<DATABASE_URL>"
Pop-Location
python backend/scripts/reconcile_site_prediction_modules.py --db-path "<DATABASE_URL>" --site-ids 4,5,6,7,8
python backend/scripts/reconcile_site_prediction_modules.py --db-path "<DATABASE_URL>" --site-ids 4,5,6,7,8 --apply
```

- 禁用模块保持现有 API 空结果格式，避免影响 legacy 前端解析。

---

## src/ 分层架构

重构后的 `backend/src/` 采用清晰的分层架构，各层职责明确：

```
backend/src/
├── main.py                         # 规范入口（canonical entry）
├── app.py                          # 兼容入口（薄壳，转发到 main/app_http）
├── tables.py                       # 兼容导出 → database/
├── db.py                           # 数据库适配器（SQLite/PostgreSQL 双引擎）
│
├── core/                           # 基础设施层
│   ├── errors.py                   # 统一异常类型 (AppError/NotFoundError/...)
│   ├── time_utils.py               # UTC/北京时间/开奖时间处理
│   └── constants.py                # 全局常量
│
├── database/                       # 数据库层（避免与 db.py 冲突）
│   ├── connection.py               # 连接管理
│   ├── bootstrap.py                # ensure_admin_tables 总入口
│   ├── seed.py                     # 默认数据播种
│   ├── migrations.py               # 轻量列迁移
│   ├── versioned_migrations.py     # PostgreSQL 显式版本化迁移账本
│   ├── summary.py                  # 数据库内容摘要
│   └── schema/                     # 按领域拆分的建表文件
│       ├── auth.py                 # admin_users / admin_sessions
│       ├── lottery.py              # lottery_types / lottery_draws
│       ├── sites.py                # managed_sites / site_fetch_runs
│       ├── prediction.py           # site_prediction_modules
│       ├── scheduler.py            # scheduler_tasks
│       ├── logs.py                 # error_logs
│       ├── config.py               # system_config_history
│       ├── legacy.py               # legacy_image_assets
│       └── indexes.py              # 性能索引
│
├── app_http/                       # HTTP 框架层
│   ├── request_context.py          # 请求上下文（含 request_id、body 缓存）
│   ├── router.py                   # 轻量 URL 路由 + 分发
│   ├── auth.py                     # HTTP 层鉴权（require_admin 等）
│   ├── site_context.py             # 多站点上下文解析（SiteContext）
│   └── response.py                 # 响应写入（JSON/HTML/文件）
│
├── routes/                         # 路由适配层（薄层）
│   ├── auth_routes.py              # /api/auth/*
│   ├── public_routes.py            # /api/public/*
│   ├── admin_site_routes.py        # /api/admin/sites/*
│   ├── admin_lottery_routes.py     # /api/admin/lottery-types/*
│   ├── admin_payload_routes.py     # /api/admin/sites/{id}/mode-payload/*
│   ├── admin_prediction_routes.py  # /api/predict/*
│   └── ... (其他路由模块)
│
├── domains/                        # 业务领域层
│   ├── sites/                      # 站点领域
│   │   ├── models.py               # ManagedSite 领域模型
│   │   ├── repository.py           # 站点 SQL 查询
│   │   ├── service.py              # 站点业务逻辑（直接实现）
│   │   └── permissions.py          # 角色权限（5级角色体系）
│   ├── lottery/                    # 彩种领域
│   │   ├── models.py               # LotteryType/LotteryDraw 模型
│   │   ├── repository.py           # 彩种/开奖 SQL 查询
│   │   ├── service.py              # 彩种业务逻辑
│   │   └── draw_time.py            # 开奖时间计算工具
│   ├── prediction/                 # 预测领域
│   │   ├── models.py               # PredictionModule/GenerationContext
│   │   ├── repository.py           # 预测模块 SQL 查询
│   │   └── service.py              # 预测业务逻辑
│   ├── configs/                    # 配置领域
│   │   ├── repository.py           # system_config SQL 查询
│   │   └── service.py              # 配置管理业务逻辑
│   ├── logs/                       # 日志领域
│   │   ├── repository.py           # error_logs SQL 查询
│   │   └── service.py              # 日志业务逻辑
│   ├── scheduler/                  # 调度任务领域
│   │   ├── repository.py           # scheduler_tasks / scheduler_task_runs SQL 查询
│   │   └── service.py              # 任务入队、抢占、运行记录、执行生命周期、重试状态
│   └── legacy/                     # 旧站兼容领域
│       └── service.py              # 旧版 API 业务逻辑
│
├── predict_engine/                 # 预测引擎层（纯算法）
│   ├── __init__.py                 # 从 predict/ 重导出
│   ├── registry.py                 # 机制注册表
│   ├── runner.py                   # 预测运行器
│   └── mechanisms/                 # 机制子模块（待拆分）
│
├── predict/                        # 预测算法（原有实现，逐步迁移到 predict_engine/）
│   ├── common.py                   # 核心预测算法
│   ├── mechanisms.py               # 所有机制定义
│   └── run_prediction.py           # CLI 入口
│
├── jobs/                           # 后台任务层
│   ├── task_types.py               # 任务类型/状态常量
│   └── handlers.py                 # 内存任务管理 + 抓取运行记录
│
└── tests/                          # 测试目录
    ├── unit/                       # 单元测试（无需数据库，47 个）
    └── integration/                # 集成测试（需要 PostgreSQL）
```

### 各层职责边界

| 层级 | 职责 | 禁止 |
|------|------|------|
| **core/** | 统一异常、时间工具、全局常量 | 不感知业务/HTTP/数据库 |
| **database/** | 连接管理、Schema 定义、播种、迁移 | 不写业务逻辑 |
| **app_http/** | HTTP 适配、路由分发、鉴权、SiteContext | 不写 SQL |
| **routes/** | 参数解析、鉴权调用、JSON 返回 | 不写复杂 SQL/业务细节 |
| **domains/** | 业务逻辑（service）、数据访问（repository） | repository 写 SQL，service 不写 |
| **predict_engine/** | 预测算法 | 不感知 HTTP/用户/站点权限 |
| **jobs/** | 后台任务调度、运行记录 | 不处理 HTTP |

### web_id 与 site_id 的关系

- `web_id` 是站点业务 ID（对应旧资料表中的 `web` 字段）
- `managed_sites.id` 是后台内部主键
- `managed_sites.web_id` 是多站点隔离的核心标识
- **禁止硬编码 `web=4`**
- 所有站点相关接口必须先解析 `SiteContext`
- 禁止通过 query/body 中的 `web` 参数跨站点读取或写入资料

### 新增代码规范

- **SQL 只能写在**: `domains/*/repository.py`、`database/`、`utils/created_prediction_store.py`
- **业务逻辑放在**: `domains/*/service.py`
- **新接口路由放在**: `routes/` 对应模块
- **数据库 schema 变更放在**: `database/schema/` 对应文件

---

## 启动流程

规范入口：

```txt
backend/src/main.py
```

兼容入口 `backend/src/app.py` 仍可启动服务，但内部会直接转发到 `backend/src/app_http/server.py` 中的唯一服务实现。

本地通过 `restart-backend.ps1` 启动时，还会一并启动后台管理界面（`3002`）。

启动顺序：

1. 从 `DATABASE_URL` 或配置中的 PostgreSQL DSN 解析正式运行数据库目标。
2. 先执行 `python -m database.versioned_migrations --db-path "$env:DATABASE_URL"`；Docker Compose 会由 `db-migrate` 服务执行同一命令并持有 PostgreSQL advisory lock。
3. API/worker 的 `ensure_admin_tables()` 只校验 `schema_migrations` 账本，不会在启动或请求路径执行结构性 DDL。
4. 调用 `init_logging()` 启用结构化文件日志和基于数据库的错误日志。
5. 启动 HTTP 服务及独立的 `scheduler-worker`；worker 持有租约后负责 timer 生命周期。

重要限制：

`scheduler-worker` 持有数据库租约后运行 `CrawlerScheduler`；持久化任务表负责可恢复的手动任务、预测、备份和台湾精准开盘，香港/澳门的精确检查仍使用 worker 内存 timer。不得运行多个活跃 worker；失去租约必须停止 timer。

---

## 测试

### 单元测试（无需数据库）

```powershell
cd backend/src
python -m pytest tests/unit/ -v
```

测试覆盖：
- `test_errors.py` — 统一异常类型（9 tests）
- `test_site_context.py` — 站点上下文解析和权限校验（15 tests）
- `test_router.py` — 路由注册、匹配和分发（9 tests）
- `test_time_utils.py` — 时间工具函数（5 tests）
- `test_predict_common.py` — 预测引擎纯函数（8 tests）

### 集成测试（需要 PostgreSQL）

```powershell
# 使用专用测试数据库
$env:TEST_DATABASE_URL = "postgresql://postgres:password@localhost:5432/liuhecai_test"
cd backend/src
python -m pytest tests/integration/ -v

# 如在正式数据库上测试（需明确授权）
$env:ALLOW_TEST_ON_PROD_DB = "1"
python -m pytest tests/integration/ -v
```

测试覆盖：
- `test_tables_bootstrap.py` — 表初始化幂等、web_id 回填、索引存在、上下文字段
- `test_prediction_generation.py` — 站点 web_id 隔离、SiteContext 解析正确性

---

## 经验教训与排查守则

这部分用于记录真实排查过程中踩过的坑，避免后续重复犯错。

### 1. `8000` 不是废弃入口

当前项目中，`8000` 端口对应的 Python 服务是正式入口，不是废弃接口。

- 规范入口文件：`backend/src/main.py`
- 兼容入口文件：`backend/src/app.py`
- 默认监听端口：`8000`
- 前端 `3000` 的旧站兼容接口最终会转发到这里
- Docker / Nginx / 健康检查也都依赖该端口

因此，看到 `127.0.0.1:3000/api/kaijiang/*` 返回异常时，不能只查前端，还必须同步检查 `8000` 的 Python 进程和真实响应。

### 2. 先验证“运行中的进程”，再相信磁盘代码

一次典型误判是：

- 磁盘上的 `backend/src/legacy/api.py` 已经恢复正常
- 但 `8000` 上实际监听的旧 Python 进程仍在运行旧逻辑
- 结果表现为：文件内容和接口返回不一致

因此遇到“代码看起来对，但接口仍然不对”时，排查顺序必须固定为：

1. 查端口监听进程是谁
2. 查该进程的启动命令
3. 直接请求真实 HTTP 接口验证返回
4. 最后才去判断是不是代码逻辑问题

建议命令：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } | Select-Object ProcessId,CommandLine
```

### 3. 排查时不要同时拉起多个 Python 后端

如果本机同时存在多个 `python backend/src/main.py` 或 `python backend/src/app.py` 进程，会导致：

- 很难确认当前到底是哪一个在响应 `8000`
- 旧进程可能继续占用端口，返回过期逻辑
- 前端 `3000` 看起来“像是没更新”，实际是请求打到了旧服务

排查或重启前应先确认：

- 当前 `8000` 是谁在监听
- 是否已经存在旧进程
- 是否真的需要重启

如果需要重启，应先停止旧进程，再启动新进程，而不是直接再开一个。

### 4. 排查顺序：先只读，后写入

推荐顺序：

1. 查路由映射
2. 查代理目标
3. 查监听进程
4. 打真实接口
5. 最后才改代码、改配置、重启服务

不要在尚未确认真实响应链路之前，直接修改兼容逻辑或数据源优先级逻辑，否则很容易扩大影响范围。

### 5. 回退前先确认文件是否受 Git 管理

有些工具脚本或临时文件并不在 Git 跟踪中。  
这类文件无法通过 `git checkout -- file` 精确恢复，只能依赖：

- IDE 本地历史
- 手工备份
- 重新生成

因此在修改前，最好先确认：

```powershell
git ls-files -- backend/src/utils/import_lottery_data.py
```

如果没有输出，说明该文件不在 Git 跟踪内，改动前应先额外备份。

---

## 核心数据表

关键表包括：

- `admin_users`：管理员账号
- `admin_sessions`：登录会话和过期时间
- `managed_sites`：被管理站点的元数据与 `web_id` 隔离配置；旧版爬虫字段不再保留
- `site_fetch_runs`：站点采集执行记录
- `lottery_types`：彩票元数据、开奖时间、数据源 URL、自动化状态
- `lottery_draws`：开奖记录和开奖状态
- `site_prediction_modules`：每个站点启用的预测模块
- `legacy_image_assets`：旧版图片映射
- `error_logs`：持久化错误日志
- `system_config`：集中式运行时配置

---

## 认证与授权

文件：

```txt
backend/src/auth.py
```

机制：

- 密码使用 `PBKDF2-SHA256` 存储。
- 哈希迭代次数来自 `auth.password_iterations`。
- 登录会在 `admin_sessions` 中创建 session token。
- Session 过期时间来自 `auth.session_ttl_seconds`。
- 过期或格式错误的 session 会在访问时被删除。

主要函数：

- `hash_password()`
- `verify_password()`
- `login_user()`
- `auth_user_from_token()`
- `logout_user()`
- `ensure_generation_permission()`

授权规则：

- 所有 `/api/admin/*` 接口都需要有效的 bearer token。
- 主动触发预测生成需要 `admin` 或 `super_admin` 角色。

---

## CRUD 数据流程

路由层（routes/）只负责 HTTP 适配，业务逻辑在 domains/ 层。

文件：

- `backend/src/routes/` — HTTP 路由处理器（薄层）
- `backend/src/domains/sites/service.py` — 站点业务逻辑
- `backend/src/domains/lottery/service.py` — 彩种业务逻辑
- `backend/src/domains/prediction/service.py` — 预测业务逻辑
- `backend/src/admin/crud.py` — 兼容导出（委托给 domains/）
- `backend/src/admin/payload.py` — mode_payload 管理
- `backend/src/admin/prediction.py` — 预测生成与安全

典型流程：

1. HTTP 请求进入 `ApiHandler.dispatch()` → `Router.dispatch()`
2. 路由根据需要执行认证（`app_http/auth.py`）
3. 站点相关接口解析 `SiteContext`（`app_http/site_context.py`）
4. 请求体由 `RequestContext.read_json()` 解析
5. routes 调用 `domains/*/service.py` 中的业务函数
6. service 通过 `domains/*/repository.py` 执行 SQL
7. 数据以 JSON 形式返回

站点管理 CRUD：

- `list_sites()`
- `get_site()`
- `save_site()`
- `delete_site()`

彩票 CRUD：

- `list_lottery_types()`
- `save_lottery_type()`
- `delete_lottery_type()`
- `list_draws()`
- `save_draw()`
- `delete_draw()`

台湾彩开奖记录补充规则：

- 通过 `save_draw()` 新增台湾彩新一期记录时，系统会在同一事务内检查新增前的最后一期记录。
- 如果该记录没有更晚一期数据，且 `next_time` 仍等于它自己的 `draw_time`（占位值），系统会自动把它的 `next_time` 回填为新一期记录的 `draw_time`。
- 如果不存在符合条件的记录，则仅新增当前记录，不执行额外更新。

用户 CRUD：

- `list_users()`
- `save_user()`
- `delete_user()`

预测模块 CRUD：

- `list_site_prediction_modules()`
- `add_site_prediction_module()`
- `update_site_prediction_module()`
- `delete_site_prediction_module()`

---

## 校验与错误处理

校验逻辑主要在业务层函数中实现，而不是只放在 HTTP handler 中。

统一异常类型（`core/errors.py`）：

| 异常类型 | HTTP 状态码 | 使用场景 |
|---------|------------|---------|
| `AppError` | 400 | 通用业务异常基类 |
| `NotFoundError` | 404 | 资源不存在 |
| `UnauthorizedError` | 401 | 未认证 |
| `ForbiddenError` | 403 | 无权限 |
| `ValidationError` | 400 | 参数校验失败 |
| `ConflictError` | 409 | 资源冲突/重复创建 |

示例：

- `save_site()` 会校验名称、web id 范围，以及 URL 模板占位符。
- `regenerate_payload_data()` 会校验表名、期号、年份和 `res_code` 格式。
- `bulk_generate_site_prediction_data()` 会校验期号范围顺序。
- `auth_user_from_token()` 会校验 session 过期时间和 token 可用性。

错误处理策略：

- 业务函数优先抛出 `core.errors` 中的统一异常类型。
- `Router.dispatch()` 捕获 `AppError` 及其子类，自动映射为对应 HTTP 状态码的 JSON 响应。
- `KeyError` 和 `PermissionError` 也有兼容映射（→ 404 / 403）。
- 请求异常会通过 `logger.exception(...)` 记录。
- 数据库日志持久化失败不会中断主要业务流程。

---

## 调度器、开奖与爬虫

文件：

```txt
backend/src/crawler/scheduler.py
backend/src/domains/scheduler/service.py
backend/src/domains/scheduler/repository.py
```

说明：

- `backend/src/crawler/crawler_service.py` 当前是兼容导出层
- `CrawlerScheduler` 的真实实现位于 `backend/src/crawler/scheduler.py`
- `backend/src/crawler/tasks.py` 当前是兼容门面，调度任务表读写已委托到 `domains/scheduler`
- `domains/scheduler/service.py` 负责 `scheduler_tasks` / `scheduler_task_runs` 的任务入队、抢占锁、运行记录、执行生命周期、完成和失败重试状态

职责：

- 自动开奖：对 `draw_time` 已经过期的奖期执行开奖。
- 精准调度台湾每日开奖。
- 自动采集香港和澳门开奖数据。
- 开奖数据采集后，延迟自动生成预测。
- 精确调度 HK/Macau 开奖前 1 秒期号检查（含重试和告警）。

当前调度器模型：

- `CrawlerScheduler.start()`
- `_schedule_auto_open()`
- `_schedule_auto_crawl()`
- `_schedule_taiwan_precise_open()`
- `domains.scheduler.service.acquire_due_scheduler_tasks()` 使用任务表状态和 `locked_at` 超时机制抢占到期任务
- `domains.scheduler.service.create_scheduler_task_run()` / `finish_scheduler_task_run()` 记录单次任务执行历史
- `domains.scheduler.service.run_due_scheduler_tasks()` 统一编排任务抢占、执行回调、运行记录写入、成功完成和失败重试状态
- `CrawlerScheduler._run_due_tasks()` 只提供任务执行回调和失败告警回调，不再直接维护 `scheduler_tasks` / `scheduler_task_runs` 生命周期

重要限制：

- 任务表读写和执行生命周期已经迁入 `domains/scheduler`，但主调度循环、具体任务执行规则仍在 `crawler/scheduler.py`。
- 当前仍不是完整的分布式任务系统；多实例部署前，还需要继续收敛 `crawler/scheduler.py` 中剩余 SQL 和调度规则，并补齐数据库级锁/幂等边界。

关键运维配置：

- `crawler.auto_open_interval_seconds`
- `crawler.auto_crawl_interval_seconds`
- `crawler.auto_crawl_recent_minutes`
- `crawler.taiwan_precise_open_hour`
- `crawler.taiwan_precise_open_minute`
- `crawler.taiwan_retry_delays_seconds`
- `crawler.taiwan_max_retries`
- `crawler.auto_prediction_delay_hours`

数据源规则：

- 香港数据源 URL 来自 `lottery_types.collect_url`，启动默认值为 `draw.hk_default_collect_url`。
- 澳门数据源 URL 来自 `lottery_types.collect_url`，启动默认值为 `draw.macau_default_collect_url`。
- **台湾彩数据由管理后台手工录入，不再使用爬虫自动导入。**

爬虫 HTTP 容错配置：

- `crawler.http_timeout_seconds`
- `crawler.http_retry_count`
- `crawler.http_retry_delay_seconds`

相关文件：

- `backend/src/crawler/HK_history_crawler.py`
- `backend/src/crawler/Macau_history_crawler.py`
- `backend/src/crawler/scheduler.py`

### 精确开奖期号检查（HK / Macau）

- 调度器在每次 `next_time` 同步后，从 `system_config` 读取 `lottery.hk_next_time` 和 `lottery.macau_next_time`。
- 在距离该时间点 **前 1 秒**，自动向对应彩票的开奖号码查询接口发送 HTTP 请求。
- 检查返回的期号是否等于 `system_config` 中该彩种的 `current_period` + 1（即预期下一期期号）。
- 期号匹配：记录日志，不做额外操作。
- 期号不匹配：每 2 秒重试一次，最多重试 3 次（共 4 次请求）。每次重试前重新读取 `next_time` 以应对时间变动。
- 全部重试失败后触发告警，写入 `error_logs` 表，可在日志管理页面查看。
- 检查完毕或 next_time 更新后，自动重新调度下一次检查。

### `current_period` / `current_year` 字段

每个彩种在 `system_config` 中维护以下字段，由调度器自动同步：

| 配置项 | 说明 |
|--------|------|
| `lottery.hk_current_period` | 香港彩当前期号（如 2026001） |
| `lottery.hk_current_year` | 香港彩当前年份 |
| `lottery.macau_current_period` | 澳门彩当前期号 |
| `lottery.macau_current_year` | 澳门彩当前年份 |
| `lottery.taiwan_current_period` | 台湾彩当前期号（由管理后台手工录入） |
| `lottery.taiwan_current_year` | 台湾彩当前年份（由管理后台手工录入） |

这些字段在爬虫成功写入新开奖数据后自动更新，确保始终反映最新已开奖期号。

### 开奖时间与 `next_time` 同步规则

- 香港彩与澳门彩（`lottery_type_id IN (1, 2)`）的下一次开奖时间，唯一权威来源是爬虫落库到 `lottery_draws.next_time` 的值。
- 后端不再对香港彩、澳门彩使用 `draw_time + 固定天数` 的方式推导 `next_time`。
- `lottery_types.next_time` 在香港彩、澳门彩场景下只是同步缓存字段，真实基准始终是“最新已开奖期”的 `lottery_draws.next_time`。
- 台湾彩（`lottery_type_id = 3`）继续保留现有推导逻辑，用最近已开奖期的 `draw_time` 派生下一期开奖时间。

同步与修复时机：

- 爬虫每次成功写入香港彩或澳门彩当期数据后，会立即把该彩种在 `lottery_types.next_time` 中的值同步为最新已开奖期的 `lottery_draws.next_time`。
- `CrawlerScheduler.start()` 启动时会执行一次全量同步检查，修复服务停机期间可能遗留的 `lottery_types.next_time` 漂移问题。
- 自动采集调度 `_auto_crawl()` 每轮结束后还会执行一次低频同步，作为运行期自愈机制，避免缓存值与最新开奖记录脱节。

告警日志：

- 如果系统发现 `lottery_types.next_time` 与“最新已开奖期”对应的权威 `next_time` 不一致，会通过 `next_time.sync` logger 记录 `warning` 日志。
- 日志会带上 `source`、`lottery_type_id`、`stored`、`effective`、`current_issue`、`next_issue`，用于定位是启动同步、爬虫写入还是后台 CRUD 场景触发了修正。

---

## 预测生成

预测链路涉及三个层：

1. **算法层**（`predict/` 和 `predict_engine/`）— 纯算法，不感知 HTTP/用户/站点
2. **业务层**（`domains/prediction/`）— 站点、期号、模块、created 表写入
3. **生成层**（`prediction_generation/`）— 批量生成编排

入口：

- 公共预测 API：`routes/admin_prediction_routes.py`
- 批量生成：`domains/prediction/service.py::bulk_generate_site_predictions`
- 共享生成器：`prediction_generation/service.py::generate_prediction_batch`
- 延迟自动化：`crawler/scheduler.py::_run_auto_prediction`

预测安全机制：

文件：

```txt
backend/src/admin/prediction.py
```

安全函数：

- `lookup_draw_visibility()`
- `resolve_prediction_request_safety()`
- `apply_prediction_row_safety()`
- `redact_prediction_result_fields()`

含义：

- 如果某一期还没有开奖，那么请求侧传入的 `res_code` 不会被信任，不能用于历史开奖结果可见性判断。
- 对于未开奖期数，响应中的 `res_code`、`res_sx`、`res_color` 等字段可以被隐藏。

未来预测与历史回填：

- 已开奖的历史数据从 `lottery_draws` 读取。
- 未来期数由 `future_periods` 创建。
- 历史回填可以使用 `res_code`（已开奖期数）
- **未来预测资料生成不能注入真实开奖结果**
- 延迟自动化流程只负责把真实开奖结果回填到已创建的预测行中，不负责立即生成下一期预测。
- 下一期预测由 `daily_prediction` 定时任务统一处理。
- `daily_prediction` 在自动补近期缺失资料时，只允许补“缺失的站点/模块/期数”，不会自动覆盖已有预测正文。
- 管理员手工“批量生成 / 重新生成”仍保留覆盖能力，这是显式人工操作，不属于自动化保护范围。

重要运行配置：

- `prediction.default_target_hit_rate`
- `prediction.max_terms_per_year`

---

## 站点数据采集

文件：

- `backend/src/utils/data_fetch.py`
- `backend/src/routes/common.py::fetch_site_data`

流程：

1. 从站点管理页面获取 mode 列表。
2. 分页获取 mode 数据。
3. 持久化 `fetched_modes` 和 `fetched_mode_records`。
4. 可选执行数据规范化。
5. 可选重建文本历史映射。
6. 将执行状态记录到 `site_fetch_runs`。

采集运行审计字段：

- `status`
- `message`
- `modes_count`
- `records_count`
- `started_at`
- `finished_at`

---

## 审计与日志

文件：

```txt
backend/src/logger.py
```

能力：

- 带轮转的 JSON 文件日志。
- `ERROR` 及以上级别日志持久化到 `error_logs` 数据库表。
- 通过装饰器记录慢调用耗时日志。
- 后台清理过期数据库日志和超出大小限制的日志文件。

关键函数：

- `init_logging()`
- `log_execution()`
- `query_error_logs()`
- `get_error_log_detail()`
- `export_error_logs()`
- `get_log_stats()`
- `trigger_cleanup()`

运行配置：

- `logging.max_file_size_mb`
- `logging.backup_count`
- `logging.error_retention_days`
- `logging.warn_retention_days`
- `logging.info_retention_days`
- `logging.max_total_log_size_mb`
- `logging.cleanup_interval_seconds`
- `logging.slow_call_warning_ms`

健康检查接口：

- `/health`
- `/api/health`

---

## 系统配置管理

运行时配置存储：

- 启动期数据库目标：`DATABASE_URL` 或 `main.py` / `app.py` 的 `--db-path`
- 启动期默认值：`backend/src/runtime_config.py`
- 运行时配置：`system_config`

核心文件：

```txt
backend/src/runtime_config.py
```

函数：

- `ensure_system_config_table()`、`seed_system_config_defaults()`：仅供 SQLite bootstrap 或 PostgreSQL 显式版本化迁移调用；API、worker 和请求路径不得调用。
- `get_config()`
- `get_config_from_conn()`
- `list_system_configs()`
- `upsert_system_config()`

管理后台 API：

- `GET /api/admin/system-config`
- `PUT /api/admin/system-config/{key}`
- `PATCH /api/admin/system-config/{key}`

设计说明：

数据库连接的启动参数不能只存在数据库中。

因此 PostgreSQL DSN 仍然需要从环境变量 `DATABASE_URL` 或启动参数中读取；运行时普通配置则由 `system_config` 与 `runtime_config.py` 默认值共同提供。

`created.mode_payload_*` 镜像表同样只会在显式版本化迁移中按 `public.mode_payload_*` 的实际表集合与 `mode_payload_tables` 元数据并集进行创建或对齐。预测生成、API 和 worker 不会在运行时建表或补列；若发现缺失镜像，应先执行迁移命令。

---

## 日志管理

页面入口：后台侧边栏 → "日志管理"（`/logs`）

### 功能概述

日志管理板块用于统一查看和分析系统运行日志，帮助快速定位问题。

### 数据来源

- **error_logs 表**：ERROR 及以上级别日志自动入库（由 `DatabaseLogHandler` 实现）
- **文件日志**：`backend/data/logs/app.log`（JSON 格式，带轮转）
- **日志统计**：`GET /api/admin/logs/stats`

### 筛选能力

| 筛选维度 | 说明 |
|---------|------|
| 日志等级 | ERROR / WARNING / INFO / DEBUG / CRITICAL |
| 模块 | 支持模糊匹配，下拉列表由实际数据动态填充 |
| 关键词 | 匹配消息内容、异常类型、异常消息、堆栈跟踪 |
| 时间范围 | 支持 datetime-local 精确到分钟 |
| 用户ID | 精确匹配 |
| 站点ID | 精确匹配 |
| 彩种 | 香港彩(1) / 澳门彩(2) / 台湾彩(3) |

### API 接口

```
GET  /api/admin/logs           → 日志列表（分页 + 多维筛选）
GET  /api/admin/logs/{id}      → 日志详情（含完整堆栈）
GET  /api/admin/logs/modules   → 已记录的模块名列表
GET  /api/admin/logs/levels    → 已记录的日志等级列表
GET  /api/admin/logs/stats     → 日志统计（总数、24h 新增、文件大小）
GET  /api/admin/logs/export    → 导出 CSV
POST /api/admin/logs/cleanup   → 手动触发日志清理
```

### 日志表结构

`error_logs` 表包含以下业务上下文字段（部分为扩展字段）：

```
site_id, web_id, lottery_type_id, year, term,
task_key, task_type, request_path, request_method,
user_id, duration_ms, request_params, stack_trace
```

---

## 配置信息管理

页面入口：后台侧边栏 → "配置管理"（`/configs`）

### 功能概述

配置信息管理板块用于统一查看和修改系统运行配置，所有修改操作自动记录变更历史。

### 配置来源与优先级

1. **环境变量**（最高优先级）— 主要用于数据库连接等敏感部署配置
2. **数据库 system_config 表** — 管理员通过后台页面可修改的运行配置
3. **`runtime_config.py` 默认值** — 默认值和初始化兜底

运行时优先级：先读数据库 `system_config`，缺失时回退到 `runtime_config.py` 默认值。

### 配置分组

| 分组 | 前缀 | 说明 |
|------|------|------|
| 彩种配置 | `draw.*` | 各彩种开奖时间、数据源URL |
| 调度器配置 | `crawler.*` | 自动开奖/抓取/预测延迟等调度参数 |
| 预测资料配置 | `prediction.*` | 预测生成参数 |
| 站点配置 | `site.*` | 站点默认URL、Token、请求参数 |
| 日志配置 | `logging.*` | 日志保留天数、轮转大小、清理间隔 |
| 认证配置 | `auth.*` | Session过期时间、密码迭代次数 |
| 系统配置 | `admin.*` | 管理员默认账号、显示名称 |

### API 接口

```
GET  /api/admin/system-config            → 列出 system_config 表原始数据
PUT  /api/admin/system-config/{key}      → 更新单个配置（含类型校验 + 自动记录历史）
GET  /api/admin/configs/groups           → 配置分组列表
GET  /api/admin/configs/effective        → 配置生效值列表（合并数据库 + 默认值，标注来源）
GET  /api/admin/configs/effective/{key}  → 单个配置生效值
POST /api/admin/configs/batch-update     → 批量更新配置
POST /api/admin/configs/{key}/reset      → 恢复配置为默认值
GET  /api/admin/configs/history          → 配置变更历史（可按 key 筛选）
```

### 配置变更历史

每次通过后台修改 `system_config` 时，系统自动在 `system_config_history` 表中记录：

- 修改前后的值
- 操作人（从当前登录 session 获取）
- 修改时间
- 修改原因（可选）

可在配置管理页面点击"历史"按钮查看每个配置项的完整变更记录。

### 配置值校验

修改配置时自动校验类型和业务约束：

| 类型 | 校验规则 |
|------|---------|
| int | 必须是整数；部分配置项要求非负 |
| float | 必须是浮点数 |
| bool | 仅接受 true/false |
| string | 不做校验 |
| json | 必须是合法 JSON |
| time | 必须是 HH:mm 或 HH:mm:ss 格式 |

---

## 已知运行风险

当前剩余风险：

- 调度器仍然是单进程、内存型调度器，不适合多实例部署下的持久化调度。
- 启动阶段仍然需要通过 `DATABASE_URL` 或启动参数提供数据库连接目标。
- 主管理后台运行流程之外的一些旧脚本和工具文件，可能仍然包含本地默认值。如果这些脚本用于生产流程，需要进一步对齐配置。

---

## 推荐部署实践

1. 在生产环境中明确设置 `DATABASE_URL`，或在启动命令中显式传入 PostgreSQL DSN。
2. 对外暴露前，修改启动默认管理员密码。
3. 首次启动后，检查 `system_config` 中的配置值。
4. 使用日志管理页面定期检查错误日志，关注 ERROR 和 WARNING 级别日志。
5. 通过配置管理页面统一管理运行参数，避免直接修改 `runtime_config.py` 中的默认值。
6. 监控 `/api/health` 和 `error_logs`。
7. 使用受监管的进程管理方式运行服务，以便服务崩溃后可以自动重启恢复。

---

# 2026-06-28 mixed 复合玩法命中规则

业务确认：`mixed` 复合类玩法按“任一维度命中即算命中”处理。

- 可参与命中判断的维度包括生肖、号码、尾数、头数、波色等由玩法配置声明的原子维度。
- 后台批量生成的台湾彩未来期模拟控制中，强制命中时只需命中其中一个真实维度；强制不中时必须避开所有真实维度标签。
- 未来期真实开奖号码仍只允许在内存中的 `DrawTruth` 里只读使用，不写入日志、任务 summary、异常文本或任何 HTTP 响应。
- `/api/predict/{mechanism}` 即时预测 API 不接入未来期真实开奖模拟控制，外部响应结构保持不变。

# 2026-06-28 预测准确率控制落地

台湾彩未来期预测准确率控制已接入后台批量生成主链路，作用范围限定为 `lottery_type_id=3`、future draw、且 `lottery_draws` 中存在未开奖期只读 `numbers` 的场景。

- 批量生成读取 `prediction.simulation.target_hit_rate`、`prediction.simulation.max_consecutive_hits`、`prediction.simulation.max_consecutive_misses`。
- 通用预测路径以及 246/331/474/476/478 等由 `predict()` 产出正文的特殊分支，会在落库前应用命中率控制。
- 杀号/排除类玩法按 `hit_checker` 语义反向处理：预测避开真实标签才算命中。
- mixed 复合类命中规则为任一维度命中；强制不中时会避开全部真实维度。
- 内部 `_simulation_should_hit` 标记只用于推进连续命中/不中状态，落库前会移除，不进入 API、日志或 created 表。

# 2026-06-28 预测领域与 SQL 收敛进展

本轮继续执行“保持前端 API 数据结构不变”的渐进式重构。外部 API 响应字段、字段顺序和 legacy 包装形态未调整。

## 已完成

- 新增 `domains/prediction/generation_repository.py`，承接批量预测生成中的开奖记录读取、未来期安全映射、站点启用模块读取、created 最近行读取、`text_history_mappings` 候选行读取。
- `prediction_generation/service.py` 中对应读取逻辑已改为 repository 调用；该文件当前保留生成编排、created 写入和任务日志写入职责。
- 新增预测领域模型：`PredictionCategory`、`DrawContext`、`DrawTruth`、`PredictionRequest`、`PredictionOutput`。
- 新增 `domains/prediction/category_service.py`，按玩法特征将机制归类为 `zodiac`、`image`、`size_parity`、`text_mapping`、`number`、`structured_mapping`、`mixed`。该模块为纯函数，不访问 SQL。
- 新增 `domains/prediction/simulation_service.py`，提供台湾彩未来期开奖模拟控制的纯领域逻辑；真实开奖号只以 `DrawTruth` 内存对象参与计算，`to_safe_dict()` 不暴露号码。
- 新增 system_config 默认项：
  - `prediction.simulation.target_hit_rate`，默认 `0.5`
  - `prediction.simulation.max_consecutive_hits`，默认 `3`
  - `prediction.simulation.max_consecutive_misses`，默认 `3`
- 新增 `domains/legacy/repository.py`，承接 legacy 图片列表、当前期号、mode_payload 元数据和 fallback 期号读取。
- `legacy/api.py` 已移除直接查询 SQL，改为调用 `domains.legacy.repository`；`legacy/frontend_compat.py` 的 `/api/post/getList` 图片读取也已委托 repository。

## 当前边界

- 台湾彩模拟控制已接入后台批量生成落库链路；`DrawTruth` 只读读取后仅用于内存命中控制，落库、日志和响应不得写入完整开奖号。
- `legacy/frontend_compat.py` 仍保留通用 mode_payload 查询 SQL；后续应按 endpoint/table 元数据继续迁入 repository。
- `helpers.py` 与 `prediction_generation/brain_teaser.py` 仍有历史查询逻辑，需要继续拆分到明确 repository。

## 验证

本轮已执行：

```powershell
cd backend/src
python -m pytest tests/unit/test_prediction_domain_models.py tests/unit/test_prediction_category_service.py tests/unit/test_prediction_generation_repository.py tests/unit/test_prediction_simulation_service.py tests/unit/test_prediction_simulation_config_defaults.py tests/unit/test_legacy_repository.py tests/unit/test_legacy_api_repository_contract.py tests/unit/test_legacy_mode_rows_overlay_delay.py tests/unit/test_api_contract_legacy_routes.py tests/unit/test_legacy_frontend_compat.py tests/unit/test_legacy_frontend_compat_image_url.py tests/unit/test_prediction_generation_overwrite_guard.py tests/unit/test_prediction_generation_legacy_mechanism_key_fallback.py tests/unit/test_api_contract_admin_routes.py -q
```

结果：

```text
42 passed
```

以及：

```powershell
python -m compileall domains/prediction/category_service.py domains/prediction/models.py domains/prediction/generation_repository.py domains/prediction/simulation_service.py domains/legacy/repository.py prediction_generation/service.py legacy/api.py legacy/frontend_compat.py runtime_config.py
```

## 架构评分更新

当前架构评分：**8.2 / 10**。

加分点：预测生成读取层和 legacy API 入口层进一步变薄；预测领域模型、玩法分类和模拟控制已具备独立测试；配置项进入 `system_config` 默认种子。

扣分点：预测 handler 尚未按大类完全拆开；少数纯静态/非 `predict()` 生成玩法仍需要后续逐步纳入统一 handler；`helpers.py`、`legacy/frontend_compat.py` 和 `brain_teaser.py` 仍有待收敛 SQL。

## 静态 JSON 映射导入

项目新增了两套独立脚本，用于将 `backend/data/json_data/` 下的静态 JSON 导入 PostgreSQL，并在预测模块中按路径快速读取：

- 导入脚本：`backend/src/utils/import_static_mappings.py`
- 读取脚本：`backend/src/utils/read_static_mapping.py`
- 示例配置：`backend/config/static_mappings.yaml`

默认会将每个 JSON 文件导入为 `public` schema 下的一张静态映射表，并自动补充逻辑路径字段 `mapping_path`，例如：

- `brain_test.json` -> `public.static_mapping_brain_test`
- `sx_verse.json` -> `public.static_mapping_sx_verse`
- 路径示例：`json_data/brain_test/1`

### 导入命令

全量替换导入：

```bash
python backend/src/utils/import_static_mappings.py \
  --config backend/config/static_mappings.yaml \
  --db-target "postgresql://user:password@host:5432/liuhecai"
```

增量导入：

```bash
python backend/src/utils/import_static_mappings.py \
  --config backend/config/static_mappings.yaml \
  --db-host host \
  --db-port 5432 \
  --db-name liuhecai \
  --db-user user \
  --db-password password \
  --incremental
```

说明：

- 默认模式为全量替换，会先清空目标表再重建数据。
- `--incremental` 会按主键执行 UPSERT，只插入新记录或更新已有记录。
- 脚本会自动建表、补列、创建 `mapping_path` 唯一索引，并输出成功/失败统计日志。
- 导入前会严格校验 JSON 是否为空、是否为数组、字段是否一致、主键是否重复。

### 读取命令

按路径读取单条记录：

```bash
python backend/src/utils/read_static_mapping.py \
  --config backend/config/static_mappings.yaml \
  --db-target "postgresql://user:password@host:5432/liuhecai" \
  --path "json_data/brain_test/1"
```

批量读取：

```bash
python backend/src/utils/read_static_mapping.py \
  --config backend/config/static_mappings.yaml \
  --db-target "postgresql://user:password@host:5432/liuhecai" \
  --paths "json_data/brain_test/1" "json_data/brain_test/2"
```

如果路径中已包含数据集名称，可以不传 `--dataset`；脚本会自动从路径推断数据集。

### Python 接口

```python
from utils.read_static_mapping import get_mapping, get_mappings

row = get_mapping(
    "json_data/brain_test/1",
    db_target="postgresql://user:password@host:5432/liuhecai",
)

rows = get_mappings(
    ["json_data/brain_test/1", "json_data/brain_test/2"],
    db_target="postgresql://user:password@host:5432/liuhecai",
)
```

返回结果为可直接序列化的字典或字典列表。查不到记录时，单条返回 `{}`，批量返回 `[]`。

### 当前数据注意事项

当前工作区中的 `backend/data/json_data/sx_verse.json` 为空文件。导入脚本会将其视为校验失败并拒绝写入，避免把空数据同步到正式库。补回有效 JSON 内容后可直接复用同一命令重新导入。

# 2026-06-27 后端重构状态更新

本轮后端优化已完成一轮阶段性收敛，重点是降低 `admin.crud`、预测响应构造、启动检查和管理 CRUD 的耦合，同时保持前端和彩票站点已经依赖的 API 返回结构不变。

## 已完成的结构调整

- `admin.crud` 已调整为兼容门面层，站点、用户、彩种、开奖、号码、预测模块等 CRUD 逐步委托到 `domains/*/service.py`。
- 新增或补齐领域服务：
  - `domains/users/service.py`
  - `domains/numbers/service.py`
  - `domains/lottery/service.py`
  - `domains/prediction/api_response.py`
  - `domains/prediction/backfill_service.py`
  - `domains/prediction/backfill_repository.py`
  - `domains/prediction/mode_payload_service.py`
  - `domains/prediction/mode_payload_repository.py`
  - `domains/sites/repository.py`
  - `domains/sites/service.py`
  - `domains/scheduler/service.py`
  - `domains/scheduler/repository.py`
- 预测 API 响应构造集中到 `domains.prediction.api_response`，避免路由和管理模块重复拼装响应。
- 调度任务表读写从 `crawler/tasks.py` 迁入 `domains.scheduler`，`crawler/tasks.py` 保留旧导入兼容门面。
- 开奖后回填所需的“最近一期已开奖”查询迁入 `domains.lottery.repository/service`，`crawler/scheduler.py` 不再直接查询这段 `lottery_draws`。
- `/api/admin/lottery-draws/latest-term` 的最近已开奖期查询迁入 `domains.lottery.repository/service`，`admin_draw_routes.py` 不再直接查询 `lottery_draws`。
- `/api/admin/backfill-predictions` 的期号推算、已开奖列表查询和 created 表回填 SQL 迁入 `domains.prediction.backfill_service/repository`，路由层只保留请求解析和响应包装。
- `/api/admin/backfill-predictions/logs` 的查询 SQL 迁入 `domains.logs.repository/service`，路由层只保留参数解析和响应包装。
- `/api/admin/logs` 查询入口改为依赖 `domains.logs.service`，并补充完整筛选参数的 API 合同测试。
- `/api/admin/logs/export` 导出入口改为依赖 `domains.logs.service.export_error_logs`，并补充响应合同测试。
- `/api/public/notice` 与 `/api/index/notice` 的公告查询迁入 `domains.sites.repository/service`，路由层只解析 `web` 参数并保持 `{ code, data: { content } }` 响应结构。
- `/api/admin/sites/{id}/mode-payload/{table}` 的列表查询，以及 `{row_id}` 更新/删除逻辑，均已迁入 `domains.prediction.mode_payload_service/repository`；`admin_payload_routes.py` 和 `admin/payload.py` 只保留路由/兼容门面职责。
- 启动风险提示抽离到 `app_http/startup_warnings.py`，`app_http/server.py` 只负责调用。
- `routes.common.fetch_site_data` 保留历史响应格式，同时内部使用更清晰的抓取运行记录函数。
- 默认预测蓝图 mode 列表已统一到数据库 schema seed 常量，避免运行时 fallback 与建表 seed 漂移。
- `routes/` 目录已无直连 SQL；路由层保留 HTTP 参数解析、站点上下文校验和响应包装。

## API 兼容性保护

本轮没有改变彩票站点预测模块 API 的返回数据结构。自动化测试已保护以下关键合同：

- `/api/predict/{mechanism}` 顶层字段顺序保持：`ok`, `protocol_version`, `generated_at`, `data`, `legacy`
- `data` 字段顺序保持：`mechanism`, `source`, `request`, `context`, `prediction`, `backtest`, `explanation`, `warning`
- 未开奖期的真实开奖结果继续隐藏，`request.res_code` 为 `null`，但上下文中仍保留 draw 信息。
- 历史兼容接口继续保留原有成功响应外形，不强行改成统一 `{ ok, data }`。
- `/api/public/notice` 与 `/api/index/notice` 公告接口响应合同已覆盖，继续返回 `{ code: 600|200, data: { content } }`。
- `/api/admin/sites/{id}/mode-payload/{table}/{row_id}` 更新/删除前的行归属校验合同已覆盖，继续保持原有更新响应和删除 `{ ok: true }` 响应。
- `admin.crud.ensure_admin_tables` 旧 patch 点已恢复，避免旧测试或旧工具依赖该入口时失效。

## 当前验证结果

在 `backend/src` 下执行：

```powershell
python -m pytest -q
```

最近一次结果：

```text
270 passed, 10 skipped
```

## 架构评分

当前后端架构评分：**8.0 / 10**。

优点：

- 主要业务已经向 `domains/` 聚合，HTTP 层、路由层、领域层边界比之前清晰。
- 预测 API 合同已有专门测试保护，适合继续重构而不破坏前端。
- 公共公告接口和管理日志/回填接口的路由层 SQL 已继续收敛，routes 现在更接近纯 HTTP 适配层。
- 调度任务表读写已开始从 `crawler/` 迁入 `domains/scheduler`，任务抢占、运行记录和失败重试有了更清晰的领域入口。
- 数据库 schema、运行配置、日志、启动警告和部分兼容层已有明确归属。
- 测试覆盖明显提升，当前全量测试通过。

扣分点：

- 仍有历史兼容包和旧模块存在，例如 `admin/`、`predict/`、部分 legacy API，短期不能删除。
- routes 已无直连 SQL；helper、legacy、prediction generation 和 `crawler/scheduler.py` 中仍有业务规则或 SQL 需要继续收敛。
- 调度器主循环仍是进程内 `threading.Timer` 风格；虽然任务表已有抢占和重试语义，但还不适合直接按多实例高可用调度器使用。
- 文档和部分源码注释存在历史编码问题，阅读和维护体验受影响。
- API 响应格式仍有历史接口与新接口并存，短期需要继续依赖合同测试保护。

## 后续优化建议

建议继续优化，但不要一次性大改。推荐优先级如下：

1. 高优先级：继续为公共 API、legacy API、预测 API 增加合同测试，尤其是彩票站点真实调用路径。
2. 高优先级：继续把 helper、legacy、prediction generation 中的散落 SQL 逐步迁移到 repository/service，保持 `routes/`、兼容门面和调度器编排层不直接写 SQL。
3. 高优先级：继续迁移 `crawler/scheduler.py` 中的任务查询、补跑判断和自动开奖规则，让 `domains/scheduler` 承担完整任务领域能力。
4. 中优先级：将进程内调度器升级为可持久化、可加锁的任务系统，避免多实例重复执行。
5. 中优先级：整理编码损坏的中文文档和注释，统一保存为 UTF-8。
6. 中优先级：继续拆分 `predict/mechanisms.py` 中体积较大的预测机制，迁移到更细的机制模块。
7. 低优先级：逐步统一新接口响应规范，但历史接口不要强改，除非前端已同步迁移。

---
# 2026-07-17 预测分类拆分与 DAO 收敛

- `backend/docs/API.md` 是唯一的 API 文档位置；历史 `backend/API.md` 已迁移，不再维护。
- `predict.mechanisms` 保留预测配置注册与兼容导出；已拆出的 `size_parity`、`zodiac`、`mixed`、`structured_mapping`、`text_mapping`、`number` 分类模块承载对应的解析、命中或格式化规则。
- `predict.mechanisms`、`predict.common`、`predict._db_helpers`、`predict.mechanism_status` 与 `prediction_generation.service` 不再直接执行业务 SQL；机制状态和任务日志分别经 `domains.prediction.state_repository` 与 `domains.prediction.generation_log_repository` 持久化。
- 所有 HTTP 响应契约保持不变；未来开奖真值仍禁止进入日志、任务报告、持久化预测内容或 API 响应。
# 2026-07-17 Image 分类与动态 Registry Builder

- `predict.categories.image` 承担连期窗口的 `start/end/content/image_url` formatter 与只读元数据加载；图片渲染、文件写入和批量编排仍保留在 `prediction_generation`，不改变落库或 HTTP payload 形状。
- `predict.categories.content_columns` 承担历史内容列读取、列合并、生肖/尾数/波色文本解析；`predict.mechanisms` 保留兼容导出与静态配置。
- 动态 mode_payload 配置的表遍历、静态模式排除和第一/第二阶段分派已迁至 `predict.registry_builder.build_dynamic_prediction_configs`；具体玩法分类规则仍由 `mechanisms.py` 注入，避免一次性改变旧规则。
- 以上仅调整内部边界；API 响应字段、字段顺序、legacy 包装和未来期开奖安全约束不变。
