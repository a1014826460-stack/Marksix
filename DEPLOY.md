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
docker compose build db-migrate        # 必须先重建：db-migrate 是运行时依赖，不在常规 build 列表里
docker compose run --rm db-migrate
```

`docker compose build python-api scheduler-worker frontend` **不会**重建 `marksix-db-migrate`。
若该镜像仍停留在旧版本，迁移脚本里没有新版本号，会打印
`Schema migrations are already current.` 而什么都不做；随后 `python-api`/`scheduler-worker`
会因 `validate_runtime_schema()` 缺少新版本号而崩溃重启
（`SchemaMigrationRequired: 数据库缺少 schema migration 版本 N`）。
出现该报错时用新镜像执行迁移即可：

```bash
docker compose build db-migrate
docker compose run --rm db-migrate     # 期望输出 Applied schema migrations: <N>
docker compose up -d python-api scheduler-worker
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
git reset --hard b9e2c921b0184dfdd98923b0ad8e2c28229d7bfd
docker compose -f docker-compose.frontend-node.yml build frontend
docker compose -f docker-compose.frontend-node.yml up -d frontend nginx
docker compose -f docker-compose.frontend-node.yml exec -T nginx nginx -t
curl -fsS https://<frontend-host>/health
curl -fsS -D - https://<frontend-host>/api/draw-history?lottery_type=3&year=2026 -o /tmp/history.json
```

中心后端节点在应用重建前先执行数据库备份和迁移检查；本次代码无数据库 schema 变更，正常发布只需重建 `python-api`、`scheduler-worker`、`frontend` 和必要的 Nginx：

```bash
git fetch origin main
git reset --hard b9e2c921b0184dfdd98923b0ad8e2c28229d7bfd
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

发布提交：`b9e2c921b0184dfdd98923b0ad8e2c28229d7bfd`。

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

### 4 分钟窗口实际部署结果（2026-08-19）

- 发布代码提交：`f45bce56ad75945a8f18ea3321978279e7e067b8`。
- 前端节点 `207.56.2.71:62594`：部署前备份目录为 `/root/Marksix/.deploy-backups/history-delay-4min-frontend-20260819T083616Z`；已重建 `frontend`，保留 `nginx` 与 TLS；Nginx `nginx -t` 成功。
- 中心后端节点 `207.56.3.82:29618`：部署前备份目录为 `/root/Marksix/.deploy-backups/history-delay-4min-backend-20260819T083604Z`，包括 `liuhecai.before.dump` 与 SHA-256；`system_config.history_backfill_delay_after_draw` 已显式更新为 `4`；已重建 `python-api`、`scheduler-worker`、`frontend`，未重建 PostgreSQL、PgBouncer 或其数据卷；Nginx `nginx -t` 成功。
- 十个站点的 `/history?type=3` 与 `/api/latest-draw?lottery_type=3` 均返回 HTTP `200`；历史 API 均返回 `Cache-Control: no-store`。
- `/wy.json` 为站点按需端点：中心的 `www.twtongtian.com`、`www.twcf888.com`、`www.twcaibawang.com` 返回 HTTP `200`；其余站点返回 HTTP `404`，但十个站点的实时开奖统一接口 `/api/latest-draw?lottery_type=3` 全部返回 HTTP `200`，不受历史展示闸门影响。

### twssz A级猛料 对/错与命中高亮修复部署结果（2026-09-23）

- 发布代码提交：`bca515a`（`fix(twssz): 修正 A级猛料 的对/错判定与命中高亮`）。
- 前端节点 `207.56.2.71:62594`：部署前备份目录为 `/root/Marksix/.deploy-backups/twssz-grade-a-20260923T065833Z`（含 `docker-compose.frontend-node.yml`、`.env`、`deploy/nginx.frontend-node.conf`、`HEAD.txt`）；仅重建 `frontend`，`nginx` 与 TLS 未改动。
- 容器内校验：`grep -c markHitLeaf /app/public/vendor/twssz/site-data-adapter.js` 为 `6`，`setAttribute("bgcolor"` 为 `0`；`liuhecai-frontend` 状态 `healthy`。
- 公网校验：`https://www.twssz.com/vendor/twssz/site-data-adapter.js` 返回 `HTTP 200`、`Cache-Control: public, max-age=0`，内容已含 `markHitLeaf`（浏览器下次加载即生效，无需强刷）。
- 真实资料校验（`https://www.twssz.com/twssz`）：8 张 A级猛料 卡片中 `265期` 显示 `开：猪08对`，猪在七肖/四肖/二肖、08 在⑧码/⑤码上呈黄色背景；`266期` 为 `开：待开奖` 且无高亮；`260期` 为 `开：鼠31`（命中判定不成立）；全部卡片均未出现“错”。

### twtongtian/twcf888 命中规则与展示修复部署结果（2026-09-23）

- 发布代码提交：`6f124c7`（九肖18码“任一命中即中”+ 平特一肖三连生肖展示）、
  `3499391`（平特一肖按平特口径）、`5baa488`（平特二肖/三肖/一尾一并按平特口径）。
