# Claude Code：backend/src 规范化分层重构 Prompt

你现在需要对彩票后台管理系统的 backend/src 进行规范化分层重构。

本次目标不是重写业务，而是在保持现有功能可用、接口尽量兼容的前提下，把项目结构整理成清晰的分层架构，方便后续多站点管理、开奖管理、预测资料生成、日志管理、配置管理继续扩展。

请严格按照以下要求执行。

---

# 一、当前项目背景

当前系统已经具备：

```text
1. PostgreSQL-only 正式运行数据库
2. 多站点管理 managed_sites
3. web_id 作为站点业务 ID
4. 彩票开奖数据 lottery_types / lottery_draws
5. 预测资料生成 prediction_generation
6. 预测机制 predict
7. created.mode_payload_* 资料写入
8. 后台配置 system_config
9. 日志 error_logs
10. 调度任务 scheduler_tasks
11. 旧站兼容 legacy
12. HTTP 路由 routes + router + RequestContext
```

当前已经完成了一部分低风险重构：

```text
app.py 已经从巨型路由文件拆薄
http/router.py 已存在
http/request_context.py 已存在
http/response.py 已存在
http/site_context.py 已存在或需要继续完善
routes/ 已经存在部分路由模块
tables.py 已经 PostgreSQL-only，并拆分了部分建表 helper
```

现在需要继续把项目规范成更清晰的分层结构。

---

# 二、本次重构总原则

请遵守以下原则：

```text
1. 保持现有接口路径尽量不变。
2. 不要引入 FastAPI、Flask、Django 等新框架。
3. 继续使用当前 ThreadingHTTPServer + 自定义 Router 架构。
4. 不要改动正式数据库为 PostgreSQL-only 的原则。
5. 不要恢复 SQLite 默认路径。
6. 不要硬编码 web=4。
7. 不要让 routes 层直接写复杂 SQL。
8. 不要让 predict 算法层感知 HTTP、用户、站点权限。
9. 不要大规模拆 predict/mechanisms.py，除非已经有测试保护。
10. 每一步重构都要保持 py_compile 通过。
11. 所有新增代码要有必要中文注释，解释业务语义，不写废话注释。
```

---

# 三、目标分层结构

请逐步将 backend/src 规范为以下结构。

```text
backend/src/
  app.py                         # 兼容入口，逐步变薄
  main.py                        # 推荐新增正式启动入口，可选

  core/
    config.py                    # 配置加载入口
    runtime_config.py            # 可复用当前 runtime_config.py 或迁移封装
    logging.py                   # 日志初始化封装
    errors.py                    # 统一异常类型
    time_utils.py                # UTC/北京时间/开奖时间处理
    constants.py                 # 全局常量
    types.py                     # 通用类型定义

  db/
    connection.py                # connect/default_db_target/engine 检测
    bootstrap.py                 # ensure_admin_tables 总入口
    schema/
      auth.py
      lottery.py
      sites.py
      prediction.py
      scheduler.py
      logs.py
      config.py
      legacy.py
      indexes.py
    seed.py                      # 默认管理员、默认彩种、默认站点
    migrations.py                # 轻量迁移 helper
    summary.py                   # database_summary

  http/
    handler.py                   # BaseHTTPRequestHandler 适配
    router.py
    request_context.py
    response.py
    auth.py                      # require_admin / require_site_access
    site_context.py              # SiteContext 解析

  routes/
    auth_routes.py
    health_routes.py
    public_routes.py
    legacy_routes.py
    admin_user_routes.py
    admin_site_routes.py
    admin_lottery_routes.py
    admin_draw_routes.py
    admin_prediction_routes.py
    admin_payload_routes.py
    admin_crawler_routes.py
    admin_config_routes.py
    admin_log_routes.py
    admin_job_routes.py
    common.py

  domains/
    sites/
      models.py
      repository.py
      service.py
      permissions.py

    lottery/
      models.py
      repository.py
      service.py
      draw_time.py

    prediction/
      models.py
      repository.py
      service.py
      generation.py
      safety.py
      diversity.py
      created_store.py

    crawler/
      models.py
      service.py
      scheduler.py
      hk.py
      macau.py
      taiwan.py

    configs/
      repository.py
      service.py
      validators.py

    logs/
      repository.py
      service.py

    legacy/
      service.py
      assets.py
      api_adapter.py

  predict_engine/
    common.py
    registry.py
    runner.py
    mechanisms/
      __init__.py
      static_rules.py
      dynamic_rules.py
      parsers.py
      formatters.py
      loaders.py
      status.py

  jobs/
    memory_jobs.py
    scheduler_tasks.py
    task_types.py
    handlers.py

  tools/
    verify_schema.py
    import_fixed_data.py
    migrate_sqlite_to_postgres.py
    normalize_payload_tables.py

  tests/
    unit/
    integration/
    fixtures/
```

