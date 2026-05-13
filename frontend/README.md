# 前端项目说明

本项目的前台展示端已经完成重构，当前的主策略不是继续 React 化旧站，而是保留旧站 `HTML + JS + CSS` 作为主展示链路，Next.js 主要负责入口整理、URL 规范化以及 API 兼容层。

## 当前主路径

当前用户访问首页时，实际运行链路如下：

```text
用户访问 /
  ↓
app/page.tsx
  ↓
301/308 规范化到 /?t=3
  ↓
proxy.ts 处理旧参数兼容与规范化
  ↓
next.config.mjs rewrite
  ↓
/vendor/shengshi8800/embed.html?type=3&web=4
  ↓
public/vendor/shengshi8800/embed.html
  ↓
public/vendor/shengshi8800/index.html
  ↓
public/vendor/shengshi8800/static/js/*.js
```

说明：

- 浏览器对外统一使用短参数风格：`/?t=1|2|3`
- 旧参数风格 `?type=3&web=4` 不再作为对外主入口
- 旧站页面主体仍位于 `public/vendor/shengshi8800/**`
- `app/legacy-shell/page.tsx` 只作为调试/回退壳保留，不是主首页

## 彩种参数约定

当前统一使用：

- `t=1`：香港彩
- `t=2`：澳门彩
- `t=3`：台湾彩

内部兼容规则：

- 外部访问 `/?type=3&web=4` 时，会被规范化到 `/?t=3`
- 外部访问 `/vendor/shengshi8800/embed.html?type=3&web=4` 时，也会被规范化到 `/?t=3`
- Next.js rewrite 再把 `/?t=3` 内部映射回旧站所需的 `type=3&web=4`

这样做的目的，是让对外 URL 简洁统一，同时不破坏旧站内部脚本对 `type/web` 的依赖。

## API 链路

前台旧 JS 不直接请求 Python backend，而是继续走 Next.js API 兼容层：

```text
旧站 JS
  ↓
/api/kaijiang/*
/api/latest-draw
/api/next-draw-deadline
/api/draw-history
/api/post/getList
/uploads/image/*
  ↓
app/api/**/route.ts
  ↓
lib/backend-api.ts
  ↓
Python backend
```

这部分属于当前有效运行链路，不能因为“不是 React 页面”就误判为可删除代码。

## 目录分工

### 主运行目录

- `app/page.tsx`：首页规范化入口
- `app/api/**`：API 兼容层
- `app/uploads/**`：上传图片代理
- `public/vendor/shengshi8800/**`：旧站前台主体
- `lib/backend-api.ts`：前后端代理调用封装
- `proxy.ts`：根路径与旧参数风格规范化
- `next.config.mjs`：首页 rewrite 与静态资源响应头配置

### 归档目录

- `_archived_unused_frontend/**`

该目录用于存放已经退出当前主运行链路的旧 React 页面/组件或明确不再使用的前端文件。

归档目录原则：

- 不删除，统一保留原始相对路径结构
- 不参与 TypeScript 检查
- 不参与 ESLint 检查
- 不参与 Next.js 页面扫描
- 不作为当前维护对象

## 当前前端架构原则

这次重构后的核心原则如下：

1. 旧站 `HTML + JS + CSS` 是前台主路径。
2. 不再把 React 首页链路当作线上主入口继续维护。
3. 不把旧站所有 JS 模块一次性重写成 React 组件。
4. Next.js 主要负责路由整理、兼容层、静态资源承载与 API 转发。
5. 后续如果要 React 化，只能逐模块迁移，不能整体推翻旧站后重写。

## 文字替换策略

旧站包含大量历史脚本和模板拼接逻辑，因此“彩种切换时哪些文字需要变化、哪些必须固定”必须严格区分。

### 必须固定不变的内容

以下区域属于品牌/壳层静态文案，不应该被彩种切换逻辑全局替换：

- 页面 `<title>`：`全网最准尽在台湾六合彩论坛`
- 导航栏论坛标题：`台湾六合彩论坛`
- 某些固定站点标题：如 `台湾论坛`、`台湾资料网`
- 彩种切换按钮本身的文案：`香港彩`、`澳门彩`、`台湾彩`

### 允许按彩种切换的内容

以下内容可以根据当前彩种变动：

- 各资料板块标题
- 各彩种对应的说明文案
- 特定模块中的彩种名称和宣传语

实现上必须使用“精确作用域替换”，不能再做整页或整棵 DOM 的粗暴全局文本替换。

## 这次重构里犯过的错误

