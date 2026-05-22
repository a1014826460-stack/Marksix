# Liuhecai 部署指南

适用于 Ubuntu 20.04 / 22.04 / 24.04 LTS。

当前仓库已经支持两种可落地的部署方式：

- 无域名 / 仅服务器 IP / HTTP
- 有域名 / HTTPS

本文档以仓库当前实际文件为准，包括：

- [docker-compose.yml](/d:/pythonProject/outsource/Liuhecai/docker-compose.yml)
- [deploy/deploy.sh](/d:/pythonProject/outsource/Liuhecai/deploy/deploy.sh)
- [deploy/verify.sh](/d:/pythonProject/outsource/Liuhecai/deploy/verify.sh)
- [deploy/nginx.conf](/d:/pythonProject/outsource/Liuhecai/deploy/nginx.conf)
- [deploy/nginx.domain.ssl.conf.example](/d:/pythonProject/outsource/Liuhecai/deploy/nginx.domain.ssl.conf.example)
- [deploy/nginx.www.shengshi8800.ssl.conf.example](/d:/pythonProject/outsource/Liuhecai/deploy/nginx.www.shengshi8800.ssl.conf.example)

## 概览

系统由 5 个容器组成：

- `postgres`
- `python-api`
- `backend-admin`
- `frontend`
- `nginx`

对外访问入口：

- `/` -> `frontend`
- `/api/*` -> `frontend` 的兼容 API 层
- `/fackyou/*` -> `backend-admin`
- `/uploads/*` -> `python-api`
- `/health` -> `python-api:/api/health`

宿主机本机访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/health`
- `127.0.0.1:5432`

## 两种部署模式

### 1. 无域名 / 服务器 IP / HTTP

适用场景：

- 刚上服务器
- 还没有域名
- 先验证业务能跑通

必须使用：

```ini
NGINX_CONF_SOURCE=./deploy/nginx.conf
PUBLIC_HOST=你的服务器IP
PUBLIC_SCHEME=http
NGINX_EXPECT_HTTPS=0
```

特点：

- 直接通过服务器 IP 访问
- 不要求证书
- 默认只走 HTTP

### 2. 有域名 / HTTPS

适用场景：

- 已经有正式域名
- 已完成 DNS 解析
- 已准备证书

必须使用：

```ini
NGINX_CONF_SOURCE=./deploy/nginx.conf.local
PUBLIC_HOST=www.example.com
PUBLIC_SCHEME=https
NGINX_EXPECT_HTTPS=1
```

并且必须存在证书文件：

```text
deploy/ssl/fullchain.pem
deploy/ssl/privkey.pem
```

说明：

- `deploy/deploy.sh` 会在启动前校验 HTTPS 模式是否真的满足条件
- 如果你开了 `NGINX_EXPECT_HTTPS=1`，但还在用默认 `deploy/nginx.conf`，脚本会直接报错

## 前置要求

- Ubuntu 20.04 / 22.04 / 24.04 LTS
- 建议 4 GB 内存起步，8 GB 更稳
- 至少 20 GB 可用磁盘
- 能访问外网
- 当前用户可使用 `sudo`

基础环境准备：

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl git nano dnsutils ufw
sudo timedatectl set-timezone Asia/Hong_Kong
```

推荐部署目录：

```bash
sudo install -d -m 755 /opt/Liuhecai
sudo chown "$USER":"$USER" /opt/Liuhecai
```

## 安装 Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

sudo apt update
sudo apt install -y docker-compose-plugin

sudo usermod -aG docker "$USER"
```

重新登录 shell 或重新 SSH 登录后执行：

```bash
docker --version
docker compose version
docker info
```

如果 `docker info` 失败：

```bash
sudo systemctl enable --now docker
docker info
```

## 获取项目

```bash
git clone https://github.com/a1014826460-stack/Marksix.git /opt/Liuhecai
cd /opt/Liuhecai
```

## 配置 `.env`

```bash
cp .env.example .env
nano .env
```

至少要修改：

```ini
POSTGRES_PASSWORD=请设置强密码
LOTTERY_SITE_ID=1

