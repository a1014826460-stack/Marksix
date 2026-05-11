# 六合彩彩票数据管理系统 - 部署指南

> 适用于 **Ubuntu 24.04 LTS** 生产环境

## 目录

- [系统架构](#系统架构)
- [前置要求](#前置要求)
- [快速部署（推荐）](#快速部署推荐)
- [手动部署步骤](#手动部署步骤)
- [数据迁移](#数据迁移)
- [服务管理](#服务管理)
- [监控与日志](#监控与日志)
- [安全配置](#安全配置)
- [故障排查](#故障排查)

---

## 系统架构

```
                    ┌──────────────┐
                    │   用户请求    │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │ Nginx :80 / :443(可选)  │  ← 统一入口
              └──────┬────────┬─────────┘
                     │        │
          ┌──────────▼──┐  ┌──▼──────────┐
          │ 前端站点     │  │ 后台管理     │
          │ :3000       │  │ :3002        │
          │ Next.js 16  │  │ Next.js 16   │
          └─────────────┘  └──────────────┘
                     │        │
                     └────┬───┘
                          │
                    ┌─────▼─────┐
                    │ Python API │
                    │ :8000      │
                    │ Python 3.12│
                    └─────┬──────┘
                          │
                    ┌─────▼──────┐
                    │ PostgreSQL │
                    │ :5432      │
                    │ 17         │
                    └────────────┘
```

### 组件说明

| 组件 | 技术栈 | 端口 | 说明 |
|------|--------|------|------|
| **前端站点** | Next.js 16 | 3000 | 面向用户的彩票数据展示站 |
| **后台管理** | Next.js 16 | 3002 | 管理员后台 CMS |
| **Python API** | Python 3.12 | 8000 | 数据处理、预测、爬虫服务 |
| **PostgreSQL** | PostgreSQL 17 | 5432 | 数据持久化存储 |
| **Nginx** | Nginx 1.27 | 80 / 443 | 反向代理；HTTPS 需额外启用 |

---

## 前置要求

### 系统要求

- **操作系统**: Ubuntu 24.04 LTS (x86_64)
- **内存**: ≥ 4 GB RAM（推荐 8 GB）
- **磁盘**: ≥ 20 GB 可用空间
- **网络**: 能访问外网（用于拉取 Docker 镜像和爬虫采集）

### 安装 Docker

```bash
# 官方一键安装脚本
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose 插件
sudo apt update
sudo apt install -y docker-compose-plugin

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker

# 验证安装
docker --version
docker compose version
docker info
```

> `deploy/deploy.sh` 会额外检查 Docker daemon 是否已经启动；仅安装 CLI 不够。

---

## 快速部署（推荐）

### 步骤 1：获取项目

```bash
git clone https://github.com/a1014826460-stack/Marksix.git
cd Marksix
```

### 步骤 2：配置环境变量

```bash
cp .env.example .env
nano .env
```

`.env` 最少需要：

```ini
POSTGRES_PASSWORD=请设置强密码
LOTTERY_SITE_ID=1
```

### 步骤 3：执行一键部署

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

脚本会自动完成：

1. 检查 Docker / Docker Compose / Docker daemon
2. 准备 `.env`
3. 创建 `deploy/ssl/` 目录
4. 构建所有镜像
5. 启动全部服务
6. 初始化 `fixed_data`（如果目标库中尚不存在）

默认访问地址：

- 前端站点：`http://服务器IP/`
- 后台管理：`http://服务器IP/admin`
- Python API：`http://服务器IP/api/`

> 默认只保证 `HTTP` 可用。`HTTPS` 需要你先补充证书和 `deploy/nginx.conf` 中的 443 `server` 配置。

### 可选：首次从 SQLite 自动迁移到 PostgreSQL

如果这是第一次部署，而且你希望把仓库中的 `backend/data/lottery_modes.sqlite3` 自动迁移到 PostgreSQL，再执行：

```bash
RUN_SQLITE_MIGRATION=1 ./deploy/deploy.sh
```

> 这个开关默认关闭，避免重部署时误把旧 SQLite 数据覆盖回 PostgreSQL。

---

## 手动部署步骤

### 1. 构建镜像

```bash
docker compose build
```

或单独构建：

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

预期至少应看到以下服务处于运行状态：

```text
postgres
python-api
backend-admin
frontend
nginx
```

### 3. 初始化数据

导入固定数据：

```bash
docker compose exec python-api python /app/src/tools/import_fixed_data.py \
    --fixed-data-path /app/data/fixed_data.json \
    --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

规范化 `mode_payload_*` 表：

```bash
docker compose exec python-api python /app/src/utils/normalize_sqlite.py \
    --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

生成文本历史映射：

```bash
docker compose exec python-api python /app/src/utils/build_text_history_mappings.py \
    --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

---

## 数据迁移

### SQLite → PostgreSQL 迁移

当前仓库的迁移脚本位置和参数如下：

```bash
docker compose exec python-api python /app/src/tools/migrate_sqlite_to_postgres.py \
    --source-sqlite /app/data/lottery_modes.sqlite3 \
    --target-dsn "postgresql://postgres:你的密码@postgres:5432/liuhecai" \
    --drop-existing
```

说明：

- `--drop-existing` 会先删除 PostgreSQL 中已有同名表，适合首次全量导入或明确要重建目标库的场景。
- 如果你要保留目标 PostgreSQL 现有数据，不要直接加这个参数。
- 当前迁移脚本会迁移 **表** 和 **索引**，并重置自增序列。
- 当前仓库中的 SQLite 数据库没有自定义 `view` / `trigger`，所以现有脚本覆盖范围对当前数据结构是够用的。

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

### 本地 PostgreSQL 迁移到服务器

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

> 建议本地和服务器使用相同 PostgreSQL 主版本；当前仓库默认镜像为 PostgreSQL 17。

### 数据库重置

```bash
docker compose down -v
docker compose up -d
```

---

## 服务管理

### 常用操作

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

### 进入容器调试

```bash
docker compose exec python-api bash
docker compose exec postgres psql -U postgres -d liuhecai
docker compose exec nginx nginx -T
```

### 验证部署

```bash
chmod +x deploy/verify.sh
./deploy/verify.sh
```

> 该脚本默认验证 HTTP。只有当你的 `deploy/nginx.conf` 中真正启用了 `listen 443` 时，它才会检查 HTTPS。

---

## 监控与日志

### 查看容器资源使用

```bash
docker stats
```

### 日志来源

| 服务 | 日志来源 |
|------|----------|
| Python API | `docker compose logs python-api` |
| 后端管理 | `docker compose logs backend-admin` |
| 前端站点 | `docker compose logs frontend` |
| PostgreSQL | `docker compose logs postgres` |
| Nginx | `docker compose logs nginx` |

### 健康检查

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/health
curl http://localhost/health
docker compose exec postgres pg_isready -U postgres -d liuhecai
```

如果已经启用了 HTTPS，再额外检查：

```bash
curl -k https://localhost/health
```

---

## 安全配置

### 1. 修改默认密码

部署后务必修改以下默认凭据：

| 项目 | 默认值 | 修改方式 |
|------|--------|----------|
| 数据库密码 | `change_me_in_production` | 修改 `.env` 中 `POSTGRES_PASSWORD` |
| 后台管理员 | `admin / admin123` | 登录后台管理后修改 |
| 启动配置默认值 | `backend/src/config.yaml` 中的默认项 | 仅作为 bootstrap 使用，生产环境建议改掉 |

### 2. 配置防火墙

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

### 3. 配置 HTTPS（可选）

当前仓库默认的 `deploy/nginx.conf` 已包含 `shengshi8800.com / www.shengshi8800.com` 的 HTTP + HTTPS 配置，但要让 `https://` 真正可用，至少还要完成下面两件事：

1. 准备证书文件并放入 `deploy/ssl/`
2. 在 `deploy/nginx.conf` 中新增 443 `server`，显式配置：

```nginx
listen 443 ssl;
ssl_certificate /etc/nginx/ssl/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/privkey.pem;
```

如果你的目标是：

- `https://www.shengshi8800.com/` 可访问
- 并且根路径自动跳到 `/legacy-shell?t=3`

可以直接参考仓库内的示例文件：

```text
deploy/nginx.www.shengshi8800.ssl.conf.example
```

如果你使用 Certbot，建议在宿主机签发证书后，把证书文件挂载给容器使用；不要直接假设 `certbot --nginx` 能自动改到容器内的 Nginx 配置。

### 4. Nginx 安全加固

建议在 `deploy/nginx.conf` 中加入：

```nginx
server_tokens off;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
```

---

## 故障排查

### 服务启动失败

```bash
docker compose logs
docker compose logs python-api --tail 100
docker compose logs backend-admin --tail 100
docker compose logs frontend --tail 100
```

### Docker 命令存在但无法启动项目

如果 `docker --version` 正常，但 `docker compose ps`、`docker info` 报错，通常是 Docker daemon 没启动：

```bash
sudo systemctl status docker
sudo systemctl start docker
```

### 访问出现 502 Bad Gateway

当前 `deploy/nginx.conf` 已使用变量化 `proxy_pass` 和 `resolver 127.0.0.11 valid=10s;`，可以降低容器重启后的 DNS 缓存问题。

快速修复仍然是：

```bash
docker compose restart nginx
```

### 数据库连接失败

```bash
docker compose exec postgres pg_isready -U postgres -d liuhecai

docker compose exec python-api python -c "
from db import connect
conn = connect('postgresql://postgres:密码@postgres:5432/liuhecai')
print('连接成功')
"
```

### 端口冲突

```bash
sudo ss -tlnp | grep -E ':(80|443|3000|3002|5432|8000)'
```

如果宿主机端口冲突，可改 `docker-compose.yml` 的宿主机端口映射。

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

---

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
    └── ssl/
```

---

## 技术支持

- **项目仓库**: https://github.com/a1014826460-stack/Marksix
- **技术栈**: Python 3.12 + Next.js 16 + PostgreSQL 17 + Nginx + Docker
