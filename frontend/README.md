# 六合彩前端站点

## 项目概述

基于 Next.js 16（React 19 / TypeScript）的六合彩论坛公开站点。核心功能是**渲染预测号码模块**——展示各种预测算法的历史结果和最新预测。

数据统一从 Python 后端获取，由 React 组件渲染为与旧站视觉一致的页面。同时通过 iframe 隔离兼容旧站 JavaScript 脚本。

### 启动方式

```powershell
# 1. 启动 Python 后端（PostgreSQL）
cd d:\pythonProject\outsource\Liuhecai
python backend/src/app.py --host 127.0.0.1 --port 8000 --db-path "postgresql://postgres:pass@localhost:5432/liuhecai"

# 2. 启动前端站点
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

### 入口说明（2026-05-08 起）

| 访问路径 | 用途 | 状态 |
|----------|------|------|
| `http://127.0.0.1:3000/legacy-shell?t=3` | **主入口** — 旧站兼容壳页面 | **当前使用** |
| `http://127.0.0.1:3000/` | 根路由，自动重定向到 `/legacy-shell?t=3` | **重定向** |
| `/` 原 React 首页 | 已封存 | **废弃** |

查询参数映射：

```
t=3 → 台湾彩 (type=3)
t=2 → 澳门彩 (type=2)
t=1 → 香港六合彩 (type=1)
```

### 环境变量

`frontend/.env.local`：

```
LOTTERY_BACKEND_BASE_URL=http://127.0.0.1:8000/api
LOTTERY_SITE_ID=1
```

---

## 架构与数据流

### 整体数据流

```
浏览器 / Client
  │
  ├─ GET /legacy-shell?t=3
  │   └─ LegacyShellPage (Client Component)
  │       └─ LegacyModulesFrame (iframe)
  │           └─ /vendor/shengshi8800/embed.html
  │               └─ 旧站 JS 脚本
  │                   └─ fetch('/api/kaijiang/*')
  │                       └─ Next.js Route Handler
  │                           └─ Python Backend /api/legacy/module-rows
  │                               └─ PostgreSQL
  │
  ├─ GET /history
  │   └─ DrawHistoryPage (Client Component)
  │       └─ fetch('/api/draw-history')
  │           └─ Python Backend /api/public/draw-history
  │               └─ PostgreSQL
  │
  ├─ GET /api/lottery-data
  │   └─ Next.js Route Handler
  │       └─ Python Backend /api/public/site-page
  │           └─ PostgreSQL
  │
  └─ GET/POST /api/predict/:mechanism
      └─ Next.js Route Handler
          └─ Python Backend /api/predict/:mechanism
              └─ PostgreSQL
```

### 两条数据链路

| 链路 | 说明 | 关键文件 |
|------|------|----------|
| **新站主数据链路** | 直接请求 Python 后端 API | `lib/backend-api.ts` |
| **旧站兼容链路** | 通过 Next.js 代理层转换旧 JS 期望格式 | `app/api/kaijiang/[[...path]]/route.ts` |

### 彩种切换

三种彩种数据在 `fetchAllLegacyModulesByGame()` 中按需加载，切换不产生额外网络请求。

```
modulesByGame = {
  taiwan:    [PublicModule[], ...],   // type=3
  macau:     [PublicModule[], ...],   // type=2
  hongkong:  [PublicModule[], ...],   // type=1
}
```

---

## 目录结构与文件说明

