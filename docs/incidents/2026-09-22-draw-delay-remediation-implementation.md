# 开奖延迟修复实施记录（本地代码，未部署）

实施日期：2026-09-22（Asia/Hong_Kong）
范围：`backend/src/**`、`frontend/**`。**未对任何服务器执行写操作。**

## 1. 改动清单

### P0-1 追赶模式真正生效（`backend/src/crawler/scheduler.py`）

| 改动 | 位置 |
| --- | --- |
| 开启 chase 时立即取消并按当前动态间隔重启 `_auto_crawl_timer` | `_set_lottery_chase_mode()` + 新增 `_rearm_auto_crawl_for_chase()` |
| 避免与正在执行的抓取轮次重复排程（新增 `_auto_crawl_running` 守卫） | `__init__()` / `_schedule_auto_crawl()` |
| 分级超时告警改为独立 15 秒轮询（新增 `crawler.staged_alert_interval_seconds`） | 新增 `_schedule_staged_timeout_alerts()`；从 `_auto_crawl()` 末尾移除调用；`start()`/`stop()` 挂载与取消 |
| “逾期未到即视为 near/chase” | `_compute_dynamic_crawl_interval()` + 新增 `_draw_is_overdue_and_unfilled()`、模块级 `_period_to_year_term()` |

### P0-2 upsert 不再回退已开盘的一期，且不再写假审计

| 改动 | 位置 |
| --- | --- |
| `ON CONFLICT DO UPDATE` 用 `CASE WHEN lottery_draws.is_opened = 1 THEN 1 ELSE excluded.is_opened END` 代替无条件回写（等价于 `GREATEST`，SQLite/PostgreSQL 通用） | `crawler/collectors.py::_upsert_draw()` |
| 仅当批次最新期**晚于**本地最新已开奖期时才开盘并写 `auto_open` 审计；同一期的刷新只走 `draw.refresh` | `crawler/scheduler.py::_process_auto_crawl_batch()` + 新增 `_is_newer_than_latest_opened()` |

### P1-1 号码完整性闸门

| 改动 | 位置 |
| --- | --- |
| 新增发布规则：澳门彩/台湾彩必须 7 个合法且不重复的号码；香港彩允许 1..7（轮序发布） | `outbox/draw_publication.py::draw_numbers_are_publishable()` / `draw_is_publishable()` |
| outbox 发布前再校验一次，半成品 payload 永不进入公开通道 | `outbox/draw_publication.py::enqueue_draw_publication()` |
| 开盘路径全部加闸门 | `_open_specific_records()`、`_auto_open_draws()`、`_open_taiwan_draws_and_update_next_time()` |
| 号码不完整时记录 WARNING 并保持 `is_opened=0` | 同上 |

### 香港彩轮序发布

- 后端：香港彩只要已有合法号码就允许开盘并按源站顺序发布当前前缀；后续每次号码补全都会产生 `draw-refresh:*` 事件刷新 Redis 公开快照（复用既有 outbox 机制）。
- 前端 `frontend/public/vendor/shengshi8800/kj/local.html` 与 `frontend/public/vendor/twsaimahui/kj/local.html`：
  - 新增 `PROGRESSIVE_REVEAL_LOTTERY_TYPES = { 1: true }`、`PROGRESSIVE_POLL_WINDOW_SEC = 900`；
  - 新增 `_progressiveBallCount()` 统计“已按顺序公布多少个号码”；
  - `load()` 中新增 `latest-draw:branch-progressive-render` 分支：香港彩不再等待 7 个号码齐全，也不做 25 秒/球的定时揭示，而是按当前已公布前缀立即渲染，号码没齐保持 5 秒轮询，每多一个号码补渲染一个；号码齐 7 个后停止轮询；
  - 香港彩轮询窗口从 210 秒放宽到 900 秒，覆盖源站 2~6 分钟的补全过程。
