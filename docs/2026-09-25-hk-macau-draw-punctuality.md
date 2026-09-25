# 港澳彩准时开奖修复（2026-09-25 澳门彩 268 期延迟 367 秒）

- 日期：2026-09-25
- 业务要求：**确保澳门彩、香港彩准时开奖**（不早开、不延误）。
- 本轮范围：仅 P1 代码级修复（不改线上配置值、不改 nginx）。

## 1. 现象与实测时间线（2026-09-25 澳门彩 268 期，北京时间）

| 时刻 | 事件 | 证据 |
| --- | --- | --- |
| 21:32:32 | 源站真实开奖 `open_time` | 源站 `current` / `lottery_draws.draw_time` |
| 21:32:01–21:33:11 | 精确检查连抓 8 轮（三源），全部 `returned_period=2026267 outcome=old_period` | `context=precise_period_check` 审计日志 |
| 21:32:50 | 旧期 267 刷新 + `next_time mismatch`：`stored=09-25 21:32 → effective=09-26 21:32` | `next_time.sync` 告警 |
| 21:33:11 | 再次开追单（"next poll in 5s"）、"retry scheduled in 60s" | `_set_lottery_chase_mode` / `_reschedule_precise_checks_once` |
| 21:33:26 | 追单抓到一次，仍为旧期 267 → **追单被关闭** | `refreshed an already-published draw (2026267)` |
| 21:33:26–21:38:30 | **无任何抓取（5 分 04 秒盲区）** | 日志空档 |
| **21:38:39.695** | 首次取到 268 并开盘 | `created_at`、`public_open_delay_seconds=367` |
| **21:38:40.764** | 推送发布（outbox） | `draw-published:2:2026:268`（lag 1.76 s） |
| 21:46:47 | 结果回填完成 | `backfill_after_draw:2:2026268` |

**结果：延迟 367.7 秒。** 同期台湾彩 267 为 14 秒（持久化任务），说明底座正常，问题在港澳的"抓取追赶"链路。

近 12 期澳门实际延迟：2.0/2.0/2.1/2.1/2.2/2.2/2.2/3.1/5.4/5.4/6.1/6.2 分钟——正是 `near=10s` 与 `far=300s` 两档的整数倍，与下面的根因一致。

## 2. 根因（四处，互相叠加）

1. **旧期刷新把排期前滚**：源站在自己切到 268 后仍会回旧期 267，且此时它给的 `next_time` 已前滚到 09-26。
   `helpers.get_effective_next_draw_payload()` 对港澳直接返回"最新已开奖行的 `next_time`"，
   `sync_lottery_type_next_time_from_latest_draw()` 再写回 `lottery_types` 与
   `system_config.lottery.*_next_time` → 系统认为"下一期"是 09-26。
2. **动态间隔因此掉到 far(300s)**：`_compute_dynamic_crawl_interval()` 看到 `next_time` 在 5 分钟窗口之外
   且未过期（在未来），直接返回 `crawl_interval_far_draw=300`。
3. **旧期刷新关闭了追单**：`_process_auto_crawl_batch()` 在"批次最新期不晚于本地最新已开奖期"分支里
   调用 `_set_lottery_chase_mode(False)`；一次旧期刷新就把追赶关掉。
4. **分级告警也把追单关掉**：`_check_staged_timeout_alerts()` 在 `target_dt > now_dt` 时同样
   `_set_lottery_chase_mode(lt, False)` —— 被污染的 `next_time` 使这条路径成为第二个"关闭开关"。
   （同时它也不再告警：`seconds_past` 为负，黄/橙/红三档全部跳过，所以 6 分钟延误没有任何告警。）

此外精确检查的"到点后重试"只有一次、60 秒后按 `next_time` 重算：一旦 `next_time` 被推到次日，
重试目标直接排到明天，链条彻底终止。

## 3. 修复内容（P1 代码级）

