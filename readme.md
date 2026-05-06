# 六合彩彩票数据管理系统

彩票网站数据抓取、归一化、预测和后台管理系统。

## 启动服务

### 1. Python API 服务（端口 8000）

```powershell
cd d:\pythonProject\outsource\Liuhecai
python backend/src/app.py
```

默认使用 SQLite 数据库 `backend/data/lottery_modes.sqlite3`。

如需指定 PostgreSQL：

```powershell
python backend/src/app.py --db-path "postgresql://user:password@localhost:5432/liuhecai"
```

可选参数：
- `--host` 监听地址（默认 `127.0.0.1`，可通过环境变量 `LOTTERY_API_HOST` 设置）
- `--port` 端口号（默认 `8000`，可通过环境变量 `LOTTERY_API_PORT` 设置）
- `--db-path` 数据库目标（SQLite 路径或 PostgreSQL DSN）

启动后访问：
- API 接口：`http://127.0.0.1:8000/api`
- **管理后台**：`http://127.0.0.1:8000//admin`（完整功能：用户、彩种、开奖、站点、号码、预测模块管理）

### 2. Next.js 管理端（端口 3002）

```powershell
cd d:\pythonProject\outsource\Liuhecai\backend
npm run dev -- --hostname 127.0.0.1 --port 3002
```

登录地址：`http://127.0.0.1:3002/login`

### 3. 前端站点（端口 3000）

```powershell
cd d:\pythonProject\outsource\Liuhecai\frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

环境变量（在 `frontend/.env.local` 中设置）：

```
LOTTERY_BACKEND_BASE_URL=http://127.0.0.1:8000/api
LOTTERY_SITE_ID=1
```

### 4. 预测 CLI

```powershell
cd d:\pythonProject\outsource\Liuhecai
python backend/src/predict/run_prediction.py --list-mechanisms
python backend/src/predict/run_prediction.py --mechanism title_234 --json
```

### 5. 数据迁移（SQLite → PostgreSQL）

```powershell
python backend/src/utils/migrate_sqlite_to_postgres.py ^
  --source-sqlite backend/data/lottery_modes.sqlite3 ^
  --target-dsn "postgresql://user:password@host:5432/liuhecai"
```

## 默认管理员账号

| 字段 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |
| 角色 | super_admin |

> 上线部署后必须在管理后台修改默认密码。
>
> 默认密码、数据库 DSN、站点 Token 等配置保存在 `backend/src/config.yaml`，部署前请修改。

## 系统架构

```
Python API (port 8000)      ← 数据抓取、归一化、预测、管理后台
  └─ 内置管理页面 /admin      ← 完整后台 SPA（用户、彩种、开奖、站点、号码、预测）
  └─ REST API /api/*         ← JSON 接口

Next.js 管理端 (port 3002)   ← 可选的后台管理 UI（shadcn/ui）
  └─ /api/python/[...path]   ← 代理到 Python API

Next.js 前端站点 (port 3000) ← 面向用户的彩票数据展示
  └─ /api/lottery-data       ← 代理到 Python API
```

## 数据流

1. **抓取** → `POST /api/admin/sites/{id}/fetch` 从远程站点爬取数据
2. **归一化** → 原始数据转为 `mode_payload_*` 标准表
3. **映射** → 建立文本→号码映射池（`text_history_mappings`）
4. **预测** → 按配置的预测机制生成预测内容
5. **展示** → `GET /api/public/site-page` 供前端读取展示

## 配置文件

`backend/src/config.yaml` 包含所有默认常量：

```yaml
database:
  default_postgres_dsn: "postgresql://..."
admin:
  username: "admin"
  password: "admin123"
site:
  manage_url_template: "https://..."
  modes_data_url: "https://..."
  default_token: "eyJ..."
```

修改配置后重启 API 服务生效。
