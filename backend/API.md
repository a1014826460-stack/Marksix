# 后端 API 文档

## 1. 文档目标与适用范围

本文档以 `backend/src/app.py` 当前实际注册的 Python 后端路由为准，面向以下场景：

- 接口调试
- 接口问题排查
- 后台接口扩展
- 前端调用
- 旧接口兼容维护
- 数据库问题定位

本文主要描述 Python 后端原生接口，即 `http://127.0.0.1:8000/api/*`。如果管理后台通过 Next.js 代理访问，或前台通过 Next.js 兼容层对外暴露接口，会在第 9 节单独说明。

## 2. 系统架构与调用链路

当前后端调用链路分为四层：

1. Python HTTP 入口：`backend/src/main.py`（正式入口）、`backend/src/app.py`（兼容入口）
2. HTTP 传输层：`backend/src/app_http/`（路由、鉴权、请求上下文、响应写入）
3. 路由层：`backend/src/routes/`（注册路由、解析 HTTP 参数、调用领域服务）
4. 领域层：`backend/src/domains/`（核心业务逻辑，不依赖 HTTP 层）
   - `domains/prediction/` — 预测模块管理、安全控制、重新生成
   - `domains/sites/` — 站点业务逻辑
   - `domains/lottery/` — 彩种业务
   - `domains/configs/` — 配置管理
   - `domains/logs/` — 日志查询
   - `domains/legacy/` — 旧站兼容
5. 数据访问与建表：
   - `backend/src/db.py` — PostgreSQL 连接适配
   - `backend/src/tables.py` — 表结构初始化
6. 采集与调度：
   - `backend/src/crawler/collectors.py` — HK/Macau 数据采集
   - `backend/src/crawler/tasks.py` — 调度器任务管理
   - `backend/src/crawler/scheduler.py` — CrawlerScheduler + 自动预测
7. 预测引擎：
   - `backend/src/predict/mechanisms.py` — 预测算法注册与实现
   - `backend/src/prediction_generation/service.py` — 批量生成编排
8. 管理端代理与前端调用：
   - `backend/app/api/python/[...path]/route.ts`
   - `backend/lib/admin-api.ts`

调用关系：

- 浏览器管理端请求 `/fackyou/api/python/...`
- Next.js 代理将其转发到 Python `/api/...`
- Python 后端路由 → 领域服务 → 数据访问层
- `domains/` 不依赖 `admin/`；`admin/` 作为兼容包装调用 `domains/`
- 所有正式业务数据统一读写 PostgreSQL

## 3. 启动方式

Python 后端（两种方式等效，推荐 `main.py`）：

```powershell
# 正式入口（推荐）
python backend/src/main.py --host 127.0.0.1 --port 8000

# 兼容入口
python backend/src/app.py --host 127.0.0.1 --port 8000
```

管理前端：

```powershell
cd backend
npm run dev -- --hostname 127.0.0.1 --port 3002
```

默认访问地址：

- Python API：`http://127.0.0.1:8000`
- 管理后台：`http://127.0.0.1:3002/fackyou/login`

如果你是通过 Docker + Nginx 部署整站，而不是本机直接启动 Python：

- 对外前台入口通常是 `http://服务器IP/` 或你的站点域名
- 对外后台入口通常是 `http://服务器IP/fackyou/login`
- Python 原生接口一般只在服务器本机或容器内网访问，例如 `http://127.0.0.1:8000/api/health`

## 4. 数据库配置

### 4.1 正式数据库

正式运行只使用 PostgreSQL。

推荐环境变量：

```env
DATABASE_URL=postgresql://user:password@host:5432/liuhecai
```

首次启动前确保：

1. PostgreSQL 服务已启动
2. 数据库 `liuhecai` 已创建
3. 环境变量 `DATABASE_URL` 已设置

注意：

- 代码中不再硬编码数据库密码
- 正式运行只接受 PostgreSQL DSN
- 如果未配置 `DATABASE_URL`，启动会立即失败并提示

### 4.2 SQLite 说明

- `backend/data/lottery_modes.sqlite3` 已废弃，不再作为默认数据库
- SQLite 不参与正式运行
- SQLite 仅保留给历史迁移或显式本地测试

### 4.3 旧 SQLite 数据迁移