| # | 位置 | 修复 |
| --- | --- | --- |
| 1 | `crawler/collectors.py::_upsert_draw` | 只有"新期首次入库"或"该期 0→1 开盘"才算排期推进；**已开奖期的重复刷新既不写 `lottery_draws.next_time`，也不触发 `lottery_types`/`system_config` 同步** |
| 2 | `crawler/scheduler.py::_process_auto_crawl_batch` | 旧期刷新不再关闭追单（`chase kept=...` 仅记录），只有新期真正开盘才关闭 |
| 3 | `crawler/scheduler.py::_reschedule_precise_checks_once` | 到点后进入**固定追赶窗口**：独立定时器每 `crawl_interval_chase`(5s) 重试，不再按 `next_time` 重算决定是否继续；追赶期间不再排普通精确检查 |
| 4 | `crawler/scheduler.py::_chase_tick`（新增） | 独立追赶心跳：每 5 秒**并发探测全部采集源**（主源 + 全部备用源），命中期望期立刻跑完整开盘管线；期望期已开盘 → 关闭追赶并恢复常规排程；超过 `open_delay_warn_seconds`(90s) 记 WARNING |
| 5 | `crawler/scheduler.py::_check_staged_timeout_alerts` | 不再因"`next_time` 还在未来"关闭追赶；追赶窗口内不重复请求源站（避免窗口期请求量翻倍） |
| 6 | `crawler/scheduler.py::_compute_dynamic_crawl_interval` | 追单判定改用带截止时间的 `_any_chase_active()`（不会因过期标记导致永久高频） |
| 7 | `crawler/scheduler.py::stop` | 停止时取消追赶定时器并清空追单状态 |

**边界收敛（避免无限高频）**：单个追赶窗口 `crawler.chase_max_seconds`（默认 900 秒），
同一期望期最多续期 `crawler.chase_max_windows`（默认 3 个 ≈ 45 分钟），
预算用尽后对该期望期停用追赶并回落常规 near/far 轮询；下一期换号后自动恢复。
追赶探测单次超时 `crawler.chase_probe_timeout_seconds`（默认 8 秒，单次不重试）。

## 4. 关于"备用源没有爬"的澄清

日志证据显示**备用源一直在爬**，误导来自三处：

1. 备用源 URL 来自**容器环境变量**（`DRAW_MACAU_BACKUP_COLLECT_URL`、
   `DRAW_MACAU_BACKUP2_COLLECT_URL`、HK 同理，均已设置），而 `system_config` 里的
   `draw.*_backup_collect_url` 是**空值** —— 只看后台配置页会以为"没配备用源"。
2. 2026-09-25 的抓取审计里三源都在用：`auto_crawl` 命中 `www.lnlllt.com` /
   `macaumarksix.com` / `api.csjid.com`，`precise_period_check` 同样三源。
3. 日志里 `backup still unavailable actual=2026267` 的语义是"**备用源也还停留在旧期**"，
   不是"没有访问备用源"（见 `_do_precise_draw_fetch_and_open`）。源站自身在开奖后
   30–60 秒内仍返回旧期（21:33:11 时三源都还是 267）。

真正的断档不是"没爬备用源"，而是 **21:33:26 之后三源都不再被爬**（第 2 节根因 3/4）。
本次修复额外把补备用源的枚举写死为"主源 + 全部备用源"，不再受
"连续失败后备用提升为主源"的切换逻辑影响。

## 5. 回归测试

`backend/src/tests/unit/test_draw_open_chase_window.py`（9 项）：

1. 已开奖期刷新不得改写 `lottery_draws.next_time` / `lottery_types.next_time` / `system_config`；
2. 新期首次入库仍必须正常推进排期；
3. 旧期刷新不得关闭追单；
4. 新期真正开盘必须关闭追单；
5. 到点后必须武装独立追赶定时器并记录期望期号；
6. 追赶窗口按预算续期、用尽后对该期望期抑制（不会无限高频）；
7. 并发探测"任一源先给出期望期就立即返回"（不等慢源）；
8. `next_time` 在未来时分级告警不得关闭追单；
9. `stop()` 必须清理追赶定时器。

## 6. 验收

- 下一次澳门开奖（21:32:32）观察 `public_open_delay_seconds`，目标 ≤60 秒；
- 香港开奖日（周二/四/六 21:30）同样核对；
- 确认 `lottery.macau_next_time` / `lottery.hk_next_time` 在旧期刷新后不再被前滚到次日；
- 确认日志出现 `Chase mode enabled ... window#1` → 命中后 `running open pipeline` →
  `opened=1 ... public_open_delay_seconds=NN`，且无 `Chase ... windows exhausted`。
