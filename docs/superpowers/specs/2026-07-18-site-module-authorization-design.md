# 站点预测模块授权设计

日期：2026-07-18  
状态：已确认，实施中

## 目标

以 `public.site_prediction_modules` 的启用行作为站点预测模块的唯一运行时授权来源，同时保持所有 HTTP API 路径、状态码、字段、字段顺序及 legacy 包装不变。

## 范围

1. 站点私有 Next API 仅使用路径 `siteKey` 对应的固定 `site_id` 与 `web_id`；查询字符串的 `site_id`、`web`、`web_id` 不再能跨站覆盖。
2. vendor 首页聚合器只可读取目标站点已启用的依赖模块；任一聚合依赖未启用时保留既有聚合对象，返回空 `history`。
3. `/api/legacy/module-rows` 和 `/api/kaijiang/*` 在带明确 `web` 时，只可返回该 `web` 对应站点已启用的 `mode_id`；未启用时保持既有元数据或 `{ data: [] }` 空结果形状。
4. 站点 5-8 的运行表按专属蓝图收敛：蓝图外行改为 `status=0`，不删除历史数据。
5. `twcf888` 的蓝图、vendor 文档与数据库启用集合一致；`51`、`197` 保留在蓝图和文档中，运行表外的 `44`、`61`、`204` 停用。
6. 以可重复的审计服务、脚本和测试持续核对运行表、蓝图、vendor 文档及前端固定依赖。

## 决策

### 路径身份优先

`/api/sites/<siteKey>/*`、`/api/twjinniu/*` 和 `/api/twcf888/*` 的站点身份由路径决定。前端注册表为每个站点显式保存 `defaultSiteId` 与 `defaultWebId`；请求中的冲突参数被忽略而不是报错，避免改变成功响应 JSON 形状。

### 启用模块校验

新增 prediction repository 查询：按 `web_id` 解析 `managed_sites`，判断 `site_prediction_modules` 中是否存在 `status=1` 的对应 `mode_id`。缺少站点或禁用模块均视为未授权。校验仅影响数据选择，不增加响应字段：

- vendor 聚合返回原有 `module_key`、`title`、`display_style` 与 `history: []`；
- legacy module rows 返回原有元数据与 `rows: []`；
- legacy kaijiang 返回既有 `{ "data": [] }`。

未带 `web` 的历史兼容查询维持现有行为，避免全局旧接口被误关闭。

### 蓝图同步

新增显式的 `reconcile_site_prediction_modules_to_blueprint()`，只对指定站点执行：启用缺失蓝图项、停用蓝图外启用项，不删除任何记录。常规 `sync_site_prediction_modules()` 继续只补齐，不隐式停用管理员的自定义项；生产收敛通过一次性脚本显式触发。

### 审计边界

审计服务输出非敏感 mode ID 差异：`missing_from_runtime`、`enabled_outside_blueprint`、vendor 文档差异和前端固定依赖差异。它不读取预测正文、未来开奖或连接串。测试使用临时数据库和静态文件；脚本通过正式数据库的 repository/service 执行。

## 不变性

- 不修改 API 路径、HTTP 状态码、成功 JSON 字段或字段顺序。
- 不删除 `site_prediction_modules`、预测历史或 created 数据。
- 不向 API、日志或审计报告输出未来开奖数据。
- `/api/public/site-page` 已按启用行读取；本次不改变其 payload 结构。

## 验证

1. 前端注册表测试证明 `site_id/web` 查询值无法改变站点私有 API 上下文。
2. vendor 聚合与 legacy 行接口测试证明禁用依赖返回原有空结果形状。
3. legacy kaijiang 测试证明禁用模块仍返回 `{ "data": [] }`。
4. SQLite 蓝图同步测试证明只停用 5-8 的蓝图外项并保留行。
5. 审计测试证明 `twcf888` 文档、蓝图、前端固定依赖和运行集合可持续比较。
