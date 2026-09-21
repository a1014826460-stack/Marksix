# 开奖延迟根因排查 + 历史开奖页同步时间

排查时间：2026-09-21（UTC）/ 2026-09-22（Asia/Hong_Kong）
排查方式：只读。CodeGraph 索引 + 两个生产节点的日志/数据库/API 取证。

## 0. 检索方式（CodeGraph）

- `codegraph upgrade` → 已是最新版 `v1.6.0`（无需变更）。
- `codegraph init -y D:\pythonProject\outsource\Liuhecai` → 索引 699 个文件，9,807 节点 / 26,592 边。
- 用 `codegraph explore` / `codegraph query` 定位：历史开奖页闸门、`historyUnlockAt`、`SiteDrawSource`、`HistoryPageContent` 等符号。

## 1. 目标节点与访问方式

| 角色 | 地址 | 目录 | 运行提交 |
| --- | --- | --- | --- |
| 中心后端节点 | `207.56.3.82:29618` | `/root/Marksix` | `964aaeb32dfdf70ac4a9e66646bfd43f56bc043e` |
| 前端节点 | `207.56.2.71:62594` | `/root/Marksix` | `964aaeb32dfdf70ac4a9e66646bfd43f56bc043e` |

**访问方式注意（重要）**：从本机直连这两个端口，TCP 可以建连但 30 秒内收不到 SSH banner（`Connection timed out during banner exchange`），说明链路被中间设备劫持/丢包，不是服务器故障。从跳板机 `8.163.93.151` 读 banner 只需 11ms。因此必须走：

```powershell
ssh -o ProxyJump=jumper -p 29618 root@207.56.3.82
ssh -o ProxyJump=jumper -p 62594 root@207.56.2.71
```

容器状态（中心）：`python-api`/`frontend`/`backend-admin` healthy，`scheduler-worker` running，`postgres`/`pgbouncer`/`redis`/`mihomo` 正常。

## 2. 完整开奖链路实测（以 2026-09-21 澳门彩第 264 期为例，北京时间）

| 时刻 (HKT) | 事件 | 证据来源 |
| --- | --- | --- |
| 21:32:00 | 计划开奖时间（`draw.macau_default_draw_time`） | `system_config` |
| 21:31:59 | 精确检查定时器触发 | scheduler 日志 |
| 21:32:11 ~ 21:32:22 | 三个源仍返回 `2026263`（`outcome=old_period`） | `draw_audit_log` `source_fetch` |
| 21:32:34 | 进入 chase mode（5s 追赶） | scheduler 日志 |
| **21:34:26** | `macaumarksix.com` 首次返回 `2026264` | `source_fetch expected_period=2026264` |
| **21:34:34** | 入库 `lottery_draws` + `is_opened=1` + 写 outbox | `lottery_draws.created_at` / `publication_outbox` |
| 21:34:52 | outbox 发布到 Redis 公开快照（lag 18s） | `publication_outbox.published_at` |
| 21:36:32 | 历史开奖页开始可见（`draw_time + 4min`） | `HISTORY_RESULT_DELAY` |

结论：这一期端到端 ≈ **2 分 34 秒**，其中上游源站发布就占了 **2 分 26 秒**，我方从“源站已有数据”到“入库并开盘”只用了 **8 秒**。

## 3. 近 30 天量化统计

- 澳门彩（`draw_time` → `created_at`）入库时延：平均 **214s**，最小 110s，最大 390s。
  - `< 200s`：18 期；`>= 250s`：**12 期（40%）**。
- 香港彩：`created_at` 反而早于 `draw_time` 72 ~ 122 秒 —— 源站先给“临时 draw_time + 部分号码”，随后改写。
- `publication_outbox` 中香港彩每期首次 `draw.published` 的球数：0 球 5 期、1 球 8 期、2 球 2 期、3 球 1 期，**没有一期是完整 7 球**。
- `draw_audit_log` 近 24h：`source_fetch` 失败 1459 次、成功 5 次（正常：源站还没出新期），`auto_open` 6 次。

## 4. 根因

### 根因 A（主因，可修复，影响约 40% 期数，多等最多 ~300s）：chase 加速不会重新排程 auto-crawl 定时器

三处代码互相咬死：

1. `backend/src/crawler/scheduler.py:766-772` `_set_lottery_chase_mode()` 只写内存标记 `self._chase_modes[lt]`，**不取消也不重启 `self._auto_crawl_timer`**。
2. `scheduler.py:1559` `_check_staged_timeout_alerts()`（唯一会打开 chase 与黄色/橙色/红色告警的地方）在 `_auto_crawl()` 的**末尾**被调用 —— 也就是“加速开关”只挂在它本该加速的那条慢轮询上，形成自锁。
3. `scheduler.py:1034-1066` `_compute_dynamic_crawl_interval()` 只看 `system_config.lottery.*_next_time` 是否落在 ±5 分钟内。而一期（哪怕是旧的）被 upsert 后，`sync_lottery_type_next_time_from_latest_draw` 会把 `next_time` 推到下一期（24h 后），于是“计划开奖时间已过、新数据还没到”这种状态被判成 far → 300s。

