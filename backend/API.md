# 后端 API 与管理系统文档

## 设计选择

当前项目的数据抓取、归一化、固定映射、文本历史映射和预测逻辑已经同时支持 SQLite 与 PostgreSQL，但当前生产链路以 PostgreSQL 为主，尤其依赖：

- `public.lottery_draws`：开奖事实表
- `public.mode_payload_*`：抓取归一化后的原始玩法历史
- `created.mode_payload_*`：本地生成的预测结果表

因此管理系统继续采用项目内自研 Python 实现，而不是直接套用现有 GitHub CMS 项目。

原因：

- 现有需求核心是“配置彩票网站 API -> 抓取 -> 归一化 -> 刷新映射 -> 预测”，通用 CMS 反而需要大量适配。
- 自研版本直接复用 `data_fetch.py`、`normalize_sqlite.py`、`build_text_history_mappings.py` 和 `predict` 模块，不重复构建功能。
- 当前实现只依赖 Python 标准库，部署成本低；后续如果要权限、审计、多用户，再迁移到 FastAPI/Django 也有清晰边界。

## 启动服务

```powershell
python backend/src/app.py --host 127.0.0.1 --port 8000
```

Python API：

```text
http://127.0.0.1:8000
```

Next 管理前端：

```powershell
cd backend
npm run dev -- --hostname 127.0.0.1 --port 3002
```

管理后台：

```text
http://127.0.0.1:3002/login
```

默认数据库目标优先级：

1. `LOTTERY_DB_PATH`
2. `DATABASE_URL`
3. 配置文件中的 PostgreSQL DSN
4. `backend/data/lottery_modes.sqlite3`

因此本地开发既可以继续使用 SQLite，也可以直接指向 PostgreSQL。

## 通用响应

成功响应为 JSON 对象。

错误响应：

```json
{
  "ok": false,
  "error": "错误说明"
}
```

## 前后端边界

本文件只描述 **Python 后端原生接口**。

- 浏览器通常不会直接调用这些接口
- 公开站点一般经由 `frontend/app/api/*` 的 Next.js 代理层访问
- 后端只负责“数据事实、预测结果、兼容输出”
- 前端只负责“代理、转发、页面展示、旧站 JS 兼容适配”

维护时请避免把前端展示拼装逻辑写回后端，也避免让前端去猜测开奖状态。
开奖是否可公开、预测是否命中，统一以后端为准。

## 健康检查

### GET `/api/health`

返回数据库和机制数量概览。

示例：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

返回字段：

- `summary.sites`：CMS 已配置站点数
- `summary.fetched_modes`：已抓取玩法配置数
- `summary.fetched_mode_records`：已抓取历史记录数
- `summary.mode_payload_tables`：已归一化玩法表数
- `summary.text_history_mappings`：文本历史映射数量
- `summary.prediction_mechanisms`：当前可用预测机制数

## 公开前台接口

这些接口供前端公开页或 Next.js 代理层调用，不需要管理员鉴权。

### GET `/api/public/site-page`

返回某个站点首页所需的完整数据。

查询参数：

- `site_id`：可选，站点 ID
- `domain`：可选，按域名匹配站点
- `history_limit`：可选，每个模块返回的历史行数，默认 `8`

返回结构：

```json
{
  "site": {
    "id": 4,
    "name": "盛世台湾六合彩",
    "lottery_type_id": 3,
    "start_web_id": 4,
    "end_web_id": 4
  },
  "draw": {
    "current_issue": "2026125",
    "result_balls": [],
    "special_ball": null
  },
  "modules": [
    {
      "id": 123,
      "mechanism_key": "pt2xiao",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "history_schema": "created",
      "history_sources": ["created", "public"],
      "history": []
    }
  ]
}
```

后端规则：

- 模块历史优先读取 `created.mode_payload_{mode_id}`
- 若 `created` 数据不足 `history_limit`，再回退补充 `public.mode_payload_{mode_id}`
- 站点模块会按站点 `lottery_type_id`、`start_web_id`、`end_web_id` 过滤
- 开奖结果统一以 `public.lottery_draws` 为准，不再从 `mode_payload_*` 反推
- 若某期在 `lottery_draws` 中 `is_opened = 0`，则该期历史返回“待开奖”，不对外暴露 `res_code/res_sx/res_color`

