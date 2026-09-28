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

## 部署工作流（含跳板机，2026-09-27 起为标准流程）

### 为什么走跳板机

直连两个节点的 SSH 握手实测 **3.0–4.1 s**；经跳板机后 **约 0.7 s**（快 5–9 倍）。
因此**默认经跳板机访问**，直连仅作兜底。

实测数据（2026-09-27，Windows 客户端，各 4–5 次握手）：

| 路径 | 中心节点 | 前端节点 | 跳板机自身 |
| --- | --- | --- | --- |
| 直连 | 3080–4064 ms | 3099–3847 ms | — |
| `ProxyJump`（推荐） | 686–769 ms | 678–725 ms | 324–431 ms |
| 本地端口转发（持久隧道） | 403–477 ms | 418–479 ms | — |

### 节点与跳板机

| 角色 | 地址 | 说明 |
| --- | --- | --- |
| 跳板机 | `8.163.93.151:22`，用户 `Administrator` | `~/.ssh/id_ed25519` |
| 中心节点 | `207.56.3.82:29618`，用户 `root` | 跑 `docker-compose.yml`（python-api / scheduler-worker / frontend / nginx / PostgreSQL / PgBouncer） |
| 前端节点 | `207.56.2.71:62594`，用户 `root` | 跑 `docker-compose.frontend-node.yml`，另有非 Liuhecai 容器 |

本地 `~/.ssh/config` 建议固化以下条目（`ProxyJump` 由 OpenSSH 自动用可用密钥完成跳板认证，无需 agent）：

```sshconfig
Host liuhecai-jump
    HostName 8.163.93.151
    User Administrator
    Port 22
    IdentityFile ~/.ssh/id_ed25519

Host liuhecai-center
    HostName 207.56.3.82
    Port 29618
    User root
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump liuhecai-jump

Host liuhecai-frontend
    HostName 207.56.2.71
    Port 62594
    User root
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump liuhecai-jump
```

### 标准发布顺序

1. **本地**：跑通回归并提交、推送。

   ```powershell
   cd backend/src; python -m pytest -q
   node frontend/test/<相关契约>.mjs
   git push origin main
   ```

2. **发布脚本走 stdin + gzip 传输**（避免在 PowerShell 里拼引号，也避免 `scp` 依赖）：

   ```powershell
   $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
   # 中心节点
   gzip -c deploy/deploy-scripts/deploy-center.sh |
     ssh -i $env:USERPROFILE\.ssh\id_ed25519 -o IdentitiesOnly=yes liuhecai-center `
       "gunzip > /tmp/deploy-center.sh && bash /tmp/deploy-center.sh $stamp"
   # 前端节点
   gzip -c deploy/deploy-scripts/deploy-frontend.sh |
     ssh -i $env:USERPROFILE\.ssh\id_ed25519 -o IdentitiesOnly=yes liuhecai-frontend `
       "gunzip > /tmp/deploy-frontend.sh && bash /tmp/deploy-frontend.sh $stamp"
   ```

   - 必须**先中心、后前端**。
   - 两个脚本都会先做时间戳备份（`/root/Marksix/.deploy-backups/tw8800-verdict-<stamp>`，
     含 `HEAD.txt`、`status.txt`、`worktree.patch`、`untracked.txt`、compose、`.env`、nginx 配置），
     再 `git merge --ff-only`，失败即停不改动运行状态。
   - 中心节点重建 `python-api`、`scheduler-worker`、`frontend`，**不重建** PostgreSQL/PgBouncer/数据卷；
     前端节点**仅重建 `frontend`**，保留 nginx、TLS 与其他容器。

3. **公网验收**：`/health`、各站首页、以及本次改动对应的静态资源与页面行为
   （静态资源验证示例：`curl -s https://<host>/vendor/shengshi8800/static/js/5xiao.js | grep -c 八肖中特`）。

4. **收尾**：清理节点 `/tmp` 上的临时脚本。

### 排障与注意事项

- 脚本用 `set -uo pipefail`（**不要加 `-e`**）：`grep -c` 未命中会返回 1，
  会让 `set -e` 在重建前中断（2026-09-27 首次发布即因此漏掉重建，后补跑修复）。
- 脚本末尾的 `/health` 自检要在容器起来后 20–30 s 再判读：`docker compose up -d` 刚返回时
  `frontend`/`python-api` 仍是 `health: starting`，此时请求会得到 **502**（正常现象，非故障）。
  以 `docker compose ps` 显示 `(healthy)` 为准。
- `ProxyJump` 不可用时，改用持久隧道：
  `ssh -N -L 12961:207.56.3.82:29618 -L 16251:207.56.2.71:62594 liuhecai-jump`，
  之后 `ssh -p 12961 root@127.0.0.1` / `ssh -p 16251 root@127.0.0.1`。
- 远端工作区常年存在站点运行期未跟踪文件（中心约 22 项、前端约 13 项），
  `git merge --ff-only` 不动它们；**禁止**在远端用 `reset --hard` / `clean`。
- `grep -c` 之类的校验计数为 0 时命令返回非 0，脚本中一律用 `|| true` 兜住。
### tw8800 判定口径修正与模板回归修复（2026-09-27 第二轮）

- 发布提交：`7816a73`（四项判定修正）→ `a4caa36`（模板声明顺序修复），已推送 `origin/main`。
- 备份目录：中心 `.deploy-backups/tw8800-verdict-20260927T141756Z`（`7816a73`）、
  `.deploy-backups/tw8800-verdict-20260927T143103Z`（`a4caa36`）；
  前端 `.deploy-backups/tw8800-verdict-20260927T142707Z`（`7816a73`）、
  `.deploy-backups/tw8800-verdict-20260927T143103Z`（`a4caa36`）。
  中心重建 `python-api`/`scheduler-worker`/`frontend`，前端仅重建 `frontend`，`nginx -t` 均通过。
- 修正内容：
  1. **特码段(65)**：`016teduan.js` 模板里出现 `'${__verdictTxt}'`（模板表达式被写进字符串），
     页面直接打印占位符 → 改为直接插值。
  2. **跑马玄机测字(331)**：真实候选是 `x7m14`（七肖14码），此前按正文「解X肖」判，
     把 267 期（特肖羊在候选内）误判为错 → 改为按 `x7m14` 判。
  3. **单双四肖(31)**：两组是**每期变化的 4+4 生肖拆分**，不是号码奇偶 → 改按特肖落在哪组判。
  4. **黑白无双(45) / 琴棋书画(26)**：接入判定，命中显示「准」，未命中不显示。
  5. **一语破天机(244)**：已接判定入口，但接口只返回诗句，没有可核对的候选生肖/号码，
     当前不显示判定（待确认命中口径后再开）。
  6. 模板声明顺序：`let __verdictTxt` 曾被插到模板**之后**，导致 17 个脚本抛
     `Cannot access '__verdictTxt' before initialization`、整块不再渲染
     （特码段消失、跑马玄机回退到厂商 HTML）→ 声明统一移到模板之前，并加契约检查。
- 契约新增两条静态检查：模板不得出现字面 `${__verdictTxt}`；声明必须先于使用（防 TDZ）。
- 公网验收：34+ 区块正常；`特码段数` 显示 `269期…开:鸡46错`、`268期…开:猴11错`；
  `单双各四肖` 266 期显示准；`黑白无双` 269 期显示错；`琴棋书画` 命中显示准；
  `2026-267期跑马玄机测字` 含「综合七肖：羊鼠蛇鸡马兔龙」，特肖羊 → 准。

#### 第三轮：作用域回归修复（提交 `14d4a37`）