# 构建镜像源（网络不稳时建议配置）
NPM_REGISTRY=https://registry.npmmirror.com/
APT_MIRROR=mirrors.aliyun.com
```

### 无域名模式示例

```ini
POSTGRES_PASSWORD=请设置强密码
LOTTERY_SITE_ID=1

NGINX_CONF_SOURCE=./deploy/nginx.conf
PUBLIC_HOST=123.123.123.123
PUBLIC_SCHEME=http
NGINX_EXPECT_HTTPS=0
```

### 有域名模式示例

```ini
POSTGRES_PASSWORD=请设置强密码
LOTTERY_SITE_ID=1

NGINX_CONF_SOURCE=./deploy/nginx.conf.local
PUBLIC_HOST=www.example.com
PUBLIC_SCHEME=https
NGINX_EXPECT_HTTPS=1
```

补充说明：

- `POSTGRES_PASSWORD` 必改
- `LOTTERY_SITE_ID` 决定前台默认站点
- `PUBLIC_HOST` 供 `deploy/verify.sh` 做访问验证
- `PUBLIC_SCHEME` 必须与实际暴露协议一致
- `NGINX_EXPECT_HTTPS=1` 时，验证脚本会按 HTTPS 检查

## 快速部署

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

脚本会执行：

1. 检查 Docker / Docker Compose / Docker daemon
2. 准备 `.env`
3. 校验当前部署模式
4. 构建镜像
5. 启动容器
6. 等待健康检查通过
7. 首次导入 `fixed_data`（如需要）

## 快速验证

```bash
chmod +x deploy/verify.sh
./deploy/verify.sh
```

验证脚本现在支持两种模式：

- HTTP/IP 模式：按 `http://PUBLIC_HOST/...` 检查
- HTTPS/域名模式：按 `https://PUBLIC_HOST/...` 检查，并使用 `curl --resolve` 映射到本机 `127.0.0.1`

## 手动部署

### 构建镜像

```bash
docker compose build
```

或分别构建：

```bash
docker compose build python-api
docker compose build backend-admin
docker compose build frontend
```

### 启动服务

```bash
docker compose up -d
docker compose ps
```

### 查看日志

```bash
docker compose logs -f
docker compose logs --tail 200 frontend
docker compose logs --tail 200 backend-admin
docker compose logs --tail 200 python-api
docker compose logs --tail 200 nginx
```

## 首次数据初始化

### 导入 `fixed_data`

```bash
docker compose exec python-api python /app/src/tools/import_fixed_data.py \
  --fixed-data-path /app/data/fixed_data.json \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

### 规范化 `mode_payload_*`

```bash
docker compose exec python-api python /app/src/utils/normalize_payload_tables.py \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

### 生成文本历史映射

```bash
docker compose exec python-api python /app/src/utils/build_text_history_mappings.py \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/liuhecai"
```

## 无域名部署说明

如果你暂时没有域名，推荐直接使用默认的 [deploy/nginx.conf](/d:/pythonProject/outsource/Liuhecai/deploy/nginx.conf)。

访问方式：

- `http://服务器IP/`
- `http://服务器IP/fackyou/login`
- `http://服务器IP/health`

注意：

- 默认 `docker-compose.yml` 暴露了 `443`，但默认 `deploy/nginx.conf` 不监听 `443`
- 没有域名时，不建议强行做公网 HTTPS
- 如果用 IP + 自签名证书，浏览器通常会提示不受信任

## 域名 + HTTPS 部署

### 第 1 步：做 DNS 解析

示例：

- `A` 记录：`@` -> 服务器公网 IP
- `A` 记录：`www` -> 服务器公网 IP

验证：

```bash
dig +short example.com
dig +short www.example.com
```

### 第 2 步：申请证书

安装 Certbot：

```bash
sudo apt update
sudo apt install -y certbot
```

如果当前 `nginx` 容器占用了 80 端口，可以暂时停掉：

