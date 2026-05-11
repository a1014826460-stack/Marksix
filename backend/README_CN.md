# Liuhecai 后端管理系统 README

## 概述

该后端是一个轻量级的管理后台和 API 服务，用于彩票数据管理、开奖数据采集、预测生成、日志记录，以及旧版前端兼容。

当前运行架构使用两层配置：

1. `backend/src/config.yaml`  
   作为启动配置使用，使服务能够启动并连接数据库。

2. `system_config` 表  
   作为运行时大多数常量和运维参数的真实配置来源。

运行时会优先读取数据库中的配置；如果某个配置项缺失，或数据库不可用，则回退到 `config.yaml`。

---

## 启动流程

主入口：

```txt
backend/src/app.py
```

启动顺序：

1. 从 `LOTTERY_DB_PATH`、`DATABASE_URL`、配置中的 PostgreSQL DSN，或本地 SQLite fallback 中解析数据库目标。
2. 调用 `ensure_admin_tables()` 创建核心表并初始化基础数据。
3. 调用 `init_logging()` 启用结构化文件日志和基于数据库的错误日志。
4. 启动 HTTP 服务。
5. 启动 `CrawlerScheduler`，用于进程内定时任务。

重要限制：

当前调度器仍然是基于 `threading.Timer` 的进程内定时调度器。它会在进程重启后通过扫描数据库状态恢复任务，但它不是分布式调度器，也不是持久化调度器。

---

## 经验教训与排查守则

这部分用于记录真实排查过程中踩过的坑，避免后续重复犯错。

### 1. `8000` 不是废弃入口

当前项目中，`8000` 端口对应的 Python 服务是正式入口，不是废弃接口。

- 主入口文件：`backend/src/app.py`
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

如果本机同时存在多个 `python backend/src/app.py` 进程，会导致：

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
- `managed_sites`：被管理站点的元数据和采集配置
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

主 HTTP 路由：

```txt
backend/src/app.py
```

CRUD 模块：

- `backend/src/admin/crud.py`
- `backend/src/admin/payload.py`
- `backend/src/admin/prediction.py`

典型流程：

1. HTTP 请求进入 `ApiHandler.dispatch()`。
2. 路由根据需要执行认证。
3. 请求体由 `read_json()` 解析。
4. `admin/*` 模块中的业务函数校验 payload 并执行 SQL。
5. 数据以 JSON 形式返回。

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

示例：

- `save_site()` 会校验名称、web id 范围，以及 URL 模板占位符。
- `regenerate_payload_data()` 会校验表名、期号、年份和 `res_code` 格式。
- `bulk_generate_site_prediction_data()` 会校验期号范围顺序。
- `auth_user_from_token()` 会校验 session 过期时间和 token 可用性。

错误处理策略：

- 业务函数抛出 `ValueError`、`KeyError` 或 `PermissionError`。
- `ApiHandler.dispatch()` 捕获异常，并映射成 JSON 响应。
- 请求异常会通过 `logger.exception(...)` 记录。
- 数据库日志持久化失败不会中断主要业务流程。

---

## 调度器、开奖与爬虫

文件：

```txt
backend/src/crawler/crawler_service.py
```

职责：

- 自动开奖：对 `draw_time` 已经过期的奖期执行开奖。
- 精准调度台湾每日开奖。
- 自动采集香港和澳门开奖数据。
- 开奖数据采集后，延迟自动生成预测。

当前调度器模型：

- `CrawlerScheduler.start()`
- `_schedule_auto_open()`
- `_schedule_auto_crawl()`
- `_schedule_taiwan_precise_open()`

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
- 台湾数据只支持导入，使用 `draw.taiwan_import_file`。

爬虫 HTTP 容错配置：

- `crawler.http_timeout_seconds`
- `crawler.http_retry_count`
- `crawler.http_retry_delay_seconds`

相关文件：

- `backend/src/crawler/HK_history_crawler.py`
- `backend/src/crawler/Macau_history_crawler.py`
- `backend/src/crawler/crawler_service.py`

---

## 预测生成

入口：

- 公共预测 API：`ApiHandler.handle_prediction()`
- 批量生成：`backend/src/admin/prediction.py::bulk_generate_site_prediction_data`
- 共享生成器：`backend/src/prediction_generation/service.py::generate_prediction_batch`
- 延迟自动化：`backend/src/crawler/crawler_service.py::_run_auto_prediction`

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
- 延迟自动化流程会先把真实开奖结果回填到已创建的预测行中，然后再生成下一期预测。

重要运行配置：

- `prediction.default_target_hit_rate`
- `prediction.max_terms_per_year`

---

## 站点数据采集

文件：

- `backend/src/utils/data_fetch.py`
- `backend/src/app.py::fetch_site_data`

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

- 启动配置：`backend/src/config.yaml`
- 运行时配置：`system_config`

核心文件：

```txt
backend/src/runtime_config.py
```

函数：

- `ensure_system_config_table()`
- `seed_system_config_defaults()`
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

因此 PostgreSQL DSN 仍然需要从 `config.yaml` 或环境变量中启动读取。

---

## 已知运行风险

当前剩余风险：

- 调度器仍然是单进程、内存型调度器，不适合多实例部署下的持久化调度。
- 启动阶段仍然依赖 `config.yaml` 来完成首次数据库连接。
- 主管理后台运行流程之外的一些旧脚本和工具文件，可能仍然包含本地默认值。如果这些脚本用于生产流程，需要进一步对齐配置。

---

## 推荐部署实践

1. 在生产环境中明确设置 `DATABASE_URL` 或 `LOTTERY_DB_PATH`。
2. 对外暴露前，修改启动默认管理员密码。
3. 首次启动后，检查 `system_config` 中的配置值。
4. 监控 `/api/health` 和 `error_logs`。
5. 使用受监管的进程管理方式运行服务，以便服务崩溃后可以自动重启恢复。