- 中心节点 `207.56.3.82:29618`：
  - `6f124c7` 备份目录 `/root/Marksix/.deploy-backups/twjinniu-twcf888-mode103-20260923T111923Z`；
    重建 `frontend`、`python-api`、`scheduler-worker`，`nginx` 与 TLS 未改动。
  - `3499391` + `5baa488` 备份目录 `/root/Marksix/.deploy-backups/flat-pingte-20260923T115550Z`；
    重建 `frontend`、`python-api`、`scheduler-worker`。
  - 两个备份目录均含 `docker-compose.yml`、`.env`、`deploy/nginx.conf`、`HEAD.txt`、`STATUS.txt`、`worktree.patch`。
- 容器内校验：`domains/prediction/generation_rules.py` 含 `43/56/103/470 → zodiac_flat`、
  `54/173 → tail_flat`；`predict/mechanisms.py` 有 6 处 `flat_zodiac=True|flat_tail=True`；
  `liuhecai-frontend`/`liuhecai-python-api` 均为 `healthy`，`Schema migrations are already current`。
- 公网校验（同一批近 19 期真实资料，`is_correct` 按新规则即时重算）：
  - `www.twcf888.com`：mode 103 `平特一肖` 2/19 → **12/19**；mode 56 `平特1肖` 3/19 → **12/19**；
    mode 54 `平特1尾` 3/19 → **12/19**；mode 470 `平特3肖` 4/19 → **19/19**；mode 43 `平特2肖` → **16/19**。
  - `www.twssz.com`：mode 56 → 10/19、mode 54 → 12/19、mode 470 → 19/19、mode 43 → 15/19；
    非平特模块保持原口径（如 mode 69 `三肖中特` 仍 4/19）。
  - `www.twtongtian.com/api/twjinniu/homepage-modules`：`265期 平特一肖 〖蛇蛇蛇〗开：08猪对`
    （旧为“错”），`平特一尾` 264/263 期显示“对”、265 期（无 5 尾）显示“错”，
    `公式平特肖` 平码命中显示 √，未命中显示 ×。
- 遗留问题（未处理）：生产上台湾彩未来期号码可能在当日 12:10 预测生成之后被后台改写
  （2026-09-23 19:17 管理员 `PUT /api/admin/draws/105948` 改写了 266 期号码），
  导致生成时校验过的受控命中失效；建议未来期号码在预测生成后不再改写，或在改写后触发该期重新生成。

### 后台开奖改写确认提示部署结果（2026-09-23）

- 发布代码提交：`92b780f`（`feat(admin): 修改未开奖期号码前给出“预测会失效”确认提示`）。
- 中心节点 `207.56.3.82:29618`：部署前备份目录 `/root/Marksix/.deploy-backups/admin-draw-confirm-20260923T140937Z`；
  `git pull` 至 `92b780f` 后仅重建 `backend-admin`（`Image marksix-backend-admin Built`），
  `nginx`、TLS、PostgreSQL、PgBouncer 均未改动；`liuhecai-backend-admin` 状态 `healthy`，`redis` `healthy`。
- 后台入口（本次核实）：生产后台由 nginx 挂在各站点的 `/fackyou` 路径下
  （`map "" $be_admin { default "backend-admin:3002"; }` 配合 `location = /fackyou` 与 `location /fackyou/`
  反代到 Next.js admin）；非 `www` 主机访问会 `301` 跳到 `https://www.<站点>/fackyou/...`，
  因此 `https://<站点>/admin` 在公网并不存在（返回 `404`）。
  - `https://www.twcf888.com/fackyou/login` → `200`；`https://www.twcf888.com/fackyou/draws` → `200`。
- 公网产物校验：`https://www.twcf888.com/fackyou/_next/static/chunks/0da5uwjn25gbc.js` 内已含编译后的守卫
  `if(a&&rU(n)!==rU(a.numbers||"")&&!confirm('第 ${u} 期尚未开奖，…确认继续保存吗？'))return;`，
  即管理员未点确认时不会发出 `PUT /admin/draws/{id}`；SSR chunk
  `backend_features_draws_DrawsPage_tsx_0t.9h~r._.js` 同步含该文案。
- 遗留问题（未处理）：`draw_audit_log` 仍不记录管理员改写开奖号码的事件
  （事件词表只有 `source_fetch`/`precise_upsert`/`precise_complete`/`auto_open`/`precise_open`/`precise_fetch`，
  操作者只有 `crawler`/`scheduler`）；本次仅按用户选择加入 UI 确认提示，未加审计日志，
  也未在改写后触发该期预测重新生成。

### 开奖模块提速：nginx 边缘缓存 + `/vendor` 静态直出部署结果（2026-09-24）

