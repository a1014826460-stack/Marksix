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
                    ┌──────▼───────┐
                    │  Nginx :80   │  ← 反向代理（统一入口）
                    └──┬───┬───┬──┘
                       │   │   │
          ┌────────────┼───┼───┼────────────┐
          │            │   │   │            │
  ┌───────▼──┐  ┌──────▼───▼──┐  ┌───────▼──┐
  │ 前端站点  │  │ 后台管理    │  │ Python   │
  │ :3000    │  │ :3002       │  │ API:8000 │
  │ Next.js  │  │ Next.js     │  │ + 爬虫   │
  └──────────┘  └─────────────┘  │ + 预测   │
                                 └─────┬─────┘
                                       │
                                ┌──────▼──────┐
                                │ PostgreSQL  │
                                │    :5432    │
                                │  持久化存储  │
                                └─────────────┘
```

### 组件说明

| 组件 | 技术栈 | 端口 | 说明 |
|------|--------|------|------|
| **前端站点** | Next.js 14 | 3000 | 面向用户的彩票数据展示站 |
| **后台管理** | Next.js 14 | 3002 | 管理员后台 CMS |
| **Python API** | Python 3.12 | 8000 | 数据处理、预测、爬虫服务 |
| **PostgreSQL** | PostgreSQL 16 | 5432 | 数据持久化存储 |
| **Nginx** | Nginx 1.27 | 80/443 | 反向代理、静态文件、SSL 终端 |

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
docker --version      # ≥ 24.0
docker compose version # ≥ 2.24
```

---

## 快速部署（推荐）

### 步骤 1：获取项目

```bash
# 从 Git 仓库克隆
git clone https://github.com/a1014826460-stack/Marksix.git
cd Marksix

# 或直接上传整个项目目录到服务器
```

### 步骤 2：配置环境变量

```bash
# 从模板创建 .env 文件
cp .env.example .env

# 编辑 .env，务必修改数据库密码
nano .env
```

`.env` 文件内容：
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
1. ✅ 检查 Docker 环境
2. ✅ 准备环境变量
3. ✅ 构建所有 Docker 镜像
4. ✅ 启动全部服务
5. ✅ 导入初始数据

部署完成后访问：
- 前端站点：`http://服务器IP/`
- 后台管理：`http://服务器IP/admin`
- Python API：`http://服务器IP/api/`

---

## 手动部署步骤

如果需要更细粒度的控制，可以按以下步骤手动操作：

### 1. 构建镜像

```bash
# 构建所有镜像
docker compose build

# 或单独构建
docker compose build python-api
docker compose build backend-admin
docker compose build frontend
```

### 2. 启动服务

```bash
# 启动所有服务（后台运行）
docker compose up -d

# 查看启动日志
docker compose logs -f

# 确认所有服务正常运行
docker compose ps
```

预期输出：
```
NAME                       STATUS
liuhecai-postgres          Up (healthy)
liuhecai-python-api        Up
liuhecai-backend-admin     Up
liuhecai-frontend          Up
liuhecai-nginx             Up
```

### 3. 初始化数据

```bash
# 导入固定数据（号码映射等）
docker compose exec python-api python /app/src/utils/import_fixed_data.py \
    --json /app/data/fixed_data.json

# 生成文本历史映射（预测用）
docker compose exec python-api python /app/src/utils/build_text_history_mappings.py

# 规范化数据表
docker compose exec python-api python /app/src/utils/normalize_sqlite.py
```

---

## 数据迁移

### SQLite → PostgreSQL 迁移

项目默认使用 PostgreSQL，如果你有旧的 SQLite 数据需要迁移：

```bash
docker compose exec python-api python /app/src/utils/migrate_sqlite_to_postgres.py \
    --sqlite /app/data/lottery_modes.sqlite3 \
    --postgres "postgresql://postgres:你的密码@postgres:5432/liuhecai"
```

### 数据库备份

```bash
# 备份 PostgreSQL 数据库（纯 SQL 格式）
docker compose exec postgres pg_dump -U postgres liuhecai > backup_$(date +%Y%m%d).sql

# 或使用自定义格式（体积更小，支持并行恢复）
docker compose exec postgres pg_dump -U postgres liuhecai -F c -f /tmp/backup.dump
docker compose cp postgres:/tmp/backup.dump ./backup_$(date +%Y%m%d).dump

# 恢复数据库（纯 SQL）
docker compose exec -T postgres psql -U postgres liuhecai < backup_20250101.sql

# 恢复数据库（自定义格式，--clean 会先删除已有表）
docker compose cp ./backup_20250101.dump postgres:/tmp/restore.dump
docker compose exec postgres pg_restore -U postgres -d liuhecai --clean --if-exists /tmp/restore.dump
```

### 本地数据迁移到服务器

将本地开发环境的 PostgreSQL 数据导出并上传到生产服务器：

**1. 本地导出**

```bash
# 如果本地使用 Docker PostgreSQL
docker compose exec -T postgres pg_dump -U postgres liuhecai -F c > liuhecai_backup.dump

# 如果本地使用原生 PostgreSQL
pg_dump -h localhost -U postgres -d liuhecai -F c -f liuhecai_backup.dump
```

**2. 上传到服务器**

```bash
scp liuhecai_backup.dump root@你的服务器IP:/opt/Liuhecai/
```

**3. 服务器上导入**

```bash
ssh root@你的服务器IP
cd /opt/Liuhecai

# 复制 dump 文件到容器并恢复（--clean 会先删除已有表，适合首次导入）
docker compose cp liuhecai_backup.dump postgres:/tmp/restore.dump
docker compose exec postgres pg_restore -U postgres -d liuhecai --clean --if-exists /tmp/restore.dump
```