下面这些错误已经被明确记录，后续维护时要避免重复：

### 1. 错把“全局替换台湾”为可行方案

这是本轮最核心的错误。旧站里同时存在：

- 需要动态变化的板块标题
- 必须静态固定的品牌标题
- 需要保持原样的按钮文字

如果直接做全局 `台湾 -> 香港/澳门` 替换，就会把导航标题、静态站名、按钮文案一起污染，导致：

- 标题被错误替换
- 按钮文字变化
- 出现不可预期的 DOM 文本串联问题

正确做法是：

- 只对明确的目标容器做替换
- 先定义静态白名单
- 再定义允许动态变化的区域

### 2. 没先确认真实 DOM 结构就补选择器

旧站很多内容不是 TS import 渲染，而是：

- `document.write`
- 字符串拼接 HTML
- 运行时注入节点

如果不先看最终 DOM，而只凭源码猜测替换位置，很容易出现“代码改了但页面没生效”或“误伤别的区域”。

正确做法是：

- 先确认最终落在哪个容器
- 再做定点替换
- 每次替换后都验证对应模块是否真的命中

### 3. 在编码不稳定的旧 HTML/JS 上反复打补丁

旧站文件存在历史编码复杂、字符串拼接密集的问题。如果在没有统一确认编码前提下反复局部补丁，很容易引入：

- 中文乱码
- 匹配字符串失效
- 正则或文本替换无法命中

正确做法是：

- 尽量用最小、可验证的方式重写宿主层逻辑
- 避免在同一文件上连续做脆弱字符串补丁
- 每次改动后立即做构建和实际文本验证

### 4. 把“地址栏不变”和“页面内部切换”当成同一件事

首页对外 URL 规范化与旧站内部 `type/web` 状态同步，是两个不同层面的问题：

- 对外 URL：应该统一为 `/?t=1|2|3`
- 对内运行：旧站很多接口和逻辑仍依赖 `type/web`

如果只修了入口 rewrite，而没有同步内部状态，就会出现：

- 地址栏是新的
- 但接口参数还是旧值或旧彩种

正确做法是同时保证：

- URL 规范化
- 内部状态同步
- API 请求参数同步刷新

### 5. 没把“滚动位置稳定”作为彩种切换的硬约束

旧站切换彩种时，如果直接 reload、replace 整页或粗暴重绘，很容易产生页面抖动、跳顶、位置丢失。

当前维护时必须把下面这件事当硬要求：

- 彩种切换前后，滚动位置要尽量保持稳定

后续如果继续调整 `embed.html` 或壳层脚本，必须优先验证这个行为。

## 后续维护禁区

除非明确评估并验证，否则不要做以下事情：

1. 不要再恢复 React 首页作为主入口。
2. 不要把 `public/vendor/shengshi8800/static/js/*.js` 因为“没有 TS import”就判定为未使用。
3. 不要删除 `app/api/**/route.ts` 中的兼容接口。
4. 不要再引入新的 UI 框架来“整体替换旧站”。
5. 不要做整页级、全文级的品牌词替换。
6. 不要在未确认最终 DOM 的情况下继续补选择器。

## 本地开发

```powershell
cd frontend
npm install
npm run dev
```

本地访问：

- `http://127.0.0.1:3000/?t=1`
- `http://127.0.0.1:3000/?t=2`
- `http://127.0.0.1:3000/?t=3`

## 构建

```powershell
cd frontend
npm run build
```

当前项目使用 npm 锁文件，不混用 pnpm/yarn。

## 推荐排查顺序

如果后续再遇到“切换彩种后标题不对 / 数据不对 / 地址栏不对 / 页面抖动”的问题，建议按这个顺序排查：

1. 先看地址栏是否仍是 `/?t=1|2|3`
2. 再看 rewrite 后是否正确进入 `/vendor/shengshi8800/embed.html?type=...&web=4`
3. 再看旧站内部状态是否已同步到当前彩种
4. 再看 `/api/kaijiang/*` 等请求里的 `type` 是否已刷新
5. 最后再看具体板块文字是否命中了正确的动态替换范围

## 相关文件

- [app/page.tsx](./app/page.tsx)
- [proxy.ts](./proxy.ts)
- [next.config.mjs](./next.config.mjs)
- [docs/frontend-legacy-js-main-path.md](./docs/frontend-legacy-js-main-path.md)
- [public/vendor/shengshi8800/embed.html](./public/vendor/shengshi8800/embed.html)
- [public/vendor/shengshi8800/index.html](./public/vendor/shengshi8800/index.html)