- 变更内容：`scripts/patch-nginx-edge-cache.py`（幂等补丁）向两台节点实际生效的配置注入
  ① http 层 `proxy_cache_path kj_api`、`gzip`、`log_format kj_timing`；
  ② 每个对外 server 块的 3 秒（开奖）/5 秒（站点开奖）/20 秒（预测聚合、公告）代理缓存
  location（`proxy_cache_lock` 并发合并、`proxy_cache_use_stale updating`、忽略上游
  `Cache-Control` 以便缓存 `private` 聚合响应、剥离 `Set-Cookie`）；
  ③ `/vendor/**` 由 nginx 直接读宿主仓库 `frontend/public`（挂载 `/srv/public`），
  `try_files ... @vendor_frontend` 保证未命中回落 Next.js。
  详细分析见 `docs/2026-09-24-vendor-draw-module-loading-and-edge-cache.md`。
- 中心节点 `207.56.3.82:29618`：备份目录 `/root/Marksix/.deploy-backups/perf-edge-cache-20260923T171525Z`
  （`nginx.conf.local`、`docker-compose.yml`、`.env`、`HEAD.txt`、`STATUS.txt`，以及
  `.pre-edge-cache-*`、`.pre-mount`、`.pre-cache-log-*` 三份时间点副本）；
  修改 `deploy/nginx.conf.local`（5 个对外 server 块）与 `docker-compose.yml`
  （nginx 增加 `./frontend/public:/srv/public:ro`）；`nginx -t` 通过，`nginx -s reload` 后
  `docker compose up -d nginx` 仅重建 nginx。
- 前端节点 `207.56.2.71:62594`：备份目录 `/root/Marksix/.deploy-backups/perf-edge-cache-20260923T171938Z`
  （`nginx.frontend-node.conf.local`、`docker-compose.frontend-node.yml`、`.env`、`HEAD.txt`、
  `STATUS.txt` 及三份时间点副本）；同样 5 个 server 块，`docker compose -f
  docker-compose.frontend-node.yml up -d nginx`。
- 前置校验：两台节点 `frontend/public` 与容器内 `/app/public` **795 个文件、抽样 md5 全部一致**，
  因此静态直出不会串版本。
- 公网/容器内校验：
  - `/vendor/twssz/index.html` 返回 `HTTP/2 200`、`server: nginx`、
    `content-length` 与宿主文件一致、**不再有 `x-powered-by: Next.js`**；
  - `/vendor/<site>/static/**` 返回 `cache-control: public, max-age=31536000, immutable`；
  - `/vendor/<site>/history.html?type=3` 仍返回历史页 `200 text/html`（Next 重写未被绕过）；
  - 十个站点 `/`、`/vendor/shengshi8800/kj/local.html`、`/api/latest-draw` 全部 200；
  - `/api/latest-draw`、`/api/next-draw-deadline`、`/api/kaijiang/*` 连续请求为
    `MISS → HIT → HIT`，`X-Cache-Status` 可见。
- 真实日志（中心节点 `/var/log/nginx/kj_cache.log`）：
  `HIT n=56 avg_rt=0.0804s`（不访问后端）、`STALE n=10 avg_rt=0.0148s`、
  `MISS n=79 avg_rt=1.9671s avg_urt=1.9498s max_urt=6.2780s`；
  回源最慢为 `/api/sites/twsaimahui/prediction-modules` **6.278 秒**、
  旧站 `/api/kaijiang/*` 各约 **2.7～2.8 秒**；30 并发相同请求触发并发合并，
  后端只被请求一次（29 HIT + 1 STALE）。
- 运维注意：`/vendor/**` 现由宿主仓库直出，**部署必须先 `git pull` 再重建 `frontend`**。
- 未部署（本地已提交，等待上线）：
  - `a4871a5`：第 1 层前端改动（开奖面板并发取数 + 5 秒缓存去重、twjsz666 单面板按需创建、
    twssz 内联图片外置、twcaibawang 图片懒加载与 SSR 并发）；
  - `4d9c806`：图片全面压缩（原地重压 + 大图转 WebP 并改写引用），
    vendor 图片 **43.03 MB → 15.05 MB（−65%）**，单张最大 **3367 KB → 366 KB**；
    `twcaibawang` 23.09 → 7.01 MB、`twjinniu` 7.94 → 2.50 MB、`twsaimahui` 2.66 → 0.97 MB。
  两项都需要：`git push` → 两台节点 `git pull` → 重建 `frontend`
  （图片本身由 nginx 直出，但 `frontend/components/twcaibawang/TwcaibawangHomeClient.tsx`
  的引用改动与面板 JS 必须重建镜像后才一致）。

### 图片压缩与前端加速上线结果（2026-09-24）

- 上线提交：`a4871a5`（前端加速）、`b2f8ea1`（nginx 边缘缓存与静态直出）、
  `4d9c806`（图片压缩）、`8bcefad`（文档）、`6823fc8`（compose 增加
  `./frontend/public:/srv/public:ro` 只读挂载）。`origin/main = 6823fc8`。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/images-frontend-20260923T183113Z`（`docker-compose.yml`、
  `.env`、`HEAD.txt`、`STATUS.txt`）；因为 nginx 挂载改动只改在节点上，先
  `git checkout -- docker-compose.yml` 再 `git pull --ff-only`（`92b780f → 6823fc8`），
  随后 `docker compose build frontend` + `up -d frontend`，`liuhecai-frontend` 状态 `healthy`。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/images-frontend-20260923T183419Z`；同样先还原
  `docker-compose.frontend-node.yml` 再 `git pull --ff-only`（`df26b50 → 6823fc8`，
  `df26b50` 是 `origin/main` 祖先，快进无冲突），之后
  `docker compose -f docker-compose.frontend-node.yml build frontend` + `up -d frontend`，
  容器 `healthy`。
