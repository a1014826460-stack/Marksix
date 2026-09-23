# 开奖与预测资料「更新时效」规格（2026-09-24）

用户要求：**开奖模块与预测资料模块必须准确更新，不得提早、不得延误。**
本文给出每一层的时效预算、实测数据、本轮修掉的延误缺陷，以及"不得提早"的既有保障。

## 1. 修掉的三个真实延误缺陷

### 1.1 Outbox 发布被 30 秒任务周期拖累（最严重）

实测（生产 `publication_outbox`，2026-09-23）：

| 事件 | 产生 → 发布 | 延迟 |
| --- | --- | --- |
| `draw-published:3:2026:266`（台湾彩 266 期） | 22:32:09 → 22:32:39 | **30.91 s** |
| `draw-published:2:2026:266` | — | 28.13 s |
| `draw-refresh:2:2026:265:1` | — | 15.28 s |
| `draw-refresh:1:2026:103:1` | — | 24.80 s |
| `draw-published:3:2026:265` | — | 1.62 s |

原因：开奖事件写入 `publication_outbox` 后，**发布只发生在 `CrawlerScheduler._schedule_task_loop()` 里**，
而该循环的周期是 `crawler.task_poll_interval_seconds`（默认 **30 秒**）。于是公网
`/api/public/latest-draw` 在开奖后最长 30 秒仍返回**上一期**（开奖快照指针还没被改写）。

修复：新增独立的 `_schedule_publication_loop()`，周期
`crawler.publication_poll_interval_seconds`（默认 **1 秒**，且不超过任务周期），
`start()` 时启动、`stop()` 时取消；原任务循环里的 drain 保留为兜底（保持既有顺序契约）。
新增日志 `Publication loop started interval=1s` 与发布审计 `Publication drain: {...}`。

### 1.2 开奖链路缓存 TTL 偏长

| 层 | 原 | 现 | 说明 |
| --- | --- | --- | --- |
| nginx 微缓存（latest-draw / next-draw-deadline / site-links） | 3 s | **1 s** | 仍用 `proxy_cache_lock` 合并瞬时并发；实测同秒第二次请求即 `HIT` |
| nginx `proxy_cache_use_stale`（开奖 tier） | `updating error timeout http_5xx` | **仅 `updating`** | 原来后端故障时会**长期**返回旧开奖；现在只允许"后台更新期间"用一份最多 1 秒旧的副本 |
| Next 进程内缓存（开奖三接口） | 3 s | **1 s** | |
| 共享面板客户端缓存 | 5 s | **3 s** | `DRAW_CACHE_FRESH_MS` |
| python-api 开奖快照指针 TTL | 120 s | **30 s** | 事件正常会立即改写指针；这是"事件丢失"时的兜底上界 |

### 1.3 预测资料的 60 秒级延误

- Next 进程内缓存对预测资料原本统一 **60 秒**：开奖后的"对/错"回填、后台改资料都会改写载荷，
  而这一层只认 URL、不认识失效事件 → 站点最长 60 秒看不到更新。
  现收紧为：`/legacy/module-rows` **10 s**、`/public/site-page` 与 `/vendor/homepage-modules` **30 s**
  （python-api 侧已是事件失效 + KV 读，重建很便宜，所以缩短 TTL 的代价主要是多几次上游请求）。
- 管理台改写/删除预测资料（`mode_payload_*`）原本**没有任何失效钩子**，只能等 300 秒 TTL。
  现于 `routes/admin_payload_routes.py` 的 PUT/PATCH/DELETE 成功后对 1/2/3 三个彩种做粗粒度代际失效
  （管理编辑频率低，粗粒度换取"绝不残留"）。

## 2. 现在的逐层时效预算

### 开奖（`/api/latest-draw` → 面板出号）

