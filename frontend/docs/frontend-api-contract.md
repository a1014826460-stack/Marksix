# 前端 API 接口文档

## 1. 文档目标

本文档描述 **`frontend` 当前实际依赖的接口契约**，用于：

- 前后端联调
- 旧站兼容接口维护
- 后端字段调整前的影响评估
- 新同事接手时快速理解数据流

本文档分为两层：

1. **浏览器 / 前端可直接调用的 Next.js 接口**
2. **这些接口向 Python 后端发起的上游请求契约**

注意：

- 本文档基于当前仓库实现整理，不是抽象设计稿。
- 若代码与文档冲突，以代码为准，并应同步修正文档。
- 旧站兼容接口 `GET /api/kaijiang/*` 的目标是“稳定复刻旧站 JS 所需格式”，不是提供新的通用领域模型。

---

## 2. 总体架构

```text
浏览器 / Client
  -> Next.js Route Handler（frontend/app/api/*）
  -> Python Backend（backend/src/app.py）
  -> PostgreSQL / SQLite 兼容数据源
```

当前前端存在两类数据链路：

- **新站主数据链路**
  - `frontend/lib/backend-api.ts`
  - 直接请求 Python 后端 `/api/public/site-page`、`/api/public/latest-draw`、`/api/predict/*`
- **旧站兼容链路**
  - `frontend/app/api/kaijiang/[[...path]]/route.ts`
  - 对 `/api/legacy/module-rows` 做二次适配，输出旧 JS 期望的数据格式

---

## 3. 通用约定

### 3.1 编码与协议

- 协议：HTTP/HTTPS
- 编码：`UTF-8`
- 数据格式：`application/json`
- 前端代理层默认使用 `cache: "no-store"`

### 3.2 错误响应约定

Next.js 代理层的错误响应统一倾向于以下结构：

```json
{
  "error": "错误标识或错误消息",
  "detail": "详细错误信息"
}
```

常见状态码：

- `400`：上游参数错误
- `404`：资源不存在
- `500`：前端代理内部处理失败
- `502`：前端代理请求后端失败

### 3.3 枚举约定

#### `type` / `lottery_type`

| 值 | 含义 |
|---|---|
| `1` | 香港六合彩 |
| `2` | 澳门六合彩 |
| `3` | 台湾六合彩 |

#### `web`

- 旧站兼容接口大多数场景使用 `web=4`
- 个别历史脚本存在其他 `web` 来源，但当前前端主路径默认仍以 `4` 为主

---

## 4. 浏览器可调用的前端接口

## 4.1 `GET /api/lottery-data`

### 说明

获取“新站页面主数据”。  
该接口是 Python 后端 `/api/public/site-page` 的代理层。

### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `site_id` | number | 否 | `LOTTERY_SITE_ID` 或 `1` | 站点 ID |
| `history_limit` | number | 否 | `8` | 每个模块返回的历史行数 |

### 请求头行为

该接口会尝试从以下请求头推导 `domain` 并转发给后端：

- `x-forwarded-host`
- `host`

若域名为 `localhost` / `127.0.0.1`，则不参与站点匹配。

### 成功响应

响应结构等价于 `PublicSitePageData`：

```ts
type PublicSitePageData = {
  site: {
    id: number
    name: string
    domain: string
    lottery_type_id: number
    lottery_name?: string
    enabled: boolean
    start_web_id: number
    end_web_id: number
    announcement?: string
    notes?: string
  }
  draw: {
    current_issue: string
    result_balls: Array<{
      value: string
      zodiac: string
      color: "red" | "blue" | "green"
    }>
    special_ball: {
      value: string
      zodiac: string
      color: "red" | "blue" | "green"
    } | null
  }
  modules: Array<{
    id: number
    mechanism_key: string
    title: string
    default_modes_id: number
    default_table: string
    sort_order: number
    status: boolean
    cssClass?: string
    history: Array<{
      issue: string
      year: string
      term: string
      prediction_text: string
      result_text: string
      is_opened: boolean
      is_correct: boolean | null
      source_web_id: number | null
      raw: Record<string, unknown>
    }>
  }>
}
```

### 失败响应

```json
{
  "error": "Failed to load site data from backend",
  "detail": "..."
}
```

### 维护建议

