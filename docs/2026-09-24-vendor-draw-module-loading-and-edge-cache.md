# 十个站点开奖模块加载机制分析与加速（2026-09-24）

本文回答两个问题：**开奖模块和预测资料不是异步加载的吗，为什么还卡？** 以及
**该从哪一层提速（重设架构 / 加大带宽 / 其他）**。结论基于代码走查 + 公网实测 +
改造后在节点上的真实缓存日志。

## 1. 结论先说

开奖模块与预测资料在**网络层确实是并发**发起的，卡顿来自四个叠加因素：

1. **关键路径太长**：开奖面板处在 3～4 层同源 iframe 链的末端，每一层文档都要
   一次串行往返，面板自己的两次接口调用还是串行的。
2. **同源 frame 共享主线程**：父页面解析 React 水合、旧站 JS 和几百 KB JSON 时，
   面板的脚本执行与渲染只能排队 —— 网络并行 ≠ 渲染并行。
3. **源站接口本身很慢**：节点日志实测旧站预测资料接口（`/api/kaijiang/*`）每次
   回源 **2.7～2.8 秒**，`/api/sites/<site>/prediction-modules` 实测 **6.28 秒**；
   而开奖接口只有 100～500 毫秒。一个旧站页面会调用几十个预测模块接口，全部压在
   **同一个单进程 Next.js** 上，开奖的小请求被排在后面。
4. **没有任何缓存层**：nginx 的 `/vendor/**`、`/api/**` 全部代理给那个单进程，
   客户端还带 `no-store` 与 `_ts` 破缓存；开奖窗口内每 5 秒轮询一次。

因此：**加大带宽基本无效**（开奖接口只有 105～520 字节），重设架构有效但成本最高，
最划算的是"边缘缓存 + 静态直出 + 前端关键路径收敛"。

## 2. 实测数据（改造前）

| 请求 | 载荷 | TTFB（经本机出口） |
| --- | --- | --- |
| `/api/next-draw-deadline`（面板第 1 步） | 105 B | 0.95 s |
| `/api/latest-draw`（面板第 2 步） | 520 B | 1.30 s |
| 静态 `kj/local.html`（基线） | 39 KB | 0.91 s |
| `/api/twcf888/homepage-modules` | 17 KB | 7.15 s |
| `/api/sites/twssz/prediction-modules` | 703 KB | 4.09 s |
| `/api/sites/twjinniu/site-page` | 588 KB | 7.51 s |

17 KB 的接口要 7 秒，说明**瓶颈是服务端聚合计算，不是字节数**。

### 面板所处的 iframe 层级（改造前）

| 站点 | 入口 | 到面板的文档层数 | 面板创建方式 |
| --- | --- | --- | --- |
| twjinniu / twcf888 / twcaibawang | Next.js 页 → 厂商首页 iframe | 3 | 静态 iframe |
| twssz / twwanli / twsyw | 厂商首页 → `kai.html` | 4 | `kai.html` 的 `KJTB` 脚本注入 |
| twjsz666 | 厂商首页 → `kai.html` | 4 | **3 个静态面板 iframe（台/澳/港）→ 一次访问 6 个开奖请求** |
| twbst528 | 厂商首页 | 3 | `KJTB.init` 注入 |
| twsaimahui | 厂商首页 | 3 | `static/js/kj.js` 动态创建 |

### 首次访问体积（改造前）

- `twcaibawang`：164 个 `<img>`、**0 个 lazy**、图片 23.1 MB（单张最大 1.18 MB）。
- `twssz`：`index.html` **1.16 MB**，其中 173 处内联 base64 图片（去重后仅 18 张）。
- `twsaimahui`：**119 个 `<script src>`**。

## 3. 本次改造（第 1 层：前端）

| 改动 | 文件 | 效果 |
| --- | --- | --- |
| 开奖面板并发取数：`load()` 与 `fetchCountdownDeadline()` 同时发起 | `frontend/public/vendor/shengshi8800/kj/local.html` | 首屏出号少一个串行往返 |
| 面板新增 5 秒新鲜窗口的 sessionStorage 缓存 + 进行中请求去重；手动刷新直连 | 同上 | 切换彩种/重建面板不再重复拉同一期；轮询去重 |
| `twjsz666` 只保留一个静态面板，其余彩种点选时按需创建 | `frontend/public/vendor/twjsz666/kai.html` | 单次访问开奖请求 6 → 2 |
| `twssz` 内联 base64 图片外置为 `/static/` 文件（18 张） | `frontend/public/vendor/twssz/index.html` | HTML **1,161,349 → 411,322 字节（−65%）**；图片可 immutable 缓存 |
| `twcaibawang` 内容图片加 `loading="lazy" decoding="async"` | `frontend/components/twcaibawang/TwcaibawangHomeClient.tsx` | 首次访问不再一次性拉 23 MB |
| `twcaibawang` 服务端两次聚合改并发（保留彩种不一致时的回退） | `frontend/app/twcaibawang/page.tsx` | 首屏 HTML 少一个完整往返 |

契约测试：`frontend/test/kj-panel-loading-contract.mjs`、
`frontend/test/vendor-static-weight-contract.mjs`、
`frontend/test/twcaibawang-first-paint-contract.mjs`。

## 4. 本次改造（第 2 层：nginx 边缘缓存 + 静态直出）

