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

## 服务器操作授权规范

**未获得用户在当前任务中的明确指令，不得对任何服务器执行操作。** 禁止自行连接 SSH、`git pull`/推送、同步文件、构建镜像、执行数据库迁移、重启容器或服务、修改配置、删除运行时残留，或以任何方式部署本地代码。

- “继续开发”“完成修复”“提交本地代码”仅授权本地工作区操作，不构成服务器授权。
- 每次服务器操作须由用户明确说明目标服务器和动作范围；未明确的服务器、服务或数据库均不得触碰。
- 获得部署授权后，先核对工作区与远端运行时文件，按本指南完成备份和保护，再执行被授权的最小操作范围。

## 密钥管理与轮换

- `DATABASE_URL`、`POSTGRES_PASSWORD`、`FRP_AUTH_TOKEN` 只能通过部署平台 Secret、受限环境变量或被 Git 忽略的本地文件注入；不得写入脚本、TOML、文档示例或日志。
- 如果历史中曾提交凭据，先在数据库和 FRP 服务端轮换旧值，再撤销旧会话和不再需要的远程端口授权。仅删除仓库文本不能使旧凭据失效。
- 在提交或部署前运行：

```powershell
pwsh -File .\scripts\check-no-secrets.ps1
```

系统由 6 个容器组成：

- `postgres`
- `pgbouncer`
- `python-api`
- `backend-admin`
- `frontend`
- `nginx`

此外，`scheduler-worker` 是独立的持久化调度进程：它执行抓取、批量生成和备份任务；
`python-api` 仅提供 HTTP 接口，不再在自身进程中启动调度 timer。部署时必须保持该容器运行。

## 多服务器集群

中心服务器 `207.56.3.82` 使用完整的 [docker-compose.yml](/d:/pythonProject/outsource/Liuhecai/docker-compose.yml)：

- 运行 PostgreSQL、PgBouncer、`python-api`、`scheduler-worker`、`backend-admin`、`frontend` 与 Nginx。
- 承载前五个前端站点和唯一可写的数据库、后台管理及调度任务。
- 通过 `https://www.tw8800.com/central-api/api` 提供统一 Python API；`/api/*` 仍保留给当前站点的 Next.js 兼容接口，不能作为跨服务器地址。

其余服务器只能使用 [docker-compose.frontend-node.yml](/d:/pythonProject/outsource/Liuhecai/docker-compose.frontend-node.yml)：

- 仅运行 `frontend` 与 Nginx；不得运行 PostgreSQL、PgBouncer、`python-api`、`scheduler-worker`、`db-migrate` 或 `backend-admin`。
- 从 `.env.frontend-node.example` 复制 `.env`，并保留：

```ini
LOTTERY_BACKEND_BASE_URL=https://www.tw8800.com/central-api/api
LOTTERY_UPLOADS_BASE_URL=https://www.tw8800.com/central-api/uploads
```

- 图片、开奖、预测和站点配置均由中心 API 返回，因此不会复制数据库或出现跨节点数据分叉。
- 前端节点部署命令：

```bash
cp .env.frontend-node.example .env
# 修改 LOTTERY_SITE_ID、PUBLIC_HOST、NGINX_CONF_SOURCE 与证书配置
docker compose -f docker-compose.frontend-node.yml build frontend
docker compose -f docker-compose.frontend-node.yml up -d
```

HTTPS frontend nodes must copy
`deploy/nginx.frontend-node.ssl.conf.example` to the ignored
`deploy/nginx.frontend-node.conf.local`, replace its domain names, and set:

```ini
NGINX_CONF_SOURCE=./deploy/nginx.frontend-node.conf.local
PUBLIC_SCHEME=https
NGINX_EXPECT_HTTPS=1
```