- 现象：上一轮注入判定后页面报 `d is not defined`（`004jyzt.js:52`），
  **家野中特整块消失**；根因是 `verdictOf(63, d)` 被放在绑定 `d` 的 `forEach` 之外。
- 修复：声明移到与行变量同一作用域；契约新增「词法绑定表 + 使用点检查」，
  会拦住这类“引用了作用域外变量”的写法。
- 备份目录：中心 `.deploy-backups/tw8800-verdict-20260927T145639Z`；
  前端 `.deploy-backups/tw8800-verdict-20260927T145639Z`。
- 验收（公网浏览器，页面 **0 个 JS 错误**）：
  - `单双四肖` 10 期逐行与接口复算一致（266/265/269/268/270/263/262 准，267/264/261 错）
  - `特码段数` 267/268/269/270 显示错、266 显示准
  - `三期中特` 显示 `中1期` / `中几期`（未开奖）
  - `跑马玄机测字` 显示「综合七肖」并给出准/错
  - `黑白无双`、`琴棋书画` 命中显示准、未命中显示错
  - 全站无字面 `${__verdictTxt}`




#### twsaimahui 开奖号码取特码修正（提交 `ae0901b`，2026-09-28）

- 现象：【三头中特】【绝杀三尾】等 12 个预测模块展示的开奖号码不是特码，而是**第一个平码**。
- 根因：这 12 个模块读 `res_code` / `res_sx` 的**第 1 项**，并附了一条自相矛盾的注释
  「第 1 项 = 本期特码/特肖（已交叉验证）」。本项目口径是**最后一项**才是特码/特肖
  （`res_code` 与 `lottery_draws.numbers` 同序）。同期其余 47 个模块一直用 `[length-1]`，未被波及。
  实例（2026 第 190 期）：正确 `狗45`，错误实现渲染成 `猪20`。
- 附带修掉一个会让发布白做的坑：本机 `core.autocrlf=true`，14 个模块源文件（含本次 12 个）
  在磁盘上是 CRLF。旧 `bundle-twsaimahui-modules.py` 按原始字节拼接，产出 CRLF bundle，
  而 `git add` 归一成 LF → **落库正文与内容哈希文件名失配**（浏览器长缓存按文件名取资源，
  哈希对不上就拿不到新代码）。现改为按 LF 归一拼接；`twsaimahui-bundle-contract` 的
  逐字节核对也同步做了行尾归一。
- 备份目录：中心 `.deploy-backups/twsaimahui-special-code-20260928T091956Z`（部署前 `94d28e3`）；
  前端 `.deploy-backups/twsaimahui-special-code-20260928T092929Z`（部署前 `94d28e3`）。
  两节点均 `git merge --ff-only` 到 `ae0901b`，中心重建 `python-api`/`scheduler-worker`/`frontend`，
  前端仅重建 `frontend`，`nginx -t` 均通过；`/tmp` 临时脚本已清理。
- 验收：
  - 十站首页 **200**；`https://www.twsaimahui.com/health` **200**；两节点容器 `(healthy)`。
  - 新 bundle `bundle-823ff3282a9b98f2.js` 公网 **200**，与本地提交**逐字节一致**
    （sha256 `da99f027…`，CR 字节 0）；旧 bundle `bundle-ddb2aa74d145ec30.js` **404**。
  - 线上 bundle 内容：`codeSplit[codeSplit.length-1]` × 53、`sxSplit[sxSplit.length-1]` × 53，
    `codeSplit[0]` / `sxSplit[0]` **各 0**。
  - 接口复算（`/api/kaijiang/getTou`、`getShaWei`，web=6/type=3）：第 270 期 deployed 得 `马37`，
    与 `lottery_draws` 末项 37 一致；旧规则会显示 `兔28`。第 269 期同理（`鸡46` vs 旧 `龙39`）。

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

### 09-26 港澳开奖实测（P1 追赶机制首次真实验收）

- **香港彩 104**：源站 `open_time=2026-09-26 21:35:23`；并行追赶探测于 `13:34:01.245Z`
  从 `www.lnlllt.com` 命中 `2026104`（`Chase lt=1: new period … found by parallel probe`），
  auto-crawl 于 `13:34:31` 开盘，`public_open_delay_seconds=15` → **准时**（早于源站标注时间）。
- **澳门彩 269**：源站 `open_time=21:32:32`；`13:34:40.578Z` `macaumarksix.com` 首次返回
  `2026269` → `13:34:50.926` 开盘，`public_open_delay_seconds=138` → **延迟 138 秒**。
  构成：`21:32:32–21:34:40` 期间**三源都还没有新期**（`www.lnlllt.com` 连续 `ReadTimeout`
  于 `13:33:48/13:34:18/13:34:48`，`macaumarksix.com`/`api.csjid.com` 仍是 `2026268`），
  我们自己的管线只占约 10 秒；相比 268 期的 367.7 秒改善 62%，且**全程无盲区**
  （追赶心跳每 5–20 秒一轮并行探测）。
- 告警链路同时验证：`YELLOW ALERT: 香港彩 draw overdue by 255s` + 邮件，
  恢复后 `13:34:32` 发"已恢复"邮件。

### 港澳"下次开奖"倒计时修复上线结果（2026-09-27）

- 上线提交：`026cde1`。origin/main 与两节点同步（push 经 `git -c http.version=HTTP/1.1`
  第 3 次重试成功；`schannel`/`openssl` 在 HTTP/2 下被中断）。
- 现象：`/api/next-draw-deadline?lottery_type=1|2` 返回 `next_time: null`，
  面板徽标一直停在 `下次开奖 --:--:--`。
- 根因：09-26 的香港 104、澳门 269 是**由备用源开盘**的
  （`api.csjid.com` / `macaumarksix.com`），这两个源的响应里**没有 `next_time` 字段**
  → `lottery_draws.next_time` 为空 → `sync_lottery_type_next_time_from_latest_draw`
  把空值写进 `lottery_types.next_time` 与 `system_config.lottery.{hk,macau}_next_time`。
  面板 `local.html` 的 `normalizeToSeconds(Number(null))===0` 走 `--:--:--` 分支（`local.html:609-610`）。
  台湾彩不受影响（其 next_time 来自未来期行/持久化任务）。
- 修复（仅代码）：
  - `helpers.compute_next_draw_time_ms()`：按排期推导——香港 `draw.hk_draw_weekdays`
    （默认 `1,3,5` = 周二/四/六，Python `weekday()` 约定）、澳门每日，
    钟点取 `draw.{hk,macau}_default_draw_time`；**台湾返回空串，不参与推导**；
  - `helpers.resolve_next_time_ms()`：优先级 = 源站值 → 仍在未来的已存值 → 排期推导，
    **绝不用空值覆盖已有排期**；
  - `sync_lottery_type_next_time_from_latest_draw` 与 `/api/public/next-draw-deadline` 共用
    （接口层兜底，库值暂时为空也能给出未来时间）。
- 部署：中心节点备份 `.deploy-backups/countdown-fix-20260927T045838Z`
  （`34202c7 → 026cde1` + 重建 `python-api`/`scheduler-worker`，`healthy`）；
  前端节点备份 `.deploy-backups/countdown-fix-20260927T050734Z`（仅 pull，无前端文件变更）。
- 一次性补正（与调度器周期同步同一路径，容器内执行）：
  `lottery.hk_next_time = 1790688600000`（**2026-09-29 21:30 北京**，周二）、
  `lottery.macau_next_time = 1790515920000`（**2026-09-27 21:32 北京**，今晚）；
  台湾 `1790519520000` 未变。两地与源站 `current` 的 `next_time` **完全一致**。