```
frontend/
├── app/                              # Next.js App Router 页面与 API 路由
│   ├── layout.tsx                    # 根布局：导入 globals.css + 旧站 CSS 链接
│   ├── globals.css                   # 补充样式（旧站缺失类名 + 组件样式，~969 行）
│   ├── page.tsx                      # 根路由：纯重定向 → /legacy-shell?t=3
│   ├── HomePageClient.tsx            # [已废弃] React 客户端页面组件（仅被 _archived 引用）
│   │
│   ├── legacy-shell/                 # 当前主入口
│   │   └── page.tsx                  # LegacyShellPage — 旧站隔离壳（iframe 模式）
│   │
│   ├── history/                      # 开奖历史页
│   │   └── page.tsx                  # DrawHistoryPage — 完整历史记录（分页/筛选/排序）
│   │
│   ├── _archived/                    # === 已封存 ===
│   │   └── root-home-page.tsx        # 原 React 首页 SSR 实现（2026-05-08 封存，仅保留参考）
│   │
│   └── api/                          # Next.js API Route Handlers
│       ├── lottery-data/route.ts     # GET  /api/lottery-data           → Python /api/public/site-page
│       ├── latest-draw/route.ts      # GET  /api/latest-draw            → Python /api/public/latest-draw
│       ├── draw-history/route.ts     # GET  /api/draw-history           → Python /api/public/draw-history
│       ├── predict/[mechanism]/route.ts  # GET|POST /api/predict/:mechanism → Python /api/predict/:mechanism
│       ├── kaijiang/[[...path]]/route.ts # GET /api/kaijiang/*          → Python /api/legacy/module-rows
│       ├── post/getList/route.ts     # GET  /api/post/getList           → Python /api/legacy/post-list
│       └── uploads/image/[...]/route.ts  # GET /uploads/image/20250322/:file  → 图片静态服务
│
├── components/                       # React 组件
│   ├── Header.tsx                    # 顶部：日期/农历/时钟/头图
│   ├── NavTabs.tsx                   # 导航栏（含推广资料表）
│   ├── LotteryResult.tsx             # 开奖结果 iframe 嵌入 + 彩种切换
│   ├── PreResultBlocks.tsx           # 三核心模块：两肖平特王 / 三期中特 / 双波中特
│   ├── PredictionModules.tsx         # 通用预测模块渲染器 + MODULE_FORMATS 配置
│   ├── LegacyModuleRegistry.tsx      # 22 个自定义渲染器注册表（按 mechanism_key 分发）
│   ├── LegacyModulesFrame.tsx        # 旧站 JS 的 iframe 沙箱（postMessage 通信）
│   ├── InfoCard.tsx                  # 信息卡片渲染
│   ├── RecordRow.tsx                 # 单行预测记录渲染
│   ├── Footer.tsx                    # 页脚（免责声明）
│   ├── theme-provider.tsx            # next-themes Provider 封装
│   └── ui/                           # === 57 个 shadcn/ui 组件（当前未使用） ===
│       └── *.tsx                     # 按钮/卡片/对话框/表单等全套 UI 组件库
│
├── lib/                              # 共享工具库
│   ├── backend-api.ts                # 核心：Python 后端 API 客户端（backendFetchJson）
│   ├── site-page.ts                  # TypeScript 类型定义（PublicSitePageData 等）
│   ├── lotteryData.ts                # 前端数据类型 + 数据转换函数 + Mock 数据
│   ├── legacy-modules.ts             # 36 个旧站模块定义（LEGACY_MODULE_DEFS）+ 批量获取
│   ├── draw-history.ts               # 开奖历史类型 + 规范化函数
│   ├── legacy-sqlite-fallback.ts     # [已废弃] SQLite 本地回退（所有函数返回 null）
│   ├── utils.ts                      # cn() — Tailwind 类名合并工具
│   └── api/
│       └── predictionRunner.ts       # 预测接口参数解析 + runPrediction()
│
├── hooks/                            # React Hooks
│   ├── use-mobile.ts                 # useIsMobile() — 响应式断点检测
│   └── use-toast.ts                  # Toast 通知系统（reducer 模式）
│
├── styles/
│   └── globals.css                   # Tailwind v4 + shadcn/ui 设计系统 CSS 变量
│
├── public/                           # 静态资源
│   ├── vendor/shengshi8800/          # 旧站静态文件（CSS/JS/图片/HTML）
│   │   ├── embed.html                # iframe 入口页面
│   │   ├── index.html                # 原始旧站首页
│   │   ├── kj/local.html             # 开奖结果 iframe 页
│   │   └── static/                   # CSS/JS/图片
│   ├── vendor/admin-history/         # 历史页静态文件
│   └── cj/term.js                    # 当前期数数据
│
├── docs/                             # 内部文档
│   ├── frontend-api-contract.md      # API 接口契约完整文档
│   ├── legacy-vs-react-comparison.md # 旧站 JS vs React 逐项对比
│   ├── legacy-js-shell-plan.md       # iframe 隔离架构设计说明
│   └── draw-history-page-implementation.md # 开奖历史页实现说明
│
└── 配置文件
    ├── package.json                  # 依赖（Next.js 16 / React 19 / shadcn/ui / recharts 等）
    ├── tsconfig.json                 # TypeScript 配置（strict / path alias @/*）
    ├── next.config.mjs               # Next.js 配置（standalone / 图片 / 缓存）
    ├── components.json               # shadcn/ui 配置
    ├── postcss.config.mjs            # PostCSS（Tailwind v4）
    └── .env.local                    # 环境变量
```