- `frontend/public/vendor/twcaibawang.com/wy.html` + `frontend/app/wy.json/route.ts` **无需改动**：`wy.json` 直接返回现有号码个数，`wy.html` 按 `openCode.split(',')` 逐个渲染，本身已是轮序语义。

### 历史开奖页 8 分钟闸门

| 改动 | 位置 |
| --- | --- |
| 默认值 4 → 8 | `runtime_config.py::history_backfill_delay_after_draw` |
| 后端历史页闸门改为读配置（默认 8 分钟），不再硬编码 4 分钟 | `public/api.py`（新增 `_history_result_delay_minutes()`，`HISTORY_RESULT_DELAY_MINUTES_DEFAULT = 8`） |
| 旧站预测出口闸门同样改为读配置 | `helpers.py`（新增 `_resolve_history_delay_minutes()`） |
| 前端快照兜底闸门改为读 `HISTORY_UNLOCK_DELAY_MINUTES`（默认 8），删除写死的 4 分钟 | `frontend/app/api/draw-history/route.ts` |
| 已部署库的存量 `system_config` 行由显式迁移 4 → 8（只迁移仍是旧默认 `'4'` 的行，不覆盖管理员自定义值） | `database/versioned_migrations.py` 迁移 29 `raise_history_publication_delay_to_eight_minutes`；`CURRENT_SCHEMA_VERSION` 28 → 29 |

`runtime_config.seed_system_config_defaults()` 只在 key 不存在时插入，因此**已部署的库必须执行迁移 29（或手工 UPDATE）才会从 4 变 20**。

### P1-2 告警阈值改为基于实际入库时延的滑动分位数

| 改动 | 位置 |
| --- | --- |
| 新增基线计算：最近 N 期 `created_at - (draw_time - 8h)` 的 p90，5 分钟缓存 | `crawler/scheduler.py::_observed_draw_arrival_latency_seconds()`、`_draw_alert_baseline_seconds()` |
| 分级阈值 = `max(配置下限, 基线 + 30/120/300)` | `_check_staged_timeout_alerts()` |
| 告警基线 = 基线（含配置下限 120s） | `alert_draw_staleness(..., grace_by_lottery=...)` |
| 静态默认阈值 30/120/300 → 180/300/600，新增 `alert.draw_latency_baseline_seconds/percentile/samples` | `runtime_config.py` |

已部署库里已经存在的 `alert.draw_*_timeout_seconds = 30/120/300` 行**不需要**修改：基线（澳门彩 p90 ≈ 320s）会自然压过旧的下限值。

## 2. 验证

```
cd backend/src && python -m pytest -q
# 833 passed, 13 skipped, 2 failed（均为预先存在：nginx 契约漂移 + 共享测试库顺序依赖）
```

唯一失败 `tests/unit/test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`
在改动前的原始工作树上同样失败（`deploy/nginx.conf` 缺少 `location = /health/live`），与本次改动无关。

```
cd backend/src && python -m pytest tests/unit/test_draw_delay_remediation.py -q
# 13 passed   （新增回归测试）
```

新增/更新的测试：

- 新增 `tests/unit/test_draw_delay_remediation.py`：追赶重排、逾期 near 判定、已开盘不回退、
  刷新不写假 `auto_open`、首次新期仍写一次审计、完整性闸门、香港彩轮序开盘与发布、
  独立告警轮询、滑动分位数基线。
- 更新 `tests/unit/test_public_draw_history_delay.py`、`tests/unit/test_legacy_mode_rows_overlay_delay.py`
  （4 分钟固定窗口 → 可配置 8 分钟）。
- 更新 `tests/unit/test_versioned_migrations.py`（版本 29 + 迁移 29 行为）。
- 更新 `tests/unit/test_scheduler_hk_macau_fast_open.py`（非法的 77 号测试夹具改为合法号码）。
- 更新 `frontend/test/history-unification-contract.mjs`（历史页可配置闸门 + 香港彩轮序发布契约）。

前端：