- 后端若新增 `modules[].history[].raw` 子字段，不会破坏前端。
- 后端若修改 `site`、`draw`、`modules` 顶层字段名，会直接影响首页 SSR 和客户端渲染。

---

## 4.2 `GET /api/latest-draw`

### 说明

获取指定彩种的最新开奖信息。  
该接口是 Python 后端 `/api/public/latest-draw` 的透明代理。

### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `lottery_type` | `1 \| 2 \| 3` | 否 | `1` | 彩种类型 |

### 成功响应示例

```json
{
  "current_issue": "202646",
  "result_balls": [
    { "value": "08", "zodiac": "猪", "color": "red" },
    { "value": "28", "zodiac": "兔", "color": "green" }
  ],
  "special_ball": {
    "value": "09",
    "zodiac": "狗",
    "color": "blue"
  }
}
```

### 失败响应

```json
{
  "error": "后端请求失败",
  "detail": "..."
}
```

---

## 4.3 `GET /api/post/getList`

### 说明

旧站图片列表兼容接口。  
该接口代理 Python 后端 `/api/legacy/post-list`，并对 `cover_image` 做 URL 规范化。

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 否 | 旧站彩种参数 |
| `web` | string | 否 | 旧站站点参数 |
| `pc` | string | 否 | 旧站端类型参数 |

### 成功响应

```json
{
  "data": [
    {
      "id": 1,
      "title": "示例",
      "file_name": "a.png",
      "storage_path": "uploads/...",
      "legacy_upload_path": "....",
      "cover_image": "/uploads/image/20250322/a.png",
      "mime_type": "image/png",
      "file_size": 12345,
      "sort_order": 1,
      "enabled": true
    }
  ]
}
```

### 约束

- `cover_image` 在前端响应中始终为站内路径或空字符串
- 其余字段基本透传后端

---

## 4.4 `GET /api/kaijiang/{endpoint}`

### 说明

这是最重要的**旧站兼容接口集合**。  
路由文件：`frontend/app/api/kaijiang/[[...path]]/route.ts`

该接口族的职责不是返回统一领域模型，而是：

- 接收旧站 JS 风格的查询参数
- 从 Python 后端 `/api/legacy/module-rows` 取原始数据
- 适配成旧脚本真正消费的返回格式

### 通用查询参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `web` | string / number | 否 | 旧站来源标识，常用 `4` |
| `type` | string / number | 否 | 彩种类型，`1/2/3` |
| `num` | string / number | 否 | 某些 endpoint 的玩法分支参数 |

### 通用响应包裹

除 `curTerm` 外，大多数接口返回：

```json
{
  "data": [...]
}
```

### 通用基础字段

绝大多数行对象都至少包含以下字段：

```ts
type LegacyBaseRow = {
  term: string
  year: string
  res_code: string
  res_sx: string
}
```

### 行结构别名

为方便后端对接，文档中使用下列结构别名：

```ts
type ContentRow = LegacyBaseRow & {
  content: string
}

type RangeContentRow = LegacyBaseRow & {
  start: string
  end: string
  content: string
}

type HeiBaiRow = LegacyBaseRow & {
  hei: string
  bai: string
}

type TitleContentJiexiRow = LegacyBaseRow & {
  title: string
  content: string
  jiexi: string
  image_url?: string
  x7m14?: string
}

type XiaoPairRow = LegacyBaseRow & {
  xiao_1: string
  xiao_2: string
}

type DaTouRow = LegacyBaseRow & {
  content: string
  tou: string
}

type QinQiRow = LegacyBaseRow & {
  title: string
  content: string
}

type QxBmRow = LegacyBaseRow & {
  xiao: string
  code: string
  ping: string
}

type JuziRow = LegacyBaseRow & {
  title: string
  content: string
}
```

### endpoint 对照表