Frontend-only node policy: always run `docker compose -f
docker-compose.frontend-node.yml ...`; never use `docker-compose.yml` on
these nodes. Before replacing a legacy full stack, archive its PostgreSQL
dump, `.env`, certificates, and `backend/data`, then remove the residual
`postgres`, `pgbouncer`, `python-api`, `scheduler-worker`, `db-migrate`, and
`backend-admin` containers and volumes. Do not copy the database or backend
runtime data to a frontend node.

中心服务器的 Nginx 配置必须包含 `location ^~ /central-api/api/` 与
`location ^~ /central-api/uploads/`。现有 HTTPS 配置使用
`deploy/nginx.conf.local` 时，也必须从 `deploy/nginx.domain.ssl.conf.example`
同步这两个区块后再重建 Nginx。

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
- `127.0.0.1:6432`

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

此 `.env` 仅用于 Linux 生产服务器的 Docker Compose。开发机不应复制或加载它；
本地开发仅使用 `backend/.env.local` 和 Windows 原生 PostgreSQL 18。

```bash
cp .env.example .env
nano .env
```

必须保留：

```ini
LIUHECAI_RUNTIME_ENV=production
```

不要在生产根 `.env` 中添加 `DATABASE_URL`。`python-api`、`scheduler-worker`
和 `db-migrate` 已由 Compose 固定注入内部 `pgbouncer:6432` DSN；部署和验证脚本
会拒绝任何根 `.env` 的 `DATABASE_URL`，以防误连接宿主机或开发数据库。

至少要修改：

```ini
POSTGRES_PASSWORD=请设置强密码
POSTGRES_POOL_MAX_SIZE=120
POSTGRES_POOL_TIMEOUT=15
PGBOUNCER_MAX_CLIENT_CONN=1200
PGBOUNCER_DEFAULT_POOL_SIZE=50
LOTTERY_SITE_ID=1

# 构建镜像源（网络不稳时建议配置）
NPM_REGISTRY=https://registry.npmmirror.com/
APT_MIRROR=mirrors.aliyun.com
```

### 无域名模式示例

```ini
POSTGRES_PASSWORD=请设置强密码
POSTGRES_POOL_MAX_SIZE=120
POSTGRES_POOL_TIMEOUT=15
PGBOUNCER_MAX_CLIENT_CONN=1200
PGBOUNCER_DEFAULT_POOL_SIZE=50
LOTTERY_SITE_ID=1

NGINX_CONF_SOURCE=./deploy/nginx.conf
PUBLIC_HOST=123.123.123.123
PUBLIC_SCHEME=http
NGINX_EXPECT_HTTPS=0
```

### 有域名模式示例

```ini
POSTGRES_PASSWORD=请设置强密码
POSTGRES_POOL_MAX_SIZE=120
POSTGRES_POOL_TIMEOUT=15
PGBOUNCER_MAX_CLIENT_CONN=1200
PGBOUNCER_DEFAULT_POOL_SIZE=50
LOTTERY_SITE_ID=1

NGINX_CONF_SOURCE=./deploy/nginx.conf.local
PUBLIC_HOST=www.example.com
PUBLIC_SCHEME=https
NGINX_EXPECT_HTTPS=1
```

补充说明：

- `POSTGRES_PASSWORD` 必改
- `POSTGRES_POOL_MAX_SIZE` 建议先保持 120，适合 6 个站点共用一套后端
- `PGBOUNCER_DEFAULT_POOL_SIZE` 决定 PgBouncer 后端复用规模
- `LOTTERY_SITE_ID` 决定前台默认站点
- `PUBLIC_HOST` 供 `deploy/verify.sh` 做访问验证
- `PUBLIC_SCHEME` 必须与实际暴露协议一致
- `NGINX_EXPECT_HTTPS=1` 时，验证脚本会按 HTTPS 检查

连接池说明：

- `POSTGRES_POOL_MAX_SIZE` 是 `python-api` 进程内连接池上限，控制应用最多同时持有多少条到 PgBouncer 的连接
- `PGBOUNCER_DEFAULT_POOL_SIZE` 是 PgBouncer 到 PostgreSQL 的后端连接池大小，控制数据库实际承载的长连接规模
- 当前默认值适合多个站点共用同一后端接口的场景；若未来流量明显上升，再结合 `pg_stat_activity` 和 PgBouncer 指标继续调整

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