```
pnpm exec tsc --noEmit            # exit 0
pnpm exec eslint frontend/app/api/draw-history/route.ts   # exit 0
node frontend/test/*.mjs          # 7 个失败全部在原始工作树上同样失败（预先存在）
```

7 个预先存在的失败：`run-prediction-modules-route-contract`、`run-site-bridge-contract`、
`run-site-registry-contract`、`twjsz666-section-inventory-contract`、`twjsz666-subpage-contract`
（缺静态图 `c73120ca0585a192625208b7bcdfd1bd.jpg`）、`twsaimahui-api-audit`（需要本地 3000 端口）、
`twsyw-adapter-contract`。均已用 `git stash` 在原始工作树复现。

## 3. 部署（本次已获授权执行）

### 3.1 发布前预检（已完成，2026-09-21T18:5x UTC）

两个节点均为 `/root/Marksix` 的 git 检出，`HEAD = 964aaeb`，`origin/main = 35d480b`，
且 `964aaeb` 是本次提交 `5f338b8` 的**严格祖先**（本地领先 8 个提交）→ `git reset --hard` 是快进，不会产生分叉。

两个节点的 `git status` 都显示大量“已修改”，需要区分两类：

- **CRLF 行尾噪声**：`scheduler.py` 2561 行全部带 `\r`、`embed.html` 1237 行全部带 `\r`，
  直接 `git diff` 会显示 5016 行改动；`git diff --ignore-cr-at-eol` 后真实改动只有
  **584 插入 / 93 删除 / 22 文件**。
- **是否为“只存在于服务器”的生产代码**：不是。把服务器工作树按 CRLF 归一化后逐文件求
  SHA-256，与本地 `5f338b8` 的 blob 对比：**23 个文件中 16 个完全一致**（含
  `result_crawler.py` 的多备用源、`_shared/lottery-site-runtime.js` 的 `mergeDraw`、
  未跟踪的 `_shared/lottery-site-draw-state.js`）；剩余 7 个的差异经逐行核对，
  **服务器侧多出来的行全部是本次提交已经取代的旧版本代码**
  （旧的 `_open_specific_records` 片段、`CURRENT_SCHEMA_VERSION = 28`、
  `test_alert_service.py` 里没有 `schema=` 的旧桩、`test_scheduler_hk_macau_fast_open.py` 里
  非法的 `11,22,33,44,55,66,77` 夹具、`from typing import Any`、`if next_dt < now_utc:`）。
  即服务器工作树是**本地已提交内容的过期快照**，不存在会被 `reset --hard` 抹掉的生产独有代码。

另外确认：中心节点实际挂载的是 `deploy/nginx.conf.local`（未跟踪的本地文件），
`deploy/nginx.conf` 虽被 `reset` 更新，但不影响线上 Nginx；证书、`.env`、`.codex-stage/` 等
未跟踪运行时文件不会被 `git reset --hard` 删除（不使用 `git clean`）。

### 3.2 备份（已完成）

| 节点 | 备份目录 | 内容 |
| --- | --- | --- |
| 中心 | `/root/Marksix/.deploy-backups/draw-delay-8min-backend-20260921T185212Z`（21 MB） | `HEAD.txt`、`STATUS.txt`、`worktree.patch`、`worktree-eol-normalized.patch`（62 KB 真实改动）、`untracked.txt`、`env.root`、`env.example`、`docker-compose.yml`、`deploy-runtime.tgz`（ssl + nginx.conf.local）、`backend-data-manifest.txt`、`compose-ps.txt`、`nginx-t.txt`、`liuhecai.before.dump`（20.6 MB `pg_dump -Fc`）+ `.sha256`（`17a6d1d94391ba56…badc997`） |
| 前端 | `/root/Marksix/.deploy-backups/draw-delay-8min-frontend-20260921T185445Z`（60 KB） | 同上（无 dump），含 `docker-compose.frontend-node.yml` 与 `env.root` |