| endpoint | modes_id | `num` 用法 | 返回行结构 | 说明 |
|---|---:|---|---|---|
| `curTerm` | - | 无 | `data` 为对象 | 返回当前期数信息 |
| `getPingte` | `43` / `56` | `num=2` -> `43`，否则 `56` | `ContentRow` | 平特接口 |
| `getSanqiXiao4new` | `197` | 无 | `RangeContentRow` | 三期类范围数据 |
| `sbzt` | `38` | 无 | `ContentRow` | 双波中特 |
| `getXiaoma` | `246` | 常传 `7` | `ContentRow` | `content` 为 JSON 字符串数组：`["牛|06", ...]` |
| `getHbnx` | `45` | 无 | `HeiBaiRow` | 黑白无双 |
| `getYjzy` | `50` | 无 | `TitleContentJiexiRow` | 一句真言 |
| `lxzt` | `46` | 无 | `ContentRow` |六肖中特 |
| `getHllx` | `8` | 可传，当前路由忽略 | `ContentRow` | 三色生肖 |
| `getDxzt` | `57` | 无 | `ContentRow` | 大小中特 |
| `getDxztt1` | `108` | 无 | `DaTouRow` | 大小中特带头数 |
| `getJyzt` | `63` | 无 | `ContentRow` | 家野中特 |
| `ptyw` | `54` | 无 | `ContentRow` | 平特一尾 |
| `getXmx1` | `151` | 可传，当前路由忽略 | `ContentRow` | 九肖一码 |
| `getTou` | `12` | 可传，当前路由忽略 | `ContentRow` | 三头中特 |
| `getXingte` | `53` | 无 | `ContentRow` | 兴特 |
| `sxbm` | `51` | 无 | `ContentRow` | 四肖八码，`content` 已转为旧脚本消费格式 |
| `danshuang` | `28` | 无 | `ContentRow` | 单双 |
| `dssx` | `31` | 无 | `XiaoPairRow` | 单双四肖 |
| `getDsnx` | `31` | 无 | `XiaoPairRow` | `dssx` 同源别名 |
| `getCodeDuan` | `65` | 无 | `ContentRow` | 特码段数 |
| `getJuzi` | `62` / `68` | `num=yqmtm` -> `68`，否则 `62` | `JuziRow` | 欲钱解特 / 欲钱买特码 |
| `getShaXiao` | `42` | 无 | `ContentRow` | 杀三肖 |
| `getCode` | `34` | 常传 `24` | `ContentRow` | 经典 24 码，`content` 应为 24 个号码逗号串 |
| `qqsh` | `26` | 无 | `QinQiRow` | 琴棋书画 |
| `getShaBanbo` | `58` | 无 | `ContentRow` | 绝杀半波 |
| `getShaWei` | `20` | 常传 `1` | `ContentRow` | 绝杀一尾 |
| `getSzxj` | `52` | 无 | `TitleContentJiexiRow` | 四字玄机 |
| `getDjym` | `59` | 无 | `TitleContentJiexiRow` | 独家幽默 |
| `getSjsx` | `61` | 无 | `ContentRow` | 四季三肖 |
| `getRccx` | `3` | 常传 `2` | `ContentRow` | 肉菜草肖 |
| `yyptj` | `244` | 无 | `ContentRow` | 一语平特佳 |
| `wxzt` | `48` | 无 | `ContentRow` | 五肖中特 |
| `getWei` | `2` | 常传 `6` | `ContentRow` | 六尾中特 |
| `jxzt` | `49` | 无 | `ContentRow` | 九肖中特 |
| `qxbm` | `246` | 无 | `QxBmRow` | 七肖七码 / 五行八码兼容格式 |
| `getPmxjcz` | `331` | 无 | `TitleContentJiexiRow` | 跑马玄机测字 |

### 特别说明 1：`getXiaoma`

`getXiaoma` 的 `content` 不是普通字符串，而是 **JSON 字符串数组**：

```json
{
  "term": "127",
  "year": "2026",
  "res_code": "06,29,42,13,27,31,36",
  "res_sx": "牛,虎,牛,马,龙,鼠,羊",
  "content": "[\"牛|06\",\"龙|03\",\"鸡|10\",\"猪|08\",\"鼠|07\",\"虎|05\",\"兔|04\"]"
}
```

### 特别说明 2：`qxbm`

`qxbm` 直接返回拆开的字段：

```json
{
  "term": "127",
  "year": "2026",
  "res_code": "06,29,42,13,27,31,36",
  "res_sx": "牛,虎,牛,马,龙,鼠,羊",
  "xiao": "牛,龙,鸡,猪,鼠,虎,兔",
  "code": "06,03,10,08,07,05,04",
  "ping": ""
}
```