- 验收：`/api/next-draw-deadline` 经 nginx + Next 全链路返回上述值；
  上线核查中心 **PASS=20 / PENDING=0 / FAIL=0**、前端 **PASS=17 / PENDING=0 / FAIL=0**；
  单测 `backend/src/tests/unit/test_next_draw_deadline_fallback.py` 9 项通过，
  全量 **916 passed / 17 skipped / 1 failed**（既有 nginx health 契约）。
- 备注：
  - 面板 HTML 里的静态占位符仍是 `下次开奖 --:--:--`，由 JS 在接口返回后替换；
    本机到公网被中断（`ERR_CONNECTION_CLOSED`）无法跑 Playwright 复核，
    客户端渲染按既有逻辑（`remainingSec>0` → `formatCountdown`）成立。
  - `runtime_config` 中 `draw.macau_default_draw_time` 的**登记默认值**是 `21:30`，
    而生产库为 `21:32`（澳门实际开奖钟点）；若库值丢失，推导会差 2 分钟，
    建议后续把登记默认值对齐（属配置项，本次未改）。
  - 自愈路径已验证：新期由备用源开盘（行内 `next_time` 为空）时，插入路径仍会触发同步，
    `resolve_next_time_ms` 会写入推导出的未来时间，倒计时不会再被清空。

### twsaimahui 单双中特判定修复 + 澳门默认钟点对齐上线结果（2026-09-27）

- 上线提交：`76ef5b8`（origin/main 与两节点一致；本机到 GitHub 的 TLS 再次被中断，
  改经**中心节点 SOCKS 隧道** `git push` 成功：`e411a82..76ef5b8`）。
- 故障：twsaimahui（web=6）「单双中特（单双选1，生肖选2）」mode 15 / 端点
  `/api/kaijiang/getDsxiao` / 文件 `004danshuang.js`，连续多期**全部显示"错"**。
- 根因两处叠加：
  1. 判定只看 `xiao` 候选生肖（2/12 生肖），**完全忽略 `content` 分类池**（6/12）。
     模块标题即「单双选1 + 生肖选2」，且 `predict/mechanisms.py::format_content_xiao_columns`
     明确注明"content 分类池与 xiao 候选生肖**互斥**"——二者合计覆盖 8/12 生肖（≈67%，
     贴合目标命中率 0.65）；只判候选肖则 2/12 ≈ 17%。线上 261–269 期真实资料：
     按「分类池 ∪ 候选肖」= **6/9 命中**，只判候选肖 = 2/9 → 即"全部是错"。
  2. 未开奖行也走 `zj?'准':'错'`，应按原逻辑显示 `??`。
- 修复（`frontend/public/vendor/twsaimahui/static/js/004danshuang.js`）：
  新增 `dsHit`（分类池命中），判定改为 `hit = dsHit || zj`（任一维度命中即命中），
  未开奖继续显示 `??`。
- bundle 处理（关键）：站点加载的是 bundle，且 bundle 文件名是**内容哈希**、
  响应头 `cache-control: public, max-age=31536000, immutable`，因此**必须改名**才能击穿缓存。
  在 `scripts/bundle-twsaimahui-modules.py` 新增 `--rebuild`（按 `bundles.json` 来源清单
  重算正文与哈希、更新 `index.html`/`bundles.json`、删除旧文件，并抽出 `compose_bundle()`
  与合并路径共用），重建结果：`bundle-a6c1849c09290a14.js → bundle-2cb4846e0d092963.js`。
  顺带修掉既有问题：`049rccx.js`（肉菜草肖）此前与 bundle 不一致，
  既有 `twsaimahui-bundle-contract.mjs` 长期失败 → 重建后**通过**（该文件仅 3 行差异，
  来自已提交的 `88d4abb`）。
- 配置对齐：`runtime_config.py` 的 `draw.macau_default_draw_time` 登记默认值
  **21:30 → 21:32**，`_compute_hk_macau_default_next_time_ms` 的兜底按彩种区分
  （香港 21:30 / 澳门 21:32）。生产库本就为 `21:32`，线上行为零变化。
- 部署：中心节点备份 `.deploy-backups/twsaimahui-verdict-20260927T053631Z`
  （`e411a82 → 76ef5b8` + 重建 `python-api`/`scheduler-worker`，`healthy`）；
  前端节点备份 `.deploy-backups/twsaimahui-verdict-20260927T054527Z`（仅 pull）。
- 上线核查：中心 **PASS=20 / PENDING=0 / FAIL=0**、前端 **PASS=17 / PENDING=0 / FAIL=0**。
- 服务内容验证（经 nginx + `Host: www.twsaimahui.com`）：
  `index.html` 引用 `bundle-2cb4846e0d092963.js`；该 bundle（200，329274 B）内
  `dsHit = true` 存在、`let hit = dsHit || zj` 存在、`getDsxiao` 块内**无**旧判定、
  未开奖分支为 `??`；响应头 `cache-control: public, max-age=31536000, immutable`
  （正是必须改文件名的原因）。
- 修复后逐期判定（真实资料）：**261 准｜262 错｜263 准｜264 错｜265 准｜266 准｜267 准｜268 准｜269 错｜270 `??`（未开奖）= 6/9**。
  - 269 期仍为"错"：该行分类池 `双生肖|鼠,虎,龙,马,猴,狗` 与候选肖 `羊,龙` 都不含
    `鸡`（46 的生肖）。`fixed_data` 的「单生肖/双生肖」「单肖/双肖」分组是**地支阴阳**口径，
    其号码奇偶与标签相反（"双生肖"内全是单数号码）；若产品要求按**号码奇偶**重做分组，
    会影响多个模块（15/28/31 等），属独立决策，本次未改。
- 契约与单测：新增 `frontend/test/twsaimahui-danshuang-verdict-contract.mjs`
  （源文件 + 站点实际加载的 bundle 双查 + 真实 9 期判定核对）通过；
  `twsaimahui-bundle-contract.mjs` 通过；`node --check` 通过；
  后端全量 **916 passed / 17 skipped / 1 failed**（既有 nginx health 契约）。

### tw8800 判定与八肖显示修复部署结果（2026-09-27）

- 发布提交：`32481e0`（`896ecea` 三期不同规则 + `4f9ba35` 全站判定 + `32481e0` 八肖显示/文档），
  已推送 `origin/main`（`31025ed..32481e0`）。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/tw8800-verdict-20260927T134420Z`
  （含 `docker-compose.yml`、`.env`、`deploy/nginx.conf`、`HEAD.txt`、`status.txt`、`worktree.patch`、`untracked.txt`）；
  `git merge --ff-only` 同步 42 个文件；重建 `python-api`、`scheduler-worker`、`frontend`；
  `nginx -t` 通过；`liuhecai-frontend`、`liuhecai-python-api` 均为 `healthy`。
  容器内校验：判定模块 414 行、`5xiao.js` 含「八肖中特」2 处、`slice(0, 5)` 残留 0 处。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/tw8800-verdict-20260927T135458Z`；
  仅重建 `frontend`（`nginx` 与 TLS 未改动），`nginx -t` 通过，`liuhecai-frontend` `healthy`。
- 公网核查（浏览器直开 `https://www.tw8800.com/vendor/shengshi8800/index.html`，20 个模块区块、152 行）：
  **显示「准」39 行 / 显示「错」25 行**，未发现「未命中却显示准」；
  `八肖中特` 每行显示满 **8 肖**（标题已由「五肖中特」改为「八肖中特」）。
- 已知展示口径（非判定错误）：`肉菜草肖`(mode 3) 每期候选是 肉/菜/草 **三组中的两组**，
  页面只渲染前两组标签，因此当特肖落在未渲染的第三组时「准」缺少可见依据
  （判定本身正确，已用生产库 `267/266/265/263/262/261` 逐期核对）。
  如需与该模块一致，可把三组标签全部渲染，属独立展示改动，本次未改。


