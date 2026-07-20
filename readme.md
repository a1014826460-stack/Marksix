# Liuhecai 项目说明

本仓库当前采用“`Next.js 前端兼容层 + 多站点旧静态资源 + Python 后端`”的结构。

当前已经明确的边界是：

- 活跃站点真实目录只放在 `frontend/public/vendor/`
- Next 负责域名分流、访问入口、API 兼容层
- 旧站 HTML、CSS、JS 仍然保留原始运行方式
- 不再保留额外的 `sites/` 源码镜像区

## 目录总览

```text
backend/                         Python API 与后台业务
frontend/                        Next.js 前端兼容层
frontend/public/vendor/          所有活跃站点的唯一真实目录
frontend/public/vendor/shengshi8800/
frontend/public/vendor/twsaimahui/
frontend/public/vendor/admin-history/
docs/                            项目文档
deploy/                          部署脚本
```

## 当前站点

### `shengshi8800`

- 真实目录：`frontend/public/vendor/shengshi8800/`
- 性质：当前默认旧站前台
- 默认入口：`/`
- 原始入口：`/vendor/shengshi8800/embed.html?type=3&web=4`

### `twsaimahui`

- 真实目录：`frontend/public/vendor/twsaimahui/`
- 性质：已由 Next 统一托管访问入口的旧静态站
- 统一入口：`/twsaimahui`
- 原始入口：`/vendor/twsaimahui/index.html`

### `admin-history`

- 真实目录：`frontend/public/vendor/admin-history/`
- 性质：开奖历史页依赖的附属静态资源
- 说明：它不是独立前台站点，而是历史页的样式与脚本资源目录

## 当前前端职责

### `frontend/app/`

- 提供页面入口
- 提供站点壳层入口
- 提供兼容页面如 `/twsaimahui`、`/history`

### `frontend/app/api/`

- 提供旧站兼容接口
- 例如：
  - `/api/kaijiang/*`
  - `/api/post/getList`
  - `/api/index/notice`
  - `/api/next-draw-deadline`

### `frontend/lib/sites.ts`

- 站点配置中心
- 管理：
  - `siteKey`
  - `routePath`
  - `vendorIndexPath`
  - `domains`
  - `defaultWebId`
  - `defaultLotteryTypeId`
  - 旧站壳样式与头图等展示配置

### `frontend/proxy.ts`

- 根据请求 `Host` 做域名分流
- 保留旧参数风格兼容

## 多域名映射

当前已配置：

- `localhost` / `127.0.0.1` -> `/`
- `www.twsaimahui.com` / `twsaimahui.com` -> `/twsaimahui`

后续新增站点时，优先改：

- [frontend/lib/sites.ts](./frontend/lib/sites.ts)
- [frontend/proxy.ts](./frontend/proxy.ts)

不要继续把域名逻辑散落到多个页面里。

## 新站点标准落位

新站点统一放在：

```text
frontend/public/vendor/<site_key>/
```

推荐目录结构：

```text
frontend/public/vendor/<site_key>/
  index.html
  embed.html
  static/
    css/
    js/
    image/
    picture/
```

命名规则：

- `site_key` 使用小写英文、数字、短横线
- 不使用中文目录名
- 不用 `prod`、`test`、`final` 这类环境语义命名真实站点目录

## 本地启动

本地开发和生产部署为硬隔离环境，不能交叉使用配置：

- 开发机只使用 Windows 原生 PostgreSQL 18：`127.0.0.1:5432`，密钥只放在
  被忽略的 `backend/.env.local`，并由本地脚本设置
  `LIUHECAI_RUNTIME_ENV=development`。
- 生产机只使用 Docker Compose：根目录被忽略的 `.env` 只保存 Compose 密钥，
  不得定义 `DATABASE_URL`；容器仅使用 `pgbouncer:6432`，并设置
  `LIUHECAI_RUNTIME_ENV=production`。
- 不在 Windows 开发机运行 `docker compose up` 作为数据库来源，也不在生产机运行
  `backend/scripts/restart-backend.ps1`。

开发前确认原生 PostgreSQL 服务运行：

```powershell
Get-Service postgresql-x64-18
```

前端：

```powershell
cd d:\pythonProject\outsource\Liuhecai
pnpm dev:frontend
```

说明：

- `pnpm dev:frontend` 现在默认走 `Webpack` 开发模式
- `Turbopack` 仅作为可选实验命令保留：`pnpm dev:frontend:turbopack`
- 这样调整是因为当前仓库包含大量旧静态站资源，`Turbopack` 在本项目下多次出现 OOM，不适合作为默认开发模式

后端：

```powershell
cd d:\pythonProject\outsource\Liuhecai
pwsh -ExecutionPolicy Bypass -File .\backend\scripts\restart-backend.ps1
```

访问入口：

- `http://127.0.0.1:3000/`
- `http://127.0.0.1:3000/twsaimahui`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:3002/fackyou/login`

## 前端排障

### `TypeError: adapterFn is not a function`

根因：

- 这是一次 `Next dev` 缓存污染问题
- 当时 `frontend/.next` 里混入了旧的代理编译产物，导致运行时同时出现了过期的 `proxy` 结果和新的 `frontend/proxy.ts`
- 结果就是开发服务器启动后，在请求 `/` 时命中了错误的中间产物，最终报出 `adapterFn is not a function`

处理方式：

```powershell
pnpm clean:frontend-cache
pnpm dev:frontend
```

### `JavaScript heap out of memory`

根因：

- 默认使用 `Turbopack` 时，当前仓库的旧站静态资源体量较大，开发态编译不稳定
- 即使已经提高 `NODE_OPTIONS=--max-old-space-size=8192`，仍然会出现 OOM

处理方式：

- 默认使用 `pnpm dev:frontend`
- 不把 `Turbopack` 作为日常开发默认命令

### `EADDRINUSE: address already in use 127.0.0.1:3000`

根因：

- 前一次 `Next dev` 异常退出后，残留的 `node` 进程没有释放 `3000` 端口

处理方式：

```powershell
pnpm kill:frontend-port
pnpm dev:frontend
```

### 推荐排障顺序

```powershell
pnpm kill:frontend-port
pnpm clean:frontend-cache
pnpm dev:frontend
```

## 当前建议保留的关键配置文件

- `frontend/lib/sites.ts`
- `frontend/proxy.ts`
- `frontend/next.config.mjs`
- `frontend/.env.local`
- `pnpm-workspace.yaml`
- `package.json`
- 后端启动会同时拉起 `8000` 的 Python API 和 `3002` 的后台管理界面

## 本次已确认整理的冗余项

- 不再保留 `sites/`
- 不再保留根目录 `twsaimahui/` 作为站点真实目录
- 不再把 `shengshi8800` 的 CSS 全局注入到所有页面
- 根目录未被引用的 `globals.css` 可以删除

## 文档入口

- [frontend/README.md](./frontend/README.md)
- [docs/FRONTEND_MULTI_SITE_GUIDE.md](./docs/FRONTEND_MULTI_SITE_GUIDE.md)
- [docs/NEW_SITE_MIN_CHECKLIST.md](./docs/NEW_SITE_MIN_CHECKLIST.md)
- [DEPLOY.md](./DEPLOY.md)
