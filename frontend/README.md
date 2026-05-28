# Frontend 说明

`frontend/` 现在不是“每个站点一套独立源码”的仓库，而是：

- 一个 Next.js 兼容层
- 多个旧静态站点的统一入口
- 多域名分流与旧接口适配层

## 当前原则

- 活跃站点真实目录统一放在 `public/vendor/<site_key>/`
- `public/vendor/` 同时是开发目录和运行目录
- Next 只保留域名分流、访问入口和 API 兼容
- 不再维护额外的站点源码镜像区

## 当前目录分工

```text
app/                        页面入口与兼容页面
app/api/                    旧接口兼容层
components/                 Next 壳层组件
lib/sites.ts                站点配置中心
proxy.ts                    多域名分流
public/vendor/              所有活跃站点真实目录
public/vendor/shengshi8800/
public/vendor/twsaimahui/
public/vendor/admin-history/
```

## 当前站点

### `shengshi8800`

- 入口：`/`
- 原始静态入口：`/vendor/shengshi8800/embed.html?type=3&web=4`
- 真实资源目录：`public/vendor/shengshi8800/**`

### `twsaimahui`

- 入口：`/twsaimahui`
- 原始静态入口：`/vendor/twsaimahui/index.html`
- 真实资源目录：`public/vendor/twsaimahui/**`

### `twcaibawang`

- 入口：`/twcaibawang`
- 原始静态入口：`/vendor/twcaibawang.com/index.html`
- 真实资源目录：`public/vendor/twcaibawang.com/**`

### `admin-history`

- 用途：开奖历史页静态资源
- 真实资源目录：`public/vendor/admin-history/**`

## `web/type` 一致性

这套前端的一个高风险点是：`lib/sites.ts` 里的默认 `web_id` 只代表站点入口默认值，不代表旧静态页运行时一定还会继续用同一个 `web` 发请求。

本仓库已经确认过的现状：

- `shengshi8800`
  - `lib/sites.ts` 默认入口是 `embed.html?type=3&web=4`
  - 旧版 `embed.html` 曾经在运行时把 `type=1/2/3` 映射成 `web=1/2/4`
  - 这会导致页面虽然从 `web=4` 入口打开，但切换彩种后实际请求落到别的 `web`
  - 2026-05 已修正为运行时统一发送 `web=4`
- `twsaimahui`
  - 运行时彩种切换集中在 `static/js/lottery_config.js` 与 `index.html`
  - 当前 `taiwan/macau/hongkong` 三个彩种都固定使用 `web=6`
  - 未发现和 `shengshi8800` 类似的运行时 `web` 漂移
- `twcaibawang`
  - 当前首页开奖 iframe 直接复用 `/vendor/shengshi8800/kj/local.html`
  - 这不一定立即出错，但属于跨站复用旧资源的潜在耦合点
  - 后续如果 `shengshi8800` 的开奖页逻辑或 `web/type` 规则变更，`twcaibawang` 可能被联动影响

新增站点、迁移旧站，或修改彩种切换逻辑时，必须同时检查下面几层：

1. `lib/sites.ts`
   - `defaultWebId`
   - `defaultLotteryTypeId`
   - `vendorIndexPath` / `embedPath`
2. 旧静态页入口
   - `index.html`
   - `embed.html`
   - 是否在运行时重写 `window.web` / `window.type`
3. 彩种配置脚本
   - `static/js/lottery_config.js`
   - 是否存在按 `type` 改写 `web` 的映射
4. 旧 JS 兼容层
   - 是否直接读取全局 `window.web`
   - 是否把写入 `window.web` 反向解释为切换 `type`
5. 嵌套 iframe / 复用资源
   - 是否引用了其他站点的 `local.html`、`index.html`、`static/js/*`
   - 是否依赖其他站点的默认 `web/type` 规则

必须避免的错误：

- 只改 `lib/sites.ts` 的 `defaultWebId`，却没有同步检查旧页运行时脚本
- 默认入口是 `web=A`，但运行时切换后偷偷请求 `web=B`
- 在一个站点里直接复用另一个站点的开奖页或 API 参数映射，却没有记录这种耦合
- 后端已经按显式 `web` 严格隔离，但前端还在继续发送错误的 `web`