### twcaibawang 判定/高亮整改 + 四字玄机候选池部署结果（2026-09-27）

- 发布提交：`5037b55`（twcaibawang 判定与高亮、琴棋书画改版、mode 52 候选池与五期唯一）
  + `70bb511`（发布脚本支持自定义备份标签、自检加 twcaibawang），已推送 `origin/main`
  （`c46f777..5037b55..70bb511`）。本轮同时把上一轮 tw8800 的 `c46f777` 一起带上线。
- 中心节点 `207.56.3.82:29618`：备份目录
  `/root/Marksix/.deploy-backups/twcaibawang-verdict-20260927T160558Z`
  （部署前 HEAD `14d4a37`，`git merge --ff-only` 同步 42 个文件）；
  重建 `python-api`、`scheduler-worker`、`frontend`；`nginx -t` 通过；
  `liuhecai-frontend` / `liuhecai-python-api` 恢复正常。
- 前端节点 `207.56.2.71:62594`：备份目录
  `/root/Marksix/.deploy-backups/twcaibawang-verdict-20260927T161506Z`；
  仅重建 `frontend`（nginx/TLS 与其他容器未改动）；六站自检均 200。
- 生产数据写入（用户授权）：在 `python-api` 容器内执行
  `insert_mode_52_sizixuanji_pool()`，向 `public.text_history_mappings` 写入
  `mode_id = 52` 的 **49 组 (title, jiexi)**：写入前 0 行 → 写入后 49 行、配对 49 行；
  脚本为 `INSERT ... ON CONFLICT DO NOTHING`，**未修改任何已生成的预测行**。
  备份目录 `/root/Marksix/.deploy-backups/mode52-seed-20260927T161644Z`（写入前后快照）。
  写入后只读复核：生成端 12 次抽样得到 **11 个不同标题、0 组未配对**；
  `_load_three_period_text_payloads(conn, 52)` 返回 49 条且全部带 `jiexi`；
  `display_unique_window(52) = 5`、`display_unique_window(62) = 5`。
- 公网验收（`https://www.twcaibawang.com/`，Playwright 实开）：
  - **0 个 JS 报错**；`#jsyb`（绝杀一波）容器数 = **1**（重复模块已消除）。
  - 逐期独立复算 115 行判定文字 + 黄底位置：**0 差异**。
  - 各模块对/错分布：9肖中特 7:1、绝杀一波 8:0、双波 6:2、24码 3:5、必杀一肖 8:0、
    天地两肖 4:4、四段中特 4:4、稳杀10码 8:0、四行中特 7:1、四头中特 6:2、
    六肖十八码 3:5、公开一肖一码 1:7、双波12码 6:2、琴棋书画 准6:错2。
  - 修复前对照：双波/24码/六肖十八码等因接口 `is_correct = null` 恒显示「对」或没有判定；
    四段中特因 `_compute_outcome_from_row` 缺段位标签**恒显示「错」**（269 期特码 46
    明明落在预测的 7 段里）。
- 同期回归（`https://www.tw8800.com/vendor/shengshi8800/embed.html`）：
  14 个模块逐期独立复算 **0 差异、0 JS 报错**；三期中特按接口新字段
  `period_zodiacs` 复算得 `263-265 中1期 / 266-268 中1期 / 269-271 中0期`，
  与生产库同源 loader 的复算完全一致（`269-271` 正是「中0期」场景）。
- 遗留说明：`天地两肖` 采用「天肖/地肖群 ∪ 两肖」并集判定（vendor 接口只比对那两肖，
  会让天地肖永不参与判定）；`公开一肖一码` 沿用后端「特肖或特码命中即对」；
  `琴棋书画` 按需求样例使用「准/错」，其余 12 个模块统一「对/错」。以上均已与用户确认。

### 十站点预测模块展示规范整改（2026-09-27/28，两轮）

**目标**：十个站点（web_id 4–13）的预测模块统一满足《预测模块展示规范》
（`docs/prediction-display-standard.md`）：命中才黄色高亮、未命中一律不高亮、
未开奖不给判定、判定与真实开奖一致、分组说明两组都显示、页面无 JS 报错。

**发布提交**：`72ba0fa`（规范+审计工具）→ `38aa264`（文档）→ `7f98c78`（twsaimahui 首批 + twbst528/twjsz666 适配器）
→ `aa9eeb7`（twssz/twjsz666 错行清黄）→ `4c716db`（twsaimahui 12 模块 + 审计加固 + R8）
→ `74353fb`（文档基线）→ `387d4be`（判定真值原子化 + tokens 形状护栏）→ `be09abc`（审计行切分/判定取法）
→ `5f850c0`（结果字段补齐脚本）→ `641dfe9`（shengshi8800/twcaibawang/twcf888/twjinniu/twwanli/twsyw + mode 38 + 号码集合展示顺序）
→ 已推送 `origin/main`。

中心节点 `207.56.3.82:29618`：备份目录
`/root/Marksix/.deploy-backups/display-standard-20260927T170247Z`（第一轮，`7f98c78`）与
`display-standard-2-20260927T180808Z`（第二轮，`641dfe9`）；重建 `python-api`、`scheduler-worker`、`frontend`；
`nginx -t` 通过；容器恢复正常。
前端节点 `207.56.2.71:62594`：备份目录 `display-standard-20260927T170954Z`（`7f98c78`）与
`display-standard-2-20260927T181512Z`（`641dfe9`）；仅重建 `frontend`。

**生产数据操作（用户授权，只填空值、不碰预测正文）**：
在 `python-api` 容器内执行 `backend/scripts/backfill_created_result_catchup.py`，
补齐 `created.mode_payload_*` 里「已开奖但 `res_code` 为空」的历史行
（前端原本只能显示 `??` 占位）。备份与前后快照目录
`/root/Marksix/.deploy-backups/rescode-catchup-20260927T181551Z`
（`before.txt` / `apply.txt` / `after.txt`）：
补齐前缺口 **214 个期号 / 14745 张表命中** → 补齐 **174 个期号、61622 行结果字段**
→ 剩余 **40 个期号 / 610 次**（这些期号在 `lottery_draws` 里没有开奖号码或未开奖，未处理）。

**公网验收（Playwright 实开，`scripts/audit-prediction-display.py`）**：

| 站点 | rows | js_errors | error | warn |
| --- | ---: | ---: | ---: | ---: |
| shengshi8800 | 440 | 0 | 0 | 11 |
| twcaibawang | 292 | 0 | 0 | 8 |
| twsaimahui | 652 | 0 | 0 | 35 |
| twjinniu | 469 | 0 | 0 | 1 |
| twcf888 | 451 | 0 | 0 | 19 |
| twssz | 289 | 0 | 0 | 52 |
| twbst528 | 468 | 0 | 0 | 74 |
| twjsz666 | 276 | 0 | 0 | 9 |
| twwanli | 202 | 0 | 0 | 1 |
| twsyw | 545 | 0 | 0 | 7 |
| **合计** | **4084** | **0** | **0** | **217** |

warn 全部是 R4（命中却没高亮，含杀号类「准=没有可高亮项」等口径判断）与 R5（连续 ≥3 期展示值相同），
无 error 级。

**生产判定真值校验**（`scripts/audit-verdict-truth.py` 在 `python-api` 容器内对生产库跑）：
`rows=22039 error=0 warn=2865`（10/10 站点 error=0）——**生产库里没有任何一行**
`is_correct` 与「候选项是否命中真实开奖」相矛盾。

**本轮修掉的主要缺陷类别**（每条的根因与证据见 `docs/vendor-sites/`）：

