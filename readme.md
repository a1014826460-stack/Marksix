# 六合彩彩票数据管理系统

彩票网站数据抓取、归一化、预测和后台管理系统。

## 启动服务

### 1. Python API 服务（端口 8000）

```powershell
cd d:\pythonProject\outsource\Liuhecai
python backend/src/app.py

cd d:\pythonProject\outsource\Liuhecai
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-backend.ps1
```

正式运行必须配置 PostgreSQL 数据库连接。推荐使用环境变量 `DATABASE_URL`，
或在 `backend/src/config.yaml` 中提供 PostgreSQL DSN。

如需显式指定 PostgreSQL：

```powershell
python backend/src/app.py --db-path "postgresql://user:password@localhost:5432/liuhecai"
```

可选参数：
- `--host` 监听地址（默认 `127.0.0.1`，可通过环境变量 `LOTTERY_API_HOST` 设置）
- `--port` 端口号（默认 `8000`，可通过环境变量 `LOTTERY_API_PORT` 设置）
- `--db-path` 数据库目标（仅正式运行 PostgreSQL DSN）

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
python backend/src/deprecated/tools/migrate_sqlite_to_postgres.py ^
  --source-sqlite D:\backup\old-lottery.sqlite3 ^
  --target-dsn "postgresql://user:password@host:5432/liuhecai"
```

说明：

- `backend/data/lottery_modes.sqlite3` 已不再作为默认数据库。
- 删除该文件不会影响正式运行，前提是 PostgreSQL 数据完整。
- 旧 SQLite 数据如需保留，请单独备份后再使用迁移脚本。

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

问题预测模块：
1，一语破天机 mode_id=244 无法与public.text_history_mappings建立映射
返回API
{"id": 175, "web": 2, "type": 3, "term": "295", "year": "2025", "content": "黑夜冬季微风凉，初夏一到细雨香", "res_code": "38,21,36,10,47,44,07", "res_sx": "龙,鸡,马,猴,羊,狗,猪", "status": 1, "res_color": "green,green,blue,blue,blue,green,red"}
2，绝杀一尾 mode_id=20 生成预测数据过于重复
返回API
{"id": 1556, "web": "5", "type": "3", "year": "2026", "term": "125", "res_code": "04,27,38,11,45,08,40", "res_sx": "兔,龙,蛇,猴,狗,猪,兔", "res_color": "blue,green,green,green,red,red,red", "status": 1, "content": "[\"2尾|02,12,22,32,42\"]"}
3，琴棋书画 mode_id=26 public.fixed_data的映射路径
223	"2026"	"四艺生肖"	2	"画"	2	"羊,猴,猪"
222	"2026"	"四艺生肖"	2	"书"	2	"虎,龙,马"
221	"2026"	"四艺生肖"	2	"棋"	2	"鼠,牛,狗"
220	"2026"	"四艺生肖"	2	"琴"	2	"兔,蛇,鸡"

返回API
{"id": 3453, "web": 5, "type": 3, "term": "126", "year": "2026", "title": "画,琴,书", "content": "羊,猴,猪,兔,蛇,鸡,虎,龙,马", "res_code": "20,34,07,18,41,02,03", "res_sx": "猪,鸡,鼠,牛,虎,蛇,龙", "res_color": "blue,red,red,red,blue,red,blue", "status": 1}

特码段数

绝杀三肖
