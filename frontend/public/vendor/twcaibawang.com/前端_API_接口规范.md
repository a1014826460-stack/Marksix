# 前端 API 接口规范文档：Zz_xgttc-108.com

> 基于上传包 `Zz_xgttc-108.com.zip` 与当前项目 `frontend.zip` 扫描生成。本文档用于指导 Next.js 前端适配、后端接口实现、旧站 vendor 静态脚本兼容，以及 Claude Code / 开发人员联调排错。

## 1. 项目结论

该上传包不是标准 Next.js 项目，而是一个 **vendor 静态站**：

```text
index.html
wy.html
wylhc.html
11169.html ~ 11184.html
4859.html / 4873.html ~ 4879.html
static/css/*
static/js/common.js
static/js/data.js
static/js/jquery*.js
static/image|picture|file/*
```

和 `Zz_www.twsaimahui.com.zip` 不同，本项目中没有发现大量 `/api/kaijiang/*` AJAX 调用。真实运行时依赖主要是：

1. `wy.html` 每 2 秒请求 `wy.json?t=random` 获取当前开奖。
2. `wylhc.html` 通过 `<script src="/index/ajax/ttklsjl?...">` 加载开奖记录 JSONP。
3. `index.html` 主体内容、高手资料、绝杀资料、图片资料大多是硬编码 HTML/图片。
4. `index.html` 还引用了上传包未包含的远程脚本 `https://xgttc-108.com/index_files/pub.js` 与 `https://xgttc-108.com/index_files/gg.js`。

因此本项目的前端 API 适配重点不是补齐 40 多个 `/api/kaijiang/*`，而是优先兼容：

```text
/wy.json
/index/ajax/ttklsjl
/index/index/history.html 或 wylhc.html
/index_files/pub.js
/index_files/gg.js
远程 uploads 图片资源本地化或代理
```

## 2. 站点识别与运行时配置

| 项目 | 扫描结果 | 说明 |
| --- | --- | --- |
| 站点域名 | `xgttc-108.com` | 从包名、外部脚本与页面 title 推断 |
| 页面名称 | `香港天天彩` | title、开奖 iframe、开奖记录页均使用该名称 |
| 旧站彩种 | 倾向 `香港彩` | 页面文案是“香港天天彩”；最终应以数据库站点配置为准 |
| `web_id` | 静态包中未出现 | 不能臆造；接入后端预测 API 前必须从 `managed_sites` / 站点域名解析得到真实 `web_id` |
| 当前开奖入口 | `wy.html` | 被 `index.html` 以 iframe 引入 |
| 历史开奖入口 | `wylhc.html` | `wy.html` 中“历史记录”链接指向该页 |
| 主要 JS 配置 | `static/js/data.js` | 包含波色映射、2020~2028 年号码生肖映射 |
| 外部脚本 | `/index_files/pub.js`, `/index_files/gg.js` | 上传包未包含，应本地化、补 mock 或移除依赖 |

### 2.1 多站点接入原则

- 有域名环境：按 `Host` / `x-forwarded-host` 解析站点。
- 无域名本地环境：使用默认站点配置兜底。
- 调用预测或模块数据接口时必须使用站点真实 `web_id`，不要把 `managed_sites.id` 当成 `web_id`。
- 页面文案可显示“香港天天彩”，但接口请求应使用数据库中的 `lottery_type_id` 与 `web_id`。

## 3. 旧站真实依赖接口清单

| 方法 | 路径 | 来源文件 | 用途 | 返回形式 |
| --- | --- | --- | --- | --- |
| GET | /wy.json?t={random} | wy.html | 当前开奖快照；页面每 2 秒轮询一次 | JSON 数组，前端只读取第 1 项 res[0] |
| GET | /index/ajax/ttklsjl?year={YYYY}&v={timestamp} | wylhc.html | 年度开奖记录；通过 script 标签加载 | JavaScript/JSONP，必须定义全局 historyAO |
| GET | /index_files/pub.js | index.html | 外部公告/站点配置脚本，上传包未包含 | JavaScript，可能定义 jy/pt 等全局变量 |
| GET | /index_files/gg.js | index.html | 外部广告/投注脚本，上传包未包含 | JavaScript，可能定义弹窗/跳转变量 |
| GET | /index/index/history.html | index.html | 历史记录导航旧链接 | HTML 页面；当前包实际包含 wylhc.html 可作为替代 |

## 4. 当前开奖接口：`GET /wy.json`

### 4.1 旧站调用方式

