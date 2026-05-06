# 六合彩前端站点 — 预测号码模块说明

## 概述

本前端站点（Next.js，端口 3000）展示六合彩论坛的公开页面，核心功能是**渲染预测号码模块**——展示各种预测算法的历史结果和最新预测。

数据统一从 Python 后端 `/api/public/site-page` 获取，由 React 组件渲染为与旧站视觉一致的页面。

---

## 预测号码模块列表

页面中展示的所有预测模块均由后端 `site_prediction_modules` 表动态控制。当前数据库已配置的模块：

| 模块名称 | mechanism_key | 数据表 | 说明 |
|---------|--------------|--------|------|
| 四字词语(澳欲钱料) | title_234 | mode_payload_234 | 四字成语预测 |

> **注意**：旧站（`/vendor/shengshi8800/index.html`）原有 43 个独立 JS 渲染的模块，由于后端数据库目前只配置了上述模块，新 React 页面仅展示已配置的模块。随着后端逐步添加更多 `site_prediction_modules` 记录，React 页面会自动显示它们，无需修改前端代码。

---

## 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  Python 后端 (port 8000)                                        │
│  /api/public/site-page                                          │
│    └─ site: 站点信息                                             │
│    └─ draw: 开奖快照（期号 + 号码球 + 特码）                       │
│    └─ modules[]: 预测模块列表                                     │
│         └─ history[]: 历史预测行                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │ fetch (服务端)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 前端 (port 3000)                                      │
│  page.tsx (Server Component)                                    │
│    └─ getPublicSitePageData() → 后端 API                        │
│    └─ transformSitePageData() → LotteryPageData                 │
│    └─ HomePageClient (Client Component)                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │ props
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  子组件                                                         │
│  ┌─ Header ─────── 日期/农历/时钟/头图                          │
│  ├─ NavTabs ────── 导航链接（一肖一码、四肖八码等）               │
│  ├─ PreResultBlocks ─ 核心3模块专用渲染（两肖平特王/三期中特/双波中特）│
│  ├─ PredictionModules ─ 通用模块渲染器（所有其他模块自动渲染）    │
│  ├─ LotteryResult ── 开奖号码球展示                              │
│  └─ Footer ─────── 版权/返回顶部                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心文件说明

### 数据层

| 文件 | 职责 |
|------|------|
| [lib/backend-api.ts](lib/backend-api.ts) | 后端 API 客户端，封装 `fetch`，提供 `getPublicSitePageData()` |
| [lib/site-page.ts](lib/site-page.ts) | 后端 API 响应类型定义（`PublicSitePageData`、`PublicModule` 等） |
| [lib/lotteryData.ts](lib/lotteryData.ts) | 前端数据类型（`LotteryPageData`）+ 数据转换函数 `transformSitePageData()` |

### 组件层

| 文件 | 渲染内容 | 数据来源 |
|------|---------|---------|
| [components/Header.tsx](components/Header.tsx) | 日期、农历、时钟、冲煞生肖、头图 | 客户端 `Date` 对象 |
| [components/NavTabs.tsx](components/NavTabs.tsx) | 导航链接（锚点跳转）+ 推广资料 | 静态配置 |
| [components/PreResultBlocks.tsx](components/PreResultBlocks.tsx) | **两肖平特王**、**三期中特**、**双波中特** | `LotteryPageData.flatKingRows / threeIssueRows / doubleWaveRows` |
| [components/PredictionModules.tsx](components/PredictionModules.tsx) | 所有其他预测模块（通用渲染器） | `LotteryPageData.rawModules` |
| [components/LotteryResult.tsx](components/LotteryResult.tsx) | 开奖号码球（6 普通球 + 1 特码球） | `LotteryPageData.resultBalls / specialBall` |
| [components/InfoCard.tsx](components/InfoCard.tsx) | 信息卡片（如"一肖中特"） | `LotteryPageData.infoSections` |
| [components/RecordRow.tsx](components/RecordRow.tsx) | 单行预测记录 | `PlainRow` |
| [components/Footer.tsx](components/Footer.tsx) | 免责声明 + 返回顶部 | — |

### 页面入口

| 文件 | 职责 |
|------|------|
| [app/page.tsx](app/page.tsx) | **服务端组件**：获取 API 数据 → 转换 → 传给客户端组件 |
| [app/HomePageClient.tsx](app/HomePageClient.tsx) | **客户端组件**：状态管理（时钟、游戏切换）+ 子组件编排 |
| [app/layout.tsx](app/layout.tsx) | 根布局：导入全局 CSS + 旧站 CSS |

### 样式

| 文件 | 内容 |
|------|------|
| [app/globals.css](app/globals.css) | 补充样式（缺失的旧站类名：`blue-text`、`black-text` 等 + `nav2`、`djck`、`KJ-TabBox`） |
| `public/vendor/.../style1.css` | 旧站核心样式（`.box`、`.pad`、`.list-title`、`.duilianpt1`、`.zl` 等） |
| `public/vendor/.../style3.css` | 旧站扩展样式 |

---

## 数据转换细节

`transformSitePageData()` 将后端 `PublicSitePageData` 转换为前端 `LotteryPageData`：

```typescript
// 已知 mechanism_key 映射（在 lotteryData.ts 中定义）：
flatKingRows    ← modules[].where(mechanism_key === "pt2xiao")    // 两肖平特王
threeIssueRows  ← modules[].where(mechanism_key === "3zxt")      // 三期中特
doubleWaveRows  ← modules[].where(mechanism_key === "hllx")      // 双波中特

// 其他所有模块保留在 rawModules 中，由 PredictionModules 自动渲染
rawModules      ← modules[]（完整副本）
```

---

## 如何添加新的预测模块

### 场景一：后端已配置新模块

1. 在 `backend` 的 `site_prediction_modules` 表中添加新记录
2. **无需修改前端代码**——`PredictionModules` 会自动渲染新模块

### 场景二：需要专用组件渲染

1. 创建新的 React 组件（如 `MyNewModule.tsx`）
2. 在 `lotteryData.ts` 的 `transformSitePageData()` 中添加 `mechanism_key` 映射
3. 在 `HomePageClient.tsx` 中将该 `mechanism_key` 加入 `excludeKeys`
4. 在 `HomePageClient.tsx` 中渲染新组件

---

## 与旧站的关系

| 对比项 | 旧站（redirect） | 新 React 版本 |
|--------|-----------------|---------------|
| 数据获取 | 43 个独立 JS × 各自 AJAX | 1 次调用 `/api/public/site-page` |
| 模块数量 | 43 个（硬编码） | 动态（由后端控制） |
| CSS | 内联 + 外部 CSS | 复用旧站 CSS 文件 |
| 访问路径 | `/vendor/shengshi8800/index.html` | `/`（首页） |
| 维护性 | 每个模块改 CSS/JS | 通用渲染器 + 按需专用组件 |

旧站文件仍保留在 `public/vendor/shengshi8800/` 目录下，可随时通过直接访问该路径查看。

---

## 启动方式

```powershell
# 1. 启动 Python 后端（PostgreSQL）
cd d:\pythonProject\outsource\Liuhecai
python backend/src/app.py --host 127.0.0.1 --port 8000 --db-path "postgresql://postgres:pass@localhost:5432/liuhecai"

# 2. 启动前端站点
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

环境变量（`frontend/.env.local`）：

```
LOTTERY_BACKEND_BASE_URL=http://127.0.0.1:8000/api
LOTTERY_SITE_ID=1
```