| 层 | 失效方式 | 最坏陈旧 |
| --- | --- | --- |
| PostgreSQL 写入 + `publication_outbox` | 开奖路径（爬虫 upsert/立即开盘/自动开盘/台湾精准开奖）都会 `enqueue_opened_draw_publication` | 0 |
| Outbox 发布循环 | 独立 1 秒循环 | **≤1 s** |
| python-api 开奖快照 | 事件改写指针；兜底 TTL 30 s | ≤30 s（正常 ≈1 s） |
| nginx 微缓存 | 1 s TTL + 并发合并 | ≤1 s + 一次上游耗时 |
| Next 进程内缓存 | 1 s TTL | ≤1 s |
| 面板客户端 | 3 s 新鲜窗口 + 开奖窗口每 5 s 轮询 | ≤3 s |
| **合计（正常路径）** | | **≈2～6 s** |
| 面板逐球揭示 | `REVEAL_INTERVAL_MS = 25000`，开奖时间后每 25 秒亮一个球 | **最长约 175 s 才显示完 7 个球（产品既定行为）** |

### 预测资料（`/api/kaijiang/*`、`prediction-modules`、`homepage-modules`、`site-page`）

| 层 | 失效方式 | 最坏陈旧 |
| --- | --- | --- |
| python-api 预测快照 | 代际计数：开奖事件、每日生成完成、管理台改开奖号码、管理台改预测资料 | ≈0（事件触发重建，实测 bump 后首次请求 57 ms、随后 2 ms 命中） |
| python-api 快照兜底 TTL | 300 s（聚合类）/ 同 | ≤300 s（事件丢失时） |
| nginx 微缓存 | 5 s（站点 draw）/ 20 s（预测聚合与 `/api/kaijiang/*`） | ≤20 s |
| Next 进程内缓存 | 10 s（`module-rows`）/ 30 s（聚合） | ≤30 s |
| 客户端 sessionStorage | 预测 60 s 新鲜窗口（网络失败时回退 15 分钟 / 24 小时） | ≤60 s |
| **合计（正常路径）** | | **≤30～50 s** |

### 其它既定时延（产品行为，非缺陷）

- **历史开奖页**：`history_backfill_delay_after_draw`（默认 8 分钟）闸门，避免抢在源站补全前公开。
- **香港彩轮序发布**：源站逐个给号，面板按已公布前缀展示，轮询窗口 900 s。
- 开奖前不显示任何号码：`/api/public/latest-draw` 等公开查询全部带 `AND is_opened = 1`
  （`public/api.py` 432/565/726/741/874 行），面板 `_shouldRevealPayload()` 要求
  `now - draw_time >= 0` 才揭示。

## 3. 验证

- 后端全量：**883 passed / 17 skipped / 1 个预先存在失败**（`test_ha_runtime_config_contract`，与本次无关）。
- 核查脚本（新增第 9 节"更新时效"）：
  - 中心节点 **PASS=20 / PENDING=0 / SKIP=8 / FAIL=0**；
  - 前端节点 **PASS=17 / PENDING=0 / SKIP=7 / FAIL=0**；
  - 其中断言：开奖 tier = 1 秒（5 个 server 块）、仅 `updating` 用旧值、面板窗口 3 秒、
    发布循环 `interval=1s` 日志存在、Outbox 无积压，并打印最近 5 次事件延迟。
- 实测层次上界（中心节点）：nginx 开奖 tier 同秒第二次请求 `HIT`，1.3 秒后仍 `HIT`（已被后台更新刷新）；
  开奖快照指针 TTL 剩余 2 秒（30 秒预算）；预测快照指针剩余 273/276 秒（300 秒预算）；
  代际键 TTL 595732 秒（7 天），值 `1`（本轮受控 bump 写入）。
- 事件级验证（下一次真实开奖后应复核）：`publication_outbox` 的
  `published_at - created_at` 应从 **10～31 秒降到 ≈1 秒**，查询语句已在核查脚本里打印。

## 4. 仍需观察 / 可继续收紧

1. **下一次真实开奖事件**的延迟复核（本轮修复后尚无新事件产生，无法立即给出实测值）。
2. 预测聚合的 nginx tier 仍是 20 秒；若要更严格，可降到 5 秒（代价是更多上游请求）。
3. 若要"事件级"而非"TTL 级"消除 Next 层 10～30 秒窗口，可让 Next 缓存键包含一个
   极小的代际探测接口（例如 `GET /api/public/prediction-generation?lottery_type=3` 返回两个计数，
   ~40 字节、KV 读 ~1 ms），从而做到"一 bump 即全链路失效"。