### 特别说明 3：`getJuzi`

- `num=juzi1` 或未传：按 `modes_id=62` 处理，主要用于“欲钱解特诗”
- `num=yqmtm`：按 `modes_id=68` 处理，主要用于“欲钱买特码”

### 特别说明 4：兼容兜底

当前 `route.ts` 对以下接口存在**本地兼容兜底逻辑**：

- `getYjzy`
- `getSzxj`
- `getJuzi`
- `getCode`
- `dssx`
- `getDsnx`
- `getXiaoma`
- `qxbm`

兜底来源：

- `backend/data/lottery_modes.sqlite3`
- `text_history_mappings`

目的：

- 当 PostgreSQL 当前行发生字段退化、结构化字段被压扁或文本缺失时，仍尽量输出旧站可渲染的数据格式

建议：

- 这属于**兼容层过渡方案**，不应被后端当成正式长期数据源
- 后端应尽量直接修复 PostgreSQL 主数据结构，逐步减少对本地 SQLite 回填的依赖

---

## 4.5 `GET /api/predict/{mechanism}`

### 说明

预测接口代理。  
当前实现会把请求转发给 Python 后端 `/api/predict/{mechanism}`。

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `res_code` | string | 否 | 预测基准号码 |
| `content` | string | 否 | 指定预测内容 |
| `source_table` | string | 否 | 指定源表 |
| `target_hit_rate` | number | 否 | 目标命中率 |
| `lottery_type` | number | 否 | 可选，传入后端做开奖可见性校验 |
| `year` | string | 否 | 可选，期号年份 |
| `term` | string | 否 | 可选，期号 term |
| `web` | string | 否 | 可选，默认 `4` |

### 请求头

| 请求头 | 必填 | 说明 |
|---|---|---|
| `Authorization` | 否 | 若前端调用方传入，则原样转发到后端 |

### 响应

当前已冻结为稳定协议：

```ts
type PredictionApiResponse = {
  ok: true
  protocol_version: string
  generated_at: string
  data: {
    mechanism: {
      key: string
      title: string
      default_modes_id: number | null
      default_table: string
      resolved_labels: string[]
    }
    source: {
      db_path: string
      table: string
      source_modes_id: number | null
      source_table_title: string
      history_count: number | null
    }
    request: {
      res_code: string | null
      content: string | null
      source_table: string | null
      target_hit_rate: number | null
      lottery_type: number | string | null
      year: number | string | null
      term: number | string | null
      web: number | string | null
    }
    context: {
      latest_term: number | string | null
      latest_outcome: string | null
      draw: {
        result_visibility: "visible" | "hidden" | "unknown"
        is_opened?: boolean | null
        issue?: string
        reason: string
      }
    }
    prediction: {
      labels: string[]
      content: unknown
      content_json: string
      display_text: string
    }
    backtest: Record<string, unknown>
    explanation: string[]
    warning: string
  }
  legacy: Record<string, unknown>
}
```

### 维护建议

- 新调用方只应依赖 `data`
- `legacy` 仅作为过渡兼容字段保留
- 若同时传入 `lottery_type + year + term`，后端会检查 `public.lottery_draws`
- 当该期 `is_opened = 0` 时，后端会忽略传入的 `res_code`

---

## 4.6 `POST /api/predict/{mechanism}`

### 请求体

支持 snake_case 与 camelCase 混用，前端会统一转发为 snake_case：

```json
{
  "res_code": "01,02,03,04,05,06,07",
  "content": "虎羊",
  "source_table": "mode_payload_43",
  "target_hit_rate": 0.8,
  "lottery_type": 3,
  "year": "2026",
  "term": "127",
  "web": "4"
}
```

也兼容：

```json
{
  "resCode": "01,02,03,04,05,06,07",
  "sourceTable": "mode_payload_43",
  "targetHitRate": 0.8,
  "lotteryType": 3,
  "year": "2026",
  "term": "127",
  "web": "4"
}
```

### 响应

- 与 `GET /api/predict/{mechanism}` 相同，透传后端结果

### 失败响应

```json
{
  "error": "预测结果生成失败",
  "detail": "..."
}
```

---

## 4.7 `GET /uploads/image/{bucket}/{filename}`

### 说明