**现场证据（三天同一签名）**

```
# 2026-09-11 (终值 327s)
13:32:36.492  Chase mode enabled for lt=2
      ...（5 分 23 秒无任何抓取日志）...
13:37:59.569  Auto-crawl 澳门彩: inserted=1 updated=0
13:37:59.611  Auto-crawl 澳门彩: opened=1 (public_open_delay_seconds=327)

# 2026-09-15 (终值 369s)
13:33:38.696  Auto-crawl 澳门彩: all 1 record(s) already up-to-date, skipped
      ...（5 分 02 秒无任何抓取日志）...
13:38:41.224  Auto-crawl 澳门彩: inserted=1 updated=0

# 2026-09-20 (终值 323s)
13:32:46.908  Precise check lt=2 still points to a passed fire time; retry scheduled in 60s
      ...（5 分 09 秒无任何抓取日志）...
13:37:55.219  Auto-crawl 澳门彩: inserted=1 updated=0
```

对照：2026-09-21 该轮 auto-crawl 恰好被排成 near（10s），就全程无空窗、时延只有 122s。**这就是“有时 2 分钟、有时 6 分钟”的全部原因。**

### 根因 B：上一期被重复 upsert → `is_opened` 被重置为 0 → 重复开盘 + 假延迟审计

- `backend/src/crawler/collectors.py:99-131` `_upsert_draw()` 的 `ON CONFLICT ... DO UPDATE` 里写了 `is_opened = excluded.is_opened`，而调度侧传入的就是 `0`。
- `scheduler.py:531-541` `_draw_needs_upsert()` 只要 `numbers`/`draw_time`/`next_time` 任一变化就判定需要更新 —— 香港彩源站“先部分号码、后补全”，所以**每一轮都会改写上一期**。
- 后果 1：`scheduler.py:1462-1471` 紧接着开盘并写审计，用**上一期**的 `draw_time` 算延迟：

```
42924  lt=2 2026 263 auto_open  opened=1 public_open_delay_seconds=86498   2026-09-21T13:34:10Z
42908  lt=2 2026 263 auto_open  opened=1 public_open_delay_seconds=86439   2026-09-21T13:33:11Z
42773  lt=1 2026 102 auto_open  opened=1 public_open_delay_seconds=166690  2026-09-21T11:53:02Z
42766  lt=1 2026 102 auto_open  opened=1 public_open_delay_seconds=166364  2026-09-21T11:47:36Z
```

`86400 ≈ 24 小时`、`166690 ≈ 46 小时` —— 这些**不是真实延迟**，是拿上一期的 `draw_time` 减出来的假值。近 7 天 14 条 `auto_open` 审计里有 6 条属于这一类。

- 后果 2：`_upsert_current_draw_records()` 与 `_open_specific_records()` 是两个独立事务，两者之间存在 `is_opened=0` 的**已提交窗口**。`/api/public/latest-draw` 与 `/api/public/draw-history` 都按 `is_opened=1` 过滤（`public/api.py:693`、`domains/lottery/repository.py`），所以已发布的一期会短暂消失/回退到上一期。

### 根因 C：香港彩以“不完整号码”对外开盘并发布

- 入库/开盘/发布链路没有“7 个号码齐全”的前置校验。
- `publication_outbox` 实例：`draw-published:1:2026:102` → `"numbers":"5"`，`published_at=2026-09-19T13:33:32Z`（21:33:32 HKT）；`...:101` → `"41,47"`；`...:100` → `"9"`。
- Redis 公开快照 TTL 120s（`cache/public_snapshots.py:69`），这 2 分钟内 `/api/latest-draw` 会把这份不完整 payload 直接返回。
- 缓解：`frontend/public/vendor/shengshi8800/kj/local.html:380-389` 的 `_hasFullBalls()`（需 6 正码 + 特码）挡住了主开奖位，所以前台表现为“停在上一期”。但 `/index/ajax/ttklsjl`、`/wy.json`、以及其它消费方没有这层保护。

### 根因 D：延迟告警基线用“计划开奖时间”，导致每期必然误报

- `_check_staged_timeout_alerts()`（yellow 30s / orange 120s / red 300s）与 `alert_draw_staleness()` 都以 `lottery.*_next_time`（HK 21:30、澳门 21:32）为基线，而上游实际发布在 110–390s 之后。
- 现场日志：

