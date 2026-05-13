# 六合彩彩票数据管理系统 - 部署指南

> 适用于 **Ubuntu 24.04 LTS**。本文以当前重构后的仓库实际结构为准。

## 概览

当前默认部署方式是：

- `Nginx` 对外暴露 `80`
- `frontend` 对外承载页面和前端兼容 API
- `backend-admin` 对外承载后台管理界面
- `python-api` 只监听宿主机 `127.0.0.1:8000`
- `postgres` 只监听宿主机 `127.0.0.1:5432`

这意味着：

- 外部用户直接访问：`http://服务器IP/`
- 外部后台入口：`http://服务器IP/admin`
- 外部 `/api/*` 是前端兼容 API，不是裸 Python API
- Python 原生 API 主要供容器内部和服务器本机使用：`http://127.0.0.1:8000/api/*`

## 前置要求

- Ubuntu 24.04 LTS
- 至少 4 GB 内存，推荐 8 GB
- 至少 20 GB 可用磁盘
- 能访问外网，用于拉取 Docker 镜像和依赖

安装 Docker 与 Compose：

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

sudo apt update
sudo apt install -y docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker

docker --version
docker compose version
docker info
```

## 快速部署

### 1. 获取项目

```bash
git clone https://github.com/a1014826460-stack/Marksix.git
cd Marksix
```

### 2. 配置环境变量

```bash
apt update && apt install nano -y
cp .env.example .env
nano .env
```

最少修改：

```ini
POSTGRES_PASSWORD=请设置强密码
LOTTERY_SITE_ID=1
```

说明：

- `POSTGRES_PASSWORD` 必改
- `LOTTERY_SITE_ID` 决定前台默认站点
- 根目录 `.env` 主要给 `docker compose` 使用

### 3. 执行一键部署

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

脚本会：

1. 检查 Docker / Docker Compose / Docker daemon
2. 准备 `.env`
3. 构建镜像
4. 启动 `postgres`、`python-api`、`backend-admin`、`frontend`、`nginx`
5. 首次导入 `fixed_data`

默认访问地址：

- 前端站点：`http://服务器IP/`
- 后台管理：`http://服务器IP/admin`
- 前端兼容 API：`http://服务器IP/api/...`

服务器本机可直接访问：

- Python API 健康检查：`http://127.0.0.1:8000/api/health`
- PostgreSQL：`127.0.0.1:5432`

### 4. 验证部署

```bash
chmod +x deploy/verify.sh
./deploy/verify.sh
```

## 手动部署

### 1. 构建镜像

```bash
docker compose build
```

或分别构建：

```bash
docker compose build python-api
docker compose build backend-admin
docker compose build frontend
```

### 2. 启动服务

```bash
docker compose up -d
docker compose ps
docker compose logs -f
```

预期服务：

```text
postgres
python-api
backend-admin
frontend
nginx
```

### 3. 初始化数据

导入 `fixed_data`：

```bash
docker compose exec python-api python /app/src/tools/import_fixed_data.py \
  --fixed-data-path /app/data/fixed_data.json \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

规范化 `mode_payload_*` 表：

```bash
docker compose exec python-api python /app/src/utils/normalize_payload_tables.py \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

生成文本历史映射：

```bash
docker compose exec python-api python /app/src/utils/build_text_history_mappings.py \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

## 服务入口说明

### 对外入口

- `http://服务器IP/`
  - 前台站点
- `http://服务器IP/admin`
  - 后台管理
- `http://服务器IP/api/latest-draw`
  - 前端兼容 API 示例

### 服务器本机入口

- `http://127.0.0.1:8000/health`
  - Python 基础健康检查
- `http://127.0.0.1:8000/api/health`
  - Python API 健康检查

### 当前代理关系

- `/` -> `frontend:3000`
- `/api/*` -> `frontend:3000`
- `/admin*` -> `backend-admin:3002`（内部重写为 `/fackyou/admin*`，适配 Next.js `basePath`）
- `/uploads/*` -> `python-api:8000`
- `/health` -> `python-api:8000/api/health`