`wy.html` 中逻辑如下：

```js
$(function () {
  getKaijiangApi();
  setInterval("getKaijiangApi()", 2000);
});

function getKaijiangApi() {
  $.get('wy.json?t=' + Math.random(), function (res) {
    renderother(res[0]);
    renderball(res[0]);
  });
}
```

### 4.2 请求规范

| 项目 | 值 |
| --- | --- |
| Method | `GET` |
| Path | `/wy.json` |
| Query | `t`，随机数，仅用于防缓存，可忽略 |
| Cache | 必须 `no-store` 或短缓存；旧页面 2 秒轮询 |
| Content-Type | `application/json; charset=utf-8` |

### 4.3 响应结构

旧页面要求返回 **数组**，并只读取第一项：

```json
[
  {
    "expect": "2026125",
    "openCode": "01,02,03,04,05,06,07",
    "zodiac": "蛇,龙,兔,虎,牛,鼠,猪",
    "wave": "red,blue,green,red,blue,green,red",
    "wuxin": "金,木,水,火,土,金,木",
    "nextexpect": "2026126",
    "nextTime": "2026-05-21 21:30:00"
  }
]
```

### 4.4 字段定义

| 字段 | 类型 | 必填 | 说明 | 前端使用位置 |
| --- | --- | --- | --- | --- |
| `expect` | string | 是 | 当前开奖期号 | `#q` |
| `openCode` | string | 是 | 7 个号码 CSV，建议保留前导 0，例如 `01,02,...,49` | 渲染 6 个正码 + 1 个特码 |
| `zodiac` | string | 是 | 7 个生肖 CSV | 每个号码下方显示 `生肖/五行` |
| `wave` | string | 是 | 7 个波色 CSV，值必须是 `red/blue/green` | 决定球背景 `r.png/g.png/b.png` |
| `wuxin` | string | 是 | 7 个五行 CSV | 每个号码下方显示 |
| `nextexpect` | string | 是 | 下期期号 | `#nextQiShu` |
| `nextTime` | string | 是 | 下期开奖时间，格式建议 `YYYY-MM-DD HH:mm:ss` | 倒计时、下期日期、星期 |

### 4.5 渲染规则

- `openCode/zodiac/wave/wuxin` 都应包含 7 项。
- 第 7 项是特码。
- `wave` 只识别 `blue`、`green`、`red`；其他值会使用默认灰色图，且当前包没有提供 `hui.png`，因此不建议返回其他值。
- 如果号码不在 `01`~`49`，前端会显示“官网正在搅珠中”这 7 个字中的对应字符，表示开奖中。
- 繁体生肖 `龍/馬/雞/豬` 会被前端转换成简体 `龙/马/鸡/猪`，后端也可以直接返回简体。

### 4.6 建议 Next 兼容实现

如果保留旧 `wy.html`，建议新增：

```text
frontend/app/wy.json/route.ts
```

由该 route 聚合当前已有接口：

```text
/api/latest-draw?lottery_type=1
/api/next-draw-deadline?lottery_type=1
```

并转换成旧页面所需数组结构。若不保留 iframe，建议直接用当前项目的 `LotteryResult` 组件替代 `wy.html`。

## 5. 历史开奖 JSONP 接口：`GET /index/ajax/ttklsjl`

### 5.1 旧站调用方式

`wylhc.html` 动态插入 script：

```js
var year = getParams('year') || new Date().getFullYear();
var historyJsKj466 = document.createElement("script");
historyJsKj466.onload = startAmKaijiangjilu;
historyJsKj466.src = '/index/ajax/ttklsjl?year=' + year + '&v=' + Date.now();
document.body.appendChild(historyJsKj466);
```

脚本加载完成后，页面读取全局变量：

```js
aoMenRecord = historyAO["data"];
var nowyear = historyAO["year"];
```

### 5.2 请求规范

| 项目 | 值 |
| --- | --- |
| Method | `GET` |
| Path | `/index/ajax/ttklsjl` |
| Query | `year`：年份；`v`：时间戳防缓存 |
| Content-Type | `application/javascript; charset=utf-8` |
| 返回格式 | JavaScript 脚本，不是纯 JSON |

### 5.3 响应结构

必须定义全局变量 `historyAO`：

```js
var historyAO = {
  "year": 2026,
  "data": [
    {
      "issue": "125",
      "openTime": "2026-05-20 21:30:00",
      "openCode": "01,02,03,04,05,06,07"
    }
  ]
};
```