旧站图片兼容静态路由，不是 JSON API，但前端对接旧图资源时会用到。

### 路由约束

- 当前仅允许 `bucket = 20250322`
- `filename` 只能是纯文件名，不能带路径穿越

### 成功响应

- 返回图片二进制流
- `Content-Type` 根据扩展名推断
- `Cache-Control: no-store`

### 失败响应

- `404 Not Found`

---

## 5. 前端到 Python 后端的上游契约

| 前端入口 | 上游后端接口 | 方法 | 说明 |
|---|---|---|---|
| `/api/lottery-data` | `/api/public/site-page` | `GET` | 主页面数据 |
| `/api/latest-draw` | `/api/public/latest-draw` | `GET` | 最新开奖 |
| `/api/post/getList` | `/api/legacy/post-list` | `GET` | 旧站图片列表 |
| `/api/kaijiang/curTerm` | `/api/legacy/current-term` | `GET` | 当前期数 |
| `/api/kaijiang/*` | `/api/legacy/module-rows` | `GET` | 旧站模块原始行 |
| `/api/predict/{mechanism}` | `/api/predict/{mechanism}` | `POST` | 预测执行 |

### 5.1 `/api/public/site-page`

后端应提供：

- `site`
- `draw`
- `modules`

并与 `frontend/lib/site-page.ts` 中的 `PublicSitePageData` 保持兼容。

后端当前实际规则：

- `modules[].history` 优先来自 `created.mode_payload_{mode_id}`
- 若 `created` 行数不足 `history_limit`，后端会自动回退补充 `public.mode_payload_{mode_id}`
- 模块历史会按站点 `lottery_type_id` 与 `start_web_id/end_web_id` 过滤
- `draw` 不再从任意 `mode_payload_*` 推导，而是直接读取 `public.lottery_draws`
- 若某期在 `lottery_draws` 中 `is_opened = 0`，则 `modules[].history[].result_text` 必须返回 `待开奖`
- 后端可额外返回 `history_schema`、`history_sources` 这类调试 / 运维字段，前端应忽略未知字段

### 5.2 `/api/public/latest-draw`

后端应提供：

```ts
{
  current_issue: string
  result_balls: Array<{
    value: string
    zodiac: string
    color: "red" | "blue" | "green"
  }>
  special_ball: {
    value: string
    zodiac: string
    color: "red" | "blue" | "green"
  } | null
}
```

后端当前实际规则：

- 只返回 `public.lottery_draws` 中最近一期 `is_opened = 1` 的开奖数据
- `numbers` 结合 `public.fixed_data` 转成 `value + zodiac + color`
- 即使存在未开奖但已抓到 `numbers` 的行，也不能提前返回给前端

### 5.3 `/api/legacy/current-term`

后端当前返回示例：

```json
{
  "lottery_type_id": 1,
  "term": "48",
  "issue": "202648",
  "next_term": "49"
}
```

前端兼容层实际只强依赖：

- `term`
- `issue`
- `next_term`

### 5.4 `/api/legacy/post-list`

后端当前返回：

```ts
{
  data: Array<{
    id: number
    title?: string
    file_name: string
    storage_path: string
    legacy_upload_path: string
    cover_image: string
    mime_type: string
    file_size: number
    sort_order: number
    enabled: boolean
  }>
}
```

### 5.5 `/api/legacy/module-rows`

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `modes_id` | number | 是 | 玩法表 ID |
| `limit` | number | 否 | 返回行数 |
| `web` | number | 否 | 站点来源过滤 |
| `type` | number | 否 | 彩种过滤 |

### 成功响应

```ts
{
  modes_id: number
  title: string
  table_name: string
  record_count?: number
  rows: Array<Record<string, unknown>>
}
```

### 后端维护要求

- 优先使用 `created.mode_payload_{mode_id}` 的数据；不足时再回退 `public.mode_payload_{mode_id}`
- 若 `created` 与 `public` 同一期同时存在，必须优先保留 `created`
- `rows` 中必须保留原表真实字段，不要强行做统一文本化
- 兼容层依赖 `title`、`content`、`jiexi`、`xiao_1`、`xiao_2`、`hei`、`bai`、`xiao`、`code` 等原始列
- 若某列本身是结构化玩法列，应优先保留原多列结构，而不是压成单列 JSON 字符串
- 开奖字段必须以 `public.lottery_draws` 为准
- 若某期在 `lottery_draws` 中 `is_opened = 0`，该行返回时必须隐藏 `res_code`、`res_sx`、`res_color`