当前这版重构后的仓库，已经不再内置可直接执行的 SQLite → PostgreSQL 迁移脚本。

如果你手里仍然只有历史 SQLite 数据，建议：

1. 在旧工具或旧分支中先完成 SQLite → PostgreSQL 迁移；
2. 再把 PostgreSQL 数据导入当前正式环境；
3. 或者为当前仓库单独补一份新的迁移脚本后再执行迁移。

也就是说，本文档中不再给出可直接运行的 `migrate_sqlite_to_postgres.py` 路径示例，以免误导。

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
  "error": "错误说明"
}
```

如果是业务异常（AppError 子类），额外返回 `code` 字段：

```json
{
  "ok": false,
  "error": "未登录或登录已失效",
  "code": "UNAUTHORIZED"
}
```

常见 `code` 值：

| code | HTTP 状态 | 说明 |
|------|-----------|------|
| `UNAUTHORIZED` | 401 | 未登录或登录已失效 |
| `FORBIDDEN` | 403 | 已登录但权限不足 |
| `NOT_FOUND` | 404 | 资源不存在或路由不匹配 |
| `VALIDATION_ERROR` | 400 | 参数校验失败 |
| `CONFLICT` | 409 | 资源冲突 |
| `APP_ERROR` | 400 | 通用业务异常 |

生产环境下 **不返回** traceback、文件路径、SQL、内部模块名。设置 `LOTTERY_DEBUG=1` 环境变量后会在 `detail` 字段返回调试信息。

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
/fackyou/api/python/...
```

示例：

- Python 原生：`/api/admin/lottery-types`
- 管理端代理：`/fackyou/api/python/admin/lottery-types`

代理目标地址由以下环境变量控制：

```env
PYTHON_API_BASE_URL=http://127.0.0.1:8000
```

默认值也是 `http://127.0.0.1:8000`。

### 9.3 前台对外 `/api/*` 兼容层

当前前台站点不是把浏览器请求直接打到 Python 原生 `/api/*`，而是先走前台 Next.js 提供的兼容层。

典型链路是：

```text
浏览器
  -> http://站点域名/api/*
  -> frontend/app/api/**/route.ts
  -> Python 原生 /api/*
```

这意味着：

- 对外站点上的 `/api/latest-draw`、`/api/draw-history`、`/api/kaijiang/*` 等路径，属于前台兼容 API
- 它们不等同于 Python 原生的 `/api/public/*`、`/api/legacy/*`
- 部署到 Ubuntu + Docker + Nginx 后，外部用户访问站点域名下的 `/api/*`，默认先命中前台 Next.js

### 9.4 注意

- 本文默认写 Python 原生路径，除非特别注明“管理端代理”或“前台兼容层”
- 如果你在管理后台页面里调试，请把路径换成 `/fackyou/api/python/...`
- 如果你在站点域名下调试前台接口，请确认自己访问的是前台兼容 API，还是 Python 原生 `/api/...`
- 不要把 Python 原生路径 `/api/...`、管理端代理路径 `/fackyou/api/python/...`、以及前台对外 `/api/*` 兼容层混为一谈

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
- 如果你是在整站部署环境里从浏览器调试，通常不会直接访问 `http://127.0.0.1:8000`，而是从服务器本机或容器内去访问这个地址

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

### GET `/api/public/current-period`

接口说明：返回指定彩种当前已开奖期号与年份。

鉴权要求：

- 是否需要登录：否
- Header：无

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---:|---|
| `lottery_type` | int | 否 | `3` | 彩种 ID（1=香港, 2=澳门, 3=台湾） |

请求体：

```json
{}
```

成功响应：

```json
{
  "lottery_type_id": 3,
  "lottery_name": "台湾彩",
  "current_period": "2026125",
  "current_year": 2026,
  "current_term": 125
}
```

无已开奖记录时返回：

```json
{
  "lottery_type_id": 3,
  "lottery_name": "台湾彩",
  "current_period": "",
  "current_year": 0,
  "current_term": 0
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/public/current-period?lottery_type=3"
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8000/api/public/current-period?lottery_type=3"
```

前端调用示例：

```ts
const res = await fetch(
  "http://127.0.0.1:8000/api/public/current-period?lottery_type=3",
)
const data = await res.json()
```

调试提示：