> **注意**：本地与服务器 PostgreSQL 大版本应保持一致（均为 16），否则可能出现兼容性问题。导入前建议先备份服务器现有数据。

### 数据库重置

```bash
# 完全重置数据库（警告：会删除所有数据）
docker compose down -v   # 删除 volumes
docker compose up -d     # 重新创建
```

---

## 服务管理

### 常用操作

```bash
# 查看所有服务状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f python-api
docker compose logs -f postgres

# 重启单个服务
docker compose restart python-api
docker compose restart frontend

# 停止所有服务
docker compose down

# 停止服务并删除数据卷（慎用）
docker compose down -v

# 更新并重新部署
git pull
docker compose build
docker compose up -d
```

### 进入容器调试

```bash
# 进入 Python API 容器
docker compose exec python-api bash

# 进入 PostgreSQL
docker compose exec postgres psql -U postgres -d liuhecai

# 查看 Nginx 配置
docker compose exec nginx nginx -T
```

### 手动触发爬虫

```bash
# 运行香港彩爬虫
docker compose exec python-api python /app/src/crawler/crawler_service.py --type hk

# 运行澳门彩爬虫
docker compose exec python-api python /app/src/crawler/crawler_service.py --type macau
```

---

## 监控与日志

### 查看容器资源使用

```bash
docker stats
```

### 日志文件位置

| 服务 | 日志来源 |
|------|----------|
| Python API | `docker compose logs python-api` |
| 后端管理 | `docker compose logs backend-admin` |
| 前端站点 | `docker compose logs frontend` |
| PostgreSQL | `docker compose logs postgres` |
| Nginx | `docker compose logs nginx` |

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 通过 Nginx 检查
curl http://localhost/health

# PostgreSQL 连接检查
docker compose exec postgres pg_isready -U postgres -d liuhecai
```

---

## 安全配置

### 1. 修改默认密码

部署后务必修改以下默认凭据：

| 项目 | 默认值 | 修改方式 |
|------|--------|----------|
| 数据库密码 | change_me_in_production | 修改 `.env` 中 `POSTGRES_PASSWORD` |
| 后台管理员 | admin / admin123 | 登录后台管理修改 |
| config.yaml 管理员 | admin / admin123 | 编辑 `backend/src/config.yaml` |

### 2. 配置防火墙

```bash
# Ubuntu 使用 ufw
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 确认规则
sudo ufw status verbose
```

### 3. 配置 HTTPS (SSL)

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 将证书放到 deploy/ssl/ 目录，或
# 修改 deploy/nginx.conf 添加 SSL 配置

# 使用 Certbot 自动获取证书
sudo certbot --nginx -d your-domain.com
```

### 4. Nginx 安全加固

在 `deploy/nginx.conf` 中添加：
```nginx
# 隐藏版本号
server_tokens off;

# 安全头
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
```

---

## 故障排查

### 服务启动失败

```bash
# 查看完整日志
docker compose logs

# 单独检查问题服务
docker compose logs python-api --tail 100
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否就绪
docker compose exec postgres pg_isready -U postgres

# 检查 API 是否能连接数据库
docker compose exec python-api python -c "
from db import connect
conn = connect('postgresql://postgres:密码@postgres:5432/liuhecai')
print('连接成功')
"
```

### 端口冲突

```bash
# 检查端口占用
sudo ss -tlnp | grep -E ':(80|443|3000|3002|5432|8000)'

# 修改 docker-compose.yml 中的端口映射
# 例如将 host 端口 3000 改为 3001:
#   ports:
#     - "127.0.0.1:3001:3000"
```

### 镜像构建失败

```bash
# 清理构建缓存后重试
docker compose build --no-cache

# 清理未使用的镜像和缓存
docker system prune -a
```

### 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 清理 Docker 资源
docker system prune -a --volumes

# 清理旧日志
sudo journalctl --vacuum-size=200M
```

---

## 目录结构

```
Liuhecai/
├── docker-compose.yml          # Docker Compose 编排配置
├── Dockerfile.python           # Python API Dockerfile
├── Dockerfile.backend          # Next.js 后台管理 Dockerfile
├── Dockerfile.frontend         # Next.js 前端站点 Dockerfile
├── .env.example                # 环境变量模板
├── DEPLOY.md                   # 本部署文档
├── backend/
│   ├── requirements.txt        # Python 依赖清单
│   ├── next.config.mjs         # Next.js 配置（standalone）
│   ├── src/                    # Python 源码
│   │   ├── app.py              # API 主入口
│   │   ├── config.yaml         # 应用配置
│   │   ├── db.py               # 数据库适配层
│   │   ├── config.py           # 配置加载
│   │   ├── crawler/            # 爬虫模块
│   │   ├── predict/            # 预测模块
│   │   └── utils/              # 工具模块
│   └── data/                   # 数据目录
│       ├── fixed_data.json     # 固定数据（号码映射）
│       ├── lottery_modes.sqlite3 # SQLite 数据库
│       ├── Images/             # 图片资源
│       └── lottery_data/       # 彩票数据
├── frontend/
│   ├── next.config.mjs         # Next.js 配置（standalone）
│   └── ...
└── deploy/
    ├── deploy.sh               # 一键部署脚本
    ├── nginx.conf              # Nginx 配置
    └── ssl/                    # SSL 证书（可选）
```

---

## 技术支持

- **项目仓库**: https://github.com/a1014826460-stack/Marksix
- **技术栈**: Python 3.12 + Next.js 14 + PostgreSQL 16 + Nginx + Docker