### GET `/api/public/latest-draw`

返回指定彩种最近一期 **已开奖** 数据。

查询参数：

- `lottery_type`：彩种 ID，默认 `1`

返回示例：

```json
{
  "current_issue": "2026125",
  "result_balls": [
    { "value": "04", "zodiac": "兔", "color": "blue" }
  ],
  "special_ball": {
    "value": "40",
    "zodiac": "兔",
    "color": "red"
  }
}
```

后端规则：

- 只读取 `public.lottery_draws` 中 `is_opened = 1` 的最新记录
- `numbers` 会结合 `public.fixed_data` 补齐生肖与波色
- 若存在未开奖记录（例如台湾彩 `type=3`），不会因为其 `numbers` 已抓到就提前返回

## 旧站兼容接口

这些接口为旧站 JS / 新站兼容层服务，输出以“兼容旧结构”为目标，不是新的领域模型。

### GET `/api/legacy/current-term`

返回当前已开奖期号与下一预测期号。

查询参数：

- `lottery_type_id`：彩种 ID，默认 `1`

后端规则：

- 只读取 `public.lottery_draws` 中 `is_opened = 1` 的最新期号
- `issue = year + term`
- `next_term` 优先取 `lottery_draws.next_term`，缺失时回退为 `term + 1`

### GET `/api/legacy/post-list`

返回旧站图片列表。

查询参数：

- `pc`
- `web`
- `type`
- `limit`

数据来源：

- `legacy_image_assets`

### GET `/api/legacy/module-rows`

返回指定旧模块的历史记录原始行。

查询参数：

- `modes_id`：必填，玩法 ID
- `web`：可选，站点来源
- `type`：可选，彩种类型
- `limit`：可选，默认 `10`

返回结构：

```json
{
  "modes_id": 50,
  "title": "一句真言",
  "table_name": "mode_payload_50",
  "rows": [
    {
      "year": "2026",
      "term": "125",
      "title": "预测一句真言",
      "content": "中树",
      "res_code": "04,27,38,11,45,08,40",
      "res_sx": "兔,龙,蛇,猴,狗,猪,兔",
      "draw_is_opened": true
    }
  ]
}
```

后端规则：

- 优先返回 `created.mode_payload_{mode_id}` 的记录
- 若 `created` 不足，再回退 `public.mode_payload_{mode_id}`
- 同一期若 `created` 与 `public` 同时存在，优先保留 `created`
- 开奖字段统一以后端查到的 `public.lottery_draws` 为准
- 若 `lottery_draws.is_opened = 0`，则返回的该行 `res_code/res_sx/res_color` 统一置空
- `mode_id=50` 的文本映射必须只读取同 `mode_id=50` 的 `text_history_mappings`
- 其他 `is_text=1` 的文本类玩法也必须按同 `mode_id` 取映射，不得跨玩法回退

## 预测接口

### GET `/api/predict/mechanisms`

