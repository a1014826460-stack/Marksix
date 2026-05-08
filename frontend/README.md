# 六合彩前端站点 — 预测号码模块说明

> 入口说明（2026-05-08 起）：
> 请使用 `http://127.0.0.1:3000/legacy-shell?t=3` 作为前端主入口。
> `http://127.0.0.1:3000/` 现仅做重定向兼容，原挂载在 `/` 的 React 首页已封存并暂停使用，请不要再把 `/` 当作开发或验收入口。

## 概述

本前端站点（Next.js，端口 3000）展示六合彩论坛的公开页面，核心功能是**渲染预测号码模块**——展示各种预测算法的历史结果和最新预测。

数据统一从 Python 后端 `/api/public/site-page` 和 `/api/legacy/module-rows` 获取，由 React 组件渲染为与旧站视觉一致的页面。

---

## 预测号码模块列表

页面展示的所有预测模块均来自旧站兼容端点（`/api/legacy/module-rows`），共 **36 个模块 × 3 种彩种**。每个模块都应有**独立的 React 渲染组件**，精确复刻旧站对应 JS 文件的格式。

> **核心原则**：不再使用通用 `duilianpt1` 渲染器。每个模块根据其 `mechanism_key` 分发到对应的自定义渲染器，确保 100% 匹配旧站的括号样式、颜色方案、CSS 类名和行布局。

### 模块 → 渲染器对照表

| 渲染类 | CSS 类名 | 包含模块 | 实现状态 |
|--------|---------|---------|---------|
| 标准 duilianpt1 + 括号配置 | `duilianpt1` | ptyx, lxzt, 3tou, xingte, ptyw, shawei, dxzt, jyzt | ⚠️ 部分实现 |
| Ptyx11 表格 | `ptyx11` | wxzt(48), jxzt(49), dxztt1(108), rccx(3), sjsx(61) | ❌ 未实现 |
| 三列 bzlx 表格 | `bzlx` | 6wei(2) | ✅ 已实现 |
| 四列 sqbk 表格 | `sqbk` | dssx/ds4x(31) | ❌ 未实现 |
| 自定义多行/期 | `qxtable` | 7x7m(246), 8jxym(151), wxbm(246), qqsh(26) | ⚠️ 部分实现 |
| 自定义复杂模块 | 多种 | pmxjcz(331) | ❌ 未实现 |
| 文本模块 | `legacy-module-text` | yjzy(50), yqmtm(68), szxj(52), djym(59), yyptj(244), qqsh(26), juzi(62) | ⚠️ 部分实现 |
| 特殊逻辑 | 多种 | shaxiao(42反向), shabanbo(58正向), tema(34双行) | ❌ 未实现 |
| 核心 3 模块 | `duilianpt1` | pt2xiao(43), 3zxt(197), hllx(38) | ✅ 已实现(PreResultBlocks) |

> 详细 42 模块逐项对比见 [docs/legacy-vs-react-comparison.md](docs/legacy-vs-react-comparison.md)。

### 数据可用性

**所有 36 个模块在三种彩种下均有数据**（台湾彩 ~72 行，澳门彩 ~10 行，香港彩 ~10 行）。无不渲染的数据缺失模块。

---

## 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  Python 后端 (port 8000)                                        │
│  /api/public/site-page                                          │
│    └─ site: 站点信息                                             │
│    └─ draw: 开奖快照（期号 + 号码球 + 特码）                       │
│    └─ modules[]: 预测模块（仅 site_prediction_modules 已配置的）    │
│                                                                  │
│  /api/legacy/module-rows?modes_id=X&type=Y&web=Z                │
│    └─ 旧站兼容接口：通过 modes_id 查询 36 种不同预测表              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ fetch (服务端并行)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 前端 (port 3000)                                      │
│  page.tsx (Server Component)                                    │
│    ├─ getPublicSitePageData()     → 站点 + 开奖                  │
│    ├─ fetchAllLegacyModulesByGame() → 36 模块 × 3 彩种          │
│    └─ merge + transformSitePageData() → LotteryPageData         │
│    └─ HomePageClient (Client Component)                          │
│         ├─ PreResultBlocks     → 3 核心模块（pt2xiao/3zxt/hllx） │
│         └─ PredictionModules   → 其余 33 模块                    │
│              └─ LegacyModuleRegistry → 按 mechanism_key 分发     │
└─────────────────────────────────────────────────────────────────┘
```

### 彩种切换架构

```
modulesByGame = {
  taiwan:    [PublicModule[], ...],   // type=3
  macau:     [PublicModule[], ...],   // type=2
  hongkong:  [PublicModule[], ...],   // type=1
}

