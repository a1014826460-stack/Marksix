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