### 3.3 发布步骤

1. 提交并推送代码（`git push origin main` → `35d480b..bffcb27`）。
2. 中心节点 `207.56.3.82:29618`：`git fetch origin main` + `git reset --hard origin/main`，重建
   `python-api`、`scheduler-worker`、`frontend`，并执行数据库迁移以应用迁移 29，
   把 `system_config.history_backfill_delay_after_draw` 从 4 改为 8。
3. 前端节点 `207.56.2.71:62594`：在 `.env` 增加 `HISTORY_UNLOCK_DELAY_MINUTES=8`，`git fetch/reset` 后仅重建
   `frontend`（`docker-compose.frontend-node.yml`）。该变量已加入两个 compose 文件的 `frontend.environment`，
   否则 `.env` 的值不会进入容器。

> **必须重建 `db-migrate` 镜像**：`docker compose build python-api scheduler-worker frontend`
> **不会**重建 `marksix-db-migrate`（它是运行时依赖，不是构建依赖）。若该镜像陈旧，迁移脚本里没有新版本号，
> 会打印 `Schema migrations are already current.` 而什么都不做，随后 `python-api` / `scheduler-worker`
> 因 `validate_runtime_schema()` 缺少新版本号而崩溃重启。正确做法：
>
> ```bash
> docker compose build db-migrate        # 让迁移镜像与新代码一致
> docker compose run --rm db-migrate     # 期望输出 Applied schema migrations: 29
> ```

### 3.4 实际发布结果（2026-09-21T19:0x–19:2x UTC）

| 项 | 结果 |
| --- | --- |
| 推送 | `35d480b..bffcb27 main -> main`；本地与 `origin/main` 一致 |
| 中心节点 HEAD | `bffcb27`（`git reset --hard` 快进，无冲突） |
| 中心节点容器 | `python-api` healthy、`frontend` healthy、`scheduler-worker` Up、`nginx -t` 通过；`postgres`/`pgbouncer`/`redis`/`mihomo`/`backend-admin` 未受影响 |
| 中心节点迁移 | `schema_migrations` 28 → **29**；`system_config.history_backfill_delay_after_draw` 4 → **8** |
| 前端节点 HEAD | `bffcb27`；`liuhecai-frontend` healthy、`nginx -t` 通过 |
| 前端节点 env | 容器内 `HISTORY_UNLOCK_DELAY_MINUTES=8` |
| 10 个站点 | `history?type=3`、`api/draw-history`、`api/latest-draw` 全部 HTTP 200 |
| 开奖面板统一 | `vendor/shengshi8800/kj/local.html` 200 且含 `_shared/kj-runtime.js` 与轮序发布代码；`_shared/kj-runtime.js` 200；twsaimahui 旧副本 `vendor/twsaimahui/kj/local.html` **404**；`/vendor/twsaimahui/index.html` 中 shim 在第 300 行、`kj.js` 在第 301 行（顺序正确） |
| 8 分钟闸门（容器内实测） | 默认 8 分钟、运行时配置读回 8.0；`draw_time + 7m59s` → False，`+8m00s` → True；旧站出口 `helpers._history_result_visible_after_delay` 边界一致 |
| 假延迟审计 | 发布后 30 分钟内 `auto_open` 审计 0 条；最后一条仍是发布前的 13:34 |
| 滞后邮件 | 发布后 15 分钟内 `Draw staleness` 告警 0 条 |

#### 发布过程中的一次短暂故障（已自愈，记录备查）

首次 `docker compose up -d` 后 `python-api` 崩溃重启 9 次，日志为
`SchemaMigrationRequired: 数据库缺少 schema migration 版本 29`。原因即上面的
`db-migrate` 镜像陈旧。处置：用新建的 `python-api` 镜像执行迁移
（`docker compose run --rm --no-deps --entrypoint sh python-api -c 'cd /app/src && python -m database.versioned_migrations --db-path "$DATABASE_URL"'`
→ `Applied schema migrations: 29`），随后 `docker compose build db-migrate` 并重新 `up -d`，全部 healthy。
故障窗口约 4 分钟（19:12–19:16 UTC），期间 `postgres`/`pgbouncer`/数据卷未被改动，
备份目录中的 `liuhecai.before.dump` 可随时回滚。