切换彩种 → activeGame 变化 → 子组件从 modulesByGame[activeGame] 重新渲染
```

所有三种彩种数据在服务端预加载，切换无额外网络请求。

---

## 核心文件说明

### 数据层

| 文件 | 职责 |
|------|------|
| [lib/backend-api.ts](lib/backend-api.ts) | 后端 API 客户端，封装 `fetch`，提供 `getPublicSitePageData()` |
| [lib/site-page.ts](lib/site-page.ts) | 后端 API 响应类型定义（`PublicSitePageData`、`PublicModule` 等） |
| [lib/lotteryData.ts](lib/lotteryData.ts) | 前端数据类型（`LotteryPageData`）+ 数据转换函数 `transformSitePageData()` |
| [lib/legacy-modules.ts](lib/legacy-modules.ts) | **旧站模块注册表**：36 个模块的 modes_id 映射 + 并行获取 + contentTransform |

### 组件层

| 文件 | 渲染内容 | 数据来源 |
|------|---------|---------|
| [components/Header.tsx](components/Header.tsx) | 日期、农历、时钟、冲煞生肖、头图 | 客户端 `Date` 对象 |
| [components/NavTabs.tsx](components/NavTabs.tsx) | 导航链接（锚点跳转）+ 推广资料 | 静态配置 |
| [components/PreResultBlocks.tsx](components/PreResultBlocks.tsx) | **两肖平特王**、**三期中特**、**双波中特** | `modulesByGame[activeGame]` |
| [components/PredictionModules.tsx](components/PredictionModules.tsx) | 通用渲染器 + 按需分发到自定义渲染器 | `modulesByGame[activeGame]` |
| [components/LegacyModuleRegistry.tsx](components/LegacyModuleRegistry.tsx) | mechanism_key → 自定义渲染器注册表 | 被 PredictionModules 调用 |
| [components/LotteryResult.tsx](components/LotteryResult.tsx) | 开奖结果（iframe 嵌入旧站开奖页面） | iframe（admin.shengshi8800.com） |
| [components/InfoCard.tsx](components/InfoCard.tsx) | 信息卡片（如"一肖中特"） | `LotteryPageData.infoSections` |
| [components/RecordRow.tsx](components/RecordRow.tsx) | 单行预测记录 | `PlainRow` |
| [components/Footer.tsx](components/Footer.tsx) | 免责声明 + 返回顶部 | — |

### 页面入口

| 文件 | 职责 |
|------|------|
| [app/page.tsx](app/page.tsx) | **根路由重定向入口**：统一跳转到 `/legacy-shell?t=3` |
| [app/_archived/root-home-page.tsx](app/_archived/root-home-page.tsx) | **封存的旧首页实现**：原 `/` React 首页，已暂停使用，仅保留参考 |
| [lib/legacy-modules.ts](lib/legacy-modules.ts) | **旧模块注册表**：定义 36 个 endpoints → modes_id 映射，提供并行获取函数 |
| [app/HomePageClient.tsx](app/HomePageClient.tsx) | **客户端组件**：状态管理（时钟、游戏切换）+ 子组件编排 |
| [app/legacy-shell/page.tsx](app/legacy-shell/page.tsx) | **当前公开入口**：旧站隔离壳页面，使用 `t=3/2/1` 表示台湾/澳门/香港 |
| [app/layout.tsx](app/layout.tsx) | 根布局：导入全局 CSS + 旧站 CSS |

### 样式

| 文件 | 内容 |
|------|------|
| [app/globals.css](app/globals.css) | 补充样式（旧站缺失类名 + 新组件样式） |
| `public/vendor/.../style.css` | 旧站核心样式（`.box`、`.pad`、`.list-title`、`.duilianpt1`、`.zl` 等） |
| `public/vendor/.../style1.css` | 旧站重置样式 |
| `public/vendor/.../style3.css` | 旧站扩展样式 |

### 文档

| 文件 | 内容 |
|------|------|
| [docs/legacy-vs-react-comparison.md](docs/legacy-vs-react-comparison.md) | **旧站 JS vs 新站 React 逐项对比表** |

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

### 场景一：后端有新的 modes_id 数据

1. 在 `lib/legacy-modules.ts` 的 `LEGACY_MODULE_DEFS` 数组中添加一条新记录：
   - 指定 `endpoint`（可复用已有或新建）、`modesId`、`title`、`key`、`limit`
   - 如果旧站 JS 使用了 `web=2`，需要添加 `web: 2`
   - 如果内容格式特殊，添加 `contentTransform`
2. 创建对应的 React 渲染组件
3. 在 `LegacyModuleRegistry.tsx` 中注册 `mechanism_key` → 渲染器映射

### 场景二：需要新的自定义渲染器

1. 对照旧站 JS 文件确定渲染格式（括号样式、颜色、CSS 类名、行布局）
2. 创建 React 组件（参考 `components/LegacyModuleRegistry.tsx` 中的实现）
3. 在注册表中添加映射
4. 在 `globals.css` 中添加缺失的 CSS 类

---

## 与旧站的关系

| 对比项 | 旧站（redirect） | 新 React 版本 |
|--------|-----------------|---------------|
| 数据获取 | 42 个独立 JS × 各自 AJAX | 1 次 site-page API + 批量获取旧模块（6 并发） |
| 模块数量 | 42 个（硬编码 JS） | 36 个（注册表驱动，精确复刻） |
| 渲染方式 | 各 JS 独立 document.write/jQuery | 各 React 组件分别渲染 |
| CSS | 内联 + 外部 CSS | 复用旧站 CSS 文件 + 补充样式 |
| 彩种切换 | 每切换需重新 AJAX | 预加载三种彩种，瞬间切换 |
| 访问路径 | `/vendor/shengshi8800/index.html` | `/legacy-shell?t=3`（当前入口） |
| 维护性 | 每个模块改 CSS/JS | 组件化，每模块独立文件 |

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

启动后请访问：

```text
http://127.0.0.1:3000/legacy-shell?t=3
```

参数映射：

```text
t=3 -> 台湾彩
t=2 -> 澳门彩
t=1 -> 香港六合彩
```

环境变量（`frontend/.env.local`）：

```
LOTTERY_BACKEND_BASE_URL=http://127.0.0.1:8000/api
LOTTERY_SITE_ID=1
```