---

## 废弃 / 已封存功能标识

| 文件/目录 | 状态 | 封存日期 | 说明 |
|-----------|------|----------|------|
| `app/_archived/root-home-page.tsx` | **已封存** | 2026-05-08 | 原 React SSR 首页，不再使用。保留仅作参考。 |
| `app/HomePageClient.tsx` | **已废弃** | 2026-05-08 | 仅被 `_archived` 引用，不再作为任何活跃路由的渲染入口。 |
| `lib/legacy-sqlite-fallback.ts` | **已废弃** | — | SQLite 本地回退逻辑，所有函数返回 `null`。请勿新增依赖。 |
| `components/ui/` (57个文件) | **未使用** | — | shadcn/ui 组件库，当前主页面不使用。可能用于未来后台功能。 |
| `public/vendor/shengshi8800/index.html` | **旧站原始页** | — | 仅保留作为对比参考，不要将其作为开发或测试入口。 |
| `app/page.tsx` (原首页逻辑) | **已替换** | 2026-05-08 | 现仅为重定向逻辑，原始内容在 `_archived/root-home-page.tsx`。 |

### 修改注意事项

1. **不要恢复 `_archived` 中的代码**。如需重新启用 React SSR 首页，先评估与 `legacy-shell` 的兼容性。
2. **不要向 `legacy-sqlite-fallback.ts` 添加新函数**。数据来源唯一应为 PostgreSQL。
3. **不要使用 `components/ui/` 来渲染预测模块**。预测模块必须使用旧站 CSS 类名（`.duilianpt1` / `.bzlx` / `.sqbk` 等）保持视觉一致。

---

## 预测号码模块列表

页面展示的所有预测模块均来自旧站兼容端点（`/api/legacy/module-rows`），共 **36 个模块 × 3 种彩种**。

> **核心原则**：不再使用通用渲染器。每个模块根据其 `mechanism_key` 分发到对应的自定义渲染器，确保 100% 匹配旧站的括号样式、颜色方案、CSS 类名和行布局。

### 模块 → 渲染器对照表

| 渲染类 | CSS 类名 | 包含模块 | 实现状态 |
|--------|---------|---------|---------|
| 标准 duilianpt1 + 括号配置 | `duilianpt1` | ptyx, lxzt, 3tou, xingte, ptyw, shawei, dxzt, jyzt | 部分实现 |
| Ptyx11 表格 | `ptyx11` | wxzt(48), jxzt(49), dxztt1(108), rccx(3), sjsx(61) | 已实现 |
| 三列 bzlx 表格 | `bzlx` | 6wei(2) | 已实现 |
| 四列 sqbk 表格 | `sqbk` | dssx/ds4x(31) | 已实现 |
| 自定义多行/期 | `qxtable` | 7x7m(246), 8jxym(151), wxbm(246), qqsh(26) | 已实现 |
| 自定义复杂模块 | 多种 | pmxjcz(331) | 已实现 |
| 文本模块 | `legacy-module-text` | yjzy(50), yqmtm(68), szxj(52), djym(59), yyptj(244), qqsh(26), juzi(62) | 已实现 |
| 特殊逻辑 | 多种 | shaxiao(42反向), shabanbo(58正向), tema(34双行) | 已实现 |
| 核心 3 模块 | `duilianpt1` | pt2xiao(43), 3zxt(197), hllx(38) | 已实现(PreResultBlocks) |

详细 42 模块逐项对比见 [docs/legacy-vs-react-comparison.md](docs/legacy-vs-react-comparison.md)。

### 添加新预测模块

