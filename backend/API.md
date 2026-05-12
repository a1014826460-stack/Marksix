# 后端 API 文档

## 1. 文档目标与适用范围

本文档以 `backend/src/app.py` 当前实际注册的 Python 后端路由为准，面向以下场景：

- 接口调试
- 接口问题排查
- 后台接口扩展
- 前端调用
- 旧接口兼容维护
- 数据库问题定位

本文只描述 Python 后端原生接口，即 `http://127.0.0.1:8000/api/*`。如果管理后台通过 Next.js 代理访问，会在第 9 节单独说明代理路径。

## 2. 系统架构与调用链路

当前后端调用链路分为四层：

1. Python HTTP 入口：`backend/src/app.py`
2. 业务模块：
   - `backend/src/public/api.py`
   - `backend/src/legacy/api.py`
   - `backend/src/admin/`
   - `backend/src/predict/`
   - `backend/src/runtime_config.py`
   - `backend/src/logger.py`
3. 数据访问与建表：
   - `backend/src/db.py`
   - `backend/src/tables.py`
4. 管理端代理与前端调用：
   - `backend/app/api/python/[...path]/route.ts`
   - `backend/lib/admin-api.ts`

调用关系：

- 浏览器管理端请求 `/admin/api/python/...`
- Next.js 代理将其转发到 Python `/api/...`
- Python 后端再进入 `public`、`legacy`、`admin`、`predict` 模块
- 所有正式业务数据统一读写 PostgreSQL

## 3. 启动方式

Python 后端：

```powershell
python backend/src/app.py --host 127.0.0.1 --port 8000
```

管理前端：

```powershell
cd backend
npm run dev -- --hostname 127.0.0.1 --port 3002
```

默认访问地址：

- Python API：`http://127.0.0.1:8000`
- 管理后台：`http://127.0.0.1:3002/admin/login`

## 4. 数据库配置

### 4.1 正式数据库

正式运行只使用 PostgreSQL。

推荐环境变量：

```env
DATABASE_URL=postgresql://user:password@host:5432/liuhecai
```

当前代码的正式运行解析顺序：

1. `DATABASE_URL`
2. `config.yaml` 中 `database.default_postgres_dsn`

如果两者都没有配置，后端应直接失败，不再回退到 SQLite。

### 4.2 SQLite 说明

- `backend/data/lottery_modes.sqlite3` 已废弃，不再作为默认数据库
- SQLite 不参与正式运行
- SQLite 仅保留给历史迁移或显式本地测试

### 4.3 旧 SQLite 数据迁移

项目仍保留历史迁移脚本，但它不参与正式运行：

```bash
python backend/src/deprecated/tools/migrate_sqlite_to_postgres.py \
  --source-sqlite /path/to/old.sqlite3 \
  --target-dsn "$DATABASE_URL"
```

## 5. 鉴权方式

### 5.1 不需要管理员 token 的接口