1. 供应商静态 `index.html` 每行自带样例黄底，适配器只改文字不清样式 → 判「错」的行仍带黄底
   （twssz 6→0、twjsz666 9→0、twbst528 2→0）。
2. 「一期」被拆到同辈单元格 / 相邻 `<tr>`，旧审计只取叶子行 → R3（error 级）整类漏报；
   审计加固后新暴露并修复 twcf888 绝杀类 24 处、twjinniu `#sxbm`/`#pmzq` 17 处、
   shengshi8800 11 处、twcaibawang 2 处。
3. 判定文字写死在模板里或与高亮各算各的（shengshi8800 `tp5.js`/`dx.js`/`018shu3x.js`、
   twcaibawang `TwcaibawangHomeClient.tsx`）。
4. 判定口径取错字段（twsaimahui `012liuxiao.js` 用码串去匹配特肖 → 六肖三码 6 期全「错」）。
5. mode 38 双波中特 `is_correct` 恒 `null`（`content_parser` 只认生肖不认波色标签）→ 命中也不显示判定。
6. 号码集合类玩法（mode 116「10码中特」等）每期前两位固定 `01.17` → 展示顺序改为按成员集合一次性置换
   （判定语义逐值验证不变）。
7. 未开奖期仍显示判定／twsyw 标题行被并进预测行造成的假阳性（审计加 `isTitleRow` + 页面标题行加
   `data-prediction-title="true"`）。

**遗留（已知、已记录、非 error）**：
`docs/prediction-display-standard.md` 第五节之二记录了 R4/R5/R8 的人工判定结论；
`R4` 对「平特三肖连」「A级大公开」等模块的命中项高亮仍欠缺（warn 级，未纳入本轮硬性要求）；
`shengshi8800/handleSelect.js` 的 `getResult()` 仍写死「准」但**无调用方**（死代码，勿复活）。

### 十站点展示告警二轮收敛（2026-09-28，warn 217 → 27）

**发布提交**：`d58865f`（已推送 `origin/main`）。中心节点备份
`/root/Marksix/.deploy-backups/display-standard-3-20260928T064016Z`，
前端节点备份 `/root/Marksix/.deploy-backups/display-standard-3-20260928T064706Z`；
重建 `python-api`、`scheduler-worker`、`frontend`（前端节点仅 `frontend`）。

**这一轮做了什么**

1. **审计工具二次加固**（决定了后面所有数字的可比性）：
   - 模块归属 = `容器 + "|" + 行内标签`（`.box.pad`、`#yxym`、`#table7` 都是多玩法共用容器，旧口径把它们混成一个模块）；
   - 行切分补齐「纯候选单元格」并把后续多个兄弟 `<tr>` 一并并入（判定在 header 行、命中黄底在 detail 行的「配对模块」终于能对齐）；
   - 过期判定字口径：判定字必须在「最后一个 `开/開`」之后的 16 字窗口内，否则退回「行尾判定字」——
     修掉笑话正文里的「**对**我又是…」被读成判定「对」这类误报；
   - R5 的展示值改为「去掉标签、取括号内容」；出现频率 ≥40% 的 token 判为标签跳过；
     隐藏元素（`getClientRects().length === 0`）不计；
   - R4/R8 豁免：排除型（杀号）玩法按模块级豁免、无容器归属（`?`）的行豁免、
     「一格多玩法」的聚合卡片（A级猛料/AAA级大公开）按卡判定豁免。

2. **真缺陷修复**（全部落地并上线）：
   - **mode 492「三头四尾」判定恒「错」**：`_check_correct_by_mechanism` 把通用复合 outcome 喂给了
     以机制专属 outcome 为契约的 checker（恒 False），且该 checker 写的是 `all(...)`（头尾同时命中），
     与 `PredictionCategory.MIXED`「任一维度命中即算命中」约束和供应商样本都不符。已改为使用
     `config.outcome_loader` 的专属目标 + `any(...)`；同时补 `prediction-contract.ts` 的头尾维度校验
     （否则前端 `reconcileVerdict` 会把修好的「对」再降级成「错」）。`generation_rules` 里 mode 492 的
     `rule_revision` 1 → 2，避免与旧语义的预约结果混淆。
   - **半波类候选判定写死**（`#banbodanshuang_shu` mode 490、twjsz666 绝杀①半波 mode 58）：
     `蓝双/绿单` 不是通用 outcome 任何原子的子串 → `excludes_hit` 恒 True。`_compute_outcome_from_row`
     补 `{波色}{单双}` 半波原子（与 `fixed_data.波色单双` 一致，01–49 全量单测）。
   - **twsaimahui `057s1x.js`（绝杀一肖）漏改**：未开奖时 `sx===''`，`''.indexOf('')===0` 使「杀肖不含特肖」
     恒成立 → 输出「？00错」并给候选标黄（S1+S3 双违规）。按同批脚本口径补 `opened` 守卫，已重建 bundle
     （`bundle-993c1bed20e86f4a.js`）。
   - **twcaibawang 四字玄机（mode 52）连续 4 期同值**：`load_recent_created_rows` 硬性要求 `content` 列，
     而 `created.mode_payload_52` 只有 `title/jiexi` → 历史恒空 → `enforce_three_period_uniqueness(52)`
     **从未生效**。去掉该硬要求后实测 `history rows: 0 → 8`。历史期不改，下期生成起生效。
   - **twssz 命中项无高亮（R4×7）**：配对模块（8肖16码/三肖六码/双波10码）根本没有标黄机制，
     残留黄底全是供应商静态样例；A级猛料卡的 `markGradeHits` 又是**卡级并集**（七肖格不含马却因三肖格命中而判「对」）。
     已把判定与高亮下沉到「展示值所在的格」，按各玩法口径（生肖=特肖；平特=整期 7 个号码；波色=特码波；
     排除型只清不标）逐值标黄，并把 `moduleRowForTerm` 的「无本期行回退第 0 行」改为返回本期空行（不再串期）。
   - **twbst528 同期号三条重复行**：`renderCompositeLines` 用 `Math.min(..., length-1)` 把越界小节回退到
     最后一个模块，「三期计划」的第 5/6 小节因此把「3.肖中特」的行写了三遍。改为越界即「暂无后端资料」。
   - **twcf888 / twjinniu / twwanli / twsyw**：平特类高亮按本期 7 个开奖号码定位命中项；绝杀一波取反且不参与高亮；
     `sanxiao15ma` 展示完整候选集合（命中的第 8/9 位不再不可见）；twwanli 波色行不再渲染「暂无后端资料」兜底串
     并照常给判定；twsyw `#nannv` 改渲染真实候选、`#kill1tou` 展示全部 3 个候选头。
   - **shengshi8800 裸 `JSON.parse` 兜底**：18 个文件改走 `safeParseJSON / parseContentList`（永不抛异常），
     正常 JSON 路径逐字节不变（16/16 模块 HTML 一致），非 JSON 输入由「整块模块空白」变为正常渲染（64/64）。
     lint L2 由 29 降至 9（余下为 helper 本体与已受 try/catch 保护的低风险点）。

**公网验收（Playwright 实开，`scripts/audit-prediction-display.py`，2026-09-28）**

| 站点 | rows | js_errors | error | warn |
| --- | ---: | ---: | ---: | ---: |
| shengshi8800 | 447 | 0 | 0 | 1 |
| twcaibawang | 292 | 0 | 0 | 3 |
| twsaimahui | 652 | 0 | 0 | 5 |
| twjinniu | 469 | 0 | 0 | 0 |
| twcf888 | 451 | 0 | 0 | 5 |
| twssz | 282 | 0 | 0 | 3 |
| twbst528 | 468 | 0 | 0 | 2 |
| twjsz666 | 276 | 0 | 0 | 0 |
| twwanli | 202 | 0 | 0 | 1 |
| twsyw | 545 | 0 | 0 | 6 |
| **合计** | **4084** | **0** | **0** | **27** |