- 一致性校验（新挂载模型的关键）：中心节点宿主 `frontend/public` 与容器内 `/app/public`
  **810 个文件、抽样 md5 全部一致**（面板 `kj/local.html`、`twssz/index.html`、
  两个新 `.webp`）；因此"nginx 直出宿主仓库"不会串版本。
- 公网校验（`-H "Accept-Encoding: identity"`，字节数即真实体积）：
  - `twcaibawang` `42ce9a…webp` 226,058 B（原 1,181 KB）；`986d68…webp` 297,608 B（原 762 KB）；
  - `twjinniu` `kingsjpz_1051…webp` 190,130 B（原 3,367 KB）；
  - `twbst528` `3089.80.webp` 142,550 B（原 1,096 KB）；
  - `twsaimahui` `log2.webp` 276,070 B（原 1,052 KB）；
  - `twsyw` `banner.png` 174,031 B（原 1,783 KB）；
  - `twssz` `index.html` 406,078 B（原 1,161,349 B）；
  - `twcaibawang.com/index.html` 含 38 处 `.webp` 引用，已转换素材的旧扩展名引用为 **0**。
- 面板校验：`www.twtongtian.com` / `www.twssz.com` / `www.twcaibawang.com` / `www.twsyw.com`
  上 `kj/local.html` 均含 `loadLatestDrawPayload`（5 秒缓存 + 去重）、初始化改为
  `load({ revealOnLoad: true })` 与 `fetchCountdownDeadline()` 并发，旧的串行模式已消失。
- 十站 `/`、`/vendor/shengshi8800/kj/local.html`、`/api/latest-draw` 全部 `HTTP 200`；
  `www.tw8800.com` 本机复查 `/`(8.3 KB)、`latest-draw`(520 B, 4.9 ms)、
  `next-draw-deadline`(105 B)、`embed.html`(47 KB) 均 200，`X-Cache-Status: HIT`。

### 预测资料快照化 P0 部署结果（2026-09-24）

- 上线提交：`249ebe5`（设计方案）、`e1968e2`（P0 实现）。`origin/main = e1968e2`。
- 变更内容（详见 `docs/2026-09-24-prediction-snapshot-design.md`）：
  - 新增 `backend/src/cache/prediction_snapshots.py`：内容寻址版本 + 指针的公开载荷快照，
    指针 TTL 300 秒，载荷递归拒绝内部标记（`_simulation_should_hit`/`should_hit`/
    `truth_source`/`future_truth`），空结果不缓存；
  - 读路径接入（命中即 KV 读，未命中查库并尽力回填，缓存异常一律回落数据库）：
    `/api/kaijiang/*`、`/api/vendor/homepage-modules`、`/api/public/site-page`；
  - 开关：`PREDICTION_SNAPSHOT_ENABLED`（默认开启）+ `system_config.prediction.snapshot.enabled`
    覆盖（进程内 5 秒缓存，可即时关停）。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/prediction-snapshot-20260923T190022Z`；
  `git pull --ff-only`（`b314ff4 → e1968e2`）+ `docker compose build python-api scheduler-worker`
  + `up -d python-api scheduler-worker`；`liuhecai-python-api` `healthy`、`scheduler-worker` 运行中。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/prediction-snapshot-20260923T190257Z`；仅同步代码
  （该节点没有 python-api，其 `/api/*` 由 Next.js 代理到中心的 `central-api`，
  因此同样受益于中心 python-api 的快照）。
- 验收（中心节点本机，直连 python-api:8000）：
  - `getPingte/getTou/getShaXiao` 连续 3 次：**1.5～7 ms**；日志中一次真实 miss 的
    `build_ms=55`；
  - 旧站十个"冷"端点走完整链（nginx → Next.js → python-api）：
    第 1 轮（快照未命中）**合计 0.819 s**，等 nginx 微缓存过期 25 秒后第 2 轮
    （快照命中）**合计 0.061 s**，单请求 4.7～8.9 ms，**13 倍**提升；
  - 公网 `https://www.twssz.com/api/kaijiang/getPingte?web=9&type=3&num=1`
    连续三次 `MISS → HIT → HIT`，`X-Cache-Status` 可见；
  - Redis 键：`public:prediction-snapshot:v1:*`（带 TTL），db0 仅此 2 个键。
- 诊断修正（重要）：nginx 日志里旧站端点 2.7～2.8 秒的 `urt` 主要来自
  "nginx → Next.js → python-api"链路在高并发爆发下的排队，而不是单次查询成本
  （python-api 侧构建实测 `build_ms=55`）。因此旧站页面的剩余延迟要靠
  "前端节点本地缓存/内网直连"来消除，而不是继续压快照构建时间。