```
13:32:44.788 WARNING Draw staleness: lt=澳门彩 latest=2026/263 next_time=2026-09-21 13:32:00 UTC < now=13:32:44 UTC
13:32:45.592 INFO    Alert email sent: [澳门彩] 开奖数据滞后报警 → ['1014826460@qq.com']
13:33:35.776 WARNING YELLOW ALERT: 澳门彩 draw overdue by 83s, accelerating polling
13:32:34.950 ORANGE ALERT: 香港彩 draw overdue by 145s (target=2026-09-15T13:30:00+00:00)
```

- 近 7 天共 16 封告警邮件，其中 `[香港彩]/[澳门彩]/[台湾彩] 开奖数据滞后报警` 各 3 封 + 合并 1 封。这会把真实故障淹没在噪声里。

### 已排除的非根因

- **前端节点不引入延迟**：无 `proxy_cache`；`/api/latest-draw`、`/api/draw-history`、`/index/ajax/ttklsjl` 全部 `cache: "no-store"` + `Cache-Control: no-store`；五站 `/api/latest-draw` 实测 200，耗时 59–170ms；对中心 API 的 RTT 仅 59ms。
- **中心侧服务健康**：24h 内开奖类请求 782 次全部 200（4 次 499 是客户端主动断开）；无 5xx；Redis 公开快照当前 keyspace 为空（TTL 120s，不构成长期陈旧）。
- 旧文档 `backend/docs/开奖延迟故障分析报告.md`（2026-05-13）里列的问题 1/2/3/5 已经修掉，当前瓶颈不在那里。

## 5. 解决方案

### P0-1 让 chase 真正生效（改 `backend/src/crawler/scheduler.py`）

1. `_set_lottery_chase_mode(lt, True)` 时，取消并按 chase 间隔**立即重启** `self._auto_crawl_timer`：

```python
def _set_lottery_chase_mode(self, lottery_type_id: int, chase: bool) -> None:
    if not hasattr(self, "_chase_modes"):
        self._chase_modes: dict[int, bool] = {}
    previous = self._chase_modes.get(lottery_type_id)
    self._chase_modes[lottery_type_id] = chase
    if chase and not previous:
        _crawler_logger.warning("Chase mode enabled for lt=%s", lottery_type_id)
        # 关键：立即把 auto-crawl 定时器切到追赶间隔，而不是等上一轮排程到期
        if self._running and getattr(self, "_auto_crawl_timer", None):
            self._auto_crawl_timer.cancel()
            interval = self._compute_dynamic_crawl_interval()
            self._auto_crawl_timer = threading.Timer(interval, self._schedule_auto_crawl)
            self._auto_crawl_timer.daemon = True
            self._auto_crawl_timer.start()
```

2. 把 `_check_staged_timeout_alerts()` 从 `_auto_crawl()` 末尾挪到**独立的 10~15s 定时器**（或挂到 60s 的 auto-open 循环），让分级告警/加速判定不再依赖被它加速的那条慢轮询。

3. `_compute_dynamic_crawl_interval()` 增加“逾期未到”判定：只要 `now >= lottery.*_next_time` 且最新一期的期号仍小于期望期号，就返回 chase/near 间隔，而不是 far。这样即使 chase 标记丢失也不会出现 300s 盲区。

### P0-2 修正开盘语义与审计口径

- `collectors._upsert_draw()` 的 `ON CONFLICT DO UPDATE` 不要无条件回写 `is_opened`：改为 `is_opened = GREATEST(public.lottery_draws.is_opened, excluded.is_opened)`，或仅在 INSERT 分支写 0，UPDATE 分支完全不碰 `is_opened`。
- `_process_auto_crawl_batch()` 只在“确实产生了比当前最新期更新的期号”时才调用 `_open_specific_records()` 并写 `auto_open` 审计；对已开盘期的数据刷新只更新号码/时间，不再写 `auto_open`，避免出现 `public_open_delay_seconds=86400/166690` 这类假值。
- 若要保留“重复开盘”告警能力，另写 `draw_rewrite` 事件，与 `auto_open` 分离。

### P1-1 完整性校验（香港彩尤其需要）

- `_upsert_current_draw_records()` / `_open_specific_records()` 增加号码完整性前置条件：正码 6 个 + 特码 1 个、去重、范围 1–49；不满足时**只入库不开盘**，等源站补全。
- `enqueue_opened_draw_publication()` 与 outbox 发布前再做一次完整性校验，杜绝把 `numbers:"5"` 这类 payload 推到 Redis 公开快照。

### P1-2 告警基线改为“上游实际发布时间”