注意：

- 当前外部 `/api/*` 不是直接转发到 Python，而是先走前端 Next.js 的兼容层
- 后台里调用 Python API 的入口是 `/admin/api/python/*`
- backend-admin 的 Next.js `basePath` 设置为 `/fackyou`，健康检查和 nginx 代理均已适配

## 数据迁移

### SQLite -> PostgreSQL

当前这版重构后的仓库，**不再包含可直接执行的一键 SQLite -> PostgreSQL 迁移脚本**。

也就是说：

- `RUN_SQLITE_MIGRATION=1 ./deploy/deploy.sh` 不会执行实际迁移
- 文档中旧的 `migrate_sqlite_to_postgres.py` 路径已失效

如果你当前手里只有历史 SQLite 数据，有两个可行方案：

1. 在旧工具或旧分支中先完成 SQLite -> PostgreSQL 迁移，再把 PostgreSQL 数据导出导入到当前环境。
2. 让我们单独补一份新的迁移脚本，再迁移。

### PostgreSQL 备份

```bash
# 纯 SQL
docker compose exec postgres pg_dump -U postgres liuhecai > backup_$(date +%Y%m%d).sql

# 自定义格式
docker compose exec postgres pg_dump -U postgres liuhecai -F c -f /tmp/backup.dump
docker compose cp postgres:/tmp/backup.dump ./backup_$(date +%Y%m%d).dump
```

### PostgreSQL 恢复

```bash
# 从 SQL 恢复
docker compose exec -T postgres psql -U postgres liuhecai < backup_20250101.sql

# 从自定义 dump 恢复
docker compose cp ./backup_20250101.dump postgres:/tmp/restore.dump
docker compose exec postgres pg_restore -U postgres -d liuhecai --clean --if-exists /tmp/restore.dump
```

### 本地 PostgreSQL 导入服务器

本地导出：

```bash
# 本地也是 Docker PostgreSQL
docker compose exec -T postgres pg_dump -U postgres liuhecai -F c > liuhecai_backup.dump

# 本地是原生 PostgreSQL
pg_dump -h localhost -U postgres -d liuhecai -F c -f liuhecai_backup.dump
```

上传到服务器：

```bash
scp liuhecai_backup.dump root@你的服务器IP:/opt/Liuhecai/
```

服务器导入：

```bash
ssh root@你的服务器IP
cd /opt/Liuhecai
docker compose cp liuhecai_backup.dump postgres:/tmp/restore.dump
docker compose exec postgres pg_restore -U postgres -d liuhecai --clean --if-exists /tmp/restore.dump
```

## 域名绑定与 HTTPS

默认的 `deploy/nginx.conf` 是通用 HTTP 配置，适合：

- 先用服务器 IP 跑通项目
- 不在首次部署时强依赖证书

如果后续要绑定域名并启用 HTTPS，按下面做。

### 1. 域名解析

在你的域名服务商后台添加 DNS 记录：

- `A` 记录：`@` -> 你的服务器公网 IP
- `A` 记录：`www` -> 你的服务器公网 IP

等解析生效后，在服务器上验证：

```bash
dig +short example.com
dig +short www.example.com
```

或：

```bash
nslookup example.com
nslookup www.example.com
```

### 2. 准备证书

把证书文件放到：

```text
deploy/ssl/fullchain.pem
deploy/ssl/privkey.pem
```

如果你用 Certbot，常见做法是把宿主机上的证书复制或软链接到 `deploy/ssl/`。

例如：

```bash
cp /etc/letsencrypt/live/example.com/fullchain.pem deploy/ssl/fullchain.pem
cp /etc/letsencrypt/live/example.com/privkey.pem deploy/ssl/privkey.pem
```

### 3. 使用 HTTPS Nginx 配置

仓库里提供了两个 SSL 配置示例：

