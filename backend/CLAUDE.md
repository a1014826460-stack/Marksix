# 后端开发规范

## 1. 数据库

正式运行只使用 PostgreSQL。  
业务代码不得默认回退 SQLite。  
SQL 只能写在 repository、db、migration、created_store 中。  
不要在 routes、HTTP handler、前端页面中写 SQL。

## 2. 多站点

web_id 是站点业务 ID。  
managed_sites.id 是后台内部主键。  
managed_sites.web_id 对应旧资料表中的 web 字段。  
start_web_id/end_web_id 仅作为旧站抓取范围兼容字段。  
所有站点相关接口必须先解析 SiteContext。  
禁止硬编码 web=4。  
禁止通过 query/body 中的 web 参数跨站点读取或写入资料。

## 3. HTTP 路由

routes 只负责：
1. 解析 HTTP 参数
2. 鉴权
3. 调用 domain service
4. 返回 JSON

routes 不写复杂 SQL，不写预测生成细节。

## 4. 业务层

复杂业务逻辑放在 domains/*/service.py。  
数据库读写放在 domains/*/repository.py。  
公共数据结构放在 domains/*/models.py。

## 5. 预测

predict_engine 只做算法，不感知 HTTP、用户、站点权限。  
prediction generation 负责站点、期号、模块、created 表写入。  
历史回填可以使用 res_code。  
未来预测资料生成不能注入真实开奖结果。

## 6. 配置

业务代码通过配置服务读取配置，不直接到处读 config.yaml/env/system_config。  
敏感配置不要明文返回给前端。

## 7. 日志

生产代码禁止 print。  
关键日志必须尽量包含：
site_id、web_id、lottery_type_id、year、term、task_type、task_key、user_id。

## 8. 测试

修改以下内容必须补测试：
1. db schema
2. 多站点 SiteContext
3. prediction_generation
4. created_store
5. 路由分发
6. 配置管理
7. 日志查询

# 2026-06-27 开发规范补充

本项目已进入“保合同、渐进式重构”阶段。后续开发时，请优先遵守以下规则。

## 架构边界

- `routes/` 只做 HTTP 参数解析、鉴权调用、调用 domain service、返回 JSON。
- `domains/*/service.py` 放业务规则。
- `domains/*/repository.py` 放领域 SQL。
- `routes/admin_draw_routes.py` 不直接查询 `lottery_draws`；最近已开奖期等读取逻辑走 `domains.lottery.service/repository`。
- `routes/public_routes.py` 中的 `/api/public/notice` 和 `/api/index/notice` 不直接查询 `managed_sites`；公告读取走 `domains.sites.service/repository`。
- `routes/admin_payload_routes.py` 不直接查询 mode_payload 行；`admin.payload` 是兼容门面，列表/更新/删除逻辑走 `domains.prediction.mode_payload_service/repository`。
- `domains/scheduler/` 放调度任务表 SQL、任务入队、抢占、运行记录、执行生命周期和失败重试状态。
- `admin/crud.py` 是历史兼容门面，不再承载新业务逻辑。
- `admin/prediction.py` 保留预测安全、兼容导出和生成入口；新响应拼装优先放到 `domains/prediction/api_response.py`。
- `domains/prediction/backfill_service.py` 和 `backfill_repository.py` 承担预测结果回填的期号推算、开奖记录读取和 created 表更新；`routes/admin_backfill_routes.py` 只做 HTTP 适配。
- `app_http/server.py` 负责装配服务，启动风险提示放在 `app_http/startup_warnings.py`。
- `crawler/tasks.py` 是兼容门面；新增调度任务能力优先写入 `domains/scheduler`，不要把新 SQL 加回 `crawler/tasks.py`。
- `crawler/scheduler.py` 暂时保留主调度循环和具体任务执行规则；任务抢占、运行记录、成功完成、失败重试应走 `domains.scheduler.service.run_due_scheduler_tasks()`，并保持外部 API 响应不变。

## API 合同优先

- 不要改变彩票站点预测模块 API 的返回结构。
- `/api/predict/{mechanism}` 顶层字段顺序保持：`ok`, `protocol_version`, `generated_at`, `data`, `legacy`。
- `data` 字段顺序保持：`mechanism`, `source`, `request`, `context`, `prediction`, `backtest`, `explanation`, `warning`。
- 历史接口不强制改成 `{ ok, data }`。
- 修改响应格式前必须先写或更新 API 合同测试。

## 测试要求

常用验证命令：

```powershell
cd backend/src
python -m pytest -q
```

最近一次基线：

```text
270 passed, 10 skipped
```

涉及以下区域时必须补测试：

1. 预测 API 响应结构
2. 未开奖期隐藏真实开奖结果
3. admin CRUD 兼容门面
4. public/legacy API 返回结构
5. site blueprint mode 列表
6. scheduler/backfill 自动化行为
7. public notice 公告接口 `{ code, data.content }` 合同
8. mode_payload 更新/删除前的站点行归属校验

## 后续优化优先级

1. 继续把 helper、legacy、prediction generation 中的散落 SQL 收敛到 repository/service；`admin.payload` 只保留兼容门面职责。
2. 增加彩票站点真实路径的 API 合同测试。
3. 继续迁移 `crawler/scheduler.py` 中的剩余 SQL 和补跑判断到 `domains/scheduler`。
4. 将进程内 scheduler 升级为可持久化、可加锁任务系统。
5. 整理历史编码损坏的文档和注释，统一 UTF-8。
6. 拆分大型预测机制文件，降低单文件维护成本。

---

# 2026-06-28 mixed 复合玩法开发约束

- `PredictionCategory.MIXED` 的业务命中语义为：任一维度命中即算命中。
- mixed 的可命中维度应通过纯领域 hit policy 计算，例如生肖、号码、尾数、头数、波色；不得在 handler 或 hit policy 中直接查询 SQL。
- 台湾彩未来期模拟控制强制不中时，必须移除全部真实维度标签，不能只移除第一个命中目标。
- 不要把未来期 `lottery_draws.numbers`、特码或完整开奖号写入日志、异常、任务 summary 或 API 响应。

# 2026-06-28 预测准确率控制开发约束

- 后台批量生成可以读取台湾彩 future draw truth；即时 `/api/predict/{mechanism}` 不能读取。
- 新增预测生成分支如果调用 `predict()` 产出正文，应接入 `_apply_simulation_to_prediction_result`，并在落库前移除内部 `_simulation_should_hit`。
- 排除/杀号类必须传递 `PredictionConfig.hit_checker`，不能硬编码为“包含 truth label 即命中”。
- 图片类如果正文来自 `predict()`，正文应受准确率控制；图片渲染仍不得使用未来期真实开奖号。

# 2026-06-28 预测领域重构补充

## 新增边界

- `prediction_generation/service.py` 只做批量生成编排、row 生成调度、created 写入和任务日志；开奖记录读取、站点启用模块读取、created 最近行读取、text history 候选读取应放在 `domains/prediction/generation_repository.py`。
- legacy 图片、当前期号、mode_payload 元数据和 fallback 期号读取应放在 `domains/legacy/repository.py`；`legacy/api.py` 保持兼容门面，不新增 SQL。
- 预测玩法分类使用 `domains/prediction/category_service.py`，分类值固定为 `zodiac`、`image`、`size_parity`、`text_mapping`、`number`、`structured_mapping`、`mixed`。
- 预测输入/输出领域对象使用 `domains/prediction/models.py` 中的 `DrawContext`、`DrawTruth`、`PredictionRequest`、`PredictionOutput`。

## 台湾彩未来期开奖安全

- 未来期真实开奖号码只能通过只读查询进入内存 `DrawTruth`。
- 禁止把未来期真实 `numbers`、特码、完整开奖号写入日志、异常文本、任务 summary 或任何 HTTP 响应。
- `/api/predict/{mechanism}` 即时预测 API 不接入台湾彩未来开奖号模拟控制。
- 后台批量生成接入模拟控制时，只读取以下配置：
  - `prediction.simulation.target_hit_rate`
  - `prediction.simulation.max_consecutive_hits`
  - `prediction.simulation.max_consecutive_misses`
- 命中/不中判断应以各玩法 `hit_checker` 语义为准，杀号/排除类不能简单等同于“包含真实目标”。

## 当前验证子集

本轮 prediction/legacy 重构子集验证结果：

```text
42 passed
```
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

# 2026-07-18 预测生成硬约束

- 台湾彩未来期的受控生成必须通过 `domains.prediction.generation_rules` 的已验证规则；未知动态玩法或专用行生成器尚未接入规则时，必须跳过未来受控生成，不能回退为概率模拟并宣称准确率受控。
- 连续窗口准确率使用 `domains.prediction.accuracy_plan`；控制记录和跨站/相邻期签名预约只允许经 `domains.prediction.generation_control_repository` 持久化到内部表 `prediction_generation_controls`。
- 控制表只能保存候选签名哈希、规则版本和布尔验证结果，禁止保存完整未来开奖号码或将该表暴露给 HTTP、public、legacy、日志、任务摘要或图片层。
- 未来受控生成的账本预约与 `created` 预测行写入必须延迟到同一事务边界提交；写入失败或跳过已有行时必须移除预约。跨站预约冲突最多重选一次；相邻期比较必须覆盖跨年期号序列。
- `backend/docs/prediction-module-rules.md` 是生成的规则审阅文档。修改未来命中规则、候选数量、跨站前缀宽度或相邻期签名策略时，必须同步更新渲染器、文档和测试。

# 2026-07-19 站点预测模块授权

- `public.site_prediction_modules(status=1)` 是站点预测模块的唯一运行时授权来源；蓝图只定义可同步的目标集合。
- 站点私有 Next API 的 `site_id`、`web`、`web_id` 由路径 `siteKey` 固定，禁止用 query 跨站覆盖。
- vendor 聚合或 legacy 模块行在带显式 `web` 时必须校验启用模块；不授权时保持既有空 `history`、`rows` 或 `{ data: [] }` 包装，禁止增加响应字段。
- 使用 `python backend/scripts/reconcile_site_prediction_modules.py --db-path "<DATABASE_URL>"` 审计站点 4-8；仅在确认审计结果后加 `--apply`。该操作只切换 `status`，不删除历史行。
- 修改站点蓝图、vendor 固定模式或站点 vendor 模块文档时，必须更新 `test_site_prediction_module_audit.py`。
- 站点 4-8 的蓝图目标必须从 `domains.prediction.site_page_dependencies` 派生，覆盖所有当前可访问页面；注释脚本、孤立资源和未调用的旧前端元数据不得授权模块。
- 页面清单中的 `controlled_future`、`history_only`、`blocked` 仅供内部生成/审计使用，禁止添加到任何 HTTP 响应；更新站点清单后须通过 versioned migration 同步已存储的 `site_blueprint_profiles`。

# 2026-07-19 安全与稳定性整改

- 所有 `req_params`、结构化日志 `result` 与 JSON 日志均须经 `security.redaction.redact_value()` 递归脱敏；不得记录密码、令牌、验证码、`numbers`、`res_code`、DSN 或其他密钥值。
- 标记为 `is_secret=1` 的 `system_config` 为可写不可读：`include_secrets=1` 仅为兼容参数，不得返回真实值；有效值和历史接口也必须掩码。
- `super_admin` 独占用户管理、系统配置及站点的创建/删除/更新；至少保留一个启用的 `super_admin`。
- 非管理员的站点访问与预测生成必须以 `site_permissions` 表的显式授权为准；`super_admin/admin` 保留全站访问。
- 管理端列表参数必须使用 `app_http.security.parse_bounded_int`，保持成功响应字段不变，拒绝非法参数时复用既有错误 envelope。
- 验证码、失败登录和会话认证表只允许在 bootstrap/migration 创建；认证请求路径不得运行 `CREATE TABLE` 或 `CREATE INDEX`，以避免验证码请求被 DDL/锁等待阻塞。
- 管理端长任务必须写入 `scheduler_tasks` 后由 `scheduler_worker` 执行；HTTP API 进程不得启动 `CrawlerScheduler`、timer 或 daemon job thread。任务轮询保留既有 `status`、`started_at`、`result`、`metadata` 字段形状。
- `site_permissions` 必须在 `managed_sites` 创建后创建；这是 PostgreSQL 的外键依赖顺序，不能放入认证表 bootstrap。
- `scheduler_worker` 必须调用 `CrawlerScheduler.start()` 并在收到 `SIGTERM`/`SIGINT` 后调用 `stop()`；只轮询持久化任务会遗漏自动抓取、自动开奖、精准检查和错过任务补跑。
- `scheduler_worker` 必须持有 `scheduler_worker_leases` 中的独占租约后才可启动 timer；续租失败时必须停止全部 timer 并释放租约，避免多个 worker 重复执行进程内调度。
- 台湾彩精准开盘只允许使用持久化 `taiwan_precise_open` 任务：`CrawlerScheduler.start()` 负责确保该任务存在，内存精准 timer 只覆盖香港/澳门，禁止两条路径重复开盘或回填。
- 管理员 session 数据库只保存 `token_hash` 和不可逆的旧列标记，禁止保存可直接使用的 bearer token；登录 JSON 中的 `token` 暂为兼容保留，同时由 HttpOnly、SameSite=Strict cookie 支持同源管理端请求。
- PostgreSQL 的结构性 DDL 只允许由 `python -m database.versioned_migrations --db-path "<DATABASE_URL>"` 执行；迁移命令必须使用 `schema_migrations` 账本与 PostgreSQL transaction advisory lock。API/worker 启动和请求路径只可校验迁移状态，不得建表、建索引、加/删列。
- `created.mode_payload_*` 镜像表只允许由显式迁移按 `public.mode_payload_*` 实际表与 `mode_payload_tables` 元数据并集创建或对齐；预测生成、API 和 worker 发现缺表时必须失败并提示执行迁移，不得在运行时修复结构。
- `runtime_config`、日志持久化及认证/管理请求路径不得调用任何 `ensure_*_table` 或配置 seed；表和默认配置只由 versioned migration 的 baseline 创建。缺失 schema 必须显式失败并要求执行迁移，不能在请求中修复。
- PostgreSQL 备份必须在启动前检查 `database.backup_min_free_space_mb`，对 `pg_dump` 和 `pg_restore --list` 分别设置超时，成功后保存 SHA-256 与 archive verification 状态；恢复验证只允许在隔离数据库演练，不能用生产库试恢复。
