# 预测资料快照化设计方案（2026-09-24）

目标：把"每个访客、每次请求都重新聚合"的预测资料读取改成**一次 KV 读**。
本文只描述方案与验收标准；实施分三阶段，每阶段可独立上线与回滚。

## 1. 现状与实测

### 1.1 取数路径

| 入口 | 前端路由 | Python 处理 | 实测 |
| --- | --- | --- | --- |
| 站点聚合资料 | `/api/sites/<siteKey>/prediction-modules` → `frontend/lib/site-api-service.ts::getSitePredictionModules` | `public.site-page` / `vendor.homepage-modules` 聚合，逐模块 `load_public_module_history` | 703 KB / **4.1 s**（TTFB），`/api/sites/<key>/site-page` 588 KB / **7.5 s** |
| 首页模块 | `/api/twjinniu/homepage-modules`、`/api/vendor/homepage-modules` | 同上（`modules=` 过滤） | 193 KB / 2.1 s；twcf888 17 KB 却要 **7.1 s** |
| 旧站逐模块资料 | `/api/kaijiang/<endpoint>?web=&type=&num=` → `frontend/app/api/kaijiang/[...path]/route.ts` | `routes/legacy_routes.py::_kaijiang_handler` → `legacy/frontend_compat.py::handle_frontend_kaijiang_api` → `_handle_standard_kaijiang`（`_resolve_endpoint_mode_id` + `get_mode_authorization_for_web_id` + `_resolve_endpoint_table_name` + `_load_mode_payload_rows` + sanitize/format） | 每次 **2.7～2.8 s**（节点 `kj_cache.log` 的 `urt`），**一个旧站页面会调用几十个** |

节点真实日志（nginx 边缘缓存上线后）：

```
MISS n=79  avg_rt=1.9671s  avg_urt=1.9498s  max_urt=6.2780s
  max_urt=6.278s  /api/sites/twsaimahui/prediction-modules
  约 2.7～2.8s    /api/kaijiang/getCypt getYwx getShatou getXysxma getJmxc getShaWei qqsh getDxd …
HIT  n=56  avg_rt=0.0804s（不访问后端）
```

结论：**瓶颈是服务端聚合计算与逐模块查询次数**，不是字节数。nginx 20 秒微缓存已经把重复请求压掉一大截，但每个 TTL 窗口内仍要付一次 2.8～6.3 秒。

### 1.2 载荷形状（实测）

```
/api/kaijiang/getPingte   → {"data":[{"content","res_code","res_sx","term"}, …8 行]}
/api/sites/twssz/prediction-modules
  → {"ok", "site":{site_key,site_id,web_id,…}, "data":{"canonical_modules":[45 × {moduleKey,title,displayKind,rows[{issue,year,term,prediction,result,status,raw}],source}], "compatibility":{…}}}
/api/site-links           → {"links":[{site_key,name,domain,url}]}
```

`res_code`/`res_sx` 是**已开奖期**的公开数据，旧站就是这样公开展示命中结果的；它们必须保留，不能被"安全校验"一刀切禁掉。

## 2. 复用现有设施（不新造轮子）

仓库里已经有完全对口的机制，快照化应当扩展它：

- `backend/src/cache/public_snapshots.py`：`PublicDrawSnapshots`
  - 键布局 `public:draw-snapshot:v1:lottery:<type>:<snapshot_type>:pointer` + `:version:<version>`；
  - `publish_versioned()`（`cache/redis_store.py` 的 Lua 脚本）：**版本键内容不可变**，同版本重复发布幂等、异内容发布被拒；指针键指向当前版本并带 TTL；写指针与写版本在同一脚本内完成。
  - 读路径：先读指针→再读版本→校验信封（`schema_version`/`snapshot_type`/`lottery_type_id`/`published_at`）→校验载荷字段白名单；
  - 读端失败（`CacheUnavailable`）**永远回落到数据库**，不影响响应。
- `backend/src/routes/public_routes.py`（`latest-draw`/`current-period`）：`snapshot 命中 → 直接返回；未命中 → 查库 → `_backfill_*` 尽力回填`。
- `backend/src/outbox/publisher.py` + `scheduler_worker.py`：`draw.published` / `draw.refresh` 事件的租约-重试投递（`drain(limit=…)`），目前只驱动开奖快照；**预测快照的失效与预热挂在这里**。
- `system_config` + 配置服务：作为快照开关的运行时来源（可即时关停，不需要改镜像）。

## 3. 方案

### 3.1 键布局