| 文件 | 适用场景 |
|------|---------|
| `deploy/nginx.domain.ssl.conf.example` | 通用域名模板，需自行替换域名 |
| `deploy/nginx.www.shengshi8800.ssl.conf.example` | 已预配 `www.shengshi8800.com`，直接可用 |

**如果使用 `www.shengshi8800.com` 域名**：

```bash
cp deploy/nginx.www.shengshi8800.ssl.conf.example deploy/nginx.conf
```

配置中已包含：
- `shengshi8800.com` -> `www.shengshi8800.com` 重定向（HTTP + HTTPS）
- `/` 默认重定向到 `/?t=3`
- `/?type=N` 自动转换为 `/?t=N`

**如果使用其他域名**：

```bash
cp deploy/nginx.domain.ssl.conf.example deploy/nginx.conf
```

然后把其中的：

- `example.com`
- `www.example.com`

替换成你的真实域名。

### 4. 重启 Nginx

```bash
docker compose restart nginx
docker compose exec nginx nginx -t
```

### 5. 验证 HTTPS

```bash
curl -I http://example.com
curl -I https://example.com
curl -I https://www.example.com
curl -k https://www.example.com/health
```

### 6. 推荐切换顺序

推荐按这个顺序做，最稳：

1. 先按默认 HTTP 配置用服务器 IP 跑通
2. 再把域名解析到服务器
3. 申请证书并放入 `deploy/ssl/`
4. 再切换到 `deploy/nginx.domain.ssl.conf.example`
5. 验证 HTTPS 正常后，再考虑启用 HSTS

## 运维常用命令

```bash
docker compose ps
docker compose logs -f
docker compose logs -f python-api
docker compose logs -f postgres
docker compose restart python-api
docker compose restart frontend
docker compose down
docker compose down -v
git pull
docker compose build
docker compose up -d
```

进入容器：

```bash
docker compose exec python-api bash
docker compose exec postgres psql -U postgres -d liuhecai
docker compose exec nginx nginx -T
```

## 健康检查

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/health
curl http://localhost/health
curl http://localhost/api/latest-draw
docker compose exec postgres pg_isready -U postgres -d liuhecai
```

启用 HTTPS 后再检查：

```bash
curl -k https://localhost/health
```

## 防火墙

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

## 故障排查

### 服务启动失败

```bash
docker compose logs
docker compose logs python-api --tail 100
docker compose logs backend-admin --tail 100
docker compose logs frontend --tail 100
docker compose logs nginx --tail 100
```

### Docker daemon 未启动

```bash
sudo systemctl status docker
sudo systemctl start docker
```

### 访问出现 502

```bash
docker compose restart nginx
docker compose logs nginx --tail 100
```

### 数据库连接失败

```bash
docker compose exec postgres pg_isready -U postgres -d liuhecai
```

### 端口冲突

```bash
sudo ss -tlnp | grep -E ':(80|443|3000|3002|5432|8000)'
```

### 镜像构建失败

```bash
docker compose build --no-cache
docker system prune -a
```

### 磁盘空间不足

```bash
df -h
docker system prune -a --volumes
sudo journalctl --vacuum-size=200M
```

## 目录结构

```text
Liuhecai/
├── docker-compose.yml
├── Dockerfile.python
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
├── DEPLOY.md
├── backend/
│   ├── requirements.txt
│   ├── next.config.mjs
│   ├── src/
│   │   ├── app.py
│   │   ├── config.yaml
│   │   ├── db.py
│   │   ├── crawler/
│   │   ├── predict/
│   │   ├── tools/
│   │   └── utils/
│   └── data/
│       ├── fixed_data.json
│       ├── lottery_modes.sqlite3
│       ├── Images/
│       └── lottery_data/
├── frontend/
└── deploy/
    ├── deploy.sh
    ├── nginx.conf
    ├── nginx.domain.ssl.conf.example
    └── ssl/
```