**生产判定真值校验**（`scripts/audit-verdict-truth.py` 在 `python-api` 容器内对生产库）：
`rows=22024 error=0 warn=3751`（10/10 站点 error=0）。

**回归**：`cd backend/src; python -m pytest -q` → `1036 passed, 13 skipped, 2 failed`，
两条失败均为既有问题（`test_ha_runtime_config_contract.py` 的 nginx 契约用例 + 并发下抖动的
`test_versioned_migrations.py::..._lock_timeout`，单独重跑通过）；前端契约
`run-prediction-token-shape-contract.mjs`（20 模块）/`run-prediction-verdict-truth-contract.mjs`/
`twsaimahui-012-liuxiao-display-contract.mjs`/`twcaibawang-verdict-contract.mjs` 全部通过。

**剩余 27 条 warn 的性质**（已逐条给出书面结论，见 `docs/vendor-sites/display-convergence-5-sites-2026-09-28.md`
与 `docs/vendor-sites/sites-7-8-12-13-display-convergence.md`）：绝大多数是 R8「整列判定全同」，
经真实开奖逐期复算属**概率内**（八肖 8/12 连对、10码 10/49 连错、杀号类连准等）或
**统计假象**（`#table7`/`.box.pad` 是十几张表共用的同一个 id/class，该组本身就是「多个玩法的未命中行并集」）。
真正的 R5 只剩 3 条，均为**生成侧相邻期唯一性**问题，已落库历史期无法靠渲染修复
（其中 twcaibawang mode 52 已修代码，下期起生效）。

### 用户报障修复：twcaibawang 判定降级 + twsaimahui 六项（2026-09-28 第四轮）

**发布提交**：`8098426`（twcaibawang 大小+2头）、`44b3a5e`（twsaimahui 四项）、
`95afd17`（tw8800 三期中特/绝杀半波、twjinniu、twcf888 及配套测试）。已推送 `origin/main`。
中心节点备份 `/root/Marksix/.deploy-backups/display-standard-4-20260928T082043Z`，
前端节点 `/root/Marksix/.deploy-backups/display-standard-4-20260928T082744Z`。

**twcaibawang「大小+2头」全错 —— 不是生成问题，是判定被降级**

- 后端聚合接口本来就对：270/269 期 `is_correct=true`（口径：大/小 命中 **或** 头码命中），
  268~264 期 false。
- 但 `frontend/lib/prediction-contract.ts::verifyVerdictAgainstCandidates()` 把它当普通玩法做
  「特码/特肖 ∈ 候选集合」交叉校验，而它的 `tokens` 是 `['【大数','32】']`（不是号码/生肖集合）
  → 判为 `contradicted` → `reconcileVerdict()` 把 `true` 强制改写成 `false`。
- 修复：新增候选口径识别（`size` / `tail` / `head_parity` / `size_head`）与精确复算，
  **没有把握时返回 `unverifiable` 放行上游判定**，不再降级；`generic`、排除型、平特型、
  三头四尾分支一行未改，`prediction.tokens`/`extra` 形状未变。同类缺陷全站共 39 行
  （`daxiao_2tou`、`dxztt1`、`toudanshuang`、`gongshi_siw`、`liuweichute`）一并修好。
- 公网复核：`270期【大数+32】开 37马 对`、`269期【大数+37】开 46鸡 对`（命中维度标黄），
  `268期【大数+36】开 11猴 错`（零黄底）。

**twsaimahui 六项**

1. **【家禽+野兽】**：该 mode 表没有 `content` 列，映射层用 `xiao` 列硬拼了假结构 `肖|`
   （竖线后为空），丢掉组名并把 6 肖渲染两遍。修法：`content = 组名|组成员`（来自 `title`）、
   `xiao = 两肖`；生成侧宽度改按 `xiao` 列推断（=2，与厂商原始数据一致）。
   公网复核：`270期家畜野兽:【野兽+虎马】开:马37准`🟡马、`269期【家禽+马虎】开:鸡46准`🟡家禽、
   `268期【家禽+虎马】开:猴11错`（零黄底）。
2. **单双四尾**：确认数据违规（`dan` 含 0、`shuang` 含 1）。已把 mode 30 纳入受控生成规则，
   候选按分组限额枚举（单尾只取 {1,3,5,7,9}、双尾只取 {0,2,4,6,8}，各 4 个）。**新生成期号起生效**，
   已落库历史行不改（线上 264~271 仍是旧值）。
3. **合数中特**：`content` 只有 `合单`/`合双` 纯标签、无号码表 → 空串 `indexOf` 恒「不中」。
   新增只读接口 `GET /api/public/fixed-data-groups?sign=合单双`（读 `public.fixed_data`，
   前端不硬编码号码表），判定改**集合精确匹配**。公网复核：
   `270期【合双】开马37中`、`268期【合单】开猴11不中`、`266期【合双】开鸡10不中`（合数=各位数字之和的奇偶）。
4. **四肖三期内必出**：旧映射只保留「窗口内最新已开奖一行」，另两期空白，且误取
   `res_code[0]/res_sx[0]`（把平码当特码）。映射**只新增** `periods` 字段（窗口内逐期开奖），
   渲染器逐期渲染。公网复核：`271期 开:待开奖 / 270期 开:马37错 / 269期 开:鸡46错`（三期各自显示）。
5. **10码中特「全错」**：判定无错——逐期复核线上 262~270 共 9 期，特码确实都不在 10 个候选里；
   生成侧历史期前两位固定 `01.17`（上一轮已修，**271 期起已无固定前缀**：实测 `02,12,35,17,27,05,31,41,28,01`）。
   mode 116 未纳入受控生成规则（纯随机 10/49，连 9 期不中≈13%）。
6. **成语平特肖**：判定正确（平特看全部 7 个号码）。`270期 守株待兔(含兔) 开奖生肖 兔,猴,蛇,虎,牛,兔,马`
   → 28、04 都是兔 → 准；`264/262 期` 候选肖不在 7 肖里 → 错。

**公网验收（Playwright 实开，`scripts/audit-prediction-display.py`，2026-09-28）**：
10/10 站点 `error=0`、`js_errors=0`，合计 4114 行 / 27 条 warn（shengshi8800 1、twcaibawang 3、
twsaimahui 5、twjinniu 0、twcf888 5、twssz 5、twbst528 2、twjsz666 0、twwanli 1、twsyw 6）。
**生产判定真值校验**：`rows=22024 error=0`。
**回归**：后端 `pytest -q` → `1063 passed, 13 skipped, 2 failed`（两条既有无失败）；
前端契约测试（token 形状 20 模块、判定真值、twcf888×3、twjinniu×2、shengshi8800×3、
twsaimahui×2 等）全部通过；其中 `shengshi8800-display-verdict-contract.mjs` 因新增
`sanqiWindowPeriods` 抽取缺失被修好。

### 10码中特（mode 116）接入受控生成（2026-09-28 第五轮）

**发布提交**：`94d28e3`。中心节点备份 `/root/Marksix/.deploy-backups/display-standard-5-20260928T090745Z`，
前端节点 `/root/Marksix/.deploy-backups/display-standard-5-20260928T091344Z`。

**需求**：用户要求把 twsaimahui「10码中特」接入受控生成规则体系，让以后生成的期次按
`prediction.simulation.target_hit_rate` 受控，而不是纯随机 10/49。

**改动**