1. 在 `lib/legacy-modules.ts` 的 `LEGACY_MODULE_DEFS` 数组中添加新记录（指定 endpoint / modesId / title / key / limit）
2. 如需特殊渲染，创建自定义渲染器
3. 在 `LegacyModuleRegistry.tsx` 中注册 `mechanism_key` → 渲染器映射
4. 如需新 CSS 类，在 `app/globals.css` 中添加

---

## API 接口规范

### 通用约定

- 协议：HTTP/HTTPS
- 编码：`UTF-8`
- 数据格式：`application/json`
- 缓存：前端代理层默认 `cache: "no-store"`
- 错误响应统一格式：

```json
{
  "error": "错误标识",
  "detail": "详细错误信息"
}
```

常见状态码：

| 状态码 | 含义 |
|--------|------|
| `400` | 上游参数错误 |
| `404` | 资源不存在 |
| `500` | 前端代理内部处理失败 |
| `502` | 前端代理请求后端失败 |

### 枚举约定

| 参数 | 值 | 含义 |
|------|-----|------|
| `type` / `lottery_type` | `1` | 香港六合彩 |
| | `2` | 澳门六合彩 |
| | `3` | 台湾六合彩 |
| `web` | `4` | 旧站默认来源标识 |

---

### 接口一：GET /api/lottery-data

**说明**：获取新站页面主数据。代理 Python 后端 `/api/public/site-page`。

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `site_id` | number | 否 | `1` | 站点 ID |
| `history_limit` | number | 否 | `8` | 每个模块返回的历史行数 |

**请求头行为**：自动从 `x-forwarded-host` 或 `host` 推导 `domain` 转发给后端。若域名为 `localhost` / `127.0.0.1`，则不参与站点匹配。

**成功响应** (200)：

```json
{
  "site": {
    "id": 1,
    "name": "台湾六合彩论坛",
    "domain": "shengshi8800.com",
    "lottery_type_id": 3,
    "lottery_name": "台湾彩",
    "enabled": true,
    "start_web_id": 1,
    "end_web_id": 100,
    "announcement": null,
    "notes": null
  },
  "draw": {
    "current_issue": "2026127",
    "result_balls": [
      { "value": "08", "zodiac": "猪", "color": "red" },
      { "value": "28", "zodiac": "兔", "color": "green" },
      { "value": "42", "zodiac": "牛", "color": "blue" }
    ],
    "special_ball": { "value": "09", "zodiac": "狗", "color": "blue" }
  },
  "modules": [
    {
      "id": 1,
      "mechanism_key": "pt2xiao",
      "title": "两肖平特王",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "sort_order": 1,
      "status": true,
      "history": [
        {
          "issue": "2026127",
          "year": "2026",
          "term": "127",
          "prediction_text": "虎羊",
          "result_text": "开：牛",
          "is_opened": true,
          "is_correct": false,
          "source_web_id": 4,
          "raw": {}
        }
      ]
    }
  ]
}
```

**失败响应** (502)：

```json
{ "error": "Failed to load site data from backend", "detail": "..." }
```

---

### 接口二：GET /api/latest-draw

**说明**：获取指定彩种的最新开奖信息。代理 Python 后端 `/api/public/latest-draw`。

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `lottery_type` | `1 \| 2 \| 3` | 否 | `1` | 彩种类型 |

**成功响应** (200)：

```json
{
  "current_issue": "2026127",
  "result_balls": [
    { "value": "08", "zodiac": "猪", "color": "red" },
    { "value": "28", "zodiac": "兔", "color": "green" }
  ],
  "special_ball": { "value": "09", "zodiac": "狗", "color": "blue" }
}
```

**失败响应** (502)：

```json
{ "error": "后端请求失败", "detail": "..." }
```

---

### 接口三：GET /api/draw-history

**说明**：获取开奖历史记录，支持分页/筛选/排序。首先尝试 Python 后端 `/api/public/draw-history`，失败时回退到本地 HTML 快照解析（仅 2025/2026 年份）。

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `lottery_type` | `1 \| 2 \| 3` | 否 | `3` | 彩种类型 |
| `year` | number | 否 | 当前年份 | 筛选年份 |
| `sort` | `"l" \| "d"` | 否 | `"l"` | 排序：l=落球顺序，d=大小顺序 |
| `page` | number | 否 | `1` | 页码（从1开始） |
| `page_size` | number | 否 | `20` | 每页条数（最大 50） |