- 待办：Redis 目前 `maxmemory=0`、`maxmemory-policy=noeviction`；快照键都有 TTL
  （≤301 秒），内存有界，但建议后续显式设置 `maxmemory` 与 `allkeys-lru` 兜底。
  P1（worker 预热与事件失效）尚未实施。

### 跨节点缓存 / 脚本合并 / 快照失效触发上线结果（2026-09-24）

- 上线提交：`ec17d6b`（Next 进程内短缓存 + 并发合并，并补齐真实热路径
  `/api/legacy/module-rows` 快照）、`5b97953`（twsaimahui 59 个启用模块脚本 → 2 个 bundle）、
  `59f1622`（快照失效触发：开奖事件 / 每日生成 / 管理台改写开奖号码三个钩子，代际计数）、
  `6d658c0`、`fac6c5c`（十站真实浏览器工具与上线核查脚本）。`origin/main = fac6c5c`。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/perf-round5-20260923T201316Z`（`docker-compose.yml`、`.env`、
  `deploy/nginx.conf.local`、`HEAD.txt`、`STATUS.txt`）；`git pull --ff-only`
  （`e1968e2 → fac6c5c`）+ `docker compose build python-api scheduler-worker frontend`
  + `up -d`；`liuhecai-frontend` `healthy`、`liuhecai-python-api` `healthy`、
  `liuhecai-scheduler-worker` 运行中、`nginx` 未重启。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/perf-round5-20260923T201618Z`；同样 `git pull --ff-only`
  （`e1968e2 → fac6c5c`）+ 重建 `frontend`，容器 `healthy`。
- 上线核查（`scripts/verify-perf-rollout.sh`，两节点各跑一次）：
  **中心节点 PASS=15 / PENDING=0 / SKIP=8 / FAIL=0**；
  **前端节点 PASS=14 / PENDING=0 / SKIP=7 / FAIL=0**（部署前分别是 PENDING=1 与 PENDING=2）。
- 快照与失效实测（中心节点，直连 python-api）：
  - `/api/legacy/module-rows?modes_id=56&limit=8&web=9&type=3`
    第一次 **49.7 ms**（未命中，日志 `build_ms=24`）、第二次 **2.4 ms**（命中）；
  - 代际失效链路：容器内用已部署模块 `bump_lottery_type(3)` → Redis 出现
    `public:prediction-snapshot:v1:generation:lottery:3 = 1`；随后同一接口第一次
    **57 ms 重建**，第二、三次 **2.2 ms 命中**；
  - 另观察到聚合类未命中构建耗时 `build_ms=1226`（`kind=homepage site=site5`），命中后消失。
- 十站真实浏览器复测（`frontend/test/live-site-draw-smoke.py`，Playwright + 系统 Chrome）：

  | 站点 | DCL 前→后 (ms) | 首球 前→后 (ms) | 备注 |
  | --- | --- | --- | --- |
  | www.twcaibawang.com | **7452 → 1094** | **8108 → 2438** | SSR 两次聚合并发的效果 |
  | www.twsaimahui.com | 1061 → 905 | 2936 → 2875 | 合并后脚本请求 119 标签 → **28 个请求**（跨 frame 统计） |
  | 其余八站 | 1655/969/952/921/1094/1108/1140/1000 → 890～1780 | 3641/2922/2812/2468/2406/2530/2858/2422 → 2140～3797 | 全部 7 个号码渲染、期号 266 一致 |

  - `img[loading="lazy"]`（跨 frame 统计）：twcaibawang **30** 个、twssz 167 个、twsyw 5 个 → 懒加载已生效。
  - 测量口径修正：原先只在主文档统计 `performance` 资源，iframe 内厂商页的资源会被漏掉；
    图片"传输体积"还受页面推进速度影响（页面变快后同一观察窗内会加载更多图），
    因此改用**模板引用体积 + `loading="lazy"` 计数 + 跨 frame 请求数**作为可比指标。
- 本轮新发现的最后一个 MB 级来源（**未处理，需单独授权**）：管理后台上传图
  `/uploads/image/20250322/1742580086567063.png` **1,085,663 B**、
  `…130762983.jpg` 427,004 B、`…119746508.jpg` 268,281 B，合计 **1.74 MB**，
  十个站点首页共用；实际文件在中心节点 `/root/Marksix/backend/data/Images/`
  （容器内 `/app/data/Images`），与仓库内同名 vendor 副本 md5 不同（是独立文件），
  `cache-control: public, max-age=86400`。

### 上传图（/uploads）压缩结果（2026-09-24，经用户单独授权）

- 授权范围：只处理上述三张，不动 `backend/data/Images` 下其余 8262 个文件
  （该目录含 `mode_478/source/` 数百张约 430 KB 的 JPEG，若按目录整体处理会误伤）。
- 备份：`/root/Marksix/.deploy-backups/uploads-images-20260923T205550Z/`，含三张原件与
  `MD5SUMS.txt`（`d299ad81…`/`c620ffb2…`/`dab21bf3…`）。
- 流程：`scp` 取回原件到本机 → `python scripts/compress-vendor-images.py --root <stage>`
  （dry-run 报 **1.70 MB → 0.54 MB**）→ `--apply` → `scp` 覆盖回节点
  （python-api 的 `/app/data/Images` 是同一挂载，立即生效）。