1. `backend/src/domains/prediction/generation_rules.py`：新增
   `116: _rule("number", _special_number, prefix_width=2)`。
   `prefix_width=2` 依据：同族 mode 77（14码中特）取 2、mode 34（24码）取 3，116 宽度最小；
   10×9=90 个有序前两位对「每期个位数站点」是可满足约束，取 1 区分度不足、取 3 收益有限。
2. **关键发现并修复：只登记规则不足以受控。** `candidate_control._candidate_sequences` 的候选是
   有序元组、预算 32768，当 `predicted_labels` 宽度等于候选宽度时，整个预算被同一组号码的
   `10!` 排列吃光——**前 32768 个候选里含特码的数量为 0**，于是需要命中时必然回落随机 fallback
   （`candidate_space_exhausted`）。这不止影响 116：mode 34/77/481/493/494/65 同样
   `can_hit=False`，即它们的「受控」在需要命中时一直是空的。
   修复：新增 `_loader_row_from_truth()` / `label_for_truth_outcome()`（把 `DrawTruth` 适配成
   `outcome_loader` 期望的开奖行，解析真实目标标签）与 `directional_hit_candidates()`
   （命中方向给出 48 个互不相同的前缀签名，避免所有候选都以真值开头）；定向重排**只在历史行为
   必然失败的方向**生效，其余情况候选顺序完全不变；互斥候选域（`selection_quotas`，如 mode 30
   单双各4尾）明确排除在定向重排之外。
3. `rule_documentation.py`：修复两个生成器缺陷——动态受控 mode（如 116）不会出现在静态
   `PREDICTION_CONFIGS` 里因而永远不入文档；mode 251 的口径段原为手写、重新生成会丢。
   顺带让 `site_page_dependencies.generation_assurance_for_mode()` 先查规则登记表
   （此前会把已登记受控的动态 mode 误报成 `history_only`；实测影响 mode 103/116/173，
   只是审计口径修正，不改变生成行为）。
4. 新增 `backend/src/tests/unit/test_prediction_mode116_10ma_control.py`（13 例）并扩展 2 个测试文件。

**验证**

- `get_generation_rule(title_116)` → `rule_id="number"`、`supported=True`、`cross_site_prefix_width=2`
  （生产容器内实测）。
- `verify_hit` 双向正确（集合语义，逆序候选仍命中）。
- 本地库真实未来期干跑（2026 第 191 期，只读真值；只写临时 sqlite）：
  4 个站点候选都含真实特码、`verified_hit=True`、跨站前缀两两不同、`reserve_control` 全部成功；
  10 站同期 10/10 distinct prefixes；`target_hit_rate=0.0` 时不中方向也正确。
- 与展示置换的兼容：`service.py` 只在 `control_plan is None` 时才调 `enforce_prediction_diversity`，
  受控行落库顺序 = 预约前缀顺序；测试证明置换会改动前缀签名，从而锁定该前提。
- `pytest -q` → `1079 passed, 13 skipped, 2 failed`（两条既有无失败）。
- 生产只读核对：`prediction_generation_controls` 中 mode 116 记录数 = 0（尚未生成）、
  `created.mode_payload_116` web6 最新期号 = 271（登记前已生成，保持原样）。

**受控起点**：从登记后的**下一次台湾彩未来期生成**起生效（271 期已存在，不受影响；272 期起受控）。
**历史期零影响**：未回填、未 UPDATE 任何已落库预测行。
**回滚**：单文件级 `git checkout` 即可；最小回滚 = 删掉 `116: _rule(...)` 那一行，
但 `candidate_control.py` 的可达性修复是独立收益（同样修复 mode 34/77 的「伪受控」），建议保留。




### 号码集合族口径复审（2026-09-28 第六轮）

**发布提交**：`83a9d98`。中心节点备份 `/root/Marksix/.deploy-backups/display-standard-6-20260928T095021Z`，
前端节点 `/root/Marksix/.deploy-backups/display-standard-6-20260928T095834Z`。
**公网验收**：10/10 站点 `error=0`、`js_errors=0`，合计 27 条 warn（与上一轮持平）。

**复审结论（逐 mode，含真实开奖复算与前端渲染器取证）**

1. **判定口径全部正确**：9/34/65/77/116/493 为 contains（特码 ∈ 候选），88/481/485/494 为 excludes（特码 ∉ 候选），
   与各自标题语义、前端渲染器、`public/api.py::_check_correct_by_mechanism` 一致，18/18 行复算 0 不一致。
   侦察阶段一度以为 481/485/493/494 的候选列异常——实为 `public.mode_payload_*` 是空表，真实候选只在 `created.*`。
2. **`prefix_width` 全部可满足**（前缀空间 = n!/(n−w)! ≥ 同期站点数）：
   9:240≥1、34:12144≥6、77:182≥1、88:42≥2、116:90≥1、481:90≥4、485:20≥2（最紧，有「允许重复前缀」兜底）、
   493:9240≥3、494:42≥1。**未改任何 width**。
3. **修掉一个真实的可达性缺陷**：`candidate_control._candidate_sequences` 的定向分支只覆盖「baseline 方向与要求相反」。
   当 baseline 已在正确一侧（mode 9/34/77 常见形态：baseline 由热门号 + 期号种子生成 → 所有站点同一条）时，
   预算仍被同一组号码的 `width!` 个排列吃光（mode 9 实测连取 60 个候选只有 1 个不同前缀）→ 第二个站点重选即
   `candidate_space_exhausted` 回落随机，**跨站前缀契约名存实亡**；且旧判据把排除类当包含类
   （mode 88 需要命中时会去构造含特码的杀号候选，`verify_hit` 必然 False）。
   已统一为 `directed_candidates()`（首号遍历候选池 → 前缀互不相同，`desired_inclusion` 决定真值进/出候选）+
   `_truth_must_be_in_candidate(rule)`；宽度 1 的二元玩法保持历史兜底。
4. **展示置换白名单改为按玩法形态派生**：`UNORDERED_NUMBER_SET_MODE_IDS` 由硬编码 `{9,65,88,116}`
   改为派生（`is_number_set_config` + bootstrap 下限 + 契约例外）。**mode 65 必须移出**——它的展示顺序
   （`content[0]-content[-1]` 区间）**就是判定契约**，置换会同时破坏展示与判定；同族 156 一并排除。
   34/77/481/485/493/494 纳入。受控行本来就跳过 `enforce_prediction_diversity`，所以纳入不会让预约前缀脱钩。
5. **9/88 登记受控规则**：`9: _rule("number", _special_number, prefix_width=2)`、
   `88: _rule("number_exclusion", _special_number, prefix_width=2)`（生产容器实测 `supported=True`）。
   **65 故意不登记**：候选必须是升序连续段，通用 `number` 规则会产生任意 12-子集 → 渲染无意义区间并改变判定；
   它已有专用 `_generate_mode_65_row`，阻塞理由写进了生成文档。
   干跑证据（只读真值 + 临时 sqlite）：266–270 期 mode 9/88/116 均 `verified_hit == target_hit`、
   同期两站前缀互不相同；mode 65 恒 `plan=None`。
6. 文档：`backend/docs/prediction-module-rules.md` 重新生成（手写段落保留，新增号码集合族语义段与 mode 65 阻塞理由），
   `backend/docs/number-set-display-order-fix-report.md` 追加第八节复审记录。测试 +15 条
   （`test_prediction_number_set_modes_9_88_control.py` 新增 9 条等），
   `pytest -q` → `1094 passed / 13 skipped / 2 failed`（两条既有失败）。