**成功响应** (200)：

```json
{
  "lottery_type": 3,
  "lottery_name": "台湾彩",
  "year": 2026,
  "sort": "l",
  "years": [2026, 2025],
  "page": 1,
  "page_size": 20,
  "total": 120,
  "total_pages": 6,
  "items": [
    {
      "issue": "2026127",
      "date": "2026年05月08日",
      "title": "台湾彩开奖记录 2026年05月08日 第2026127期",
      "balls": [
        { "value": "08", "color": "red", "zodiac": "猪", "element": "金", "wave": "红波", "size": "小", "oddEven": "单", "combinedOddEven": "合单", "animalType": "家畜", "sumOddEven": "和单" }
      ],
      "specialBall": { "value": "09", "color": "blue", "zodiac": "狗" }
    }
  ]
}
```

**失败响应** (200 + 空列表)：回退快照解析失败时返回空列表。

---

### 接口四：GET/POST /api/predict/:mechanism

**说明**：预测执行接口。代理 Python 后端 `/api/predict/:mechanism`。

**GET 查询参数 / POST 请求体**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `res_code` | string | 否 | — | 预测基准号码（逗号分隔，如 `"01,02,03,04,05,06,07"`） |
| `content` | string | 否 | — | 指定预测内容（如 `"虎羊"`） |
| `source_table` | string | 否 | — | 指定源表（如 `"mode_payload_43"`） |
| `target_hit_rate` | number | 否 | — | 目标命中率 |
| `lottery_type` | number | 否 | — | 彩种类型，传入后做开奖可见性校验 |
| `year` | string | 否 | — | 期号年份 |
| `term` | string | 否 | — | 期号 term |
| `web` | string | 否 | `"4"` | 旧站来源标识 |

POST 请求体支持 snake_case 与 camelCase 混用：
```json
{
  "res_code": "01,02,03,04,05,06,07",
  "source_table": "mode_payload_43",
  "target_hit_rate": 0.8,
  "lottery_type": 3
}
```

**请求头**：

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `Authorization` | 否 | 若传入，原样转发到后端 |

**成功响应** (200)：

```json
{
  "ok": true,
  "protocol_version": "1.0",
  "generated_at": "2026-05-09T10:00:00Z",
  "data": {
    "mechanism": {
      "key": "pt2xiao",
      "title": "两肖平特王",
      "default_modes_id": 43,
      "default_table": "mode_payload_43",
      "resolved_labels": ["虎", "羊"]
    },
    "source": {
      "db_path": "postgresql://...",
      "table": "mode_payload_43",
      "source_modes_id": 43,
      "source_table_title": "两肖平特王",
      "history_count": 100
    },
    "request": {
      "res_code": null,
      "content": null,
      "source_table": null,
      "target_hit_rate": null,
      "lottery_type": null,
      "year": null,
      "term": null,
      "web": "4"
    },
    "context": {
      "latest_term": 127,
      "latest_outcome": "08,28,42",
      "draw": {
        "result_visibility": "visible",
        "is_opened": true,
        "issue": "2026127",
        "reason": "is_opened=1"
      }
    },
    "prediction": {
      "labels": ["虎", "羊"],
      "content": null,
      "content_json": "",
      "display_text": "虎,羊"
    },
    "backtest": {},
    "explanation": [],
    "warning": ""
  },
  "legacy": {}
}
```

**失败响应** (500)：

```json
{ "error": "预测结果生成失败", "detail": "..." }
```

---

### 接口五：GET /api/kaijiang/:endpoint

**说明**：旧站兼容接口集合。将 Python 后端 `/api/legacy/module-rows` 的原始数据适配为旧 JS 脚本期望的格式。这是兼容层核心接口，不要把这些 endpoint 统一为扁平结构。

**通用查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `web` | string/number | 否 | 旧站来源标识，常用 `4` |
| `type` | string/number | 否 | 彩种类型 `1/2/3` |
| `num` | string/number | 否 | 某些 endpoint 的玩法分支参数 |

**通用响应格式**（除 `curTerm` 外）：

```json
{ "data": [...] }
```

**通用基础行字段**（每行至少包含）：