- 数据来源是 `lottery_draws` 表中最新的 `is_opened=1` 记录
- 若彩种从未录入过已开奖数据，四个返回值均为空/0

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
const res = await fetch("/fackyou/api/python/auth/login", {
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
const res = await fetch("/fackyou/api/python/admin/lottery-types", {
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
await fetch("/fackyou/api/python/admin/lottery-types/3", {
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
const res = await fetch("/fackyou/api/python/admin/draws?limit=50", {
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
const res = await fetch("/fackyou/api/python/admin/sites", {
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
await fetch("/fackyou/api/python/admin/sites/4/fetch", {
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
const res = await fetch("/fackyou/api/python/predict/mechanisms")
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
const res = await fetch("/fackyou/api/python/predict/pt2xiao", {
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
- `POST /api/admin/sites/{site_id}/prediction-modules/bulk-delete-estimate`
- `DELETE /api/admin/sites/{site_id}/prediction-modules/bulk-delete`

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
const res = await fetch("/fackyou/api/python/admin/sites/4/prediction-modules", {
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
await fetch("/fackyou/api/python/admin/sites/4/prediction-modules/run", {
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

### POST `/api/admin/sites/{site_id}/prediction-modules/bulk-delete-estimate`

接口说明：按当前站点、已选预测模块和期数范围，预估 `created.mode_payload_*` 中将删除的记录数。

请求体示例：

```json
{
  "moduleIds": ["pt2xiao", "tema12"],
  "periodRange": {
    "start": 2026001,
    "end": 2026010
  }
}
```

成功响应：

```json
{
  "moduleCount": 2,
  "periodCount": 10,
  "estimatedRows": 20,
  "limitExceeded": false
}
```

说明：
- 仅允许删除当前 `site_id` 下已启用的模块
- 删除范围会自动按当前站点的 `lottery_type_id` 与 `web_id` 过滤
- 若预计删除量超过前端约定的 1000 条，会返回 `limitExceeded=true`

### DELETE `/api/admin/sites/{site_id}/prediction-modules/bulk-delete`

接口说明：按当前站点、预测模块与期数范围，批量删除测试生成的预测资料。

请求体示例：

```json
{
  "moduleIds": ["pt2xiao", "tema12"],
  "periodRange": {
    "start": 2026001,
    "end": 2026010
  }
}
```

成功响应：

```json
{
  "ok": true,
  "deleted": 20,
  "estimated": 20,
  "modules": [
    {
      "moduleId": "pt2xiao",
      "tableName": "mode_payload_43",
      "deleted": 10
    }
  ]
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

### 预测资料回填接口

接口说明：批量回填预测资料的 `res_code` / `res_sx` / `res_color` 字段。遍历指定期号范围内的所有已开奖记录，将开奖号码对应的结果信息写入所有 `created.mode_payload_*` 表中匹配的记录。

### POST `/api/admin/backfill-predictions`

接口说明：按彩种和期号范围，将已开奖记录的号码、生肖、波色回填到预测资料中。

鉴权要求：

- 是否需要登录：是
- Header：
  - `Authorization: Bearer <token>`
  - `Content-Type: application/json`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---:|---|
| 无 | - | - | - | 所有参数通过请求体传递 |

请求体：

```json
{
  "lottery_type_id": 3,
  "start_issue": "2026001",
  "end_issue": "2026010",
  "table_names": ["mode_payload_43", "mode_payload_65"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---:|---|
| `lottery_type_id` | int | 否 | 彩种 ID，默认 `3` |
| `start_issue` | string | 是 | 起始期号，例如 `2026001` |
| `end_issue` | string | 是 | 结束期号，例如 `2026010` |
| `table_names` | string[] | 否 | 指定仅回填这些 `mode_payload_*` 表；不传则回填所有 created 预测表 |

成功响应：

```json
{
  "ok": true,
  "data": {
    "lottery_type_id": 3,
    "start_issue": "2026001",
    "end_issue": "2026010",
    "draw_count": 10,
    "total_affected": 420,
    "draws": [
      {
        "year": 2026,
        "term": 1,
        "issue": "2026001",
        "numbers": "04,27,38,11,45,08,40",
        "res_sx": "兔,豬,牛,狗,龍,蛇,猴",
        "res_color": "蓝,红,绿,蓝,红,蓝,红",
        "updated_tables": [
          {"table": "mode_payload_43", "affected": 1},
          {"table": "mode_payload_65", "affected": 1}
        ],
        "total_affected": 42
      }
    ]
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "期号范围 2026001-2026010 内没有已开奖记录"
}
```

curl 示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/backfill-predictions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"lottery_type_id":3,"start_issue":"2026001","end_issue":"2026010"}'
```

PowerShell 示例：

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "http://127.0.0.1:8000/api/admin/backfill-predictions" `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"lottery_type_id":3,"start_issue":"2026001","end_issue":"2026010"}'
```

前端调用示例：

```ts
const res = await fetch("/fackyou/api/python/admin/backfill-predictions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({
    lottery_type_id: 3,
    start_issue: "2026001",
    end_issue: "2026010",
  }),
})
const data = await res.json()
```

调试提示：

- 只会操作 `is_opened=1` 且已录入号码的已开奖记录
- 回填仅更新 `res_code`、`res_sx`、`res_color` 三者均为空的记录，已有回填数据的记录不会被覆盖
- 不传 `start_issue`/`end_issue` 时，自动按 `prediction.recent_period_count`（默认 10）追溯近期期数
- 遍历 `created` schema 下所有 `mode_payload_*` 表，按 `type` + `year` + `term` 匹配更新

### GET `/api/admin/backfill-predictions/logs`

接口说明：查询回补检查与生成事件的执行日志。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `lottery_type_id` | int | 否 | - | 彩种 ID |
| `period` | string | 否 | - | 期号模糊匹配（如 `2026133`） |
| `action` | string | 否 | - | 动作筛选：`skipped`/`generated`/`error` |
| `date_from` | string | 否 | - | 起始时间 |
| `date_to` | string | 否 | - | 结束时间 |
| `page` | int | 否 | `1` | 页码 |
| `page_size` | int | 否 | `30` | 每页数量（最大 200） |

成功响应：

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id": 1,
        "created_at": "2026-05-13T04:04:23Z",
        "level": "INFO",
        "message": "[回补] 期号=2026133 动作=generated 详情=inserted=3 updated=0",
        "lottery_type_id": 3
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 30,
    "total_pages": 1
  }
}
```

curl 示例：

```bash
curl -X GET "http://127.0.0.1:8000/api/admin/backfill-predictions/logs?lottery_type_id=3&period=2026133&page_size=30" \
  -H "Authorization: Bearer <token>"
```

## 21. 邮件报警接口

状态：已实现

### 概述

邮件报警系统用于在以下场景自动发送告警邮件：

1. **爬虫连续失败** ─ 爬虫连续重试 N 次无法获取数据后触发（阈值由 `alert.crawler_retry_threshold` 控制，默认 3）
2. **预测数据断层** ─ `daily_prediction_cron_time` 触发后，若启用站点的 `created` 预测数据未覆盖到目标期号（当前期+1），触发报警
3. **开奖数据滞后** ─ 最新已开奖记录的 `next_time` 已过当前北京时间，但无新数据入库
4. **精确期号不匹配** ─ 调度器精确开奖检查全部重试失败后触发

### 配置说明

邮件报警依赖以下 `system_config` 配置项（可在后台配置管理页面修改）：

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `alert.email_enabled` | bool | true | 是否启用邮件报警 |
| `alert.email_recipients` | json | `["1014826460@qq.com"]` | 报警邮件收件人列表 |
| `alert.smtp_host` | string | `smtp.qq.com` | SMTP 服务器地址 |
| `alert.smtp_port` | int | `587` | SMTP 端口（587=TLS） |
| `alert.smtp_username` | string | `""` | SMTP 登录用户名（通常为邮箱地址） |
| `alert.smtp_password` | string | `""` | SMTP 密码或授权码（敏感） |
| `alert.smtp_from_name` | string | `Liuhecai 报警系统` | 发件人显示名称 |
| `alert.crawler_retry_threshold` | int | `3` | 爬虫连续失败报警阈值 |

### GET `/api/admin/alert/recipients`

接口说明：获取当前配置的报警邮件收件人列表。

鉴权要求：

- 是否需要登录：是

成功响应：

```json
{
  "ok": true,
  "data": {
    "recipients": ["1014826460@qq.com", "admin@example.com"]
  }
}
```

### PUT `/api/admin/alert/recipients`

接口说明：更新报警邮件收件人列表。

请求体：

```json
{
  "recipients": ["1014826460@qq.com", "admin@example.com"]
}
```

成功响应：

```json
{
  "ok": true,
  "data": {
    "recipients": ["1014826460@qq.com", "admin@example.com"]
  }
}
```

失败响应：

```json
{
  "ok": false,
  "error": "无效邮箱地址: not-an-email"
}
```

### POST `/api/admin/alert/test-email`

接口说明：发送一封测试邮件到当前配置的收件人，用于验证 SMTP 配置是否正确。

请求体：

```json
{}
```

成功响应：

```json
{
  "ok": true,
  "message": "测试邮件已发送（异步），请稍后检查收件箱"
}
```

curl 示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/alert/test-email" \
  -H "Authorization: Bearer <token>"
```

调试提示：

- 使用前必须先在后台配置管理页面设置 `alert.smtp_username` 和 `alert.smtp_password`
- QQ 邮箱需使用授权码而非登录密码（QQ 邮箱设置 → 账户 → POP3/SMTP 服务 → 生成授权码）
- 邮件发送为异步，不会阻塞主流程
- 若 `alert.email_enabled` 设为 `false`，所有报警只写日志不发送邮件

## 22. 日志管理接口

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

## 23. 配置管理接口

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

## 24. 调试与排错指南

### 23.1 接口 404

检查：

1. Python API 是否启动在 `127.0.0.1:8000`
2. 请求路径是否带了 `/api`
3. 是否把 `/api/...` 与 `/fackyou/api/python/...` 混用了
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
2. 浏览器访问的是 `/fackyou/api/python/...`、站点对外 `/api/*` 兼容层，还是 Python 原生 `/api/...`
3. Next.js `basePath=/fackyou` 是否被正确考虑
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

## 25. 新增 API 开发规范

### 24.1 后端新增接口流程

1. 在合适模块中新增处理逻辑：
   - `domains/` — 核心业务逻辑
   - `routes/` — HTTP 路由注册
   - `public/` — 公开接口
   - `legacy/` — 旧站兼容
2. 在 `backend/src/app_http/server.py` 的 `build_router()` 中注册路由
3. 统一解析 query 与 JSON body（通过 RequestContext）
4. 做参数校验
5. 做鉴权校验（通过 app_http/auth.py 中间件）
6. 使用统一数据库连接（db.py → PostgreSQL）
7. 返回 JSON（通过 ResponseWriter）
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

业务异常错误（推荐）：

```json
{
  "ok": false,
  "error": "错误说明",
  "code": "ERROR_CODE"
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
- 数据库密码不得硬编码在代码中，只通过 `DATABASE_URL` 环境变量传入
- 建表与字段变更应集中在 `backend/src/tables.py`
- 不要把 SQL 分散写在前端页面或临时脚本里
- 路由层和 HTTP 层不写 SQL；SQL 集中在 repository 和 db 层

### 24.5 目录结构规范

- `app_http/` — HTTP 传输层（路由、鉴权、请求响应），不写业务逻辑
- `routes/` — 注册路由、解析参数、调用领域服务、返回 JSON，不写复杂 SQL
- `domains/` — 核心业务逻辑、数据访问（repository），**不依赖 `admin/`**
- `admin/` — 兼容包装层，调用 `domains/` 并导出，不实现新业务逻辑
- `crawler/` — 数据采集（collectors）、任务管理（tasks）、调度器（scheduler）
- `predict/` — 预测算法和配置管理
- `prediction_generation/` — 批量预测生成编排

## 26. 测试与验证

### 25.1 测试命令

```powershell
# 编译检查
cd backend/src
python -m compileall .

# 单元测试（不需要数据库）
python -m pytest tests/unit/ -v

# 集成测试（需要测试数据库）
$env:TEST_DATABASE_URL = "postgresql://postgres:password@host:5432/liuhecai_test"
python -m pytest tests/integration/ -v

# 全部测试
python -m pytest tests/ -v
```

### 25.2 已验证的 API 端点（2026-05-13 测试通过）

| 端点 | 方法 | 鉴权 | 状态 | 说明 |
|------|------|------|------|------|
| `/api/health` | GET | 否 | ✅ | 返回 29 机制, 894 期, 337 表 |
| `/api/auth/login` | POST | 否 | ✅ | 返回 token, expires_at, user |
| `/api/auth/me` | GET | 是 | ✅ | 返回当前用户信息 |
| `/api/auth/logout` | POST | 是 | ✅ | 删除 session |
| `/api/admin/sites` | GET | 是 | ✅ | 返回站点列表 |
| `/api/admin/sites` (未登录) | GET | — | ✅ | 返回 401 + `{"ok":false,"error":"未登录或登录已失效"}` |
| `/api/admin/users` | GET | 是 | ✅ | 返回用户列表 |
| `/api/admin/lottery-types` | GET | 是 | ✅ | 返回彩种列表 |
| `/api/admin/draws` | GET | 是 | ✅ | 返回开奖记录 |
| `/api/admin/numbers` | GET | 是 | ✅ | 返回号码映射 |
| `/api/admin/system-config` | GET | 是 | ✅ | 返回 69 个配置项 |
| `/api/admin/logs` | GET | 是 | ✅ | 返回 496 条日志 |
| `/api/admin/logs/stats` | GET | 是 | ✅ | 返回日志统计 |
| `/api/admin/configs/groups` | GET | 是 | ✅ | 返回配置分组 |
| `/api/admin/configs/effective/{key}` | GET | 是 | ✅ | 返回配置有效值 |
| `/api/admin/fetch-runs` | GET | 是 | ✅ | 返回抓取运行记录 |
| `/api/admin/jobs/{job_id}` | GET | 是 | ✅ | 返回后台任务状态 |
| `/api/admin/sites/{id}/prediction-modules` | GET | 是 | ✅ | 返回 42 个模块 |
| `/api/admin/sites/{id}/prediction-modules/generate-all` | POST | 是 | ✅ | 提交批量生成任务 |
| `/api/admin/sites/{id}/prediction-modules/run` | POST | 是 | ✅ | 执行单次预测 |
| `/api/admin/sites/{id}/mode-payload/{table}` | GET | 是 | ✅ | 返回模式数据 (205 行) |
| `/api/public/site-page` | GET | 否 | ✅ | 返回站点首页数据 |
| `/api/public/latest-draw` | GET | 否 | ✅ | 返回最新开奖 (issue=132) |
| `/api/predict/mechanisms` | GET | 否 | ✅ | 返回 335 个机制 |
| `/api/predict/{mechanism}` | POST | 是 | ✅ | 返回预测结果 (labels=鸡 猴) |
| `/api/legacy/current-term` | GET | 否 | ✅ | 返回当前期号 |
| `/api/legacy/post-list` | GET | 否 | ✅ | 返回图片列表 |
| `/api/legacy/module-rows` | GET | 否 | ✅ | 返回模块历史行 |
| `/api/public/current-period` | GET | 否 | ✅ | 返回彩种当前期号 |
| `/api/admin/backfill-predictions` | POST | 是 | ✅ | 回填 res_code/res_sx/res_color；支持自动追溯 |
| `/api/admin/backfill-predictions/logs` | GET | 是 | ✅ | 查询回补事件日志 |
| `/api/admin/alert/recipients` | GET | 是 | ✅ | 获取报警收件人列表 |
| `/api/admin/alert/recipients` | PUT | 是 | ✅ | 更新报警收件人列表 |
| `/api/admin/alert/test-email` | POST | 是 | ✅ | 发送测试报警邮件 |

### 25.3 自动化测试结果

```
python -m compileall .  →  通过
python -m pytest tests/ →  94 collected: 88 passed, 8 skipped (0 failed)

单元测试 (88 passed):
  test_admin_auth_error.py          5 passed
  test_alert_service.py             9 passed
  test_entrypoint_no_duplicate.py   10 passed
  test_error_response.py            4 passed
  test_errors.py                    8 passed
  test_predict_common.py            8 passed
  test_router.py                    7 passed
  test_routes_common_compat.py      9 passed
  test_site_context.py              15 passed
  test_time_utils.py                4 passed

集成测试 (8 passed with TEST_DATABASE_URL):
  test_prediction_generation.py     3 passed (web_id 隔离)
  test_tables_bootstrap.py          5 passed (表初始化幂等)
```

## 27. 常见问题

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