启动后确认 worker 状态：

```bash
docker compose ps scheduler-worker
docker compose logs --tail=100 scheduler-worker
```

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
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@pgbouncer:6432/liuhecai"
```

### 规范化 `mode_payload_*`

```bash
docker compose exec python-api python /app/src/utils/normalize_payload_tables.py \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@pgbouncer:6432/liuhecai"
```

### 生成文本历史映射

```bash
docker compose exec python-api python /app/src/utils/build_text_history_mappings.py \
  --db-path "postgresql://postgres:${POSTGRES_PASSWORD}@pgbouncer:6432/liuhecai"
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
- `pgbouncer`：`127.0.0.1:6432`

说明：

- `frontend` 和 `backend-admin` 已改为轻量健康路由，不再依赖完整页面渲染
- 这能减少部署时被“页面级探针”误判为不健康的概率

## SQLite 迁移说明

当前仓库不再包含可直接执行的一键 SQLite -> PostgreSQL 迁移脚本。

也就是说：

- `RUN_SQLITE_MIGRATION=1 ./deploy/deploy.sh` 不会自动完成真实迁移
- 如果你只有旧的 SQLite 数据，需要先在旧工具或旧分支中完成迁移，再导入 PostgreSQL

## PostgreSQL 备份

调度器通过 `scheduler-worker` 执行 `pg_dump -Fc` 备份；`backend/data/backups` 必须挂载到持久化磁盘或对象存储同步目录，不能只依赖容器可写层。备份开始前会检查可用空间，`pg_dump` 与 `pg_restore --list` 都有超时，并在完成后保存 SHA-256 校验和。

关键运行配置：

- `database.backup_timeout_seconds`：`pg_dump` 最大运行时间，默认 900 秒。
- `database.backup_verify_timeout_seconds`：归档校验最大时间，默认 60 秒。
- `database.backup_min_free_space_mb`：开始前需要的最小可用空间，默认 1024 MiB。
- `database.backup_retention_days`：保留天数；清理前先确认备份已复制到异地存储。

部署前先运行显式 schema 迁移；API 和 worker 不会自行建表：

```bash
docker compose run --rm db-migrate
```

该迁移同时对齐 `created.mode_payload_*` 镜像：它使用 `public.mode_payload_*` 实际表与
`mode_payload_tables` 元数据的并集。新增预测模块或发现 `created` 缺表时，执行该迁移，
不要重启 API/worker 期待运行时自动建表或补列。

```bash
docker compose exec postgres pg_dump -U postgres liuhecai > backup_$(date +%Y%m%d).sql
```

自定义格式：

```bash
docker compose exec postgres pg_dump -U postgres liuhecai -F c -f /tmp/backup.dump
docker compose cp postgres:/tmp/backup.dump ./backup_$(date +%Y%m%d).dump
sha256sum ./backup_$(date +%Y%m%d).dump
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

## 备份恢复演练

至少每季度在隔离的测试数据库进行一次演练，不能直接在生产库验证恢复：

```bash
# 1. 校验归档是否可读，及其校验和是否匹配备份任务记录。
pg_restore --list ./backup_20250101.dump >/dev/null
sha256sum ./backup_20250101.dump

# 2. 创建隔离目标并恢复；实际名称按运维环境调整。
createdb liuhecai_restore_drill
pg_restore --clean --if-exists --no-owner -d liuhecai_restore_drill ./backup_20250101.dump