列出所有可用预测机制。

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/predict/mechanisms
```

### POST `/api/predict/{mechanism}`

执行指定预测机制。

权限说明：

- 需要管理员登录态
- 请求头需携带 `Authorization: Bearer <token>`

请求体：

```json
{
  "res_code": "02,25,11,33,06,41,01",
  "content": null,
  "source_table": null,
  "target_hit_rate": 0.65
}
```

字段说明：

- `res_code`：可选，外部传入最新开奖结果，最后一个号码按特码处理。
- `content`：可选，保留给调用方审计。
- `source_table`：可选，覆盖机制默认 SQLite 来源表。
- `target_hit_rate`：可选，目标历史回测命中率。

冻结后的稳定响应结构：

```json
{
  "ok": true,
  "protocol_version": "2026-05-08",
  "generated_at": "2026-05-08T12:00:00+00:00",
  "data": {
    "mechanism": {
      "key": "pt2xiao",
      "title": "平特2肖",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "resolved_labels": ["鼠", "牛"]
    },
    "source": {
      "db_path": "postgresql://...",
      "table": "mode_payload_43",
      "source_modes_id": 43,
      "source_table_title": "平特2肖",
      "history_count": 983
    },
    "request": {
      "res_code": null,
      "content": null,
      "source_table": "mode_payload_43",
      "target_hit_rate": 0.65,
      "lottery_type": 3,
      "year": "2026",
      "term": "127",
      "web": "4"
    },
    "context": {
      "latest_term": 127,
      "latest_outcome": "羊",
      "draw": {
        "issue": "2026127",
        "draw_found": true,
        "is_opened": false,
        "result_visibility": "hidden",
        "reason": "draw_unopened"
      }
    },
    "prediction": {
      "labels": ["马", "牛"],
      "content": "马,牛",
      "content_json": "\"马,牛\"",
      "display_text": "马,牛"
    },
    "backtest": {
      "target_hit_rate": 0.65,
      "selected_hit_rate": 0.679342
    },
    "explanation": [],
    "warning": "..."
  },
  "legacy": {}
}
```

说明：

- 新调用方只应依赖 `ok + protocol_version + data`
- `legacy` 仅作为过渡兼容字段保留，后续不建议继续依赖
- 当请求同时传入 `lottery_type + year + term` 时，后端会查询 `public.lottery_draws`
- 若该期 `is_opened = 0`，则后端会忽略传入的 `res_code`，避免把未开奖真实号码喂给预测算法

示例：

```powershell
$body = @{ target_hit_rate = 0.65 } | ConvertTo-Json
Invoke-RestMethod `
  -Method POST `
  -Uri http://127.0.0.1:8000/api/predict/title_234 `
  -ContentType application/json `
  -Body $body
```

也支持 GET 查询参数：

```text
/api/predict/title_234?target_hit_rate=0.65&source_table=mode_payload_234
```

## CMS 站点管理接口

## 登录与管理员用户

默认管理员：

```text
用户名：admin
密码：admin123
```

上线部署后必须立即修改默认密码。

### POST `/api/auth/login`

```json
{
  "username": "admin",
  "password": "admin123"
}
```

返回：

```json
{
  "token": "Bearer token",
  "user": {
    "id": 1,
    "username": "admin",
    "display_name": "系统管理员",
    "role": "super_admin",
    "status": true
  }
}
```

后续 `/api/admin/*` 接口需要携带：

```text
Authorization: Bearer <token>
```

### 管理员用户接口

- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/{id}`
- `DELETE /api/admin/users/{id}`

用户字段：

- `username`：登录用户名
- `display_name`：显示名称
- `password`：密码；更新时留空表示不变
- `role`：角色标识
- `status`：是否允许登录

## 彩种管理接口

- `GET /api/admin/lottery-types`
- `POST /api/admin/lottery-types`
- `PUT /api/admin/lottery-types/{id}`

字段：

- `name`：彩种名称
- `draw_time`：开奖时间，例如 `21:30`
- `collect_url`：采集地址
- `status`：状态

## 开奖管理接口

- `GET /api/admin/draws`
- `POST /api/admin/draws`
- `PUT /api/admin/draws/{id}`
- `DELETE /api/admin/draws/{id}`

字段：

- `lottery_type_id`：彩种 ID
- `year`：年份
- `term`：期数
- `numbers`：开奖号码，逗号分隔
- `draw_time`：开奖时间
- `status`：状态
- `is_opened`：是否开奖
- `next_term`：下一期数

### GET `/api/admin/sites`

列出彩票网站配置。

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/admin/sites
```

### POST `/api/admin/sites`

新增站点配置。

```json
{
  "name": "默认盛世站点",
  "enabled": true,
  "start_web_id": 1,
  "end_web_id": 10,
  "manage_url_template": "https://admin.shengshi8800.com/ds67BvM/web/webManage?id={web_id}",
  "modes_data_url": "https://admin.shengshi8800.com/ds67BvM/web/getModesDataList",
  "token": "后台 token",
  "request_limit": 250,
  "request_delay": 0.5,
  "notes": "备注"
}
```