```json
{
  "term": "127",
  "year": "2026",
  "res_code": "06,29,42,13,27,31,36",
  "res_sx": "牛,虎,牛,马,龙,鼠,羊"
}
```

**Endpoint 对照表**：

| endpoint | modes_id | `num` 用法 | 返回行结构 |
|----------|----------|-----------|-----------|
| `curTerm` | — | 无 | 对象（含 term/issue/next_term） |
| `getPingte` | 43/56 | `num=2`→43, 否则→56 | content 文本行 |
| `getSanqiXiao4new` | 197 | 无 | start/end/content 范围行 |
| `sbzt` | 38 | 无 | content 文本行 |
| `getXiaoma` | 44 | 常传 `7` | content 为 JSON 数组 |
| `getHbnx` | 45 | 无 | hei/bai 行 |
| `getYjzy` | 50 | 无 | title/content/jiexi 行 |
| `lxzt` | 46 | 无 | content 文本行 |
| `getHllx` | 8 | 忽略 | content 文本行 |
| `getDxzt` | 57 | 无 | content 文本行 |
| `getDxztt1` | 108 | 无 | content/tou 行 |
| `getJyzt` | 63 | 无 | content 文本行 |
| `ptyw` | 54 | 无 | content 文本行 |
| `getXmx1` | 151 | 忽略 | content 文本行 |
| `getTou` | 12 | 忽略 | content 文本行 |
| `getXingte` | 53 | 无 | content 文本行 |
| `sxbm` | 51 | 无 | content 文本行 |
| `danshuang` | 28 | 无 | content 文本行 |
| `dssx` / `getDsnx` | 31 | 无 | xiao_1/xiao_2 行 |
| `getCodeDuan` | 65 | 无 | content 文本行 |
| `getJuzi` | 62/68 | `num=yqmtm`→68, 否则→62 | title/content 行 |
| `getShaXiao` | 42 | 无 | content 文本行 |
| `getCode` | 34 | 常传 `24` | content 为 24 码逗号串 |
| `qqsh` | 26 | 无 | title/content 行 |
| `getShaBanbo` | 58 | 无 | content 文本行 |
| `getShaWei` | 20 | 常传 `1` | content 文本行 |
| `getSzxj` | 52 | 无 | title/content/jiexi 行 |
| `getDjym` | 59 | 无 | title/content/jiexi 行 |
| `getSjsx` | 61 | 无 | content 文本行 |
| `getRccx` | 3 | 常传 `2` | content 文本行 |
| `yyptj` | 244 | 无 | content 文本行 |
| `wxzt` | 48 | 无 | content 文本行 |
| `getWei` | 2 | 常传 `6` | content 文本行 |
| `jxzt` | 49 | 无 | content 文本行 |
| `qxbm` | 44 | 无 | xiao/code/ping 行 |
| `getPmxjcz` | 331 | 无 | title/content/jiexi 行 |

---

### 接口六：GET /api/post/getList

**说明**：旧站图片列表兼容接口。代理 Python 后端 `/api/legacy/post-list`。

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 否 | 旧站彩种参数 |
| `web` | string | 否 | 旧站站点参数 |
| `pc` | string | 否 | 旧站端类型参数 |

**成功响应** (200)：

```json
{
  "data": [
    {
      "id": 1,
      "title": "示例",
      "file_name": "a.png",
      "storage_path": "uploads/...",
      "legacy_upload_path": "...",
      "cover_image": "/uploads/image/20250322/a.png",
      "mime_type": "image/png",
      "file_size": 12345,
      "sort_order": 1,
      "enabled": true
    }
  ]
}
```

---

### 接口七：GET /uploads/image/:bucket/:filename

**说明**：旧站图片静态服务，非 JSON API。

**路由约束**：
- 仅允许 `bucket = 20250322`
- `filename` 不能带路径穿越

**成功响应** (200)：图片二进制流，`Content-Type` 根据扩展名推断，`Cache-Control: no-store`

**失败响应** (404)：文件不存在

---

## 前端到 Python 后端的上游契约