```bash
cd /opt/Liuhecai
docker compose stop nginx

sudo certbot certonly --standalone \
  -d example.com \
  -d www.example.com \
  --agree-tos \
  -m you@example.com \
  --non-interactive

docker compose start nginx
```

### 第 3 步：放置证书

```bash
sudo cp /etc/letsencrypt/live/example.com/fullchain.pem deploy/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/example.com/privkey.pem deploy/ssl/privkey.pem
sudo chown "$USER":"$USER" deploy/ssl/fullchain.pem deploy/ssl/privkey.pem
```

### 第 4 步：准备 HTTPS Nginx 配置

通用域名模板：

```bash
cp deploy/nginx.domain.ssl.conf.example deploy/nginx.conf.local
```

如果使用 `www.tw8800.com`：

```bash
cp deploy/nginx.www.shengshi8800.ssl.conf.example deploy/nginx.conf.local
```

如使用通用模板，请把里面的：

- `example.com`
- `www.example.com`

替换成你的真实域名。

### 第 5 步：更新 `.env`

```ini
NGINX_CONF_SOURCE=./deploy/nginx.conf.local
PUBLIC_HOST=www.example.com
PUBLIC_SCHEME=https
NGINX_EXPECT_HTTPS=1
```

### 第 6 步：检查并重启

```bash
docker compose exec nginx nginx -t
docker compose restart nginx
```

### 第 7 步：验证 HTTPS

```bash
curl -I http://example.com
curl -I https://example.com
curl -I https://www.example.com
curl -k https://www.example.com/health
```

预期：

- `http://example.com` 返回 `301` 或 `308`
- `https://example.com` 跳转到 `https://www.example.com`
- `https://www.example.com/health` 返回 `200`

## 更换域名或新增域名

下面分两种情况：

- 更换现有主域名，例如：`www.shengshi8800.com` -> `www.tw8800.com`
- 新增第二个域名，例如：在 `www.tw8800.com` 之外，再增加 `www.twsaimahui.com`

### 场景 1：更换现有主域名

推荐顺序：

1. 先完成新域名的 DNS 解析
2. 再申请或重新签发新域名证书
3. 再修改 Nginx 配置中的 `server_name` 和跳转目标
4. 再检查 `.env` 中的 `PUBLIC_HOST`
5. 最后重建 `nginx` 容器并验证

示例：将主域名切换到 `www.tw8800.com`

1. 准备新证书

```bash
docker compose stop nginx

sudo certbot certonly --standalone \
  -d tw8800.com \
  -d www.tw8800.com \
  --agree-tos \
  -m you@example.com \
  --non-interactive
```

2. 复制证书

```bash
sudo cp /etc/letsencrypt/live/tw8800.com/fullchain.pem deploy/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/tw8800.com/privkey.pem deploy/ssl/privkey.pem
sudo chown "$USER":"$USER" deploy/ssl/fullchain.pem deploy/ssl/privkey.pem
```

3. 更新 Nginx 配置

- 如果你使用仓库里的专用模板，例如 [deploy/nginx.www.shengshi8800.ssl.conf.example](/d:/pythonProject/outsource/Liuhecai/deploy/nginx.www.shengshi8800.ssl.conf.example)，需要把其中旧域名替换为新域名
- 或者重新从模板复制到 `deploy/nginx.conf.local`，再手工检查 `server_name`、`return 301`、注释示例域名是否都已更新

4. 更新 `.env`

```ini
NGINX_CONF_SOURCE=./deploy/nginx.conf.local
PUBLIC_HOST=www.tw8800.com
PUBLIC_SCHEME=https
NGINX_EXPECT_HTTPS=1
```

5. 重建 Nginx

注意：如果你修改了 `NGINX_CONF_SOURCE` 或替换了挂载配置源，`docker compose restart nginx` 可能不够，建议直接重建容器：

```bash
docker compose up -d --force-recreate nginx
docker compose exec nginx nginx -t
```

6. 验证

```bash
curl -I http://tw8800.com
curl -I https://tw8800.com
curl -I https://www.tw8800.com
curl -k https://www.tw8800.com/health
```