- 结果（节点与服务端实测一致）：

  | 文件 | 压缩前 | 压缩后 | 处理 |
  | --- | --- | --- | --- |
  | `1742580086567063.png` | 1,085,663 B | **249,805 B** | PNG 量化 256 色，966×671 不变 |
  | `1742580130762983.jpg` | 427,004 B | **233,233 B** | JPEG q80 渐进式，783×1280 不变 |
  | `1742580119746508.jpg` | 268,281 B | **84,187 B** | 实为 PNG（扩展名 .jpg），量化 256 色，960×1280 不变 |
  | 合计 | 1,780,948 B | **567,225 B（−68%）** | 尺寸与格式容器均未改变 |

- 视觉核对（`read_image` 逐张看原件与压缩后）：密集色块"六合大全"表、红字黄底生肖表、
  绿字黑字对照表均无可见劣化（这三张都是平面色块图，256 色足够）。
- 浏览器复核（`frontend/test/live-uploads-images-check.py`，真实 Chrome，`fetch +
  createImageBitmap` 强制解码，不受 `loading="lazy"` 影响）：

  | 站点 | 三张图 | 结果 |
  | --- | --- | --- |
  | www.tw8800.com | 全部 | 200，249805/233233/84187 B，解码 966×671 / 783×1280 / 960×1280，DOM natural 一致 |
  | www.twsaimahui.com | 全部 | 同上 |
  | www.twssz.com | 全部 | 同上（DOM 中为 lazy 首屏外未加载，属正常） |
  | www.twbst528.com | 全部 | 同上（**跨节点 `/uploads/` 代理路径**同样生效） |

  `www.twsyw.com` 因本机链路三次打开失败未跑浏览器检查，但 curl 实测
  `https://www.twsyw.com/uploads/image/20250322/*` 返回 200 与新体积（249805/233233/84187），
  服务端路径已确认。

### twsyw 开奖标签页内联（iframe 层数收敛第一步）部署结果（2026-09-24）

- 变更内容（提交 `ad8b0b2`）：把 `kai.html` 的标签页/面板/样式/`KJTB` 脚本内联进
  `twsyw/index.html`，删除 `<iframe src="kai.html">` 这一层；`kai.html` 文件保留以兼容直链
  与旧契约。适配器随之改造：
  - `knownDrawFrame`（`iframe[src='kai.html']`）→ 惰性 `drawPanelFrame()`
    （`.KJ-TabBox .KJ-IFRAME`，该 iframe 由内联脚本在本页创建）；
  - `renderDraw()` 改为写回**同文档**的 `[data-current-issue]`（原先写 kai 帧的文档）；
  - 彩种切换由 `postMessage` 改为内联脚本直接调用
    `window.TwsywSiteDataAdapter.selectLottery(type)`；消息监听保留但不再依赖中间帧。
