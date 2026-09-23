# 第 4 项：消除"每请求跨节点公网回源"（2026-09-24）

目标（用户四项中的第 4 项）：前端节点不要再为每个请求跨公网回中心节点，并评估是否需要
Next 多副本。本文记录实测证据、已实施的改动、以及"多副本"为什么暂不做。

## 1. 现状与实测

前端节点 `207.56.2.71` 上，Next.js 的每个 `/api/*` 请求都会按
`LOTTERY_BACKEND_BASE_URL=https://www.tw8800.com/central-api/api` 跨公网回到中心节点，
链路是：浏览器 → 本地 nginx → 本地 Next 路由 → **公网 HTTPS 到中心** → 中心 nginx →
python-api → pgbouncer → PostgreSQL。

关键发现（本轮修正了一个此前的误判）：

1. 前端 `/api/kaijiang/<endpoint>`（旧站一页几十次）**主路径并不是** Python 的
   `/api/kaijiang/*`，而是 Next 路由转成 `/api/legacy/module-rows?modes_id=&limit=&web=&type=`
   调用 Python（`frontend/app/api/kaijiang/[[...path]]/route.ts`）。Python 的
   `/api/kaijiang/*` 只是未映射端点的兜底。
2. 因此第一版快照（只覆盖 `/api/kaijiang/*`）**没有命中真实热路径**：Redis 里只有 2 个键，
   真实访客（`web=4`）的流量全部走 `/legacy/module-rows`。
3. 单次 Python 侧构建只要 `build_ms=55`；nginx 日志里 2.7～2.8 秒的 `urt` 主要来自
   高并发爆发下"nginx → Next.js → python-api"链路的排队，而不是单条查询。
4. 节点资源（实测，凌晨低峰）：中心节点 8 vCPU / 7.7 GB，`frontend` CPU 7.66%、
   内存 78 MB，`python-api` 0.02% / 48 MB，load 0.15；前端节点 `frontend` CPU 0.00% /
   51 MB。**没有任何 CPU/内存饱和迹象。**

## 2. 已实施：Next 进程内短缓存 + 并发合并（"本地缓存"）

新增 `frontend/lib/upstream-cache.ts`，并在唯一的取数收口点
`frontend/lib/backend-api.ts::backendFetchJson` 接入（只作用于 GET、无 body）：

- 分档 TTL：开奖三接口 3 秒；`/public/site-page`、`/vendor/homepage-modules`、
  `/legacy/module-rows` 60 秒；`/legacy/current-term` 15 秒；`/public/site-links` 30 秒；
  `/public/forced-announcement` 5 秒；其余 0（不缓存）。
- **进行中请求合并**：同一 URL 的并发调用只回源一次（旧站一页几十个并发请求是关键场景）。
- 失败不缓存；容量上限 400 条；`LOTTERY_UPSTREAM_CACHE=0` 可整体关停。
- 契约：`frontend/test/upstream-cache-contract.mjs`（分档、命中、并发合并、过期、失败不缓存、
  关停、容量上限）。

覆盖的跨节点路径：`/api/kaijiang/*`（经 Next 路由 → `/legacy/module-rows`）、
`/public/site-page`、`/vendor/homepage-modules`。三个薄的直通代理
（`/api/latest-draw`、`/api/next-draw-deadline`、`/api/draw-history`）仍各自 fetch，
它们载荷只有 105～748 字节且已被本地 nginx 3～30 秒微缓存覆盖，故本轮不改。

## 3. 已实施：补齐真实热路径的后端快照

后端新增快照 kind `legacy-rows`，并接入 `/api/legacy/module-rows`
（`backend/src/routes/legacy_routes.py::module_rows`）：载荷形状是
`{modes_id,title,table_name,rows}`（没有 `data` 键），键为
`public:prediction-snapshot:v1:legacy-rows:web<id>:lottery:<type>:rows-<modes_id>-<limit>-<digest>`，
空 `rows` 不缓存（避免把"无数据/未授权"缓存 300 秒）。
这样即使跨节点请求到达中心，也是一次 KV 读而不是重新查表聚合。

## 4. "Next 多副本"：本轮不做，给出触发条件

实测（见 §1.4）显示前端进程 CPU 长期接近 0、内存 50～78 MB，瓶颈在跨节点链路的排队，
而排队已由三层缓存吸收：本地 nginx 微缓存（3/5/20 秒 + 并发合并）、Next 进程内缓存
（3～60 秒 + 并发合并）、中心 python-api 快照（KV 读）。

因此**不部署多副本**，理由与替代方案：

| 方案 | 收益 | 代价 |
| --- | --- | --- |
| 现在：三层缓存 | 重复请求 0 次回源；实测旧站十端点 0.819 s → 0.061 s | 首次/过期请求仍跨节点一次（实测约 94 ms 热路径） |
| Next 多副本 + nginx upstream | 并发 SSR/取数能力翻倍 | 内存翻倍；`proxy_pass http://$be_frontend` 用了变量 + DNS，多副本需要改写成 `upstream` 块并放弃变量（改配置面更大）；缓存各自独立、命中率下降 |
| 内网直连（专线/WireGuard 或限制源 IP 的明文端口） | 去掉公网 RTT 与 TLS | 需要网络与安全改动，收益约 94 ms/次 |

**触发条件（满足任一即重启多副本评估）**：高峰期（12:00～12:20、22:30～22:45）
`liuhecai-frontend` CPU 持续 >70%；或 Node 事件循环延迟 >200 ms；或
`kj_cache.log` 中 MISS 占比在高峰期 >50% 且 `rt` 分位数明显上升。

## 5. 回滚

- 前端：`LOTTERY_UPSTREAM_CACHE=0` 立即退化为直连（无需改镜像），或回滚 `backend-api.ts`。
- 后端：快照开关 `PREDICTION_SNAPSHOT_ENABLED=0`；
  `/api/legacy/module-rows` 的改动只增加了一次缓存查询，关停后与改动前完全一致。