- `GET /health`
- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/predict/mechanisms`
- `GET /api/public/*`
- `GET /api/legacy/*`

### 5.2 需要 token 的接口

- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET|POST /api/predict/{mechanism}`
- `/api/admin/*`

### 5.3 Token 格式

`POST /api/auth/login` 返回的是原始 token，不含 `Bearer ` 前缀。后续请求必须自行拼接：

```text
Authorization: Bearer <token>
```

### 5.4 角色限制

当前代码里，以下“主动生成/执行”接口额外要求用户角色为 `admin` 或 `super_admin`：

- `GET|POST /api/predict/{mechanism}`
- `POST /api/admin/lottery-types/{id}/crawl-only`
- `POST /api/admin/lottery-types/{id}/crawl-and-generate`
- `POST /api/admin/sites/{site_id}/mode-payload/{table}/regenerate`
- `POST /api/admin/sites/{site_id}/prediction-modules/run`
- `POST /api/admin/sites/{site_id}/prediction-modules/generate-all`

## 6. 通用请求规范

- 请求体默认使用 JSON
- 有请求体时建议带 `Content-Type: application/json`
- 管理接口统一返回 UTF-8 JSON
- 布尔参数多数支持 `1/0`、`true/false`
- 常见时间格式：
  - 开奖时间：`YYYY-MM-DD HH:mm:ss`
  - 彩种展示时间：通常为 `HH:mm`
  - 日志和会话过期时间：ISO datetime

## 7. 通用响应规范

当前项目存在“新接口规范”和“历史接口返回结构并存”的情况。

### 7.1 当前统一错误结构

绝大多数错误由 `send_error_json(...)` 返回：

```json
{
  "ok": false,
  "error": "错误说明",
  "detail": "可选，调试细节或 traceback"
}
```

### 7.2 推荐的新接口成功结构

新增接口建议优先遵守：

```json
{
  "ok": true,
  "data": {}
}
```

### 7.3 当前代码中的实际情况

历史接口仍大量保留专用结构，例如：

- `/api/auth/login`：`{ token, expires_at, user }`
- `/api/admin/users`：`{ users: [...] }`
- `/api/admin/draws`：`{ draws: [...] }`
- `/api/public/site-page`：`{ site, draw, modules }`
- `/api/predict/{mechanism}`：`{ ok, protocol_version, generated_at, data, legacy }`

## 8. 通用错误码

当前后端主要使用以下 HTTP 状态码：

- `400 Bad Request`：参数错误、业务校验失败
- `401 Unauthorized`：未登录、token 无效或过期
- `403 Forbidden`：已登录但角色权限不足
- `404 Not Found`：路由不存在、资源不存在
- `405 Method Not Allowed`：方法不支持
- `500 Internal Server Error`：未捕获异常、依赖服务异常

## 9. 前端代理说明

### 9.1 Python 原生路径

Python 后端真实路由统一是：

```text
/api/...
```

例如：

```text
/api/admin/sites
/api/public/site-page
/api/predict/pt2xiao
```

### 9.2 管理端 Next.js 代理路径

管理前端实际通过 `backend/app/api/python/[...path]/route.ts` 转发，请求浏览器路径为：

```text
/admin/api/python/...
```

示例：

- Python 原生：`/api/admin/lottery-types`
- 管理端代理：`/admin/api/python/admin/lottery-types`

代理目标地址由以下环境变量控制：

```env
PYTHON_API_BASE_URL=http://127.0.0.1:8000
```

默认值也是 `http://127.0.0.1:8000`。

### 9.3 注意

- 本文默认写 Python 原生路径
- 如果你在管理后台页面里调试，请把路径换成 `/admin/api/python/...`
- 不要把 Python 原生路径 `/api/...` 和管理端代理路径 `/admin/api/python/...` 混用

## 10. 健康检查接口

### GET `/api/health`

接口说明：返回当前数据库连接摘要和关键表统计。

鉴权要求：

- 是否需要登录：否
- Header：无

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| 无 | - | - | - | - |

请求体：

```json
{}
```

成功响应：

```json
{
  "ok": true,
  "summary": {
    "db_target": "postgresql://...",
    "db_engine": "postgres",
    "admin_users": 1,
    "lottery_types": 3,
    "lottery_draws": 100,
    "sites": 4,
    "fetched_modes": 0,
    "fetched_mode_records": 0,
    "mode_payload_tables": 0,
    "text_history_mappings": 0,
    "site_prediction_modules": 0,
    "legacy_image_assets": 0,
    "prediction_mechanisms": 29
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "错误说明"
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/health"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/health"
```

前端调用示例：

```ts
const res = await fetch("http://127.0.0.1:8000/api/health")
const data = await res.json()
```

调试提示：

- `db_engine` 正式运行应为 `postgres`
- `/health` 也是已实现的健康别名，但返回结构不同：`{ status, engine }`

## 11. 公开前台接口

状态：已实现

### GET `/api/public/site-page`

接口说明：返回公开站点首页数据，不主动生成预测，只读取已配置站点模块与历史记录。

鉴权要求：

- 是否需要登录：否
- Header：无

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `site_id` | int | 否 | - | 指定站点 ID |
| `domain` | string | 否 | - | 按域名匹配启用站点 |
| `history_limit` | int | 否 | `8` | 每个模块返回的历史条数 |

请求体：

```json
{}
```

成功响应：

```json
{
  "site": {
    "id": 4,
    "name": "盛世台湾六合彩",
    "domain": "example.com",
    "lottery_type_id": 3,
    "start_web_id": 4,
    "end_web_id": 4,
    "enabled": true
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
      "sort_order": 10,
      "status": true,
      "title": "平特2肖",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "history_table": "mode_payload_43",
      "history_schema": "created",
      "history_sources": ["created", "public"],
      "history": []
    }
  ]
}
```

失败响应：

```json
{
  "ok": false,
  "error": "未找到可展示的站点配置"
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/public/site-page?site_id=4&history_limit=8"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/public/site-page?domain=example.com&history_limit=8"
```

前端调用示例：

```ts
const res = await fetch(
  "http://127.0.0.1:8000/api/public/site-page?site_id=4&history_limit=8",
)
const data = await res.json()
```

调试提示：

- 公开页只返回站点已启用的 `site_prediction_modules`
- 历史数据优先读 `created.mode_payload_*`，不足时回退 `public.mode_payload_*`
- 开奖结果统一以 `lottery_draws` 为准
- 若对应期次 `is_opened = 0`，不会对外暴露真实开奖字段

### GET `/api/public/latest-draw`

接口说明：返回指定彩种最近一期已开奖数据。

鉴权要求：

- 是否需要登录：否

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `lottery_type` | int | 否 | `1` | 彩种 ID |

请求体：

```json
{}
```

成功响应：

```json
{
  "current_issue": "2026125",
  "result_balls": [
    { "value": "04", "color": "blue", "zodiac": "兔" }
  ],
  "special_ball": {
    "value": "40",
    "color": "red",
    "zodiac": "兔"
  }
}
```

失败响应：

```json
{
  "current_issue": "",
  "result_balls": [],
  "special_ball": null
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/public/latest-draw?lottery_type=3"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/public/latest-draw?lottery_type=3"
```

前端调用示例：

```ts
const res = await fetch(
  "http://127.0.0.1:8000/api/public/latest-draw?lottery_type=3",
)
const data = await res.json()
```

调试提示：

- 该接口只读取 `lottery_draws.is_opened = 1` 的记录
- 不会因为未开奖期已经抓到 `numbers` 就提前对外展示

### GET `/api/public/next-draw-deadline`

接口说明：返回最新期次与下一期开奖时间摘要。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `lottery_type` | int | 否 | `3` | 彩种 ID |

成功响应示例：

```json
{
  "current_issue": "2026125",
  "next_issue": "2026126",
  "next_time": "1747146600000",
  "server_time": "1747041600"
}
```

### GET `/api/public/draw-history`

接口说明：返回指定彩种某年的已开奖历史。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `lottery_type` | int | 否 | `3` | 彩种 ID |
| `year` | int | 否 | 当前年份 | 查询年份 |
| `sort` | string | 否 | `l` | `l`=落球顺序，`d`=号码排序 |

成功响应包含：

- `lottery_type`
- `lottery_name`
- `year`
- `sort`
- `years`
- `items`

## 12. 旧站兼容接口

状态：已实现，建议新业务不要继续依赖。

### GET `/api/legacy/current-term`

接口说明：给旧站 JS 返回当前已开奖期号和下一预测期号。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `lottery_type_id` | int | 否 | `1` | 彩种 ID |

成功响应示例：

```json
{
  "lottery_type_id": 3,
  "term": "125",
  "issue": "2026125",
  "next_term": "126"
}
```

### GET `/api/legacy/post-list`

接口说明：返回旧站图片卡片列表。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `pc` | int | 否 | 配置值 | 旧站来源 PC 参数 |
| `web` | int | 否 | 配置值 | 旧站来源站点参数 |
| `type` | int | 否 | 配置值 | 旧站来源彩种参数 |
| `limit` | int | 否 | `20` | 返回条数 |

成功响应示例：

```json
{
  "data": [
    {
      "id": 1,
      "title": null,
      "file_name": "a.jpg",
      "legacy_upload_path": "/uploads/image/20250322/a.jpg"
    }
  ]
}
```

### GET `/api/legacy/module-rows`

接口说明：返回指定 `modes_id` 的旧模块历史行。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `modes_id` | int | 是 | - | 玩法 ID |
| `web` | int | 否 | - | 站点来源过滤 |
| `type` | int | 否 | - | 彩种类型过滤 |
| `limit` | int | 否 | `10` | 返回条数 |

成功响应包含：

- `modes_id`
- `title`
- `table_name`
- `rows`

兼容说明：

- 优先返回 `created` 里的生成结果
- 不足时回退到 `public`
- 同一期同时存在时优先 `created`

## 13. 登录与管理员接口

状态：已实现

### POST `/api/auth/login`

接口说明：管理员登录，返回原始 token 与用户信息。

鉴权要求：

- 是否需要登录：否
- Header：
  - `Content-Type: application/json`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| 无 | - | - | - | - |

请求体：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

成功响应：

```json
{
  "token": "raw-token-string",
  "expires_at": "2026-05-13T09:00:00+00:00",
  "user": {
    "id": 1,
    "username": "admin",
    "display_name": "系统管理员",
    "role": "super_admin",
    "status": true
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "用户名或密码错误"
}
```

curl 示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "admin", password: "admin123" }),
})
const data = await res.json()
localStorage.setItem("liuhecai_admin_token", data.token)
```

调试提示：

- 返回的是原始 token，不带 `Bearer `
- 后续请求头必须手动拼 `Authorization: Bearer <token>`

### GET `/api/auth/me`

接口说明：返回当前登录管理员信息。

成功响应：

```json
{
  "user": {
    "id": 1,
    "username": "admin",
    "role": "super_admin",
    "status": true
  }
}
```

### POST `/api/auth/logout`

接口说明：删除当前 session。

成功响应：

```json
{
  "ok": true
}
```

### 管理员用户接口

已实现路由：

- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/{id}`
- `PATCH /api/admin/users/{id}`
- `DELETE /api/admin/users/{id}`

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `username` | string | 必填，管理员用户名 |
| `display_name` | string | 选填，默认回退为用户名 |
| `role` | string | 当前代码未做强枚举校验；生成类权限实际依赖 `admin` / `super_admin` |
| `status` | bool/int | `true/1` 表示可登录，`false/0` 表示禁用 |
| `password` | string | 新增时必填；更新时留空表示不修改密码 |

创建成功响应：

```json
{
  "user": {
    "id": 2,
    "username": "editor",
    "display_name": "编辑",
    "role": "admin",
    "status": true
  }
}
```

删除限制：

- 系统至少要保留一个可登录管理员

## 14. 彩种管理接口

状态：已实现

已实现路由：

- `GET /api/admin/lottery-types`
- `POST /api/admin/lottery-types`
- `PUT /api/admin/lottery-types/{id}`
- `PATCH /api/admin/lottery-types/{id}`
- `DELETE /api/admin/lottery-types/{id}`
- `POST /api/admin/lottery-types/{id}/crawl-only`
- `POST /api/admin/lottery-types/{id}/crawl-and-generate`

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 彩种主键 |
| `name` | string | 必填，彩种名称 |
| `draw_time` | string | 展示用开奖时间，当前项目通常使用 `HH:mm` |
| `collect_url` | string | 开奖抓取源地址 |
| `next_time` | string | 服务端推导，不接受前端直接修改 |
| `status` | bool/int | 是否启用 |

### GET `/api/admin/lottery-types`

接口说明：返回彩种列表。

鉴权要求：

- 是否需要登录：是
- Header：
  - `Authorization: Bearer <token>`

成功响应：

```json
{
  "lottery_types": [
    {
      "id": 3,
      "name": "台湾彩",
      "draw_time": "22:30",
      "collect_url": "",
      "next_time": "1747146600000",
      "status": true
    }
  ]
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/admin/lottery-types" \
  -H "Authorization: Bearer <token>"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/admin/lottery-types" `
  -Headers @{ Authorization = "Bearer <token>" }
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/admin/lottery-types", {
  headers: { Authorization: `Bearer ${token}` },
})
const data = await res.json()
```

### PUT `/api/admin/lottery-types/{id}`

接口说明：更新彩种信息。

请求体：

```json
{
  "name": "台湾彩",
  "draw_time": "22:30",
  "collect_url": "",
  "status": true
}
```

成功响应：

```json
{
  "lottery_type": {
    "id": 3,
    "name": "台湾彩",
    "draw_time": "22:30",
    "collect_url": "",
    "next_time": "1747146600000",
    "status": true
  }
}
```

前端调用示例：

```ts
await fetch("/admin/api/python/admin/lottery-types/3", {
  method: "PUT",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({
    name: "台湾彩",
    draw_time: "22:30",
    collect_url: "",
    status: true,
  }),
})
```

### 爬取相关彩种接口

- `POST /api/admin/lottery-types/{id}/crawl-only`
  - 立即爬取指定彩种数据
- `POST /api/admin/lottery-types/{id}/crawl-and-generate`
  - 提交后台任务，返回 `{ ok, job_id, message }`

## 15. 开奖管理接口

状态：已实现

已实现路由：

- `GET /api/admin/draws`
- `POST /api/admin/draws`
- `PUT /api/admin/draws/{id}`
- `PATCH /api/admin/draws/{id}`
- `DELETE /api/admin/draws/{id}`

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `lottery_type_id` | int | 彩种 ID。当前创建/更新逻辑只允许 `3`（台湾彩） |
| `year` | int | 年份 |
| `term` | int | 期号 |
| `numbers` | string | 必须是 7 个逗号分隔号码 |
| `draw_time` | string | 开奖时间，格式通常为 `YYYY-MM-DD HH:mm:ss` |
| `next_time` | string | 下一期开奖时间戳字符串 |
| `is_opened` | bool/int | 是否允许对外展示开奖结果 |
| `next_term` | int | 下一期号 |
| `status` | bool/int | 记录状态 |

### GET `/api/admin/draws`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `limit` | int | 否 | `200` | 返回条数 |

成功响应：

```json
{
  "draws": [
    {
      "id": 1,
      "lottery_type_id": 3,
      "lottery_name": "台湾彩",
      "year": 2026,
      "term": 125,
      "numbers": "04,27,38,11,45,08,40",
      "draw_time": "2026-05-12 22:30:00",
      "next_time": "1747146600000",
      "status": true,
      "is_opened": true,
      "next_term": 126
    }
  ]
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/admin/draws?limit=50" \
  -H "Authorization: Bearer <token>"
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/admin/draws?limit=50", {
  headers: { Authorization: `Bearer ${token}` },
})
```

### POST `/api/admin/draws`

请求体：

```json
{
  "lottery_type_id": 3,
  "year": 2026,
  "term": 126,
  "numbers": "01,02,03,04,05,06,07",
  "draw_time": "2026-05-13 22:30:00",
  "is_opened": false,
  "status": true,
  "next_term": 127
}
```

成功响应：

```json
{
  "draw": {
    "id": 2,
    "lottery_type_id": 3,
    "year": 2026,
    "term": 126,
    "numbers": "01,02,03,04,05,06,07",
    "is_opened": false,
    "status": true
  }
}
```

调试提示：

- `numbers` 必须恰好 7 个号码，范围 `01` 到 `49`
- 创建/更新非台湾彩会被拒绝
- `draw_time` 未到时，不能提前设置 `is_opened = true`
- 公开接口是否暴露开奖结果依赖 `is_opened`

## 16. 站点管理接口

状态：已实现

已实现路由：

- `GET /api/admin/sites`
- `POST /api/admin/sites`
- `GET /api/admin/sites/{site_id}`
- `PUT /api/admin/sites/{site_id}`
- `PATCH /api/admin/sites/{site_id}`
- `DELETE /api/admin/sites/{site_id}`

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 站点主键 |
| `name` | string | 站点名称 |
| `domain` | string | 公开站点域名 |
| `lottery_type_id` | int | 绑定彩种 |
| `enabled` | bool/int | 是否启用 |
| `start_web_id` | int | 抓取起始 web_id |
| `end_web_id` | int | 抓取结束 web_id |
| `manage_url_template` | string | 站点后台列表地址模板，必须包含 `{web_id}` 或 `{id}` |
| `modes_data_url` | string | 玩法详情数据接口 |
| `request_limit` | int | 单次抓取页大小 |
| `request_delay` | float | 请求间隔秒数 |
| `announcement` | string | 公告 |
| `notes` | string | 备注 |
| `token_present` | bool | 是否已配置 token |
| `token_preview` | string | token 前 8 位预览，不返回明文 |

说明：

- 当前站点表主键是 `id`
- `start_web_id / end_web_id` 是抓取来源范围
- 不要把 `web_id` 与 `managed_sites.id` 混为一谈

### GET `/api/admin/sites`

成功响应：

```json
{
  "sites": [
    {
      "id": 4,
      "name": "盛世台湾六合彩",
      "domain": "example.com",
      "lottery_type_id": 3,
      "lottery_name": "台湾彩",
      "enabled": true,
      "start_web_id": 4,
      "end_web_id": 4,
      "token_present": true,
      "token_preview": "abcd1234..."
    }
  ]
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/admin/sites" \
  -H "Authorization: Bearer <token>"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/admin/sites" `
  -Headers @{ Authorization = "Bearer <token>" }
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/admin/sites", {
  headers: { Authorization: `Bearer ${token}` },
})
```

### POST `/api/admin/sites`

请求体：

```json
{
  "name": "盛世台湾六合彩",
  "domain": "example.com",
  "lottery_type_id": 3,
  "enabled": true,
  "start_web_id": 4,
  "end_web_id": 4,
  "manage_url_template": "https://example.com/index.php?c=manage&a=modes_list&id={web_id}",
  "modes_data_url": "https://example.com/index.php?c=api&a=modes_data",
  "token": "secret-token",
  "request_limit": 250,
  "request_delay": 0.5,
  "announcement": "",
  "notes": ""
}
```

成功响应：

```json
{
  "site": {
    "id": 5,
    "name": "盛世台湾六合彩",
    "enabled": true,
    "token_present": true,
    "token_preview": "secret-t..."
  }
}
```

注意：

- 新建站点后，后端会尝试复制 `site_id=1` 的预测模块配置到新站点
- `token` 会保存到 PostgreSQL，但普通查询不会返回明文

## 17. 抓取与后处理接口

状态：已实现

抓取链路：

```text
站点配置
-> 抓取 modes_list
-> 抓取 modes_data
-> 写入 fetched_modes / fetched_mode_records
-> 归一化 mode_payload_*
-> 刷新 text_history_mappings
```

已实现路由：

- `POST /api/admin/sites/{site_id}/fetch`
- `GET /api/admin/fetch-runs`
- `POST /api/admin/normalize`
- `POST /api/admin/text-mappings`
- `GET /api/admin/jobs/{job_id}`
- `GET /api/admin/lottery-draws/latest-term`
- `POST /api/admin/crawler/run-hk`
- `POST /api/admin/crawler/run-macau`
- `POST /api/admin/crawler/run-all`
- `POST /api/admin/crawler/import-taiwan`
- `GET /api/admin/legacy-images`

### POST `/api/admin/sites/{site_id}/fetch`

接口说明：按站点配置抓取数据，并可选执行归一化与文本映射刷新。

请求体：

```json
{
  "normalize": true,
  "build_text_mappings": true
}
```

成功响应：

```json
{
  "run_id": 12,
  "status": "success",
  "message": "抓取完成",
  "modes_count": 28,
  "records_count": 560,
  "post_process": {
    "normalized_tables": 28,
    "text_mappings": {
      "ok": true
    }
  }
}
```

curl 示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/sites/4/fetch" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"normalize\":true,\"build_text_mappings\":true}"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/admin/sites/4/fetch" `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"normalize":true,"build_text_mappings":true}'
```

前端调用示例：

```ts
await fetch("/admin/api/python/admin/sites/4/fetch", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ normalize: true, build_text_mappings: true }),
})
```

调试提示：

- 失败后先查 `/api/admin/fetch-runs`
- 异常详情看 `/api/admin/logs`
- 若站点被禁用，会直接拒绝抓取

### GET `/api/admin/fetch-runs`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `limit` | int | 否 | `20` | 返回条数 |

成功响应：

```json
{
  "runs": [
    {
      "id": 12,
      "site_id": 4,
      "site_name": "盛世台湾六合彩",
      "status": "success",
      "message": "抓取完成",
      "modes_count": 28,
      "records_count": 560
    }
  ]
}
```

### POST `/api/admin/normalize`

接口说明：执行 `mode_payload_*` 归一化。

成功响应：

```json
{
  "normalized_tables": 28,
  "tables": []
}
```

### POST `/api/admin/text-mappings`

接口说明：重建文本历史映射。

### GET `/api/admin/jobs/{job_id}`

接口说明：查询后台任务状态。

### GET `/api/admin/lottery-draws/latest-term`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `lottery_type_id` | int | 否 | `1` | 彩种 ID |

成功响应：

```json
{
  "year": 2026,
  "term": 125,
  "draw_time": "2026-05-12 22:30:00"
}
```

## 18. 号码管理接口

状态：已实现

这些接口直接读写 `fixed_data`，预测模块也依赖这张表。

已实现路由：

- `GET /api/admin/numbers`
- `POST /api/admin/numbers`
- `PUT /api/admin/numbers/{id}`
- `PATCH /api/admin/numbers/{id}`
- `DELETE /api/admin/numbers/{id}`

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 主键 |
| `name` | string | 显示名称 |
| `code` | string | 号码 |
| `category_key` | string | 分类键，底层对应 `sign` |
| `year` | string | 年份或映射批次 |
| `status` | bool/int | 启用状态 |
| `type` | int | 业务类型字段 |
| `xu` | int | 顺序字段 |

### GET `/api/admin/numbers`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `limit` | int | 否 | `300` | 返回条数 |
| `keyword` | string | 否 | `""` | 模糊匹配 `name/sign/code` |

成功响应：

```json
{
  "numbers": [
    {
      "id": 1,
      "name": "兔",
      "code": "04",
      "category_key": "生肖",
      "year": "2026",
      "status": true,
      "type": 0,
      "xu": 0
    }
  ]
}
```

### PUT `/api/admin/numbers/{id}`

接口说明：更新固定号码映射。

## 19. 预测机制接口

状态：已实现

### GET `/api/predict/mechanisms`

接口说明：列出当前所有预测机制及其默认表、默认 mode_id、启用状态。

鉴权要求：

- 是否需要登录：否

成功响应：

```json
{
  "mechanisms": [
    {
      "key": "pt2xiao",
      "title": "平特2肖",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "status": 1
    }
  ]
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/predict/mechanisms"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/predict/mechanisms"
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/predict/mechanisms")
const data = await res.json()
```

### POST `/api/predict/{mechanism}`

接口说明：执行指定预测机制。支持 `GET` 和 `POST` 两种方式，但都要求已登录且有生成权限。

鉴权要求：

- 是否需要登录：是
- Header：
  - `Authorization: Bearer <token>`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `res_code` | string | 否 | - | 7 个号码，逗号分隔 |
| `content` | string | 否 | - | 调试信息透传 |
| `source_table` | string | 否 | 机制默认表 | 指定历史来源表，例如 `mode_payload_43` |
| `target_hit_rate` | float | 否 | 配置值 | 目标回测命中率 |
| `lottery_type` | int/string | 否 | - | 彩种 |
| `year` | int/string | 否 | - | 年份 |
| `term` | int/string | 否 | - | 期号 |
| `web` | int/string | 否 | `4` | web 标识 |

请求体：

```json
{
  "res_code": "02,25,11,33,06,41,01",
  "content": null,
  "source_table": "mode_payload_43",
  "target_hit_rate": 0.65,
  "lottery_type": 3,
  "year": "2026",
  "term": "127",
  "web": "4"
}
```

成功响应：

```json
{
  "ok": true,
  "protocol_version": 1,
  "generated_at": "2026-05-12T09:24:26.394Z",
  "data": {
    "mechanism": {
      "key": "pt2xiao",
      "title": "平特2肖",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "resolved_labels": []
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
      "latest_outcome": null,
      "draw": {
        "result_visibility": "hidden",
        "reason": "draw_found"
      }
    },
    "prediction": {
      "labels": [],
      "content": {},
      "content_json": "{}",
      "display_text": "{}"
    },
    "backtest": {},
    "explanation": [],
    "warning": ""
  },
  "legacy": {}
}
```

失败响应：

```json
{
  "ok": false,
  "error": "不支持的预测机制: title_48。当前支持: ..."
}
```

curl 示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/predict/pt2xiao" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"source_table\":\"mode_payload_43\",\"target_hit_rate\":0.65,\"lottery_type\":3,\"year\":\"2026\",\"term\":\"127\",\"web\":\"4\"}"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/predict/pt2xiao" `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"source_table":"mode_payload_43","target_hit_rate":0.65,"lottery_type":3,"year":"2026","term":"127","web":"4"}'
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/predict/pt2xiao", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({
    source_table: "mode_payload_43",
    target_hit_rate: 0.65,
    lottery_type: 3,
    year: "2026",
    term: "127",
    web: "4",
  }),
})
```

调试提示：

- 预测接口只负责生成预测资料，不承诺预测准确率
- 若指定期次尚未开奖，后端会阻止把真实 `res_code` 注入预测
- `mechanism_key` 必须能在 `backend/src/predict/mechanisms.py` 中解析

### 管理端预测机制列表与状态接口

已实现路由：

- `GET /api/admin/predict/mechanisms`
- `PATCH /api/admin/predict/mechanisms/{key}`

说明：

- `GET` 返回的结构与 `/api/predict/mechanisms` 一样
- `PATCH` 请求体为 `{ "status": 0 | 1 }`
- 代码注释里写了 `/{key}/status`，但 Python 实际路由匹配的是 `PATCH /api/admin/predict/mechanisms/{key}`

## 20. 站点预测模块接口

状态：已实现

已实现路由：

- `GET /api/admin/sites/{site_id}/prediction-modules`
- `POST /api/admin/sites/{site_id}/prediction-modules`
- `PUT /api/admin/sites/{site_id}/prediction-modules/{module_id}`
- `PATCH /api/admin/sites/{site_id}/prediction-modules/{module_id}`
- `DELETE /api/admin/sites/{site_id}/prediction-modules/{module_id}`
- `POST /api/admin/sites/{site_id}/prediction-modules/run`
- `POST /api/admin/sites/{site_id}/prediction-modules/generate-all`

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `mechanism_key` | string | 对应 `predict/mechanisms.py` 中的机制 key |
| `mode_id` | int | 玩法 ID，未传时回退机制默认 `default_modes_id` |
| `status` | bool/int | 是否启用 |
| `sort_order` | int | 展示顺序 |

### GET `/api/admin/sites/{site_id}/prediction-modules`

成功响应：

```json
{
  "site": {
    "id": 4,
    "name": "盛世台湾六合彩"
  },
  "modules": [
    {
      "id": 1,
      "site_id": 4,
      "mechanism_key": "pt2xiao",
      "mode_id": 43,
      "status": 1,
      "sort_order": 10,
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "display_title": "平特2肖",
      "resolved_mode_id": 43
    }
  ],
  "available_mechanisms": [
    {
      "key": "pt2xiao",
      "title": "平特2肖",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "configured": true
    }
  ]
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/admin/sites/4/prediction-modules" \
  -H "Authorization: Bearer <token>"
```

前端调用示例：

```ts
const res = await fetch("/admin/api/python/admin/sites/4/prediction-modules", {
  headers: { Authorization: `Bearer ${token}` },
})
```

### POST `/api/admin/sites/{site_id}/prediction-modules/run`

接口说明：执行一次站点预测模块。

请求体：

```json
{
  "mechanism_key": "pt2xiao",
  "res_code": "",
  "content": "",
  "source_table": "mode_payload_43",
  "target_hit_rate": 0.65
}
```

成功响应：

返回结构与 `/api/predict/{mechanism}` 内部 `predict(...)` 原始结果一致，不是统一的 `{ module: ... }` 包装。

curl 示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/sites/4/prediction-modules/run" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"mechanism_key\":\"pt2xiao\",\"source_table\":\"mode_payload_43\",\"target_hit_rate\":0.65}"
```

前端调用示例：

```ts
await fetch("/admin/api/python/admin/sites/4/prediction-modules/run", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({
    mechanism_key: "pt2xiao",
    source_table: "mode_payload_43",
    target_hit_rate: 0.65,
  }),
})
```

### POST `/api/admin/sites/{site_id}/prediction-modules/generate-all`

接口说明：按期号范围批量生成预测数据，返回后台任务。

请求体常用字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `start_issue` | string | 是 | 起始期号，例如 `2026001` |
| `end_issue` | string | 是 | 结束期号，例如 `2026010` |
| `lottery_type` | int | 否 | 默认取站点绑定彩种 |
| `mechanism_keys` | array/string | 否 | 指定机制 key 列表 |
| `future_periods` | int | 否 | 未来期数 |
| `future_only` | bool | 否 | 仅未来期 |

成功响应：

```json
{
  "ok": true,
  "job_id": "job-123",
  "message": "批量生成已放入后台执行，可通过 /api/admin/jobs/{job_id} 查询进度"
}
```

### 站点数据表管理接口

这组接口已实现，但它们操作的是 `mode_payload_*` 明细表，适合站点数据维护。

已实现路由：

- `GET /api/admin/sites/{site_id}/mode-payload/{table}`
- `POST /api/admin/sites/{site_id}/mode-payload/{table}/regenerate`
- `PUT /api/admin/sites/{site_id}/mode-payload/{table}/{row_id}`
- `PATCH /api/admin/sites/{site_id}/mode-payload/{table}/{row_id}`
- `DELETE /api/admin/sites/{site_id}/mode-payload/{table}/{row_id}`

说明：

- `table` 必须匹配 `mode_payload_{数字}`
- 列表查询支持 `type`、`web`、`page`、`page_size`、`search`、`source=public|created|all`
- 更新/删除时 `source` 只能是 `public` 或 `created`

## 21. 日志管理接口

状态：已实现

已实现路由：

- `GET /api/admin/logs`
- `GET /api/admin/logs/{id}`
- `GET /api/admin/logs/modules`
- `GET /api/admin/logs/levels`
- `GET /api/admin/logs/stats`
- `GET /api/admin/logs/export`
- `POST /api/admin/logs/cleanup`

### GET `/api/admin/logs`

支持筛选参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | int | 页码，默认 `1` |
| `page_size` | int | 每页数量，最大 `200` |
| `level` | string | 日志级别 |
| `module` | string | 模块名模糊匹配 |
| `keyword` | string | `message/exc_message/stack_trace` 模糊匹配 |
| `date_from` | string | 起始时间 |
| `date_to` | string | 结束时间 |
| `user_id` | string | 用户 ID |
| `site_id` | string | 站点 ID |
| `web_id` | string | web ID |
| `lottery_type_id` | string | 彩种 ID |
| `year` | string | 年份 |
| `term` | string | 期号 |
| `task_type` | string | 任务类型 |
| `task_key` | string | 任务键 |
| `path` | string | 请求路径 |

成功响应：

```json
{
  "items": [],
  "rows": [],
  "total": 0,
  "page": 1,
  "page_size": 30,
  "total_pages": 1,
  "available_levels": ["ERROR"],
  "available_modules": ["app"]
}
```

### 其他日志接口

- `GET /api/admin/logs/{id}`：返回单条日志详情
- `GET /api/admin/logs/modules`：返回模块名列表
- `GET /api/admin/logs/levels`：返回级别列表
- `GET /api/admin/logs/stats`：返回总量、24h 数据量、按级别统计、文件目录大小
- `GET /api/admin/logs/export`：当前只支持 `level/module/keyword/date_from/date_to`
- `POST /api/admin/logs/cleanup`：触发一次清理，返回 `{ ok, db_deleted, db_remaining }`

## 22. 配置管理接口

状态：已实现

已实现路由：

- `GET /api/admin/system-config`
- `PUT /api/admin/system-config/{key}`
- `PATCH /api/admin/system-config/{key}`
- `GET /api/admin/configs/groups`
- `POST /api/admin/configs/batch-update`
- `GET /api/admin/configs/effective`
- `GET /api/admin/configs/effective/{key}`
- `GET /api/admin/configs/history`
- `POST /api/admin/configs/{key}/reset`

未实现路由：

- `GET /api/admin/configs`

### 配置分组

当前代码内置分组：

- `lottery`：彩种配置
- `scheduler`：调度器配置
- `prediction`：预测资料配置
- `site`：站点配置
- `logging`：日志配置
- `auth`：认证配置
- `system`：系统配置
- `legacy`：旧站兼容配置

### GET `/api/admin/system-config`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `prefix` | string | 否 | `""` | 按 key 前缀过滤 |
| `include_secrets` | bool/int | 否 | `0` | 是否返回敏感值明文 |

成功响应：

```json
{
  "configs": [
    {
      "key": "database.default_postgres_dsn",
      "value_text": "",
      "value_type": "string",
      "description": "Bootstrap PostgreSQL DSN for initial startup.",
      "is_secret": 1,
      "updated_at": "2026-05-12T09:00:00.000Z"
    }
  ]
}
```

### PUT `/api/admin/system-config/{key}`

请求体：

```json
{
  "value": 0.65,
  "value_type": "float",
  "description": "默认命中率",
  "is_secret": false,
  "change_reason": "后台调整"
}
```

成功响应：

```json
{
  "config": {
    "key": "prediction.default_target_hit_rate",
    "value_text": "0.65",
    "value_type": "float"
  }
}
```

### 其他配置接口

- `GET /api/admin/configs/groups`
  - 返回 `{ groups: [...] }`
- `POST /api/admin/configs/batch-update`
  - 请求体：`{ "updates": [{ "key": "...", "value": ..., "value_type": "..." }] }`
- `GET /api/admin/configs/effective`
  - 查询参数：`group`、`keyword`、`source`
- `GET /api/admin/configs/effective/{key}`
  - 返回单个配置的 `value/default_value/effective_value/source`
- `GET /api/admin/configs/history`
  - 查询参数：`key`、`page`、`page_size`
- `POST /api/admin/configs/{key}/reset`
  - 恢复到 `config.yaml` 默认值

## 23. 调试与排错指南

### 23.1 接口 404

检查：

1. Python API 是否启动在 `127.0.0.1:8000`
2. 请求路径是否带了 `/api`
3. 是否把 `/api/...` 与 `/admin/api/python/...` 混用了
4. 对应路由是否真的在 `backend/src/app.py` 注册
5. 请求方法是否正确

### 23.2 接口 401 / 403

检查：

1. 是否已经执行 `POST /api/auth/login`
2. 是否带了 `Authorization` 头
3. 是否拼成 `Bearer <token>`
4. token 是否过期
5. 当前用户 `role` 是否有生成权限

### 23.3 接口 400

检查：

1. JSON 请求体是否合法
2. `Content-Type` 是否正确
3. 必填参数是否缺失
4. 参数类型是否错误
5. 时间格式是否符合要求
6. `mechanism_key` 是否真实存在
7. `mode_payload_*` 表名是否符合 `mode_payload_{数字}`

### 23.4 接口 500

检查：

1. `DATABASE_URL` 是否正确
2. PostgreSQL 是否启动
3. 关键表是否存在
4. `created` schema 是否存在
5. `mode_payload_*` 是否存在
6. 后端日志是否有 traceback
7. `/api/admin/logs` 是否能查到对应错误

### 23.5 前端能访问但接口失败

检查：

1. `PYTHON_API_BASE_URL` 是否正确
2. 浏览器访问的是 `/admin/api/python/...` 还是 Python 原生 `/api/...`
3. Next.js `basePath=/admin` 是否被正确考虑
4. 浏览器 Network 面板里的真实请求 URL
5. Python 后端日志

### 23.6 预测资料为空

检查：

1. 站点是否绑定了正确 `lottery_type_id`
2. 站点是否配置了 `prediction-modules`
3. `mechanism_key` 是否存在于 `predict/mechanisms.py`
4. 对应 `mode_payload_*` 是否有历史数据
5. `lottery_draws` 是否存在对应期号
6. 是否误把未开奖期的真实结果当作可见结果

## 24. 新增 API 开发规范

### 24.1 后端新增接口流程

1. 在合适模块中新增处理逻辑：
   - `public`
   - `legacy`
   - `admin`
   - `predict`
2. 在 `backend/src/app.py` 注册路由
3. 统一解析 query 与 JSON body
4. 做参数校验
5. 做鉴权校验
6. 使用统一数据库连接
7. 返回 JSON
8. 记录关键日志
9. 更新本文档

### 24.2 响应规范

新增接口优先返回：

```json
{
  "ok": true,
  "data": {}
}
```

列表接口优先返回：

```json
{
  "ok": true,
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

错误返回：

```json
{
  "ok": false,
  "error": "错误说明"
}
```

### 24.3 日志规范

关键接口建议记录：

- `module`
- `action`
- `user_id`
- `site_id` 或 `web_id`
- `lottery_type_id`
- `year`
- `term`
- `duration_ms`
- `error`
- `stack trace`

### 24.4 数据库规范

- 正式运行不得默认依赖 SQLite
- 正式运行必须走 PostgreSQL
- 建表与字段变更应集中在 `backend/src/tables.py`
- 不要把 SQL 分散写在前端页面或临时脚本里

## 25. 常见问题

### 25.1 为什么文档不再写 SQLite 默认数据库

因为当前正式运行已统一为 PostgreSQL，SQLite 只保留作历史迁移或显式测试用途。

### 25.2 为什么 `/api/predict/{mechanism}` 不是公开接口

因为代码里会执行 `ensure_generation_permission(...)`，必须登录且角色满足权限要求。

### 25.3 为什么站点接口不返回 token 明文

因为 `get_site()` 和 `list_sites()` 默认使用脱敏输出，只返回 `token_present` 和 `token_preview`。

### 25.4 为什么公开接口不直接暴露未开奖期结果

因为公开数据最终受 `lottery_draws.is_opened` 控制，未开奖期必须隐藏真实结果字段。

### 25.5 为什么有些成功响应不是 `{ ok: true, data: ... }`

因为项目中还保留了不少历史接口结构；新增接口应尽量收敛到统一规范，但当前代码并未完全完成统一。