#### 尚需在开奖窗口观察的验收项

以下三项只能在真实开奖时观察，下一次香港彩/澳门彩开奖为 **2026-09-22 21:30 / 21:32（北京时间）**：

- 香港彩按号码逐个出现在开奖位（轮序发布）；
- 慢周期不再出现 ~5 分钟抓取空窗（对比 `public_open_delay_seconds` 是否稳定 ≤200s）；
- 计划开奖时间之后不再收到常规“开奖数据滞后”邮件。

### 3.5 原验收清单

- 澳门彩/香港彩计划开奖时间后 ≤20 秒内 `is_opened=1`（源站已发布的前提下）；
- 慢周期不再出现 5 分钟抓取空窗；
- `draw_audit_log.auto_open` 不再出现 `public_open_delay_seconds ≈ 86400`；
- 香港彩按号码逐个出现在开奖位；
- 历史开奖页在 `draw_time + 8 分钟`（且号码齐全）后出现最新一期；
- 近 7 天不再收到常规“开奖数据滞后”邮件。

## 4. 十个站点开奖模块统一性（已彻底统一）

| 站点目录 | 域名 | 开奖模块 |
| --- | --- | --- |
| shengshi8800 | www.tw8800.com | 共享 `/vendor/shengshi8800/kj/local.html`（`static/js/kj.js`） |
| twjinniu | www.twtongtian.com | 共享（`index.html` iframe） |
| twcaibawang.com | www.twcaibawang.com | 共享（`index.html` iframe + React `TwcaibawangHomeClient.tsx`） |
| twcf888.com | www.twcf888.com | 共享（`index.html` iframe） |
| twbst528 | www.twbst528.com | 共享（`index.html`） |
| twjsz666 | www.twjsz666.com | 共享（`kai.html`） |
| twssz | www.twssz.com | 共享（`kai.html` + `site-config.js: drawFramePath`） |
| twsyw | www.twsyw.com | 共享（`kai.html`） |
| twwanli | www.twwanli.com | 共享（`kai.html`） |
| twsaimahui | www.twsaimahui.com | 共享（经由 `/vendor/_shared/kj-runtime.js`） |

- **10 个站点现在全部加载同一个文件** `frontend/public/vendor/shengshi8800/kj/local.html`。
- 原先 `twsaimahui/kj/local.html` 是与共享文件仅差 21 行新增 / 4 行删除的副本（纯 URL 垫片）。
  本次已把垫片抽成 `/vendor/_shared/kj-runtime.js`：
  - 共享 `local.html` 引入该垫片，用 `LegacyKjRuntime.buildAppUrl()/buildHistoryUrl()` 取代写死路径；
  - `twsaimahui/static/js/kj.js` 用 `LegacyKjRuntime.buildVendorPath("kj/local.html")` 指向共享面板；
  - `twsaimahui/index.html` 在 `static/js/kj.js` 之前加载垫片；
  - `twsaimahui/kj/local.html` 已删除。
- 垫片在没有 `window/parent.LEGACY_TWSAIMAHUI_RUNTIME` 时**原样返回以 `/` 开头的路径**，其余 9 个站点
  行为与改造前完全一致；`history-unification-contract.mjs` 现在强制 twsaimahui 不得再分叉面板。
- 实时开奖接口层同样是统一的：10 站都走 `frontend/app/api/latest-draw/route.ts` → 中心
  `/api/public/latest-draw`（`cache: no-store`）。`twcaibawang.com/wy.html` 是额外的旧站页面，
  走 `/wy.json`，本身已支持逐个号码渲染，无需改动。
