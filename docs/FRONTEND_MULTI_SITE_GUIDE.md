# 前端多站点管理规范

本文定义当前仓库的前端多站点管理规则，目标是避免：

- 站点真实目录重复
- 域名分流规则散落
- 新站点接入时路径混淆
- 误把附属静态资源目录当成独立站点

## 一句话原则

活跃站点真实目录只放在 `frontend/public/vendor/<site_key>/`。

## 目录规范

### 活跃站点

```text
frontend/public/vendor/<site_key>/
```

建议结构：

```text
index.html
embed.html
static/
  css/
  js/
  image/
  picture/
```

### Next 入口层

```text
frontend/app/
frontend/lib/sites.ts
frontend/proxy.ts
```

### 附属静态资源

```text
frontend/public/vendor/admin-history/
```

说明：

- 这是历史页依赖资源
- 它不是独立站点

## 当前配置入口

### 站点配置中心

[frontend/lib/sites.ts](/d:/pythonProject/outsource/Liuhecai/frontend/lib/sites.ts)

这里统一维护：

- `siteKey`
- `routePath`
- `vendorIndexPath`
- `domains`
- `legacyPublicBasePath`
- `defaultGame`
- `defaultWebId`
- `defaultLotteryTypeId`
- `forumTitle`
- `headerImagePath`
- `embedPath`
- `shellCssPaths`

### 域名分流入口

[frontend/proxy.ts](/d:/pythonProject/outsource/Liuhecai/frontend/proxy.ts)

### 静态资源缓存规则

[frontend/next.config.mjs](/d:/pythonProject/outsource/Liuhecai/frontend/next.config.mjs)

## 命名规则

`site_key` 必须满足：

- 小写英文
- 可带数字
- 可带短横线

示例：

- `shengshi8800`
- `twsaimahui`
- `new-site-01`

不要使用：

- 中文目录名
- 带环境含义的真实目录名，如 `prod`、`test`、`final`

## 当前站点边界

### `shengshi8800`

- 真实目录：`frontend/public/vendor/shengshi8800/`
- 默认对外入口：`/`

### `twsaimahui`

- 真实目录：`frontend/public/vendor/twsaimahui/`
- 对外入口：`/twsaimahui`

### `admin-history`

- 真实目录：`frontend/public/vendor/admin-history/`
- 分类：附属静态资源，不算独立站点

## 新站点接入流程

1. 复制已有旧站到 `frontend/public/vendor/<site_key>/`
2. 修改旧站自身配置，如 `index.html`、`embed.html`、`static/js/lottery_config.js`
3. 在 `frontend/lib/sites.ts` 注册站点
4. 如需独立入口，新增 `frontend/app/<site_key>/page.tsx`
5. 在本地用目标域名或路径联调
6. 检查兼容 API 是否覆盖旧站请求

## 已明确不再使用的结构

- `sites/`
- 根目录 `twsaimahui/`
- “再复制一份源码区，然后再同步到 public/vendor” 的做法

## 维护红线

1. 不要为活跃站点再建立第二套真实目录
2. 不要把域名逻辑硬编码进多个页面组件
3. 不要把 `admin-history` 当成普通站点复制接入
4. 不要把某个站点的样式全局注入到所有页面
5. 新站点接入后要同步更新 README 与本文档

## 开发运行约定

- 默认启动命令：`pnpm dev:frontend`
- 默认开发模式：`Webpack`
- 可选实验命令：`pnpm dev:frontend:turbopack`

当前之所以不把 `Turbopack` 作为默认模式，是因为该仓库同时承载了多个旧静态站目录，开发态编译时更容易触发内存不稳定问题。

## 常见故障

### `adapterFn is not a function`

根因：

- `frontend/.next` 中存在过期的开发缓存
- 旧代理编译产物和当前 `frontend/proxy.ts` 混用，导致首页请求进入错误的适配链路

修复：

```powershell
pnpm clean:frontend-cache
pnpm dev:frontend
```

### `EADDRINUSE: 127.0.0.1:3000`

根因：

- 崩溃后的 `node` 残留进程没有释放端口

修复：

```powershell
pnpm kill:frontend-port
pnpm dev:frontend
```

### `JavaScript heap out of memory`

根因：

- `Turbopack` 在当前多旧站资源仓库中开发态内存占用过高

修复：

- 切回 `pnpm dev:frontend`
- 不把 `Turbopack` 当作默认开发模式
