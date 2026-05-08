# 开奖历史数据展示页实现说明

## 目标

基于 `frontend/Zz_admin.shengshi8800.com` 中的开奖历史页面快照，在前端项目新增一套同样视觉结构的开奖记录页面，并支持：

- 从开奖结果模块的“查看历史记录”跳转进入。
- 按台湾彩、澳门彩、香港彩筛选开奖记录。
- 按年份筛选开奖记录。
- 保留旧站的展示选项：平码/特码、生肖/五行、波色/大小、单双/合单双、家禽野兽/总和单双。
- 后端 API 未完成时，前端从旧站 HTML 快照解析数据作为临时兜底。

## 已复用的旧站资源

已将旧站静态资源复制到：

```text
frontend/public/vendor/admin-history/static
```

历史页使用以下旧站 CSS，尽量保持原页面视觉：

```text
/vendor/admin-history/static/css/bootstrap.min.css
/vendor/admin-history/static/css/kj.css
/vendor/admin-history/static/css/pintuer.css
/vendor/admin-history/static/css/style1.css
```

旧站原始数据快照仍保留在：

```text
frontend/Zz_admin.shengshi8800.com/history-2_1000555062.html
frontend/Zz_admin.shengshi8800.com/history-2025_2.html
```

## 新增文件

```text
frontend/app/history/page.tsx
frontend/app/api/draw-history/route.ts
frontend/lib/draw-history.ts
frontend/docs/draw-history-page-implementation.md
```

## 页面路由

历史页访问地址：

```text
/history?type=3&year=2026&sort=l&page=1&page_size=20
```

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `type` / `lottery_type` | `1 \| 2 \| 3` | 否 | `1=香港彩`，`2=澳门彩`，`3=台湾彩`，默认 `3` |
| `year` | number | 否 | 年份，默认当前年份 |
| `sort` | `l \| d` | 否 | `l=落球顺序`，`d=大小顺序`，默认 `l` |
| `page` | number | 否 | 当前页码，默认 `1` |
| `page_size` | number | 否 | 每页条数，默认 `20`，前端支持 `10/20/30/50` |

## 跳转规则

开奖结果模块内的“查看历史记录”已改为：

```text
/history?type={lotteryType}
```

也就是：

```text
台湾彩 -> /history?type=3
澳门彩 -> /history?type=2
香港彩 -> /history?type=1
```

实现位置：

```text
frontend/public/vendor/shengshi8800/kj/local.html
```

## 前端 API 代理

前端页面请求：

```text
GET /api/draw-history?lottery_type=3&year=2026&sort=l&page=1&page_size=20
```

该路由会优先请求后端：

```text
GET {LOTTERY_BACKEND_BASE_URL}/public/draw-history?lottery_type=3&year=2026&sort=l&page=1&page_size=20
```

如果后端接口尚未实现或请求失败，前端会解析 `frontend/Zz_admin.shengshi8800.com` 中的 HTML 快照作为兜底数据，便于页面先完整展示。

为避免历史记录一次性加载过多导致卡顿，历史页现在要求分页返回。后端如果暂时未提供分页字段，Next.js 代理会对返回的 `items` 做临时切片兜底，但正式接口建议由后端完成分页查询。

## 后端需要返回的数据结构

建议后端返回：

```json
{
  "lottery_type": 3,
  "lottery_name": "台湾彩",
  "year": 2026,
  "sort": "l",
  "years": [2026, 2025],
  "page": 1,
  "page_size": 20,
  "total": 45,
  "total_pages": 3,
  "items": [
    {
      "issue": "048",
      "date": "2026年05月07日",
      "title": "台湾彩开奖记录 2026年05月07日 第048期",
      "balls": [
        {
          "value": "23",
          "color": "red",
          "zodiac": "猴",
          "element": "木",
          "wave": "红",
          "size": "小",
          "oddEven": "单",
          "combinedOddEven": "合单",
          "animalType": "野兽",
          "sumOddEven": "双"
        }
      ],
      "specialBall": {
        "value": "49",
        "color": "green",
        "zodiac": "马",
        "element": "土",
        "wave": "绿",
        "size": "大",
        "oddEven": "单",
        "combinedOddEven": "合单",
        "animalType": "家禽",
        "sumOddEven": "双"
      }
    }
  ]
}
```

字段约定：

| 字段 | 说明 |
| --- | --- |
| `lottery_type` | `1=香港彩`，`2=澳门彩`，`3=台湾彩` |
| `lottery_name` | 页面展示名称 |
| `year` | 当前返回年份 |
| `sort` | 当前排序方式，`l` 或 `d` |
| `years` | 可选择年份列表 |
| `page` | 当前页码 |
| `page_size` | 每页条数 |
| `total` | 当前筛选条件下的总记录数 |
| `total_pages` | 当前筛选条件下的总页数 |
| `items` | 当前页开奖记录列表，按页面展示顺序返回，不建议一次返回全部历史 |
| `items[].balls` | 6 个普通球 |
| `items[].specialBall` | 特码球 |
| `color` | 建议返回 `red`、`blue`、`green`，前端会映射为旧站球样式 |
| `element` | 五行：金、木、水、火、土 |

## 旧站结构映射

每一期记录仍渲染为旧站相同结构：

```html
<div class="kj-tit">...</div>
<div class="kj-box">
  <ul class="clearfix">
    <li>普通球</li>
    ...
    <li class="kj-jia">+</li>
    <li>特码球</li>
  </ul>
</div>
```

这样可以继续复用 `kj.css` 里的球图、颜色、间距和旧站移动端适配。

## 注意事项

- 当前前端兜底解析只用于后端未完成前的展示验证，正式数据应以后端 `/public/draw-history` 为准。
- 如果后端支持更多年份，只需要在 `years` 中返回，页面会自动显示年份按钮。
- 如果不同彩种的波色、生肖、五行规则由后端计算，前端只负责展示，不再重复推导。