**旧提交的连带影响（本轮一并上线）**：本轮 fast-forward 之前，仓库里已有两个来自并行会话的提交
`ae0901b`（twsaimahui 预测模块开奖号码取特码 `res_code/res_sx` 末项 + bundle 行尾收敛）与
`6f294f7`（其发布记录）。它们已随本轮一起上线。

**未解决项（需用户决策）**

- **历史数据口径反向**：`created.mode_payload_88/481/485/494` 的历史行按 **contains**（把特码放进候选集合）生成，
  而展示口径是 **excludes**（杀号）→ 历史期 62.1%/82.0%/93.2%/78.7% 显示「错」（随机基线分别为 14.3%/20.4%/10.2%/14.3%）。
  这是**生成侧历史缺陷**，修复需要重生成历史行（改动已落库预测正文），本轮**未改任何历史数据**。
  新生成期次已按正确方向（本轮的方向修正）产出。
- **并行会话**：本工作区在本次会话期间出现过第三方写入（例如 `frontend/public/vendor/twbst528/site-data-adapter.js`
  的 178 行未提交改动）。该改动引入 4 处 R3（判定「错」仍有黄底）回归，**已回退**，未提交。
- 派生白名单覆盖面扩大到全部号码集合族（含本次未启用的 mode）；`185 单双各16码`、`294 尾拖尾` 这类
  名字可能暗示顺序的玩法建议后续单独复核渲染器顺序敏感性。

### 用户决策与并发会话协调（2026-09-28 第六轮收尾）

- **历史数据不修复（用户决定）**：杀号类 mode 88/481/485/494 的历史行按 contains 生成、展示口径为 excludes，
  历史上 62.1%/82.0%/93.2%/78.7% 显示「错」。用户明确「不需要」重生成历史行，因此
  **不回溯修改任何已落库预测正文**；新生成期次已按正确方向产出。
- **185「单双各16码」/294「尾拖尾」的顺序敏感性复核（用户决定）**：不需要。
- **并发会话协作**：本工作区确认存在并行会话写入（第三方提交 `ae0901b`、`6f294f7`；
  并行进行中的 `frontend/public/vendor/shengshi8800/static/js/004jyzt.js`、`019ma24.js`）。
  已把协作约定写入 `AGENTS.md`「并发会话协作约定」：只提交自己改的文件（禁止 `git add -A`）、
  共享文件串行修改、发布前先 `git fetch`、发现未经证实的第三方改动造成回归先 revert 并记录、
  每轮跑固定验收。本会话已按该约定执行：
  - 回退了并行会话那份 178 行的 `frontend/public/vendor/twbst528/site-data-adapter.js` 改动
    （本地展示审计 `error` 由 0 变 4：4 处 R3「判定错仍带黄底」），未提交；回退后 twbst528 恢复 `error=0`。
  - 核实并行会话**进行中**的 shengshi8800 改动（004jyzt/019ma24）未引入回归：
    本地 `rows=443 error=0 js_errors=0`、线上 `rows=447 error=0 js_errors=0`。
  - 本轮未再使用 `git add -A`；`HEAD` 与 `origin/main` 已同步（`6fc84b5`）。

### twssz 展示规范整改（2026-09-28 第七轮）

**用户需求**：① 全部模块文字居中；只有命中的生肖/号码/波色/段数/文字才允许黄底，其余文字一律不许高亮。
②【A级猛料大公开】字号放大。③ 异常检查。

**发布提交**：`ea1d5de`（twssz 改动）+ `9183f3b`（与并行会话提交合并）。中心节点
`display-standard-7-20260928T…` / `display-standard-8-20260928T…`（第二次用于追平并行会话的
`9c6c320`），前端节点 `display-standard-7-20260928T…`；当前两节点均为 `9c6c320`。

**改动（仅 twssz 两个文件 + 一份报告）**
- `frontend/public/vendor/twssz/index.html`：新增 `<style id="twssz-prediction-display-standard">`
  （`text-align:center !important` 覆盖供应商 40 处内联左对齐；A级猛料字号；≤480px 单列堆叠）。
- `frontend/public/vendor/twssz/site-data-adapter.js`：渲染后给真正包住预测模块的祖先容器打
  `data-prediction-center`；清理错误黄底（整行黄底 32 处、AAA级大公开**样例生肖残留** 17 处、
  空 span 黄底 17 处、命中项连标点 5 处、模块标题黄字 32 处），并补上 41 处正确的逐项命中高亮；
  修复「一波中特最新一期整行空白（期号错位一格）」。
- 报告：`docs/vendor-sites/twssz-prediction-display-remediation.md`。

**验收（本地 + 线上实测）**

| 口径 | rows | error | warn | js_errors |
| --- | ---: | ---: | ---: | ---: |
| twssz 本地（改后） | 282 | 0 | 3 | 0 |
| twssz 线上（改后） | 282 | 0 | 4 | 0 |

- Playwright 计算样式：**52/52 预测模块 `text-align: center`**（改前 51/52 非居中），900px 与 375px 一致。
- 黄底元素 153 → 128（本地）/135（线上），逐个核对均为本期命中项；「错」的行零黄底、未开奖不给判定不高亮。
- A级猛料 `.dbt1 span` computed `font-size` **13.33px → 17px**，正文 12px → 16px（900/375 同值）；
  ≤480px 改单列堆叠，行聚类换行单元格 0 个、无横向溢出。
- `audit-verdict-truth.py --site twssz` → `rows=2236 error=0`。
- 报告但未修（详见报告 §3.4）：6 个模块历史上就「命中却没有黄底」（`daxiao`/`pt2xiao`/`sanxiao_siwei_xiao`/
  `danshuangtema` 用 `√`/`ma24` 精选24码/`title_48-ai` AI心水**完全不显示判定**），逐项补高亮需要为 6 个渲染器
  各写一套玩法语义，建议单独立项；R8 三条 warn 与基线相同（候选集大，连对在概率内）。

**并行会话**：本轮按 `AGENTS.md` 协作约定只提交 twssz 自己的文件（未用 `git add -A`）；
`origin/main` 在此期间新增了并行会话的 twbst528/独家公式提交，已用 `git merge`（非强推）合并后推送，
并补跑一次中心节点发布追平版本。

### 待处理：twbst528 线上 5 处 R3（2026-09-28 第七轮收尾时发现，未修）

第七轮发布后全站线上审计（`python scripts\audit-prediction-display.py --json <out>`）显示
**twbst528 `rows=383 error=5`**，全部是 R3（判定「错」但仍有一处黄色高亮）：

```
#xiaoma_xiaoma|鸡,猴,马      第269期 鸡,猴,马 开:46鸡错
#toudanshuang_shu|0头双.3头单.4头单.4头双.  第266期 … 开:10鸡错
?|本期                        268期本期【蛇.猴】输尽光 开:11猴错
?|红肖                        第269期 红肖|马,兔,鼠,鸡 绿肖|羊,龙,牛,狗 开:46鸡错
?|蓝单                        第270期 蓝单|03,09,15,25,31,37,41,47 开:37马错
```

这些出现在 `frontend/public/vendor/twbst528/**` 的最新一轮重写（并行会话提交 `418a29a`/`9c6c320`/`306407a`）之后，
属于「判定为错的行仍保留/新加了黄底」这一类（S3）。按 `AGENTS.md` 协作约定，
**本会话未修改该文件**（并行会话正在连续迭代它，避免互相覆盖）。

修复方向（供接手者参考）：把这 5 个渲染器的黄底条件绑到「本期判定 = 命中」上——
杀号/排除类玩法「准」表示没有可高亮的命中项（应零黄底），命中期只标真正命中的那一项；
未开奖期不给判定、不高亮。验收：`python scripts\audit-prediction-display.py twbst528`
必须回到 `error=0`、`js_errors=0`。