# 3. 检查关键表和最近开奖记录，记录恢复耗时、RPO 与 RTO。
psql -d liuhecai_restore_drill -c "SELECT COUNT(*) FROM lottery_draws;"
dropdb liuhecai_restore_drill
```

演练记录应包含：备份文件名、SHA-256、恢复开始/结束时间、校验查询结果、负责人与发现的问题。任何校验失败都应保留归档、停止清理，并通过告警渠道处理。

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

## 2026-08-19 历史开奖记录强制窗口发布记录

发布提交：`ce73a89f597a39e55929fe04a2719ff2076ac8dc`（已推送至 `origin/main`）。

当前强制窗口为固定 4 分钟：历史开奖记录统一入口 `/history`、后端及兼容出口、前端快照降级均以实际 `draw_time + 4 分钟` 控制，使用 `no-store` 缓存策略与旧历史 URL rewrite。台湾彩以北京时间 `22:32:00` 开奖为例，`22:35:59` 前隐藏，`22:36:00` 起显示；香港彩、澳门彩同样从各自实际开奖时间起计算 4 分钟。实时开奖接口、开奖状态更新和调度发布流程不读取此展示闸门，保持正常显示。

本次目标节点：

- 前端节点：`207.56.2.71:62594`，使用 `/root/Marksix/docker-compose.frontend-node.yml`，保留其 `.env`、Nginx 本地配置、证书、站点运行期内容和其他非 Liuhecai 容器。
- 中心后端节点：`207.56.3.82:29618`，使用 `/root/Marksix/docker-compose.yml`，保留 PostgreSQL、PgBouncer、数据库卷、`backend/data`、上传文件、备份、证书和本地 Nginx 配置。

标准发布顺序：

```bash
git fetch origin main
git reset --hard <4-minute-release-commit>
docker compose -f docker-compose.frontend-node.yml build frontend
docker compose -f docker-compose.frontend-node.yml up -d frontend nginx
docker compose -f docker-compose.frontend-node.yml exec -T nginx nginx -t
curl -fsS https://<frontend-host>/health
curl -fsS -D - https://<frontend-host>/api/draw-history?lottery_type=3&year=2026 -o /tmp/history.json
```

中心后端节点在应用重建前先执行数据库备份和迁移检查；本次代码无数据库 schema 变更，正常发布只需重建 `python-api`、`scheduler-worker`、`frontend` 和必要的 Nginx：

```bash
git fetch origin main
git reset --hard <4-minute-release-commit>
docker compose build python-api scheduler-worker frontend
docker compose up -d python-api scheduler-worker frontend nginx
docker compose exec -T nginx nginx -t
curl -fsS https://<backend-host>/health
```

验收要求：十个站点的 `/history?type=3` 和所有旧历史 URL 均返回标准历史页面；`/api/draw-history` 与 `/index/ajax/ttklsjl` 均返回 `Cache-Control: no-store`；台湾彩在 `22:35:59` 隐藏、`22:36:00` 显示，其他彩种以实际 `draw_time + 4 分钟` 验证；`/api/latest-draw`、`/wy.json` 和开奖发布测试保持通过。

本次执行记录：本地回归已通过，前端节点 SSH 只读预检成功并确认运行前端专用 Compose；中心后端节点 `103.203.48.178:19789` 在 `2026-08-19` 预检时 TCP 连接被拒绝，因此在该端口恢复前不得声称中心后端已部署或重启。远端工作树存在大量站点运行期修改，任何后续发布必须先按本指南创建时间戳备份，再同步发布提交。

实际发布结果（2026-08-19）：

- 前端节点 `207.56.2.71:62594` 已同步 `92ed6cb8dca5825d2329ecba72bb12a099cf5842`，仅重建 `frontend` 容器；`liuhecai-frontend` 健康检查为 `healthy`，Nginx `nginx -t` 通过。
- 前端节点备份目录：`/root/Marksix/.deploy-backups/history-delay-20260819T032328Z`。备份含部署前 HEAD、工作树 patch、未跟踪文件清单、`.env`、TLS 证书、本地 Nginx 配置、`backend/data` 与前端 Compose 配置。
- 已验证的前端域名：`www.twbst528.com`、`www.twjsz666.com`、`www.twssz.com`、`www.twsyw.com`、`www.twwanli.com`；各自 `/history?type=3` 返回 HTTP `200`。全部 8 个兼容历史路径返回 HTTP `200`，`/api/draw-history` 返回 `Cache-Control: no-store`。
- 中心后端节点尚未接入：`103.203.48.178:19789` 返回连接拒绝；`103.203.48.178:22` 可建立 SSH 握手但拒绝当前公钥认证。待 SSH 服务恢复至指定端口或提供可认证的访问方式后，按本节“中心后端节点”步骤同步同一发布提交、重建 `python-api`/`scheduler-worker`/`frontend`、执行 Nginx 与健康检查。

后端实际发布结果（2026-08-19，修正后的中心节点地址）：

- 中心后端节点为 `207.56.3.82:29618`；已同步 `6a3ff82bbe7131582bc2368a1df4140b3384b832`，并完成 `python-api`、`scheduler-worker`、`frontend`、`backend-admin`、Nginx 重建。
- 迁移命令 `docker compose run --rm db-migrate` 输出 `Schema migrations are already current.`；PostgreSQL 与 PgBouncer 卷未重建或删除。
- 中心节点发布前备份目录：`/root/Marksix/.deploy-backups/history-delay-backend-20260819T033711Z`，其中包含工作树 patch、运行期文件归档、Compose 快照、Nginx 检查结果，以及 `liuhecai.before.dump` 和 SHA-256 校验文件。
- 中心 `python-api`、`frontend`、`backend-admin` 健康状态均为 `healthy`；`scheduler-worker` 正常运行；Nginx `nginx -t` 通过。
- 中心历史 API `https://www.tw8800.com/central-api/api/public/draw-history?lottery_type=3&year=2026` 返回 HTTP `200` 和 `Cache-Control: no-store`；实时开奖 API `/api/latest-draw?lottery_type=3` 返回 HTTP `200` 与当前期号。
- 中心五站 `www.tw8800.com`、`www.twtongtian.com`、`www.twsaimahui.com`、`www.twcf888.com`、`www.twcaibawang.com` 的 `/history?type=3` 均返回 HTTP `200`；前端节点五站 `www.twbst528.com`、`www.twjsz666.com`、`www.twssz.com`、`www.twsyw.com`、`www.twwanli.com` 均已在前述记录中验证为 HTTP `200`。8 个旧历史兼容路径在中心节点均返回 HTTP `200`。