```
public:prediction-snapshot:v1:web:<web_id>:lottery:<type>:legacy:<endpoint>:pointer
public:prediction-snapshot:v1:web:<web_id>:lottery:<type>:legacy:<endpoint>:version:<version>

public:prediction-snapshot:v1:web:<web_id>:lottery:<type>:site:<history_limit>:pointer
public:prediction-snapshot:v1:web:<web_id>:lottery:<type>:site:<history_limit>:version:<version>

public:prediction-snapshot:v1:web:<web_id>:lottery:<type>:homepage:<modules_hash>:pointer
public:prediction-snapshot:v1:web:<web_id>:lottery:<type>:homepage:<modules_hash>:version:<version>
```

- `web_id` 是站点业务 ID（`managed_sites.web_id`），与现有 `public:site-lottery:v1:id:<site_id>` 缓存共存；**不允许**用 query 里的 `web` 跨站读写（现有 `_handle_standard_kaijiang` 已经按 `web` + `get_mode_authorization_for_web_id` 校验，快照键与之一致）。
- `version = "<期号>-<sha256(payload)[:12]>"`：内容寻址，保证版本键不可变与重试幂等；同一期内容变化（管理员改资料、重算）自然产生新版本并切换指针。
- `endpoint` 只接受白名单字符 `[A-Za-z0-9_-]`（沿用 `_VERSION_RE` 的严格校验）。

### 3.2 载荷校验（安全边界）

新增 `backend/src/cache/prediction_snapshots.py::PublicPredictionSnapshots`，遵循与开奖快照相同的原则：**只存"该 HTTP 端点此刻已经公开返回的 JSON"**，因此不会产生新的暴露面。校验分两层：

1. 结构校验：顶层必须是对象；`legacy` 必须是 `{"data": [...]|{}}`；`site` 必须有 `ok`/`site`/`data`；`homepage` 必须是现有 vendor 聚合 envelope。
2. 禁止字段递归扫描：`_simulation_should_hit`、`should_hit`、`is_opened`、`raw_numbers`、`truth_source` 等内部标记**一律拒绝**（防止未来期生成内部字段被顺手带进 Redis）；命中即拒绝发布并记录一条结构化告警（不含载荷）。

未来期真值的额外防线：
- 预测快照的**指针 TTL 有上限**（默认 300 s，见 3.4），即使有人误发布也只能存活一个 TTL；
- 发布只发生在"HTTP 已经返回过该 JSON"的路径或 worker 调用**同一构建函数**时，不新增读取数据库的旁路；
- 单元测试覆盖"含 `_simulation_should_hit` 的载荷被拒绝发布"。

### 3.3 读路径（第一阶段，收益最大、风险最低）

| 端点 | 改造 |
| --- | --- |
| `GET /api/kaijiang/<endpoint>`（`routes/legacy_routes.py::_kaijiang_handler`） | 先按 `(web_id, type, endpoint)` 读快照；命中直接返回；未命中查库并尽力回填（`publish` 失败只记日志） |
| `GET /api/public/vendor/homepage-modules`、`/api/public/site-page`、站点私有 `prediction-modules`/`site-page`/`homepage-modules` | 先按 `(web_id, type, history_limit/modules_hash)` 读快照；命中直接返回；未命中查库并回填 |

- 失败一律回落数据库：`CacheUnavailable`、校验失败、JSON 解析失败都当作 miss。
- 值班开关：`system_config.prediction.snapshot.enabled`（默认 `0`＝关闭）；读取端每次请求读一次进程内短缓存（≤5 s）的开关值，关闭时完全绕过快照（等价于今天的路径），**不需要改镜像即可紧急关停**。
- 观测：结构化日志 `snapshot=hit|miss|bypass`，字段 `web_id`、`lottery_type_id`、`endpoint`、`history_limit`、`build_ms`；不记录载荷。

### 3.4 TTL 与失效

| 快照 | 指针 TTL | 失效触发 |
| --- | --- | --- |
| `legacy:<endpoint>` | 300 s | 开奖事件（`draw.published`/`draw.refresh`）、预测生成完成、管理员改资料/开奖号码 |
| `site:<history_limit>` | 300 s | 同上 |
| `homepage:<modules_hash>` | 300 s | 同上 |

失效动作 = **删除指针键**（版本键靠 TTL 自然过期）。这样下一个请求会重建并发布新版本；即使失效消息丢失，也最多陈旧 300 s。开奖窗口内（22:32 前后）可以把 `latest-draw` 保持不变，只对预测快照失效，避免开奖路径被拖慢。