注意：  
这不是要求一次性全部完成。请按照下面的阶段逐步迁移，优先保证功能正确和接口兼容。

---

# 四、第一阶段：建立开发规范文件

请新增或完善：

```text
backend/CLAUDE.md
```

写入后端开发规范，至少包含以下内容：

```markdown
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
```

---

# 五、第二阶段：整理 core 层

请新增：

```text
backend/src/core/
```

并逐步迁移或封装以下能力。

## 5.1 core/errors.py

新增统一异常类型：

```python
class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"

class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"

class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"

class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"
```

后续 routes 和 service 尽量抛这些异常，不要到处抛裸 `KeyError` / `ValueError`。

## 5.2 core/time_utils.py

新增统一时间工具：

```text
utc_now_text()
beijing_now()
parse_hhmm()
validate_hhmm()
combine_draw_datetime()
```

开奖时间相关逻辑后续统一放这里，不要在 crawler、public、prediction_generation 里各写一套。

## 5.3 core/constants.py

集中放：

```text
DEFAULT_PAGE_SIZE
MAX_PAGE_SIZE
BEIJING_TIMEZONE
CREATED_SCHEMA_NAME
```

如果已有同名常量，先复用，不要重复定义冲突。

---

# 六、第三阶段：整理 db 层

当前 `tables.py` 可以保留作为兼容入口，但请逐步拆分。

## 6.1 新增 db 目录

```text
backend/src/db/
  __init__.py
  bootstrap.py
  summary.py
  seed.py
  migrations.py
  schema/
    __init__.py
    auth.py
    lottery.py
    sites.py
    prediction.py
    scheduler.py
    logs.py
    config.py
    legacy.py
    indexes.py
```

## 6.2 保持 tables.py 兼容

不要立即删除 `tables.py`。  
先让 `tables.py` 变成兼容导出入口，例如：

```python
from db.bootstrap import ensure_admin_tables
from db.summary import database_summary
from db.connection import default_db_target
```

如果当前 `db.py` 已经存在并承担连接能力，不要强行与 `db/` 包冲突。  
如果文件名冲突，请采用：

```text
db_layer/
```

或者：

```text
database/
```

避免 Python import 冲突。

## 6.3 schema 拆分要求

把当前 tables.py 中的建表 helper 逐步移动到：

```text
schema/auth.py
schema/lottery.py
schema/sites.py
schema/prediction.py
schema/scheduler.py
schema/logs.py
schema/config.py
schema/legacy.py
schema/indexes.py
```

每个文件只负责一个领域的表和索引。

## 6.4 seed 拆分要求

默认数据播种放到：

```text
db/seed.py
```

包括：

```text
默认管理员
默认彩种
默认站点
默认站点预测模块同步
```

表结构和默认数据不要长期混在同一个函数里。

---

# 七、第四阶段：完善 http 层

当前已有：

```text
http/router.py
http/request_context.py
http/response.py
http/site_context.py
```

请继续规范。

## 7.1 RequestContext

确保 RequestContext 至少包含：

```python
@dataclass
class RequestContext:
    method: str
    path: str
    query: dict[str, list[str]]
    body: dict[str, Any]
    db_path: str | Path
    user: dict[str, Any] | None
    request_id: str
    handler: Any
```

## 7.2 SiteContext

确保 SiteContext 至少包含：

```python
@dataclass(frozen=True)
class SiteContext:
    site_id: int
    web_id: int
    name: str
    domain: str | None
    lottery_type_id: int | None
    enabled: bool
```

实现或完善：

```python
resolve_site_context(...)
resolve_site_context_from_request(...)
validate_web_matches_site(...)
require_site_access(...)
```

规则：

```text
1. 路径中的 site_id 是后台站点接口的权威来源。
2. query/body 中的 web/web_id 如果存在，必须等于当前站点 web_id。
3. 公开接口可以通过 site_id、domain、Host 解析站点。
4. 找不到站点时返回明确错误。
5. 禁止静默默认 web=4。
```

## 7.3 http/auth.py

新增或整理：

```python
require_admin(ctx)
require_generation_permission(ctx)
require_site_access(ctx, site_id)
```

第一阶段可以让 super_admin/admin 拥有全部站点权限，但接口结构要预留 site_admin/operator/viewer。