| 前端入口 | 上游后端接口 | 方法 | 说明 |
|----------|-------------|------|------|
| `/api/lottery-data` | `/api/public/site-page` | GET | 主页面数据 |
| `/api/latest-draw` | `/api/public/latest-draw` | GET | 最新开奖 |
| `/api/draw-history` | `/api/public/draw-history` | GET | 开奖历史 |
| `/api/predict/:mechanism` | `/api/predict/:mechanism` | POST | 预测执行 |
| `/api/kaijiang/curTerm` | `/api/legacy/current-term` | GET | 当前期数 |
| `/api/kaijiang/*` | `/api/legacy/module-rows` | GET | 旧站模块原始行 |
| `/api/post/getList` | `/api/legacy/post-list` | GET | 旧站图片列表 |

### 后端维护要求

1. **保持字段名兼容**：不要修改 `site`、`draw`、`modules` 顶层字段名
2. **保留多列结构**：旧站玩法的多列结构（`hei/bai`、`xiao_1/xiao_2`、`xiao/code/ping`）不要压成单列 JSON 字符串
3. **开奖字段以 `public.lottery_draws` 为准**：`is_opened = 0` 时必须隐藏 `res_code`/`res_sx`/`res_color`
4. **created 表优先**：`modules.history` 优先取 `created.mode_payload_{mode_id}`，不足时回退 `public.mode_payload_{mode_id}`
5. **新增字段前向兼容**：后端新增 `raw` 子字段不会破坏前端，但修改顶层字段名会

---

## 给 AI 修复者的指导

### 修复前必读

1. **先读 `docs/frontend-api-contract.md`** — 理解完整 API 契约
2. **先读 `docs/legacy-js-shell-plan.md`** — 理解为什么用 iframe 隔离旧站 JS
3. **先读 `docs/legacy-vs-react-comparison.md`** — 理解每个模块的渲染要求

### 常见问题排查路径

| 症状 | 排查起点 |
|------|----------|
| 页面白屏 / 模块不显示 | 检查 Python 后端是否在 `127.0.0.1:8000` 运行，检查 `.env.local` 配置 |
| 旧站模块渲染错误 | 检查 `LegacyModuleRegistry.tsx` 中的渲染器映射是否正确 |
| API 返回 502 | 检查后端 `/api/public/site-page` 是否正常响应 |
| iframe 加载空白 | 检查 `public/vendor/shengshi8800/embed.html` 是否存在 |
| 开奖结果不对 | 检查 `public.lottery_draws` 中 `is_opened` 字段 |
| 历史页无数据 | 检查 `public/cj/Zz_admin.shengshi8800.com/` 下快照文件是否存在 |
| 样式错乱 | 检查 `app/globals.css` 和 `public/vendor/shengshi8800/static/css/` 是否被修改 |

### 修改约束

- **禁止**：修改 `lib/legacy-sqlite-fallback.ts` 让它返回真实数据（该文件已弃用）
- **禁止**：修改 `_archived/` 目录下的代码（已封存）
- **禁止**：在 `api/kaijiang/[[...path]]/route.ts` 中将不同 endpoint 统一为相同输出格式
- **允许**：在 `LegacyModuleRegistry.tsx` 中新增自定义渲染器
- **允许**：在 `app/globals.css` 中添加缺失的 CSS 类名
- **允许**：修改 `lib/legacy-modules.ts` 中的 `LEGACY_MODULE_DEFS`

### 后端改接口前检查清单

1. 是否修改了 `/api/public/site-page` 的顶层字段名？
2. 是否修改了 `modules[].history[]` 的基础字段？
3. 是否把旧站玩法的多列结构压成了单列字符串？
4. 是否改变了 `type=1/2/3` 的语义？
5. 是否改变了 `res_code`、`res_sx` 的存储格式？
6. 是否新增了需要前端兼容层识别的新 `modes_id`？

---

## 测试

### API 测试

```powershell
# 启动后端和前端后运行
cd frontend
npx ts-node --project tsconfig.json test/api-test.ts
```

或使用脚本：

```powershell
node test/run-api-test.js
```

API 测试覆盖所有 7 个前端接口的所有参数组合，详见 [test/api-test.ts](test/api-test.ts)。

---

## 推荐协作方式

若后端准备调整接口：

1. 先在 `docs/frontend-api-contract.md` 中更新拟变更契约
2. 后端给出真实响应样例
3. 前端对照 `lib/site-page.ts` 或对应 `route.ts` 做兼容评估
4. 完成联调后再删除旧兼容分支