推荐自检方式：

1. 打开站点首页，分别切换所有彩种 Tab
2. 在浏览器 Network 中确认 `/api/kaijiang/*`、`/api/post/*`、`/api/index/*` 请求里的 `web/type`
3. 对照 `lib/sites.ts` 的站点默认配置，确认“默认入口值”和“运行时实际请求值”是否一致
4. 如果刻意设计为不一致，必须在本文档里明确记录原因

## 关键配置

### `lib/sites.ts`

这是当前前端最重要的站点配置入口，集中管理：

- 站点路径
- 绑定域名
- 旧站真实入口
- 默认 `web_id`
- 默认 `lottery_type_id`
- 壳层标题、头图、样式资源

后续新增站点时，优先修改这里，不要把配置散落到页面组件里。

### `proxy.ts`

负责：

- 根据 `Host` 把不同域名分流到对应站点入口
- 兼容旧参数风格

### `next.config.mjs`

负责：

- Next 构建设置
- `vendor` 静态资源缓存头

## 当前访问规则

当前已配置：

- `localhost` / `127.0.0.1` -> `/`
- `www.twsaimahui.com` / `twsaimahui.com` -> `/twsaimahui`

## 新站点接入标准

新站点真实目录统一放在：

```text
public/vendor/<site_key>/
```

建议结构：

```text
public/vendor/<site_key>/
  index.html
  embed.html
  static/
    css/
    js/
    image/
    picture/
```

接入流程最少包括：

1. 复制一个已有旧站目录到 `public/vendor/<site_key>/`
2. 修改旧站内 `index.html`、`embed.html`、`static/js/lottery_config.js`
3. 在 `lib/sites.ts` 注册站点配置
4. 检查 `app/api/**` 是否覆盖该站所需旧接口
5. 联调页面、公告、图片、预测模块

## 本地开发

```powershell
cd d:\pythonProject\outsource\Liuhecai
pnpm dev:frontend
```

说明：

- 默认命令已经切换为 `Webpack` 开发模式
- `Turbopack` 只保留为可选命令：`pnpm dev:frontend:turbopack`
- 原因不是功能差异，而是当前仓库在 `Turbopack` 下存在明显的开发态内存稳定性问题

访问：

- `http://127.0.0.1:3000/`
- `http://127.0.0.1:3000/twsaimahui`

## 开发排障

### 1. `adapterFn is not a function`

这不是业务代码报错，而是开发缓存污染。

已确认的根因是：

- `frontend/.next` 中残留了旧的 `proxy` 编译结果
- 运行时混入过期产物后，请求 `/` 会命中错误的中间层适配逻辑

处理：

```powershell
pnpm clean:frontend-cache
pnpm dev:frontend
```

### 2. `JavaScript heap out of memory`

已确认的根因是：

- 当前项目挂载了大量旧静态站资源
- `Turbopack` 在这个仓库的开发态编译中不稳定，容易出现 OOM

处理：

- 日常开发使用 `pnpm dev:frontend`
- 只在明确需要时才尝试 `pnpm dev:frontend:turbopack`

### 3. `EADDRINUSE: 127.0.0.1:3000`

已确认的根因是：

- 前一次开发服务器崩溃后，有残留 `node` 进程继续占用 `3000`

处理：

```powershell
pnpm kill:frontend-port
pnpm dev:frontend
```

### 推荐恢复顺序

```powershell
pnpm kill:frontend-port
pnpm clean:frontend-cache
pnpm dev:frontend
```

## 当前已经整理掉的混淆点

- 不再使用 `sites/` 作为额外源码区
- 不再使用根目录 `twsaimahui/` 作为站点真实目录
- 不再在全局 `layout.tsx` 里硬编码加载 `shengshi8800` 样式

## 仍建议保留的文件

- `components.json`
  - 这是前端 UI 工具配置，不属于站点冗余
- `public/vendor/admin-history/`
  - 这是历史页静态资源，不是重复站点
- `app/twsaimahui/page.tsx`
  - 这是统一入口，不是站点副本