---

# 八、第五阶段：规范 routes 层

routes 只做 HTTP 适配，不做复杂业务。

请检查所有 routes 文件：

```text
routes/auth_routes.py
routes/public_routes.py
routes/legacy_routes.py
routes/admin_site_routes.py
routes/admin_payload_routes.py
routes/admin_prediction_routes.py
routes/admin_config_routes.py
routes/admin_log_routes.py
routes/admin_lottery_routes.py
routes/admin_draw_routes.py
routes/admin_crawler_routes.py
routes/admin_job_routes.py
```

要求：

```text
1. routes 不直接写复杂 SQL。
2. routes 不直接拼接复杂 created row。
3. routes 不处理大量业务 if/elif。
4. routes 只调用 domains/*/service.py 或现有 admin/* service。
5. 所有 /api/admin/sites/{site_id}/... 必须先解析 SiteContext。
6. 所有 mode_payload 接口必须校验 web 与当前站点一致。
7. 所有 prediction generation 接口必须使用当前 SiteContext.web_id。
```

## 8.1 路由冲突检查

重点检查：

```text
/api/admin/sites/{site_id}/mode-payload/...
```

必须进入 payload 路由，不允许被 sites 大前缀路由抢占。

如果当前 router 存在 prefix 遮挡，请使用更精确的 regex 或参数路由。

---

# 九、第六阶段：建立 domains 层

先做最重要的三个领域：

```text
domains/sites
domains/lottery
domains/prediction
```

不要一次性把所有业务搬完。

## 9.1 domains/sites

新增：

```text
domains/sites/models.py
domains/sites/repository.py
domains/sites/service.py
domains/sites/permissions.py
```

职责：

```text
站点查询
站点创建/更新
站点启用/停用
site_id/web_id 解析
domain 解析
站点权限判断
```

原来 `admin/crud.py` 中的站点相关函数可以逐步迁移进来。

## 9.2 domains/lottery

新增：

```text
domains/lottery/models.py
domains/lottery/repository.py
domains/lottery/service.py
domains/lottery/draw_time.py
```

职责：

```text
彩种管理
开奖数据管理
最新开奖查询
开奖历史查询
下一期开奖时间
开奖时间校验
```

原来 `public/api.py`、`admin/crud.py`、`crawler` 中的开奖查询逻辑可以逐步迁移。

## 9.3 domains/prediction

新增：

```text
domains/prediction/models.py
domains/prediction/repository.py
domains/prediction/service.py
domains/prediction/generation.py
domains/prediction/safety.py
domains/prediction/created_store.py
```

职责：

```text
站点预测模块管理
预测资料批量生成
未开奖安全判断
created.mode_payload_* 写入
多站点 web_id 隔离
```

可以先保留旧的 `prediction_generation/service.py`，但让它调用新的 `domains/prediction/generation.py`，或者反过来先在旧文件中提取 helper。

---

# 十、第七阶段：规范 predict / prediction_generation

## 10.1 predict 目录

当前 `predict/mechanisms.py` 不要马上大拆。

先做：

```text
1. 清理 SQLite 注释和类型误导
2. print 改 logger
3. db_path 命名逐步改为 db_target
4. 补核心纯函数测试
5. 给机制输出加黄金样例测试
```

后续再迁移到：

```text
predict_engine/
```

## 10.2 prediction_generation

当前最重要要求：

```text
1. 禁止 web=4
2. 必须通过 SiteContext.web_id 写入 created row
3. 必须记录 site_id/web_id/lottery_type/year/term
4. 特殊 mode_id 生成逻辑逐步拆 helper
5. 主函数 generate_prediction_batch 不要继续膨胀
```

建议拆成：

```text
resolve_generation_context()
load_site_modules()
load_target_draws()
generate_module_rows()
build_created_row()
save_created_row()
```

---

# 十一、第八阶段：jobs 层

新增：

```text
jobs/
  memory_jobs.py
  scheduler_tasks.py
  task_types.py
  handlers.py
```

迁移：

```text
routes/common.py 中的 start_background_job
scheduler_tasks 表相关操作
自动开奖后预测生成任务
手动批量生成任务
```

要求：

```text
所有 job 必须有 metadata：
site_id
web_id
lottery_type_id
year
term
task_type
created_by
```

---

# 十二、第九阶段：测试和验证

请新增或完善测试目录：

```text
tests/unit/
tests/integration/
tests/fixtures/
```

优先补这些测试。

## 12.1 schema 测试

