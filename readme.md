# 六合彩彩票数据管理系统

彩票网站数据抓取、归一化、预测和后台管理系统。

当前仓库由三部分组成：

- `python-api`：Python 原生 HTTP API，负责抓取、数据处理、预测和后台业务接口
- `backend-admin`：Next.js 管理后台，浏览器通过 `/admin/api/python/*` 代理访问 Python API
- `frontend`：Next.js 前台站点，浏览器对外看到的 `/api/*` 多数是前台兼容层，不是 Python 原生接口

## 本地启动

### 1. Python API 服务

```powershell
cd d:\pythonProject\outsource\Liuhecai
python backend/src/app.py --host 127.0.0.1 --port 8000
```

或：

```powershell
cd d:\pythonProject\outsource\Liuhecai
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-backend.ps1
```

正式运行必须配置 PostgreSQL 数据库连接。推荐通过环境变量 `DATABASE_URL` 指定。

如需显式指定 PostgreSQL：

```powershell
python backend/src/app.py --db-path "postgresql://user:password@localhost:5432/liuhecai"
```

可选参数：

- `--host` 监听地址，默认 `127.0.0.1`
- `--port` 端口号，默认 `8000`
- `--db-path` 数据库目标，正式运行只应使用 PostgreSQL DSN

启动后：

- Python 原生 API：`http://127.0.0.1:8000/api`
- Python 健康检查：`http://127.0.0.1:8000/api/health`

注意：

- 当前不再推荐把 Python 内置 `/admin` 当作主要后台入口文档化使用
- 仓库里的管理后台主维护入口是独立的 Next.js 管理端

### 2. Next.js 管理端

```powershell
cd d:\pythonProject\outsource\Liuhecai\backend
npm run dev -- --hostname 127.0.0.1 --port 3002
```

登录地址：

- `http://127.0.0.1:3002/admin/login`

管理端通过：

- `/admin/api/python/*`

代理到 Python 原生：

- `/api/*`

### 3. 前端站点

```powershell
cd d:\pythonProject\outsource\Liuhecai\frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

环境变量可放在 `frontend/.env.local`：

```env
LOTTERY_BACKEND_BASE_URL=http://127.0.0.1:8000/api
LOTTERY_SITE_ID=1
```

本地前台主入口：

- `http://127.0.0.1:3000/?t=1`
- `http://127.0.0.1:3000/?t=2`
- `http://127.0.0.1:3000/?t=3`

说明：

- 根路径 `/` 会规范化到 `/?t=3`
- 当前生产前台主路径是旧站壳层 `public/vendor/shengshi8800/**`
- `legacy-shell` 主要保留给调试/回退，不是默认主入口

### 4. 预测 CLI

```powershell
cd d:\pythonProject\outsource\Liuhecai
python backend/src/predict/run_prediction.py --list-mechanisms
python backend/src/predict/run_prediction.py --mechanism title_234 --json
```

## 部署

Ubuntu 服务器部署请直接看：

- [DEPLOY.md](./DEPLOY.md)

当前默认部署方式是：

- `http://服务器IP/` -> 前端站点
- `http://服务器IP/admin` -> 管理后台
- `http://服务器IP/api/*` -> 前台兼容 API
- Python 原生 `http://127.0.0.1:8000/api/*` 主要供服务器本机和容器内访问

## 数据迁移

### SQLite -> PostgreSQL

当前这版重构后的仓库，**不再内置可直接执行的 SQLite -> PostgreSQL 迁移脚本**。

这意味着：

- 旧文档中的 `migrate_sqlite_to_postgres.py` 路径已经失效
- `backend/data/lottery_modes.sqlite3` 也不再是正式运行数据库

如果你仍有历史 SQLite 数据：

1. 先在旧工具或旧分支中完成 SQLite -> PostgreSQL 迁移
2. 再把 PostgreSQL 数据导入当前环境
3. 或者单独为当前仓库补新的迁移脚本

说明：

- 删除 `backend/data/lottery_modes.sqlite3` 不应影响正式运行，前提是 PostgreSQL 数据已完整
- SQLite 现在仅保留作历史备份或显式测试用途

## 默认管理员账号

| 字段 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |
| 角色 | `super_admin` |

上线后请立即修改默认密码。

## 系统架构

```text
Python API (port 8000)
  -> REST API /api/*
  -> health /health, /api/health

Next.js Admin UI (port 3002)
  -> /admin
  -> /admin/api/python/* -> proxy to Python API

Next.js Frontend (port 3000)
  -> /?t=1|2|3
  -> /api/* compatibility routes
  -> public/vendor/shengshi8800/** legacy foreground shell
```

## 数据流

1. 抓取：`POST /api/admin/sites/{id}/fetch`
2. 归一化：生成 `mode_payload_*`
3. 映射：建立 `text_history_mappings`
4. 预测：按配置机制生成预测内容
5. 展示：前台通过 Python `/api/public/site-page` 的数据，经前端兼容层对外展示

## 配置

后端默认配置主要由 `backend/src/runtime_config.py` 中的启动默认值和数据库 `system_config` 表共同提供；正式环境应优先通过数据库配置和环境变量覆盖敏感项。

典型配置项包括：

```yaml
database:
  default_postgres_dsn: "postgresql://..."
admin:
  username: "admin"
  password: "admin123"
site:
  manage_url_template: "https://..."
  modes_data_url: "https://..."
```

修改配置后请重启对应服务。