### 5.6 `/api/predict/{mechanism}`

后端当前由前端统一以 `POST` 调用，前端转发请求体为：

```json
{
  "res_code": "01,02,03,04,05,06,07",
  "content": "虎羊",
  "source_table": "mode_payload_43",
  "target_hit_rate": 0.8,
  "lottery_type": 3,
  "year": "2026",
  "term": "127",
  "web": "4"
}
```

后端维护要求：

- 稳定协议字段为 `ok`、`protocol_version`、`generated_at`、`data`
- `legacy` 仅保留给过渡兼容，不应作为新接口契约
- 若请求带 `lottery_type + year + term`，后端必须校验 `public.lottery_draws`
- 当对应期次 `is_opened = 0` 时，后端必须忽略传入的 `res_code`

---

## 6. 当前代码中的关键契约文件

| 文件 | 作用 |
|---|---|
| `frontend/lib/backend-api.ts` | 前端访问 Python 后端的通用客户端 |
| `frontend/lib/site-page.ts` | `/api/public/site-page` 类型定义 |
| `frontend/lib/api/predictionRunner.ts` | `/api/predict/{mechanism}` 参数解析与转发 |
| `frontend/app/api/lottery-data/route.ts` | 主页面数据代理 |
| `frontend/app/api/latest-draw/route.ts` | 最新开奖代理 |
| `frontend/app/api/post/getList/route.ts` | 图片列表兼容代理 |
| `frontend/app/api/kaijiang/[[...path]]/route.ts` | 旧站兼容接口核心适配层 |
| `frontend/lib/legacy-sqlite-fallback.ts` | 旧站文本/结构退化时的本地兜底读取 |

---

## 7. 已知约束与注意事项

### 7.1 `/api/lottery-data` 与首页 SSR 不是同一条调用路径

- 首页 `app/page.tsx` 当前通过 `backendFetchJson()` **直接请求** Python 后端
- `/api/lottery-data` 是一个额外的前端代理接口，适合浏览器端或调试使用

因此：

- 若仅修改 `/api/lottery-data`，首页 SSR 不一定跟着变化
- 若修改 `frontend/lib/backend-api.ts` 或后端 `/api/public/site-page`，首页 SSR 会直接受影响

### 7.2 旧站兼容接口不是统一 schema

`/api/kaijiang/*` 明确是“按 endpoint 输出不同格式”的兼容层。  
后端不要尝试把这些 endpoint 再统一为一个扁平结构，否则旧 JS / 旧样式 React 复刻层会再次错乱。

### 7.3 兼容兜底应逐步下线

`legacy-sqlite-fallback.ts` 的存在，是为了在 PostgreSQL 历史数据修复完成前保证页面不崩。  
长期目标仍应是：

- PostgreSQL 主表结构正确
- `/api/legacy/module-rows` 原始字段完整
- 前端不再依赖本地 SQLite 回填

---

## 8. 变更清单

后端改接口前，请至少检查以下问题：

1. 是否修改了 `/api/public/site-page` 的顶层字段名
2. 是否修改了 `modules[].history[]` 的基础字段
3. 是否把旧站玩法的多列结构压成了单列字符串
4. 是否改变了 `type=1/2/3` 的语义
5. 是否改变了 `res_code`、`res_sx` 的存储格式
6. 是否新增了需要前端兼容层识别的新 `modes_id`

前端改兼容层前，请至少检查以下问题：

1. 是否仍保持旧 JS 期望的字段名
2. 是否错误地把某个 endpoint 输出统一成了 `content`
3. 是否误把本地 SQLite 兜底写成了正式主逻辑
4. 是否同步更新了本文档

---

## 9. 推荐协作方式

若后端准备调整接口，建议按以下顺序协作：

1. 先在本文档中更新拟变更契约
2. 后端给出真实响应样例
3. 前端对照 `site-page.ts` 或 `route.ts` 做兼容评估
4. 完成联调后再删除旧兼容分支

这样可以最大程度避免“字段看似没变，但旧站兼容渲染已坏”的问题。