```text
tests/integration/test_tables_bootstrap.py
```

测试：

```text
空 PostgreSQL 数据库可以初始化
重复初始化幂等
managed_sites.web_id 存在
scheduler_tasks 上下文字段存在
error_logs 上下文字段存在
索引存在
```

## 12.2 SiteContext 测试

```text
tests/unit/test_site_context.py
```

测试：

```text
path site_id 解析
query site_id 解析
domain 解析
web 与站点不一致时报错
web=4 不再作为默认值
```

## 12.3 prediction generation 测试

```text
tests/integration/test_prediction_generation.py
```

测试：

```text
站点 web_id=7 时，生成 row_data.web 必须是 7
不能写成 4
未开奖期不能注入真实 res_code
部分模块失败时有错误记录
```

## 12.4 router 测试

```text
tests/unit/test_router.py
```

测试：

```text
/api/admin/sites/{site_id}/mode-payload/... 不被 /api/admin/sites/ 大前缀遮挡
更具体路由优先匹配
404 能正确返回
```

---

# 十三、文档更新

请更新：

```text
backend/API.md
backend/CLAUDE.md
README.md 或 README_CN.md 中后端部分
```

必须说明：

```text
1. src 分层结构
2. routes/domain/repository 的职责边界
3. web_id 与 site_id 的关系
4. PostgreSQL-only
5. 禁止硬编码 web=4
6. 新增接口应该放哪里
7. SQL 应该放哪里
8. 预测资料生成链路
```

---

# 十四、迁移策略

请不要一次性移动所有文件导致大量 import 失效。

建议采用以下方式：

```text
1. 先新增新目录和新模块
2. 旧模块保留兼容导出
3. 新代码逐步调用新模块
4. 通过 py_compile 和接口测试确认无误
5. 最后再清理旧入口
```

例如：

```python
# 旧 tables.py
from database.bootstrap import ensure_admin_tables
from database.summary import database_summary
```

如果直接使用 `db/` 目录会与现有 `db.py` 冲突，请优先使用：

```text
database/
```

而不是强行改名导致 import 混乱。

---

# 十五、禁止事项

请不要做以下事情：

```text
1. 不要引入新 Web 框架。
2. 不要恢复 SQLite 默认数据库。
3. 不要删除现有业务功能。
4. 不要大规模拆 predict/mechanisms.py。
5. 不要改变现有 API 路径，除非保留兼容。
6. 不要在 routes 里新增复杂 SQL。
7. 不要在前端或组件中写 SQL。
8. 不要硬编码 web=4。
9. 不要把待实现功能写成已实现。
10. 不要为了分层而产生大量空壳文件。
```

---

# 十六、验证命令

每个阶段完成后至少运行：

```bash
python -m py_compile app.py
python -m py_compile http/*.py
python -m py_compile routes/*.py
python -m py_compile tables.py
python -m py_compile prediction_generation/*.py
python -m py_compile predict/*.py
```

如果新增了目录，也要运行：

```bash
python -m py_compile core/*.py
python -m py_compile database/*.py
python -m py_compile database/schema/*.py
python -m py_compile domains/sites/*.py
python -m py_compile domains/lottery/*.py
python -m py_compile domains/prediction/*.py
python -m py_compile jobs/*.py
python -m py_compile tools/*.py
```

如果项目有 pytest，运行：

```bash
pytest tests/unit
pytest tests/integration
```

至少手动验证接口：

```text
GET /api/health
POST /api/auth/login
GET /api/admin/sites
GET /api/admin/sites/{site_id}
GET /api/admin/sites/{site_id}/mode-payload/{table}
POST /api/admin/sites/{site_id}/prediction-modules/generate-all
GET /api/admin/jobs/{job_id}
GET /api/public/site-page?site_id={site_id}
GET /api/public/latest-draw?site_id={site_id}
GET /api/admin/logs
GET /api/admin/configs/effective
```

---

# 十七、最终输出格式

每完成一个阶段，请输出：

```text
## 阶段目标

## 修改摘要

## 新增文件

## 修改文件

## 删除或废弃文件

## 保持兼容的旧入口

## 分层调整说明

## 多站点隔离说明

## PostgreSQL-only 说明

## 验证结果

## 仍需处理的问题
```

最终完成后，请输出：

```text
## 总体重构摘要

## 最终 src 分层结构

## 各层职责说明

## 关键业务链路

## API 兼容情况

## 数据库变更情况

## 测试与验证结果

## 后续建议
```

请严格按照“低风险、分阶段、保持兼容、明确分层”的方式完成重构。