### 5.4 字段定义

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `historyAO.year` | number/string | 是 | 当前返回数据所属年份 |
| `historyAO.data` | array | 是 | 开奖历史列表，建议按最新期在前排序 |
| `data[].issue` | string | 是 | 期号，不需要带“期”字 |
| `data[].openTime` | string | 是 | 开奖时间，页面会取前 10 位作为日期，并用它判断生肖年份 |
| `data[].openCode` | string | 是 | 7 个号码 CSV，页面根据号码和 `static/js/data.js` 自行计算生肖/波色 |

### 5.5 与当前 Next 接口的对应关系

当前项目已有：

```text
GET /api/draw-history?lottery_type=1&year=2026&sort=l&page=1&page_size=50
```

推荐两种改造方式：

1. **保留旧 `wylhc.html`**：新增兼容 route `/index/ajax/ttklsjl`，内部调用 `/api/draw-history`，再输出 `var historyAO = ...;`。
2. **重写历史页**：把 `wylhc.html` 改为 React 页面，直接请求 `/api/draw-history`，不再使用 JSONP。

## 6. 当前 Next.js 前端 API 层规范

上传包本身没有 Next API Route，但当前项目 `frontend.zip` 已有以下接口，可作为新站适配的标准接口层：

| 方法 | 路径 | 参数 | 用途 |
| --- | --- | --- | --- |
| GET | /api/lottery-data | site_id?, history_limit? | 聚合站点信息、最新开奖、预测模块数据；Next 转发后端 /api/public/site-page |
| GET | /api/latest-draw | lottery_type? | 最新开奖；Next 转发后端 /api/public/latest-draw |
| GET | /api/next-draw-deadline | lottery_type? | 下期开奖时间/服务器时间；Next 转发后端 /api/public/next-draw-deadline |
| GET | /api/draw-history | lottery_type/type?, year?, sort?, page?, page_size/limit? | 开奖记录；Next 转发后端 /api/public/draw-history，失败时可快照兜底 |
| GET | /api/post/getList | web?, type?, pc? | 旧站图片/帖子列表；Next 转发后端 /api/legacy/post-list |
| GET/POST | /api/predict/[mechanism] | mechanism + res_code/content/source_table/target_hit_rate/lottery_type/year/term/web | 统一预测生成代理；Next 调用后端 /api/predict/:mechanism |
| GET | /api/kaijiang/[[...path]] | web?, type?, num? | 兼容旧站 /api/kaijiang/* 模块；当前 xgttc 静态包没有直接调用这些端点 |

### 6.1 `/api/lottery-data` 响应结构

用于 React 版本首页一次性加载站点数据、开奖数据、预测模块数据：

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
    result_balls: Array<{ value: string; zodiac: string; color: "red" | "blue" | "green" }>
    special_ball: { value: string; zodiac: string; color: "red" | "blue" | "green" } | null
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

### 6.2 `/api/draw-history` 响应结构

```ts
type DrawHistoryResponse = {
  lottery_type: 1 | 2 | 3
  lottery_name: string
  year: number
  sort: "l" | "d"
  years: number[]
  page: number
  page_size: number
  total: number
  total_pages: number
  items: Array<{
    issue: string
    date: string
    title: string
    balls: Array<DrawHistoryBall>
    specialBall?: DrawHistoryBall
  }>
}
```

其中：

```ts
type DrawHistoryBall = {
  value: string
  color: "red" | "blue" | "green" | string
  zodiac: string
  element: string
  wave?: string
  size?: string
  oddEven?: string
  combinedOddEven?: string
  animalType?: string
  sumOddEven?: string
}
```

### 6.3 `/api/kaijiang/[[...path]]` 当前已支持的旧站端点

当前项目已经支持下列旧站兼容 endpoint，但本次 `Zz_xgttc-108.com.zip` 没有直接调用这些路径。如果后续把静态 HTML 模块改造成动态模块，可优先复用这些端点或直接使用 `/api/lottery-data`。

```text
curTerm, getPingte, getSanqiXiao4new, sbzt, getXiaoma, getHbnx, getYjzy, lxzt, getHllx, getDxzt, getDxztt1, getJyzt, ptyw, getXmx1, getTou, getXingte, sxbm, danshuang, dssx/getDsnx, getCodeDuan, getJuzi, getShaXiao, getCode, qqsh, getShaBanbo, getShaWei, getSzxj, getDjym, getSjsx, getRccx, yyptj, wxzt, getWei, jxzt, qxbm, getPmxjcz
```

## 7. 首页静态模块与 API 改造建议

`index.html` 中大多数内容是静态写死，不是通过接口渲染。扫描到的主要页面模块如下：

| 模块 | 位置 | 当前数据来源 | 说明 |
| --- | --- | --- | --- |
| 开奖 iframe | index.html → wy.html | wy.json | 显示当前期开奖、倒计时、历史记录入口 |
| 开奖记录页 | wylhc.html | /index/ajax/ttklsjl | 按年份加载历史开奖并在前端计算生肖/波色 |
| 五肖五码 | index.html | 静态 HTML | 125/124/123 等期次写死在页面中 |
| 平特一肖 | #ptyx | 静态 HTML / 可改造为预测模块 | 展示平特预测历史 |
| 平特一尾 | #ptyw | 静态 HTML / 可改造为预测模块 | 展示尾数预测历史 |
| 大小单双 | #dxds | 静态 HTML / 可改造为预测模块 | 展示单双大小预测历史 |
| 双波 | #sbzt | 静态 HTML / 可改造为预测模块 | 展示双波预测历史 |
| 天地两肖/天地中特 | #tdzt / #tdsx | 静态 HTML / 可改造为预测模块 | 展示天地肖预测历史 |
| 琴棋书画 | #qqsh | 静态 HTML / 可改造为预测模块 | 展示琴棋书画预测历史 |
| 一肖一码 | #ayxym | 静态 HTML / 可改造为预测模块 | 公开一肖一码区域 |
| 高手榜单 | #gslist + 11169~11184.html | 静态 HTML 详情页 | 文章/公式详情页，不是 AJAX |
| 绝杀榜 | #jsb + 4873~4879.html | 静态 HTML 详情页 | 绝杀公式详情页，不是 AJAX |
| 精品图纸 | #liuhetuku + static/file/static/picture | 静态图片/本地资源 + 部分远程 uploads | 图库图片列表 |

### 7.1 推荐改造策略

| 场景 | 推荐方案 | 原因 |
| --- | --- | --- |
| 快速还原页面 | 保留 `index.html + 静态详情页`，只补 `/wy.json` 与 `/index/ajax/ttklsjl` | 改动最小，页面能跑起来 |
| 接入真实开奖 | 用 `/api/latest-draw` + `/api/next-draw-deadline` 生成 `/wy.json` | 对旧 iframe 兼容 |
| 接入真实历史 | 用 `/api/draw-history` 生成 `historyAO` JSONP | 对 `wylhc.html` 兼容 |
| 接入预测模块 | 用 `/api/lottery-data` 或 `/api/kaijiang/*` 映射模块 | 避免继续硬编码 125/124/123 期 |
| 多站点复用 | 建 Next shell + vendor 静态资源，站点由 domain/web_id 决定 | 符合多站点隔离规则 |

## 8. 高手/绝杀详情页清单

这些页面都是本地静态 HTML，没有 AJAX。可以作为文章详情页静态资源保留；若后续后台可编辑，则建议设计文章 API。

| 文件 | 标题/模块 |
| --- | --- |
| 11169.html | 逢买必中 |
| 11170.html | 四头必中 |
| 11171.html | 家禽野兽 |
| 11172.html | 天地+2肖 |
| 11173.html | 稳料四肖中 |
| 11174.html | 合数大小 |
| 11175.html | 5尾中特 |
| 11176.html | 精准五行 |
| 11177.html | 一波中特 |
| 11178.html | 合数单双 |
| 11179.html | 琴棋书画 |
| 11180.html | 平特③肖连 |
| 11181.html | 6尾中特 |
| 11182.html | 三头中特 |
| 11183.html | 三行中特 |
| 11184.html | 一句中特 |
| 4873.html | 绝杀1头 |
| 4874.html | 绝杀1肖 |
| 4875.html | 绝杀1波 |
| 4876.html | 绝杀1尾 |
| 4877.html | 稳杀十码 |
| 4878.html | 稳杀2肖 |
| 4879.html | 杀平2码 |
| 4859.html | 旧一期绝杀1头 |

### 8.1 建议文章 API

如果要把这些详情页改成后台管理内容，建议新增文章列表与详情接口：

```text
GET /api/vendor/articles?site_id={site_id}&category={category}&term={term}
GET /api/vendor/articles/{slug}
```

列表响应：

```json
{
  "data": [
    {
      "id": 11169,
      "slug": "11169",
      "title": "香港天天彩【逢买必中】公式",
      "term": "2026125",
      "category": "高手资料",
      "href": "11169.html",
      "updated_at": "2026-05-20T00:00:00+08:00"
    }
  ]
}
```

详情响应：

```json
{
  "id": 11169,
  "slug": "11169",
  "title": "香港天天彩【逢买必中】公式",
  "html": "<div>...</div>",
  "text": "2026125期 逢买必中 ...",
  "source_file": "11169.html"
}
```

## 9. 静态资源与远程资源规范

### 9.1 本地资源

| 类型 | 路径 | 用途 |
| --- | --- | --- |
| CSS | `static/css/main.css`, `custom.css`, `style.css`, `nystyle.css` | 首页和详情页样式 |
| 开奖球图片 | `static/image/r.png`, `g.png`, `b.png` | 红波/绿波/蓝波球背景 |
| 首页图片 | `static/picture/*`, `static/file/*` | 图库、广告、资料图片 |
| 生肖/波色映射 | `static/js/data.js` | 历史记录页计算生肖和波色 |

### 9.2 远程资源

| 资源 | 源码位置 | 建议 |
| --- | --- | --- |
| `https://xgttc-108.com/index_files/pub.js` | `index.html` | 上传包未包含。建议拉取本地化，或移除依赖并补齐全局变量 mock。 |
| `https://xgttc-108.com/index_files/gg.js` | `index.html` | 上传包未包含。建议拉取本地化，或用后端公告/广告接口替代。 |
| `http://ht.xgttc-108.com/uploads/...` | `index.html` | 建议改为 HTTPS、本地镜像或通过 Next 静态代理，避免混合内容和防盗链。 |
| `/index_files/bg.jpg` | `index.html` body background | 上传包未包含。建议补到 `public/vendor/xgttc-108/index_files/bg.jpg` 或移除背景。 |

### 9.3 脚本加载顺序风险

`index.html` 当前加载顺序是：

```html
<script src="static/js/common.js"></script>
<script src="static/js/jquery.min.js"></script>
<script src="https://xgttc-108.com/index_files/pub.js"></script>
<script src="https://xgttc-108.com/index_files/gg.js"></script>
```

但 `common.js` 开头就使用了 `$`，后续又使用 `jy.siteid` 和 `pt.link`。因此在标准浏览器中存在风险：

```text
$ is not defined
jy is not defined
pt is not defined
```

建议调整为：

```html
<script src="static/js/jquery.min.js"></script>
<script src="/index_files/pub.js"></script>
<script src="/index_files/gg.js"></script>
<script src="static/js/common.js"></script>
```

或者在 Next shell 中彻底移除 `common.js` 的底部导航/下载栏逻辑，改成 React 组件。

## 10. 后端适配规则

### 10.1 `/wy.json` 适配规则

从后端最新开奖转换为旧格式：

```text
latest_draw.issue/current_issue     → expect
latest_draw.result_balls + special  → openCode / zodiac / wave / wuxin
next_draw.next_issue                → nextexpect
next_draw.next_time                 → nextTime
```

颜色映射：

```text
red   → red
blue  → blue
green → green
红波  → red
蓝波  → blue
绿波  → green
```

号码必须补零：

```text
1 → "01"
9 → "09"
49 → "49"
```

### 10.2 `/index/ajax/ttklsjl` 适配规则

从 `/api/draw-history` 转换为旧 JSONP：

```text
item.issue                         → issue
item.date 或 draw.opened_at         → openTime
balls[0..5] + specialBall.value    → openCode
```

输出必须是 JavaScript：

```js
var historyAO = { year: 2026, data: [...] };
```

### 10.3 静态预测模块适配规则

如果继续保留静态 HTML，则无需预测 API。若要动态化：

1. 先在数据库里用 `public.fetched_mode_records.payload` 找目标 `modes_id` 的真实 payload 形状。
2. 不要凭页面标题直接猜字段。
3. 前端展示字段必须 mirror 存储 payload。
4. 命中判断统一使用 `res_code` 最后一位作为特码；生肖类优先用 `res_sx` 最后一位。
5. 切换彩种时更新数据，不改变 URL。

## 11. 联调示例

### 11.1 当前开奖旧兼容

```bash
curl "http://localhost:3000/wy.json?t=123"
```

期望返回：

```json
[
  {
    "expect": "2026125",
    "openCode": "01,02,03,04,05,06,07",
    "zodiac": "蛇,龙,兔,虎,牛,鼠,猪",
    "wave": "red,blue,green,red,blue,green,red",
    "wuxin": "金,木,水,火,土,金,木",
    "nextexpect": "2026126",
    "nextTime": "2026-05-21 21:30:00"
  }
]
```

### 11.2 历史开奖旧 JSONP

```bash
curl "http://localhost:3000/index/ajax/ttklsjl?year=2026&v=1"
```

期望返回：

```js
var historyAO = {"year":2026,"data":[{"issue":"125","openTime":"2026-05-20 21:30:00","openCode":"01,02,03,04,05,06,07"}]};
```

### 11.3 新式历史开奖

```bash
curl "http://localhost:3000/api/draw-history?lottery_type=1&year=2026&page=1&page_size=20"
```

### 11.4 新式聚合首页

```bash
curl "http://localhost:3000/api/lottery-data?site_id=1&history_limit=8"
```

### 11.5 预测接口

```bash
curl "http://localhost:3000/api/predict/flat_king?lottery_type=1&web=真实web_id&target_hit_rate=0.6"
```

## 12. 错误码与降级策略

| 场景 | HTTP 状态 | 响应/行为 | 说明 |
| --- | --- | --- | --- |
| 后端不可用 | 502 | `{ error, detail }` | Next 代理层返回，前端显示占位或旧静态内容 |
| 当前开奖为空 | 200 | `openCode` 可返回占位或空值 | 旧 `wy.html` 会显示“官网正在搅珠中” |
| 历史年份无数据 | 200 | `var historyAO={year,data:[]};` | 不要返回 404，否则 JSONP onload 后页面会空白 |
| 站点无法解析 | 200/404 | 本地环境使用默认站点，正式环境可 404 | 避免本地 no-domain 调试失败 |
| 远程脚本缺失 | 200 | 提供空 shim | `/index_files/pub.js`、`gg.js` 可以先返回安全空脚本 |

空 shim 示例：

```js
window.jy = window.jy || { siteid: "xgttc-108", cur: "index" };
window.pt = window.pt || { link: "#", name: "" };
```

## 13. 验收清单

| 检查项 | 标准 |
| --- | --- |
| 首页能打开 | `index.html` 或 Next shell 正常渲染，无 `$ is not defined` 阻断 |
| 当前开奖显示 | `wy.html` 或 React 组件显示 7 个球、生肖、五行、倒计时 |
| 历史记录显示 | `wylhc.html?year=2026` 能渲染历史开奖列表 |
| 旧链接可用 | `/index/index/history.html` 要么重定向到 `wylhc.html`，要么重写为 React history 页面 |
| 外部脚本安全 | `pub.js`/`gg.js` 已本地化、shim 或移除，不依赖不可控远程站 |
| 远程图片安全 | `http://ht.xgttc-108.com/uploads` 已本地化或代理为 HTTPS |
| 多站点隔离 | 修改 xgttc 不影响其他 vendor 站点 |
| `web_id` 正确 | 后端预测接口使用真实 `web_id`，不是 `managed_sites.id` |
| payload 对齐 | 预测模块动态化时，字段形状以 `public.fetched_mode_records.payload` 为准 |

## 14. Claude Code 修改建议 Prompt

```text
请在当前 Next.js 前端中为 vendor 站点 Zz_xgttc-108.com 增加旧站兼容层：

1. 不要重写所有静态页面，先保证旧 vendor 能运行。
2. 新增 /wy.json route，内部调用现有 /api/latest-draw 与 /api/next-draw-deadline，输出旧 wy.html 需要的数组结构：expect/openCode/zodiac/wave/wuxin/nextexpect/nextTime。
3. 新增 /index/ajax/ttklsjl route，内部调用 /api/draw-history，输出 application/javascript，定义全局 var historyAO = { year, data }。
4. 将 /index/index/history.html 重定向到 /wylhc.html 或 Next history 页面。
5. 为 /index_files/pub.js 和 /index_files/gg.js 提供本地 shim，避免 common.js 因 jy/pt 缺失报错。
6. 调整静态脚本加载顺序：jquery -> pub.js/gg.js -> common.js；或在 Next shell 中移除 common.js 依赖。
7. 不要把 managed_sites.id 当作 web_id；若需要调用预测接口，必须从域名解析得到真实 web_id。
8. 保持多站点隔离，不要改动其他 vendor 站点的 API shape。
9. 若把首页预测区块动态化，必须先读取 public.fetched_mode_records.payload，并按目标 modes_id 的 payload shape 输出。
10. 完成后执行：npm run build 或 npx tsc --noEmit，并手动验证 /wy.json、/index/ajax/ttklsjl、/api/draw-history。
```