说明：

- `manage_url_template` 必须包含 `{web_id}` 或 `{id}`。
- `modes_data_url` 是获取 `all_data` 的接口地址。
- `token` 会保存到本地 SQLite，仅建议部署在可信内网环境。
- `domain`：站点域名。
- `lottery_type_id`：站点绑定彩种。
- `announcement`：网站公告。

### GET `/api/admin/sites/{site_id}`

查看单个站点。

### PUT `/api/admin/sites/{site_id}`

更新站点。若 `token` 传空或不传，则保留旧 token。

### DELETE `/api/admin/sites/{site_id}`

删除站点配置，不会删除已抓取的彩票数据。

## 抓取与后处理

### POST `/api/admin/sites/{site_id}/fetch`

按站点配置抓取数据，并可选执行归一化和文本映射刷新。

请求体：

```json
{
  "normalize": true,
  "build_text_mappings": true
}
```

处理流程：

1. 按 `start_web_id` 到 `end_web_id` 遍历站点。
2. 通过 `manage_url_template` 获取每个站点的 `modes_list`。
3. 按 `modes_id` 请求 `modes_data_url`，获取 `all_data`。
4. 写入 `fetched_modes` 和 `fetched_mode_records`。
5. 可选执行 `normalize_payload_tables()`，生成 `mode_payload_*`。
6. 可选执行 `build_text_history_mappings()`，刷新文本历史映射池。

示例：

```powershell
$body = @{ normalize = $true; build_text_mappings = $true } | ConvertTo-Json
Invoke-RestMethod `
  -Method POST `
  -Uri http://127.0.0.1:8000/api/admin/sites/1/fetch `
  -ContentType application/json `
  -Body $body
```

### GET `/api/admin/fetch-runs`

查看最近抓取记录。

```text
/api/admin/fetch-runs?limit=20
```

### POST `/api/admin/normalize`

手动执行归一化。

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/api/admin/normalize
```

### POST `/api/admin/text-mappings`

手动刷新 `text_history_mappings`。

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/api/admin/text-mappings
```

## 号码管理接口

号码管理直接读写 `fixed_data` 单表，保证后台配置和预测机制同源。

- `GET /api/admin/numbers?keyword=&limit=300`
- `PUT /api/admin/numbers/{id}`

返回字段：

- `id`
- `name`：名称
- `code`：开奖号码或候选值
- `category_key`：分类标识，对应 `fixed_data.sign`
- `year`
- `status`

## 站点数据管理接口

站点数据管理用于给站点添加预测彩票号码模块，模块来源为：

```text
backend/src/predict/mechanisms.py
```

### GET `/api/admin/sites/{site_id}/prediction-modules`

返回站点已配置模块和全部可用预测机制。

### POST `/api/admin/sites/{site_id}/prediction-modules`

```json
{
  "mechanism_key": "title_234",
  "status": true,
  "sort_order": 0
}
```

### DELETE `/api/admin/sites/{site_id}/prediction-modules/{module_id}`

删除站点预测模块配置。

### POST `/api/admin/sites/{site_id}/prediction-modules/run`

执行某个预测模块。

```json
{
  "mechanism_key": "title_234",
  "target_hit_rate": 0.65
}
```

## 前端管理页面

Next 模板页面位于 `backend/app`：

- `/login`：登录
- `/`：控制台
- `/users`：管理员用户管理
- `/lottery-types`：彩种管理
- `/draws`：开奖管理
- `/sites`：站点管理
- `/sites/{id}/data`：站点数据管理
- `/numbers`：号码管理
- `/prediction-modules`：预测模块列表

前端通过 `backend/app/api/python/[...path]/route.ts` 代理到 Python API，避免浏览器直接跨域访问 Python 服务。

## SQLite 是否足够

当前阶段 SQLite 足够，原因：