- 把 `alert.draw_yellow/orange/red_timeout_seconds` 由 30/120/300 调整为基于**上一期实际入库时延滑动分位数**的阈值（例如 p50+60s / p95+60s / p99），或直接抬到 180/300/600s。
- `alert_draw_staleness()` 的基线从“计划开奖时间”改成“上一期实际 `draw_time` + 常规间隔（含上游发布时延）”。
- 保留 `alert.cooldown_seconds=3600` 抑制重复邮件，但需要把“同一期重复改写”与“新期未到”区分开（见 P0-2）。

### P2 观测与回归

- `draw_audit_log` 增加 `expected_period`、`data_available_at`、`source_published_at` 字段，把“上游时延”和“我方时延”分开统计。
- 在 `/health` 的 `draws` 段增加每彩种的 `last_cycle_latency_seconds` 与 `p50/p95`，便于验收。
- 补单元测试：`_set_lottery_chase_mode(True)` 必须重新排程；`_upsert_draw` 更新已开盘期不得把 `is_opened` 置 0；不完整号码不得开盘/发布。

## 6. 历史开奖数据页面：入口与同步更新时间（问题 2）

### 页面入口

| 类型 | 路径 |
| --- | --- |
| 标准页面（推荐） | `/history?type=1`（香港彩）、`?type=2`（澳门彩）、`?type=3`（台湾彩） |
| 旧站兼容路径（全部 rewrite 到 `/history`） | `/index/index/history.html`、`/baomaqg/am/kaijiangjilu.html`、`/vendor/*/history.html`、`/vendor/*/wylhc.html` |
| 旧站 JSONP 接口 | `/index/ajax/ttklsjl?year=YYYY` → 内部调 `/api/draw-history` |

实现位置：`frontend/app/history/page.tsx` → `frontend/app/api/draw-history/route.ts` → 中心 `/api/public/draw-history` → `backend/src/public/api.py:get_draw_history()`；重写规则在 `frontend/proxy.ts:13-23`。

### 同步更新时间

历史页对**每一条**开奖记录单独设了一个展示闸门，条件是“**该期 `draw_time`（北京时间）+ 4 分钟**”：

- `backend/src/public/api.py:647` `HISTORY_RESULT_DELAY = timedelta(minutes=4)`，`_history_result_visible()` 要求 `now >= draw_time + 4min`，且 `is_opened = 1`；
- `backend/src/helpers.py:626-643` 旧接口/预测出口用同一个固定 4 分钟（注释明确写了不得继承可配置的回填延迟）；
- `frontend/app/api/draw-history/route.ts:71-75` `historyUnlockAt()` 快照兜底同样是 4 分钟；
- `routes/public_routes.py:135` 与前端 route 都返回 `Cache-Control: no-store`，所以浏览器/网关不会再叠加缓存延迟。

**注意**：`system_config.history_backfill_delay_after_draw = 4` 只控制“预测结果回填任务”的排程（`scheduler._schedule_backfill_after_draw`），**不再控制历史页的展示闸门**——历史页的 4 分钟是硬编码的。

因此，最新一期在历史开奖数据页面出现的时刻是：

> **可见时刻 = max(该期 `draw_time` + 4 分钟, 数据实际入库时刻)**

由于 `draw_time` 用的是源站回报的**实际**开奖时间，具体到各彩种（北京时间）：

| 彩种 | `draw_time` 典型值 | 闸门解锁时刻 | 实测入库时刻 | 历史页实际可见 |
| --- | --- | --- | --- | --- |
| 澳门彩 | 21:32:32 | 21:36:32 | 21:34:34（快周期） | **21:36:32** |
| 澳门彩（慢周期，占 40%） | 21:32:32 | 21:36:32 | 21:37:55 ~ 21:38:41 | **21:37:55 ~ 21:38:41**（被入库时间拖后） |
| 香港彩 | 21:33:00 ~ 21:39:14（源站逐步改写） | 对应 draw_time + 4 分钟 ≈ 21:37 ~ 21:43 | 21:33 ~ 21:36 | 以最终 `draw_time + 4min` 为准 |
| 台湾彩 | 22:32:00（固定） | **22:36:00** | 22:32:10 ~ 22:32:26 | **22:36:00** |

补充：历史页只在进入/切换参数时加载一次，**不会自动轮询**；用户需要刷新页面才能看到新一期。实时开奖位（`vendor/shengshi8800/kj/local.html`）每 5 秒轮询 `/api/latest-draw`，不受这个 4 分钟闸门影响。

## 7. 一句话结论

延迟由两段叠加而成：**上游源站本身要 2~6 分钟才发布结果**（不可控），以及**我方调度在“计划开奖时间已过”后掉进 300s 慢轮询盲区、最多再白等 3 分钟**（可控，占 40% 期数）。历史开奖页则是设计上的 `draw_time + 4 分钟` 闸门，慢周期时还要再等数据入库。