- 契约同步：`twsyw-adapter-contract.mjs`（断言内联结构 + 不再有 kai iframe + 适配器不依赖
  中间帧；顺带修正两条与现状不符的陈旧断言 270→实际 280/内联、190px→200px），
  `twsyw-live-mapping-contract.py`（帧查找改为厂商页同文档）；
  新增 `twsyw-inlined-draw-contract.py`（本地静态服务器 + 桩 API 的端到端回归）。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/twsyw-inline-20260923T221219Z`；`git pull --ff-only`
  （`772e12e → ad8b0b2`）+ 重建 `frontend`，容器 `healthy`。
- 中心节点 `207.56.3.82:29618`：`git pull --ff-only` + 重建 `frontend`，容器 `healthy`
  （该站不在中心节点服务，重建只为保持盘上/镜像一致）。
- 验证：
  - 本地端到端（`twsyw-inlined-draw-contract.py`，同源静态服务 + 拦截
    `/api/sites/twsyw/**`）**15 项全 PASS**：无 kai 帧、无活动 kai iframe、
    标签页默认加载台湾彩面板、点 2/1/3 后面板 src 正确切换、适配器被直接调用
    （`[2,1,3]`，无 postMessage）、**期号写回同文档**（`2500`/`1500`/`3500`）、
    539 行预测渲染、面板高度 ≥190 未裁切；
  - 线上（`TWSYW_BASE_URL=https://www.twsyw.com` 跑 pytest）
    `twsyw-live-mapping-contract.py`：**1 passed in 5.75s**，逐项断言真实执行，
    含四个彩种切换、`[data-current-issue]` 期号、面板高度、25 个预测区、
    资源图完整加载，且 `page_errors`/`console_errors` 均为空；
  - 十站真实浏览器回归：**10/10 ok**，`www.twsyw.com` **frame 数 4 → 3**
    （正是被移除的那一层），其余站点 frame 数与改动前一致；上传图压缩效果同时可见
    （`tw8800` 图片 1740 → 555 KB、`twsaimahui` 2040 → 855 KB）。
  - 前端静态契约：42/48 通过，失败项从 7 个降到 6 个（`twsyw-adapter-contract` 由预先失败
    转为通过），剩余 6 个均为既有失败项。
- 备注：`site-ui-browser-contract.py` 不含 twsyw，无需同步；本轮未动 `twssz`/`twwanli`/
  `twbst528`/`twsaimahui`/`twjsz666`（各有不同的面板创建方式或 React 外壳），
  按同一路径逐个推进。

### 预测资料不可变 + 结果字段回填容错上线结果（2026-09-24）

- 业务硬约束（用户口径）：**准时开奖、不能泄露、预测资料准时更新、更新后不得修改**。
- 上线提交：`22289d4`（预测资料不可变）、`9fb4db7`（结果字段回填容错）。`origin/main = 9fb4db7`。
- 自动化核查（两节点各一次）：中心节点 **PASS=20 / PENDING=0 / SKIP=8 / FAIL=0**；
  前端节点 **PASS=17 / PENDING=0 / SKIP=7 / FAIL=0**。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/prediction-immutability-20260923T233600Z`；
  `git pull --ff-only`（`310a6fd → 22289d4 → 9fb4db7`）
  + `docker compose build python-api scheduler-worker` + `up -d`；
  `liuhecai-python-api` `healthy`、`liuhecai-scheduler-worker` 运行中、
  日志出现新的 `Publication loop started interval=1s`（`23:55:53Z`）。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/prediction-immutability-20260923T235755Z`；
  仅 `git pull --ff-only`（本轮无前端文件变更，`liuhecai-frontend` 保持 `healthy` 不重建）。
- 未变的部分：`nginx` 未重启（本轮无 nginx 配置改动），5 个 server 块的开奖 tier 仍为 1 秒。
- 四原则实测证据（中心节点）：
  1. **准时开奖**：`is_opened=0` 且已过开奖时间的期数 = **0**（三个彩种），
     未到开奖时间却已开奖 = **0**；timer 正常重排（`Precise check 澳门彩 → 2026-09-24T13:31:59Z`、
     香港彩 → `2026-09-26T13:29:59Z`），待执行任务含 `taiwan_precise_open`（`14:32:00Z`）与
     `daily_prediction`（`04:00:00Z`）。
  2. **不能泄露**：121 张启用模块 created 表中"未开奖期却写入真实结果"的行 = **0**；
     公开载荷（`/api/latest-draw`、`/api/kaijiang/getPingte`）对未开奖期真值的命中次数 = **0**；
     返回体期号为已开奖的 `2026266`；`prediction_generation_controls` 只存
     `signature_hash`/`prefix_hash`，明文号码命中 = **0**。
  3. **预测资料准时更新**：Outbox `pending=0`（114 条全 published）、发布循环 1 秒；
     Redis 指针 TTL 符合预算（开奖快照 ≤30 秒、预测快照 199～204 秒剩余 / 300 秒、代际键存在）；
     三个彩种最新已开奖期（香港 103、澳门 266、台湾 266）结果字段补全后剩余空值 = **0**；
     部署后 `AutoPred backfill error` = **0** 条；公开出口三站均返回 `term=266`
     且 `res_code`/`res_sx` 正常（如 `res_code":"01,27,37,20,43,02,10"`）。
  4. **更新后不得修改**：容器内实测 `allow_overwrite = parse_bool(payload.get("allow_overwrite"), False)`、
     `generate_prediction_batch` 运行时缺省 `allow_overwrite=False`；结果回填代码为
     `CASE WHEN <空值>` 逐列只填 + 逐表 `SAVEPOINT`（缺失 `res_*` 列的表直接跳过）。
- 本轮发现并修复的生产缺陷（`9fb4db7`）：`created.mode_payload_273`/`335` 没有
  `res_code`/`res_sx`/`res_color` 列。原先的循环内 `try/except + continue` 无法阻止
  PostgreSQL 事务进入 aborted 状态，循环外的 `schema_table_exists` 随即抛
  `current transaction is aborted`，导致**每次开奖后的结果字段回填整体丢失**
  （日志证据：`2026-09-22T13:46:11Z`、`2026-09-23T13:47:06Z`、`2026-09-23T14:40:10Z`）。
  修复后实测：单次调用扫描 363 张 created 表，**121 张被回填、541 行写入、无异常**。
- 历史缺口（**待授权**）：截至上线，仍有 **63,560** 行历史已开奖期记录缺结果字段
  （121 张表；补全当前三期已用 1,623 行）。公开页面显示不受影响——读路径
  `apply_lottery_draw_overlay()` 会以 `public.lottery_draws` 覆盖开奖结果，
  但后台资料列表与命中统计读的是库内 `res_*`。建议单独授权一次
  `backfill_created_result_fields(..., overwrite=False)` 的历史补齐（只填空值，不改正文），
  预计耗时数分钟。
- 备注：预测生成节奏仍是既有设计——`TASK_TYPE_AUTO_PREDICTION` 已废弃，
  预测生成严格限定为 `daily_prediction`（`daily_prediction_cron_time` = 北京时间 12:00）
  与管理台手动触发；因此下一期（澳门/台湾 267）将在北京时间 12:00 生成，
  早于当日 21:32/22:32 开奖约 10 小时。若要改成"开奖后立即生成"，属于设计变更，需另行决定。

### 港澳彩准时开奖 P1 修复上线结果（2026-09-25）

- 上线提交：`713168f`（港澳准时开奖：有限自驱追赶窗口）、`4ba27ef`（台湾彩开奖逻辑零改动护栏）。
- 触发原因（实测）：2026-09-25 澳门彩 268 期，源站 `open_time=21:32:32`，我方
  `created_at=21:38:39.695`、推送 `21:38:40.764` → **延迟 367.7 秒**。
  根因四处（详见 `docs/2026-09-25-hk-macau-draw-punctuality.md`）：
  ① 旧期 267 刷新把 `next_time` 从 09-25 前滚到 09-26；② 动态抓取间隔因此掉到 `far=300s`；
  ③ 旧期刷新关闭追单（`_process_auto_crawl_batch`）；④ 分级告警又因"`next_time` 在未来"
  第二次关闭追单；形成 21:33:26–21:38:39 的 **5 分 04 秒盲区**。
- 代码修复（仅 P1，未改线上配置值、未改 nginx）：
  - `crawler/collectors.py::_upsert_draw`：仅"新期首次入库"或"该期 0→1 开盘"才推进并同步
    `next_time`；已开奖期刷新不再前滚排期；
  - `crawler/scheduler.py`：旧期刷新不再关闭追单；到点后进入固定追赶窗口（独立定时器每 5 秒
    **并发探测主源 + 全部备用源**，命中即跑完整开盘管线）；窗口 `chase_max_seconds=900`、
    最多续期 `chase_max_windows=3` 后对该期望期抑制并回落常规排程；分级告警不再用未来
    `next_time` 关追单且窗口内不重复抓取；`stop()` 清理追赶定时器；
  - **台湾彩零改动**：`_chase_is_active`/`_set_lottery_chase_mode` 对 lt=3 保持改造前语义
    （标记为真即追赶、无截止时间、不启动独立定时器、不做并发探测），
    分级告警在 `next_time` 已处未来时照旧关闭台湾追单标记。
- 传输方式说明（重要）：本次操作机到 GitHub 的 TLS 被中断
  （`schannel: failed to receive handshake` 与 openssl `unexpected eof while reading`），
  `git push` / `git ls-remote` 均失败；两台节点可正常读取 GitHub 但无推送凭据。
  因此改用 **`git bundle`（`33c0a66..main`，含 `713168f`、`4ba27ef`，SHA 一致）**
  + `scp` 传至节点后 `git fetch <bundle> main && git merge --ff-only`，
  节点历史与本地完全一致；**origin/main 仍停在 `33c0a66`，待操作机网络恢复后补推**。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/p1-chase-window-20260925T193727Z`；
  合并到 `4ba27ef` + `docker compose build python-api scheduler-worker` + `up -d`；
  `liuhecai-python-api` `healthy`、`scheduler-worker` 运行中，日志出现新的
  `Publication loop started interval=1s`（`19:45:04Z`）；精准检查按预期重排
  （香港 `2026-09-26T13:29:59Z`、澳门 `2026-09-26T13:31:59Z`）。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/p1-chase-window-20260925T194754Z`；同样方式合并到
  `4ba27ef`（本轮无前端文件变更，未重建，`liuhecai-frontend` `healthy`）。
- 上线核查（`scripts/verify-perf-rollout.sh`）：
  **中心节点 PASS=20 / PENDING=0 / SKIP=8 / FAIL=0**；
  **前端节点 PASS=17 / PENDING=0 / SKIP=7 / FAIL=0**。
- 部署产物级冒烟（在 `liuhecai-scheduler-worker` 容器内、临时 sqlite 库上执行，未触碰生产数据）：
  1. 旧期 267 刷新带入被前滚的 09-26 `next_time` → `lottery_draws` / `lottery_types` /
     `system_config` 三者均保持 09-25 原值（**未前滚**）；
  2. 新期 268 首次入库 → 三者正常推进到 09-26（真实排期推进未被误伤）；
  3. 追赶窗口武装独立定时器、`window#1` 计数正确；
  4. 台湾彩：标记为真即追赶、无截止时间、无独立定时器（保持旧语义）；
  5. 并发探测：慢主源（3s）+ 快备用源 → **0.03s** 返回期望期。
- 单测：`backend/src/tests/unit/test_draw_open_chase_window.py` 11 项全通过；
  全量后端 **910 passed / 13 skipped / 1 failed**（唯一失败是既有的 nginx health 契约；
  另一个 Postgres 锁定集成测试为套件内偶发抖动，单跑与其中一次全量均通过，
  且不导入本次改动的任何模块）。
- 待验收（真实开奖）：香港 `2026-09-26 21:30`、澳门 `2026-09-26 21:32`（北京）观察
  `public_open_delay_seconds ≤ 60`、`lottery.{hk,macau}_next_time` 不再被前滚到次日、
  日志出现 `Chase mode enabled … window#1` → `running open pipeline` → `opened=1`
  且无 `windows exhausted`。