### 场景 2：新增第二个域名

例如：

- 已有：`www.tw8800.com`
- 新增：`www.twsaimahui.com`

这种情况下，不是替换原域名，而是让同一个 `nginx` 同时服务两个正式域名。

需要同时满足 3 个条件：

1. 新域名已完成 DNS 解析
2. 证书已扩展为覆盖全部域名
3. `deploy/nginx.conf.local` 中同时存在两组 `server` 配置

#### 第 1 步：扩展证书

如果已有证书只包含旧域名，执行扩展：

```bash
docker compose stop nginx

sudo certbot certonly --standalone \
  -d tw8800.com \
  -d www.tw8800.com \
  -d twsaimahui.com \
  -d www.twsaimahui.com \
  --agree-tos \
  -m you@example.com \
  --non-interactive \
  --expand
```

说明：

- `--expand` 表示把现有证书扩展成包含更多域名的新证书
- 证书签发完成后，继续覆盖 `deploy/ssl/fullchain.pem` 和 `deploy/ssl/privkey.pem`

```bash
sudo cp /etc/letsencrypt/live/tw8800.com/fullchain.pem deploy/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/tw8800.com/privkey.pem deploy/ssl/privkey.pem
sudo chown "$USER":"$USER" deploy/ssl/fullchain.pem deploy/ssl/privkey.pem
```

#### 第 2 步：把第二域名的 `server` 配置追加到主配置

仓库已提供第二域名示例：

- [deploy/nginx.www.twsaimahui.ssl.conf.example](/d:/pythonProject/outsource/Liuhecai/deploy/nginx.www.twsaimahui.ssl.conf.example)

如果你当前的 `deploy/nginx.conf.local` 已经是 `www.tw8800.com` 的正式配置，可直接追加：

```bash
cat deploy/nginx.www.twsaimahui.ssl.conf.example >> deploy/nginx.conf.local
```

说明：

- `www.tw8800.com` 和 `www.twsaimahui.com` 需要分别有自己的 `server_name`
- 不能只保留一个域名的 `server` 块，否则另一个域名会落到默认站点或被错误跳转

#### 第 3 步：检查并重建 Nginx

```bash
docker compose up -d --force-recreate nginx
docker compose exec nginx nginx -t
```

如果 `nginx -t` 报错，优先检查：

- 是否重复追加了同一份 `server` 配置
- 是否存在相同 `server_name` 的重复定义
- 证书文件是否已经复制到 `deploy/ssl/`

#### 第 4 步：分别验证两个域名

```bash
curl -I http://tw8800.com
curl -kI https://www.tw8800.com/health

curl -I http://twsaimahui.com
curl -kI https://www.twsaimahui.com/health
```

预期：

- `http://tw8800.com` 跳转到 `https://www.tw8800.com/...`
- `https://www.tw8800.com/health` 返回 `200`
- `http://twsaimahui.com` 跳转到 `https://www.twsaimahui.com/...`
- `https://www.twsaimahui.com/health` 返回 `200`

### 关于 `.env` 的说明

新增第二个域名时，通常不需要增加第二套 `.env`。

当前 `.env` 中：

- `NGINX_CONF_SOURCE` 控制 Nginx 实际挂载哪份配置
- `PUBLIC_HOST` 主要用于 `deploy/verify.sh` 的默认验证目标
- `PUBLIC_SCHEME` 和 `NGINX_EXPECT_HTTPS` 用于部署脚本和验证脚本的 HTTPS 模式判断

也就是说：

- 多域名托管的关键在 `deploy/nginx.conf.local`
- `.env` 只需要保留一个默认 `PUBLIC_HOST`，例如 `www.tw8800.com`
- 对第二个域名，请手工使用 `curl` 单独验证，或临时覆盖 `VERIFY_HOST`

例如：

```bash
VERIFY_HOST=www.twsaimahui.com ./deploy/verify.sh
```

## 推荐切换顺序

推荐按这个顺序上线，最稳：

