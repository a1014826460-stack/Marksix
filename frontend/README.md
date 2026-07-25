# Frontend 多站点说明

`frontend/` 是 Next.js 兼容层加多个旧站静态资源入口，不是统一 UI 工程。各站可以继续保留自己的 HTML、CSS、JS、字体、颜色和布局；新站接入时优先模仿目标网页外观。

当前统一的重点是预测模块数据契约：不同后端接口返回的数据先转换成 canonical prediction schema，再由站点 adapter 转成该站旧 JS 或 React 页面需要的 payload。

## 当前目录分工

```text
app/                         页面入口与 API 兼容层
app/api/prediction-modules/   统一预测模块契约接口
components/                  Next 壳层组件
lib/prediction-contract.ts   canonical prediction schema 与后端数据转换
lib/prediction-adapters.ts   canonical -> 站点兼容 payload
lib/sites.ts                 站点配置中心
public/vendor/<site_key>/    各站真实 HTML/CSS/JS/图片资源
```

## 当前站点

- `shengshi8800`: `/`, 静态入口 `/vendor/shengshi8800/embed.html?type=3&web=4`
- `twsaimahui`: `/twsaimahui`, 静态入口 `/vendor/twsaimahui/index.html`
- `twcaibawang`: `/twcaibawang`, 静态入口 `/vendor/twcaibawang.com/index.html`

## 预测数据契约

核心类型位于 `lib/prediction-contract.ts`：

- `CanonicalPredictionModule`: `moduleKey`, `title`, `displayKind`, `rows`, `source`
- `CanonicalPredictionRow`: `issue`, `year`, `term`, `prediction`, `result`, `status`, `raw`
- `prediction`: `text`, `tokens`, `groups`, `imageUrl`, `extra`
- `result`: `isOpened`, `isCorrect`, `code`, `zodiac`, `color`, `text`

来源转换：

- `/public/site-page` -> `canonicalizePublicSitePageData()`
- `/vendor/homepage-modules` -> `canonicalizeVendorHomepageModules()`
- 旧 `mode_payload_*` 字段通过 `raw` 保留，但正式渲染应优先读 canonical 字段。

站点适配：

- `adaptPublicSitePageDataWithCanonicalModules()` 输出兼容旧 `PublicSitePageData`
- `adaptVendorHomepageModulesWithCanonicalModules()` 输出兼容旧 `VendorHomepageModulesResponse`
- `/api/prediction-modules` 同时返回 canonical `data` 和 `compatibility` payload，供新站旧 JS 或 React 页面接入。

## 新站接入流程

1. 将目标站 HTML/CSS/JS 放入 `public/vendor/<site_key>/`。
2. 在 `lib/sites.ts` 注册 `siteKey`, `routePath`, `vendorIndexPath`, `domains`, `defaultWebId`, `defaultLotteryTypeId`。
3. 建立该站点的 prediction adapter，明确页面需要的 `moduleKey` 列表。
4. 旧 JS 不直接读取后端原始返回，统一请求 `/api/prediction-modules?site_key=<site_key>&lottery_type=...`；仅有 `site_id` 时也必须是注册站点，且同时传入的 `site_key` 与 `site_id` 必须指向同一站点。
5. adapter 负责将 canonical row 转成目标页面字段，并定义空数据、待开奖、已开奖、命中、未命中的展示文本。
6. 验收时重点检查预测模块能否在目标样式中正常显示，以及 Network 中 `web/type/lottery_type` 参数是否正确。

## `web/type` 一致性检查

新增站点、迁移旧站或修改彩种切换逻辑时，必须同时检查：

- `lib/sites.ts`: `defaultWebId`, `defaultLotteryTypeId`, `vendorIndexPath`, `embedPath`
- 旧页面入口：`index.html`, `embed.html`
- 彩种配置脚本：是否运行时改写 `window.web` / `window.type`
- 旧 JS 请求：是否直接读取全局 `web/type`
- 嵌套 iframe：是否复用其他站点资源并继承了对方默认参数

## 本地开发

```powershell
cd d:\pythonProject\outsource\Liuhecai
pnpm dev:frontend
```

## UI 保持的数据接入