- 数据规模主要是本地抓取、归一化和预测回测，单机读多写少。
- 预测机制依赖本地表扫描，SQLite 文件部署和备份成本最低。
- 管理后台当前是少量管理员使用，写入并发压力不高。

建议升级到 PostgreSQL/MySQL 的条件：

- 多管理员高并发写入。
- 需要多实例部署 Python API。
- 抓取任务并发化、队列化，写入频率明显升高。
- 需要更完整的权限、审计、事务隔离和远程备份体系。

结论：开发、单机部署、小团队使用 SQLite 足够；正式商业化、多站点高并发运营建议迁移 PostgreSQL。

## 预测脚本清理说明

`backend/src/predict/predict_*.py` 已删除。后端统一使用：

```text
backend/src/predict/run_prediction.py
```

命令行仍可用：

```powershell
python backend/src/predict/run_prediction.py --mechanism title_234 --json
python backend/src/predict/run_prediction.py --list-mechanisms
```

## 2026-05 PostgreSQL And Frontend Integration Addendum

### Database target

- The backend now accepts either a SQLite file path or a PostgreSQL DSN in `--db-path`.
- Database compatibility helpers live in `backend/src/db.py`.
- Use `backend/src/utils/migrate_sqlite_to_postgres.py` to copy the existing SQLite database into PostgreSQL without regenerating historical prediction data.

Example:

```powershell
python backend/src/utils/migrate_sqlite_to_postgres.py `
  --source-sqlite backend/data/lottery_modes.sqlite3 `
  --target-dsn "postgresql://user:password@host:5432/liuhecai"
```

### Public site page API

- `GET /api/public/site-page`

Query parameters:

- `site_id`: optional site id, defaults to the first enabled site.
- `domain`: optional exact domain match for multi-site resolution.
- `history_limit`: optional history row limit per enabled module.

Response shape:

```json
{
  "site": {
    "id": 1,
    "name": "Default Site"
  },
  "draw": {
    "current_issue": "2026123",
    "result_balls": [],
    "special_ball": null
  },
  "modules": [
    {
      "id": 1,
      "mechanism_key": "title_234",
      "title": "Module title",
      "default_table": "mode_payload_234",
      "sort_order": 0,
      "status": true,
      "history": []
    }
  ]
}
```

Notes:

- This endpoint reads existing historical rows from `mode_payload_*` tables.
- It does not generate new prediction data.
- Public module order follows `site_prediction_modules.sort_order`.
- Public module visibility follows `site_prediction_modules.status`.
- Text-type modules resolve `text_history_mappings` by the same `mode_id` as the module.
- `mode_id=50` returns the legacy-compatible `{"data":[...]}` payload shape in the frontend proxy.

### Admin-only prediction execution

The following routes now require an authenticated admin or super admin token:

- `GET /api/predict/{mechanism}`
- `POST /api/predict/{mechanism}`
- `POST /api/admin/sites/{site_id}/prediction-modules/run`

The public frontend should not call these routes for page rendering.

### Site prediction module management

- `GET /api/admin/sites/{site_id}/prediction-modules`
- `POST /api/admin/sites/{site_id}/prediction-modules`
- `PATCH /api/admin/sites/{site_id}/prediction-modules/{module_id}`
- `PUT /api/admin/sites/{site_id}/prediction-modules/{module_id}`
- `DELETE /api/admin/sites/{site_id}/prediction-modules/{module_id}`

Update payload example:

```json
{
  "status": true,
  "sort_order": 20
}
```

This is the configuration consumed by the frontend public page.

### Frontend runtime configuration

The frontend project now reads backend data through:

- `frontend/lib/backend-api.ts`
- `frontend/app/api/lottery-data/route.ts`
- `frontend/app/page.tsx`

Supported environment variables:

- `LOTTERY_BACKEND_BASE_URL`
  Example: `http://127.0.0.1:8000/api`
- `LOTTERY_SITE_ID`
  Example: `1`

If `LOTTERY_SITE_ID` is not provided, the frontend defaults to site `1`.

前端已有 `frontend/lib/api/predictionRunner.ts` 调用统一入口，不需要每个玩法一个 Python 脚本。