1. 先用无域名 / IP / HTTP 模式把项目跑通
2. 再配置 DNS
3. 再申请证书
4. 再切换到 `deploy/nginx.conf.local`
5. 再把 `.env` 改成 HTTPS 模式
6. 最后执行 `./deploy/deploy.sh` 和 `./deploy/verify.sh`

## 健康检查

当前健康检查入口：

- `python-api`：`http://127.0.0.1:8000/health`
- `python-api API`：`http://127.0.0.1:8000/api/health`
- `frontend`：容器内 `http://127.0.0.1:3000/health`
- `backend-admin`：容器内 `http://127.0.0.1:3002/fackyou/health`
- `nginx`：对外 `/health`

说明：

- `frontend` 和 `backend-admin` 已改为轻量健康路由，不再依赖完整页面渲染
- 这能减少部署时被“页面级探针”误判为不健康的概率

## SQLite 迁移说明

当前仓库不再包含可直接执行的一键 SQLite -> PostgreSQL 迁移脚本。

也就是说：

- `RUN_SQLITE_MIGRATION=1 ./deploy/deploy.sh` 不会自动完成真实迁移
- 如果你只有旧的 SQLite 数据，需要先在旧工具或旧分支中完成迁移，再导入 PostgreSQL

## PostgreSQL 备份

```bash
docker compose exec postgres pg_dump -U postgres liuhecai > backup_$(date +%Y%m%d).sql
```

自定义格式：

```bash
docker compose exec postgres pg_dump -U postgres liuhecai -F c -f /tmp/backup.dump
docker compose cp postgres:/tmp/backup.dump ./backup_$(date +%Y%m%d).dump
```

## PostgreSQL 恢复

SQL 恢复：

```bash
docker compose exec -T postgres psql -U postgres liuhecai < backup_20250101.sql
```

自定义 dump 恢复：

```bash
docker compose cp ./backup_20250101.dump postgres:/tmp/restore.dump
docker compose exec postgres pg_restore -U postgres -d liuhecai --clean --if-exists /tmp/restore.dump
```

## 运维常用命令

```bash
docker compose ps
docker compose logs -f
docker compose restart python-api
docker compose restart frontend
docker compose restart backend-admin
docker compose restart nginx
docker compose down
docker compose down -v
git pull
docker compose build
docker compose up -d
```

注意：

- `docker compose down -v` 可能删除 PostgreSQL 数据卷
- 生产执行前请确认备份

进入容器：

```bash
docker compose exec python-api bash
docker compose exec postgres psql -U postgres -d liuhecai
docker compose exec nginx nginx -T
```

## 防火墙

如果服务器前面还有云厂商安全组，请同时放行：

- `22/tcp`
- `80/tcp`
- `443/tcp`

然后再启用 UFW：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

## 故障排查

### 1. 服务启动失败

```bash
docker compose ps
docker compose logs --tail 100 python-api
docker compose logs --tail 100 backend-admin
docker compose logs --tail 100 frontend
docker compose logs --tail 100 nginx
```

### 2. Docker daemon 未启动

```bash
sudo systemctl status docker
sudo systemctl start docker
```

### 3. 访问 502

```bash
docker compose restart nginx
docker compose logs --tail 100 nginx
```

### 4. 数据库连接失败

```bash
docker compose exec postgres pg_isready -U postgres -d liuhecai
```

### 5. 端口冲突

```bash
sudo ss -tlnp | grep -E ':(80|443|3000|3002|5432|8000)'
```

### 6. 镜像构建失败

```bash
docker compose build --no-cache
```

如果需要清理：

```bash
docker system prune -a
```

### 7. 磁盘空间不足

```bash
df -h
docker system prune -a --volumes
sudo journalctl --vacuum-size=200M
```

注意：

- `docker system prune -a --volumes` 可能删除未使用卷
- 操作前请确认备份

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
├── frontend/
└── deploy/
    ├── deploy.sh
    ├── verify.sh
    ├── nginx.conf
    ├── nginx.domain.ssl.conf.example
    ├── nginx.www.shengshi8800.ssl.conf.example
    └── ssl/
```