五站不使用共享 UI runtime。供应商提供的 HTML、CSS、JS、图片和既有 renderer 是视觉真相；
共享层只负责规范 API、请求去重、会话缓存与加载状态，不创建或替换 DOM。

- 浏览器数据客户端：`public/vendor/_shared/lottery-site-data-client.js`
- 站点适配器：`public/vendor/<vendor-directory>/site-data-adapter.js`
- 安全配置：`sites/<siteKey>/site-adapter.ts`，固定为 `existing-dom-only`
- UI 基线：`lib/site-platform/site-ui-baseline.ts`

数据客户端使用：

```js
const client = window.LotterySiteDataClient.create({ siteKey: "example-site" })
const draw = await client.loadDraw({ lotteryType: 3 })
const predictions = await client.loadPredictions({ lotteryType: 3, historyLimit: 8 })
```

返回值固定为 `{ state: "ready" | "stale" | "error", data?, error?, source }`。开奖缓存为
5 秒新鲜 / 60 秒陈旧回退；预测缓存为 60 秒新鲜 / 15 分钟陈旧回退。所有请求均使用同源
`/api/sites/<siteKey>/draw` 和 `/api/sites/<siteKey>/prediction-modules`。

共享脚本不得调用 `document.createElement`、`appendChild`、`replaceChildren`、`innerHTML`、
`document.write`，不得注入 CSS，也不得禁用或改写供应商预测脚本。变更导航、页尾、开奖或
预测 UI 必须先取得用户明确授权。

访问：

- `http://127.0.0.1:3000/`
- `http://127.0.0.1:3000/twsaimahui`
- `http://127.0.0.1:3000/twcaibawang`

常用校验：

```powershell
pnpm --filter @liuhecai/frontend exec tsc --noEmit
```

## 注意事项

- 不统一 UI、组件库、颜色、字号、间距或动效。
- 站点外观由目标网页资源决定。
- 预测模块必须有稳定 `moduleKey`。
- 同一玩法在不同站点只通过 adapter 改展示字段，不改 canonical 数据。
- `raw` 只是兼容兜底，新实现不要直接依赖后端临时字段。

## Registry-Driven Multi-Site Notes

The five public sites are resolved through `lib/sites.ts` and
`lib/site-registry.ts`.

Registered site keys:

- `shengshi8800`
- `twsaimahui`
- `twcaibawang`
- `twjinniu`
- `twcf888`

Each site config includes `renderMode` and `capabilities`. Current render modes:

- `legacy-shell`: `shengshi8800`
- `iframe-vendor`: `twsaimahui`
- `react-home`: `twcaibawang`, `twjinniu`, `twcf888`

Preferred API paths:

- `GET /api/sites/<siteKey>/site-page`
- `GET /api/sites/<siteKey>/homepage-modules`
- `GET /api/sites/<siteKey>/article-detail?article_id=...`
- `GET /api/sites/<siteKey>/prediction-modules`
- `POST /api/sites/<siteKey>/traffic-events`

Legacy API paths remain available as compatibility forwarders and should call
`lib/site-api-service.ts`. Compatibility forwarders record `api_compat_hit`
traffic events without blocking the original response.

Public page traffic is collected by `components/SiteTrafficTracker.tsx`. It uses
`navigator.sendBeacon` first and `fetch(..., { keepalive: true })` as fallback.
The frontend endpoint forwards to Python backend `/api/public/traffic-events`,
where raw IP addresses are hashed before storage.

## Vendor 数据接入试点

`twsaimahui` 是数据客户端的试点。它在原 `site-bridge.js` 后加载数据客户端与
`site-data-adapter.js`，但继续使用原开奖 iframe、导航、预测脚本与页尾图片。适配器只会
预加载规范数据并派发 `site-data:ready`；不会挂载共享 UI。

To scaffold and validate a new vendor site:

```powershell
pnpm site:scaffold --site-key example-site
# Copy the supplied archive to frontend/public/vendor/example-site/.
# Then fill the generated manifest with actual siteId, webId, domains and modules.
pnpm site:sync-manifests
pnpm site:validate --site-key example-site
```

不要猜测未知供应商模块如何消费预测行。页面必须声明经审核的 existing-DOM adapter 与选择器
合同；不存在安全既有节点时，保持空选择器，不新增挂载容器。
