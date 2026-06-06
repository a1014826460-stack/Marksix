# 台湾创富网前端 API 接口规范

站点基线:
- `site_key=twcf888`
- `site_id=8`
- `web_id=8`
- `lottery_type=3`
- `domain=www.twcf888.com`

模块状态:
- `live_backed`
- `snapshot_only`
- `blocked_requires_backend_work`

## 公共开奖接口

### `GET /api/latest-draw?lottery_type=1|2|3`

参数:
- `lottery_type`: `1=香港`, `2=澳门`, `3=台湾`

返回重点:
- 最新期号
- `res_code / res_sx / res_color`
- 未开奖时不得泄露实际结果字段

### `GET /api/next-draw-deadline?lottery_type=1|2|3`

参数:
- `lottery_type`: `1=香港`, `2=澳门`, `3=台湾`

返回重点:
- `deadline`
- `next_term`

## 兼容层接口

### `GET /wy.json`

用途:
- 旧站脚本兼容入口
- 站点通过 Host / Referer 命中 `twcf888`

返回重点:
- `term`
- `next_time`
- `draw_is_opened`
- 未开奖前不回传真实开奖结果

### `GET /index/ajax/ttklsjl?year=YYYY`

参数:
- `year`: 年份，例如 `2026`

用途:
- 兼容 `kai.html` / 历史数据页

## twcf888 专用接口

### `GET /api/twcf888/site-page?site_id=8&web_id=8&lottery_type=3&history_limit=8`

参数:
- `site_id`: 默认 `8`
- `web_id`: 默认 `8`
- `lottery_type`: 默认 `3`
- `history_limit`: 默认 `8`

返回结构:
- `site`: 站点请求上下文
- `data.site_page`: 共享 `/public/site-page` 返回的数据
- `data.required_mode_ids`: twcf888 当前固定 live mode ids
- `data.blocked_items`: 当前 blocked 栏目名列表
- `data.snapshot_only_items`: 当前 snapshot_only 栏目名列表
- `data.live_backed_articles`: 已接线详情页的 live 数据可用性摘要

当前 `required_mode_ids`:

```text
5, 12, 14, 15, 20, 26, 27, 38, 41, 42, 43, 45, 49, 50, 53, 54, 57, 66, 69, 74, 88, 103, 132, 143, 198, 279, 470, 472, 473, 482, 483
```

### `GET /api/twcf888/homepage-modules?lottery_type=3`

参数:
- `lottery_type`: 默认 `3`

返回结构:
- `site`
- `legend`
- `sections[]`
- `live_mode_summary[]`

`sections[].cards[]` 字段:
- `article_id`
- `title`
- `group`
- `route`
- `mode_id`
- `module_status`
- `data_status`
- `latest_issue`
- `notes`

`data_status` 说明:
- `live_ready`: 已拿到实时历史记录
- `missing_live_data`: blueprint 要求 live，但当前数据缺失
- `snapshot`: 静态快照栏目
- `blocked`: blocked 栏目

### `GET /api/twcf888/article-detail?group=amgst|jsb|jhq|gs&article_id=...&lottery_type=3`

参数:
- `group`: `amgst | jsb | jhq | gs`
- `article_id`: 站内文章 ID
- `lottery_type`: 默认 `3`

返回结构:
- `site`
- `article.id`
- `article.title`
- `article.group`
- `article.modeId`
- `article.moduleStatus`
- `article.sourceKind`
- `article.status`
- `article.notes`
- `article.contentHtml`

`article.status` 说明:
- `ok`: 已使用 live 预测记录渲染
- `fallback_snapshot`: 当前内容来自原站静态快照
- `missing_live_data`: 该栏目应为 live_backed，但当前未取到实时记录

当前新增 live 文章:
- `7623 4行4头`
  使用 `mode 482 + mode 483` 复合渲染。
- `7629 准杀7码`
  使用 `mode 88`，结果口径保持原站 `准 / 错`。
- `7638 精准7尾`
  使用 `mode 74`。

展示约定:
- `黑白中特(mode 45)` 未开奖默认显示白肖。
- `黑白中特(mode 45)` 已开奖后命中哪边就显示哪边。
- `4行4头` 命中头时高亮头，命中行时高亮行，保持原站“命中哪边显示哪边”的展示思路。
- 所有 live 模块在未开奖时都不得泄露 `res_code / res_sx / res_color`。

## 详情页路由

- `/twcf888/amgst/[articleId]`
- `/twcf888/jsb/[articleId]`
- `/twcf888/jhq/[articleId]`
- `/twcf888/gs/[articleId]`

## 接线原则

- 首页 UI、配色、DOM 顺序保持 vendor 原样。
- `pub.js` / `gg.js` 必须走本地兼容路由。
- `kai.html` 继续复用共享开奖实现。
- 彩种切换时，开奖模块与预测模块必须同步切换到同一个 `lottery_type`。
- 对 blocked 项只允许显示缺数或静态快照，不允许假 live 数据。

## 当前仍待业务确认的栏目

- `7636 八肖来财`
- `7637 特码单双`
- `6101 稳料四肖中`
- `6109 6尾中特`
- `2287 绝杀一行`
- `2289 绝杀二尾`
- `2290 绝杀一波`
- `3051 稳中七肖`
- `3053 内幕资料`

这些栏目当前要么仍为 `snapshot_only`，要么仍为 `blocked_requires_backend_work`，后续只能在语义确认后继续 live 化。
# 2026-06-06 更新

- `GET /api/twcf888/article-detail` 当前已确认新增 live 栏目：
  - `6101 稳料四肖中 -> mode 47`
  - `6109 6尾中特 -> mode 2`
- 当前仍未转 live 的栏目：
  - `3051 稳中七肖`
  - `3053 内幕资料`
  - `2287 绝杀一行`
  - `2289 绝杀二尾`
  - `2290 绝杀一波`

# 2026-06-06 更新 (batch 2)

- 全部 remaining blocked/snapshot 栏目批量转 live：
  - `2287 绝杀一行 -> mode 98`
  - `2289 绝杀二尾 -> mode 95`
  - `2290 绝杀一波 -> mode 143`
  - `3051 稳中七肖 -> mode 100`
  - `3053 内幕资料 -> mode 198`
  - `7636 八肖来财 -> mode 180`
  - `7637 特码单双 -> 复合 mode 28(单双) + mode 57(大小)`
  - `3肖防3码 -> mode 226`
  - `18码中特 -> mode 122`
  - `双波10码 -> mode 224`
- 当前仍不是 live 的栏目：
  - `广东5兄弟` (blocked)
  - `官方图库` (snapshot_only，非预测模块)

当前 `required_mode_ids`:

```text
2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 53, 54, 57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 198, 224, 226, 279, 470, 472, 473, 482, 483
```