### 4 分钟窗口部署执行记录（2026-08-19）

发布提交：`<4-minute-release-commit>`。

1. 后端节点发布前，在 `/root/Marksix` 生成时间戳备份目录，保存工作树 patch、运行期文件清单、Compose 快照和 PostgreSQL 自定义格式备份及 SHA-256。
2. 同步发布提交后，显式将数据库配置更新为 `4`，使已存在的 `system_config` 不再保留旧的 `60`：

```bash
docker compose exec -T postgres psql -U postgres -d liuhecai -c "UPDATE system_config SET value_text = '4', value_type = 'int', updated_at = NOW() WHERE key = 'history_backfill_delay_after_draw';"
```

3. 仅重建 `python-api`、`scheduler-worker` 和 `frontend`；不重建 PostgreSQL、PgBouncer 或数据卷：

```bash
docker compose build python-api scheduler-worker frontend
docker compose up -d python-api scheduler-worker frontend nginx
docker compose exec -T nginx nginx -t
```

4. 前端节点使用 `docker-compose.frontend-node.yml`，仅重建 `frontend` 并保留 Nginx/TLS：

```bash
docker compose -f docker-compose.frontend-node.yml build frontend
docker compose -f docker-compose.frontend-node.yml up -d frontend nginx
docker compose -f docker-compose.frontend-node.yml exec -T nginx nginx -t
```

5. 发布后检查所有十个站点的 `/history?type=3`、历史 API `Cache-Control: no-store`，并分别检查 `/api/latest-draw?lottery_type=3` 和 `/wy.json` 返回成功；后两项用于确认实时开奖未受历史展示窗口影响。