由 `scripts/patch-nginx-edge-cache.py` 注入到两台节点实际生效的配置
（`deploy/nginx.conf.local`、`deploy/nginx.frontend-node.conf.local`），幂等可重复执行。

- **http 层**：`proxy_cache_path ... keys_zone=kj_api:16m`、`gzip on`（`gzip_types` 含
  JSON/JS/CSS）、`log_format kj_timing`（`rt=`/`urt=`/`ucs=`）。
- **每个对外 server 块**的缓存 tier：
  - 3 秒：`/api/latest-draw`、`/api/next-draw-deadline`、`/api/site-links`
  - 5 秒：`/api/sites/<site>/draw`
  - 20 秒：`/api/kaijiang/`、`/api/public/forced-announcement`、`/api/index/notice`、
    `/api/sites/<site>/{prediction-modules,site-page}`、
    `/api/<site-or-vendor>/{homepage-modules,site-page,article-detail}`
  - 全部启用 `proxy_cache_lock`（并发合并）、`proxy_cache_use_stale updating`、
    `proxy_cache_background_update`、`proxy_ignore_headers Cache-Control`、
    `proxy_hide_header Set-Cookie`、`proxy_set_header Accept-Encoding ""`（缓存存未压
    缩体，由 nginx 按客户端压缩，避免缓存了 gzip 响应发给不支持 gzip 的客户端）。
- **`/vendor/**` 静态直出**：nginx 直接读宿主仓库 `frontend/public`（挂载到
  `/srv/public`），`/vendor/<site>/static/**` 保持 `max-age=31536000, immutable`，
  其余 HTML/根级 JS 保持 `max-age=0, must-revalidate`（部署后立即生效）；
  `try_files $uri @vendor_frontend` 确保未命中时**回落到 Next.js**。
  两个必须继续走应用的旧路径 `/vendor/<site>/(history|wylhc).html` 单独保留代理。

> ⚠️ 因为 `/vendor/**` 现在由宿主仓库直出，**部署必须先 `git pull` 再重建 `frontend`**，
> 否则磁盘上的静态资源会与镜像版本不一致。

## 5. 改造后实测（节点上的真实日志）

中心节点 `/var/log/nginx/kj_cache.log`：

```
HIT      n=56  avg_rt=0.0804s  max_rt=0.5010s  （不访问后端）
MISS     n=79  avg_rt=1.9671s  max_rt=6.3910s  avg_urt=1.9498s max_urt=6.2780s
STALE    n=10  avg_rt=0.0148s  （边更新边返回旧值）
UPDATING n=11  avg_rt=0.0000s  （并发合并期间直接返回）
```

回源耗时（`urt`）排行（改造前必须由每个访客各自承担）：

```
miss n=1 avg_urt=6.278s  /api/sites/twsaimahui/prediction-modules
miss n=1 avg_urt=2.838s  /api/kaijiang/getCypt
miss n=1 avg_urt=2.821s  /api/kaijiang/getYwx
miss n=1 avg_urt=2.813s  /api/kaijiang/getShatou
miss n=1 avg_urt=2.810s  /api/kaijiang/getXysxma
miss n=3 avg_urt=2.708s  /api/kaijiang/getShaXiao
...（十余个旧站预测模块接口均在 2.7～2.8 秒）
```

并发合并验证（30 个并发相同请求，`proxy_cache_lock`）：

```
29 ucs=HIT   1 ucs=STALE   其余为并发期间直接返回
=> 后端只被请求一次
```

前端节点：`/api/latest-draw` 回源耗时从"本地 Next → 公网中心 → 中心 Next →
python-api"降到 **avg_urt=0.094s**（中心节点已缓存该接口）。

## 6. 仍然建议的后续项（未做）

1. **预测资料快照化**（第 3 层）：把 588 KB～703 KB 聚合按
   `(site, lottery_type, 期号)` 预生成为快照（Redis 或物化行），回源从"多模块
   查询 ×2.8 秒"变成一次 KV 读。这是根治"预测资料拖慢开奖"的手段。
2. 前端节点本地缓存/内网直连中心，去掉每个请求的公网往返。
3. Next.js 多副本（现在十站共用一个单进程），或至少 2 vCPU 起步。
4. nginx 之外再加 CDN 承担 `/vendor/**`（资源已是 immutable，改造成本低）。
5. 图片体积治理（`twcaibawang` 23 MB 首次访问）与 `twsaimahui` 119 个 script 合并。
6. 继续减少 iframe 层数：把面板并入入口页，去掉 `kai.html` 中转。

## 7. 复现与回滚

```powershell
# 补丁（幂等；--apply 才写回，默认 dry-run）
python scripts/patch-nginx-edge-cache.py <conf>                  # dry-run
python scripts/patch-nginx-edge-cache.py <conf> --apply --backup-dir <dir>
python scripts/patch-nginx-edge-cache.py <conf> --add-access-log --apply --backup-dir <dir>
# 校验与生效（在节点上）
docker exec liuhecai-nginx nginx -t
docker exec liuhecai-nginx nginx -s reload
```

回滚：恢复备份目录里的 `nginx.conf.local` / `nginx.frontend-node.conf.local` 与
`docker-compose*.yml`，然后 `nginx -t` + `nginx -s reload`（挂载回滚需
`docker compose up -d nginx`）。