### 3.5 预热（第二阶段）

在 `scheduler_worker` 的 outbox 消费循环里，事件处理成功后追加一次**有预算的预热**：

1. 事件给出 `(web_id 或 lottery_type, year, term)`；
2. 取该站点启用模块（`public.site_prediction_modules` + 蓝图）与最近被访问过的 `legacy endpoint` 集合；
3. 在 `budget_ms`（默认 20 s）内按热度顺序构建并发布快照；
4. 超预算即停止并记录，下一轮继续（幂等，因为版本内容寻址）。

热度来源：nginx `kj_cache.log` 里的 `endpoint` 统计（第三阶段可做离线统计表），第一版用固定顺序 + 站点启用模块顺序即可。

## 4. 实施阶段

| 阶段 | 内容 | 交付 | 上线影响 |
| --- | --- | --- | --- |
| P0 | `prediction_snapshots.py` + 读路径（legacy & site）+ 开关 + 单测 | 命中即 KV 读；未命中同今天 | 开关默认关闭 → 打开后逐步验证；随时可关停 |
| P1 | outbox 事件触发失效 + worker 预热 + 日志/指标 | 首访不再是"第一个倒霉蛋" | 只影响 worker，不改变响应 |
| P2 | 前端取数改造（`site-data-adapter` 使用带版本号的一次取数）、nginx TTL 回调（命中快照后可放宽到 60 s） | 进一步减少请求数 | 前端可独立回滚 |

## 5. 验收标准

1. 功能等价：同一 `(web_id, type, endpoint/history_limit)` 下，快照命中与直连数据库返回**逐字节相同**（用现有契约测试 + 快照对比测试证明）。
2. 性能：`/api/kaijiang/*` 命中路径本机 `time_total` ≤ 20 ms（今天 2.7～2.8 s）；`prediction-modules` 命中 ≤ 50 ms（今天 4.1 s）。
3. 安全：含内部标记的载荷被拒绝；Redis 中不存在 `_simulation_should_hit`、未来期 `res_code`/`numbers` 等键值（用扫描测试断言）。
4. 可回滚：`prediction.snapshot.enabled=0` 后 5 秒内所有读路径回到数据库直连；删除指针键即可强制重建。
5. 观测：`snapshot=hit/miss/bypass` 计数、`build_ms` 分位数、Redis 内存占用。

## 6. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 快照陈旧导致命中判定显示过期结果 | 指针 TTL ≤ 300 s + 开奖/生成/后台编辑三类事件失效；后台编辑走同一失效函数 |
| 未来期真值被带进缓存 | 只存已公开响应 + 递归禁止字段 + TTL 上限 + 扫描测试 |
| Redis 不可用 | 所有读写包 `CacheUnavailable`，一律回落数据库（沿用现有模式） |
| 版本键膨胀 | 版本键 TTL = 指针 TTL + 1 s（现有脚本行为），指针切换后旧版本自然过期；另有 `maxmemory`/`maxmemory-policy` 兜底（部署时确认） |
| 预热把 worker 拖住 | `budget_ms` 预算 + 每轮 `limit`，超时即停；预热失败不影响开奖事件投递 |

## 7. 已确认的实现参数（2026-09-24）

- 指针 TTL：**300 秒**；版本 = 载荷内容哈希（前 16 位十六进制），同一内容重复发布幂等。
- 开关：`PREDICTION_SNAPSHOT_ENABLED` 环境变量（默认开启），并支持
  `system_config.prediction.snapshot.enabled` 覆盖（进程内 5 秒缓存，可即时关停）。
- P0 范围：读路径 + 回填（`/api/kaijiang/*`、`/api/vendor/homepage-modules`、
  `/api/public/site-page`）；worker 预热留到 P1。
- 载荷校验按实测形状放宽：`is_opened` 是公开历史行字段（实测 222 行全部 `is_opened=true`，
  未开奖行不进入公开载荷），不再禁止；仍禁止 `_simulation_should_hit`、`should_hit`、
  `truth_source`、`future_truth` 等内部标记。
- 空结果（`{"data": []}`）不写缓存，避免把授权拒绝缓存 300 秒。

## 8. 待确认的三个决策

1. 指针 TTL：**300 s**（推荐，兼顾新鲜度与收益）／60 s（更保守）／900 s（收益最大）。
2. 开关默认值：**默认关闭**，上线后手动打开（推荐）；或默认开启、发现异常再关。
3. P0 范围：**只做读路径 + 回填**（推荐，一次上线风险最小）；或连同 P1 预热一起上线。
