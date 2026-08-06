# 台湾彩开奖高可用架构设计

## 1. 文档状态

- 状态：已确认设计，尚未实施
- 设计日期：2026-08-07
- 适用范围：Liuhecai 公共站点、Python API、开奖与预测调度、缓存、数据库、图片资产及运维监控
- 核心目标：台湾彩开奖时刻 22:32 在访问量升至平时数十倍时，十个现有站点及未来新增站点仍能稳定读取开奖和预测资料

本设计不改变现有 `Site`、`Site Key`、`Site Adapter`、`Compatibility Layer` 和 `Prediction Module` 的领域含义。新增站点继续复用统一 Python API；本次改造解决的是中心 API、数据库、缓存和资产存储的单点与峰值承载问题，不是重新设计多站点模型。

## 2. 已核实的当前架构

### 2.1 仓库约束

- 浏览器访问各站点 `/api/*` 时，先进入 Next.js `Compatibility Layer`，再由前端服务访问 Python 原生 `/api/*`。
- 跨服务器调用使用 `https://www.tw8800.com/central-api/api`，不能将该路径与浏览器侧 `/api/*` 混为一层。
- Python API 使用 `ThreadingHTTPServer`，当前生产只有一个实例。
- `scheduler-worker` 已从 API 进程分离，并通过 PostgreSQL 持久任务和 worker 租约维持单活。
- 正式数据库为 PostgreSQL；PgBouncer 已存在；当前没有 Liuhecai Redis、消息队列或共享对象存储。
- `/uploads/*` 当前读取 Python API 容器中的 `backend/data/Images`，不适合多 API 节点生成和读取动态图片。

### 2.2 2026-08-07 只读核查的服务器现状

| 节点 | 当前 Liuhecai 服务 | 资源概况 | 约束 |
|---|---|---|---|
| 服务器 A `207.56.3.82` | PostgreSQL、PgBouncer、Python API、scheduler-worker、后台、前端、Nginx | 约 8 GiB 内存，根盘约 914 GiB、使用约 26%，无 Swap | 当前中心 API、数据库和调度单点 |
| 服务器 B `207.56.2.71` | 前端、Nginx | 约 8 GiB 内存，根盘约 218 GiB、使用约 12%，无 Swap | 同机还运行独立的 startrace API、worker、PostgreSQL 和 Redis，必须做资源隔离 |

服务器 A 的 Nginx 目前将 `/central-api/api/` 固定转发到单个 `python-api:8000`。服务器 B 当前没有运行 Liuhecai Python API。目标架构必须从这个状态渐进迁移，不能假设两台机器已经是对称的应用节点。

现有 `DEPLOY.md` 的“frontend-only node 不得运行 Python API 或 scheduler-worker”规则描述的是当前架构。目标架构明确改变这一部署边界：服务器 B 将通过新的受控应用节点 Compose/覆盖配置运行一个无状态 Python API 和一个候选 Worker，而不是误用现有 `docker-compose.frontend-node.yml` 或部署完整数据库栈。实现阶段必须同步修订该部署政策、Compose 文件和验收脚本。

## 3. 服务目标与不变量

### 3.1 服务目标

| 指标 | 目标 |
|---|---|
| 公共 API P95 | 小于 500 ms |
| Redis/CDN 缓存命中路径 P95 | 小于 150 ms |
| 开奖主库提交至十站点可读 | 小于 10 秒 |
| PostgreSQL RPO | 0，已确认提交的开奖数据不可丢失 |
| PostgreSQL 自动切换 RTO | 小于等于 60 秒 |
| 只读副本最大可接受延迟 | 5 秒，超过即从读池摘除 |
| 核心开奖服务可用性 | 单个 API 实例或单台应用服务器故障时继续服务 |

节点规格和最终限流数值必须依据基线压测与 10 倍、30 倍、50 倍阶梯压测确定，不能只依据当前空闲资源推算。

### 3.2 业务与发布不变量

1. Future Issue 必须继续生成所有已启用站点必需的 Prediction Module；不得因缓存或多实例改造静默跳过。
2. 缺失未来预测必须留下持久失败/审计记录并发送告警。
3. 开奖只能由持久调度任务执行；多个候选 Worker 仍通过租约保持单活，重启和接管不得重复开奖。
4. `is_opened=0` 的 Future Issue 不是公开开奖结果，任何公共响应、缓存、CDN、日志或异常均不得泄露号码、生肖、波色或命中结果。
5. Redis、CDN、预测生成、流量统计或图片处理失败不得回滚已提交的开奖，也不得阻塞核心开奖发布链路。

## 4. 目标架构

```text
浏览器
  |
  v
[厂商无关 CDN / WAF]
  |- 静态 Vendor Assets 与 Prediction Assets
  |- 各站点公开 GET /api/* 的短时边缘缓存
  |- IP/域名/路径级限流、DDoS 防护、源站健康检查
  |
  +------------------------+------------------------+
  |                                                 |
  v                                                 v
[服务器 A Nginx]                                [服务器 B Nginx]
  |- 前五个站点 Compatibility Layer                |- 后五个站点 Compatibility Layer
  |- HAProxy-A                                     |- HAProxy-B
  |                                                 |
  +--------------------------+----------------------+
                             |
                             v
                     [Python API 无状态集群]
                       |- API-1：服务器 A
                       |- API-2：服务器 A
                       |- API-3：服务器 B
                             |
              +--------------+----------------+
              |              |                |
              v              v                v
       [托管 Redis HA] [托管 PostgreSQL HA] [托管对象存储]
       |- 热点快照      |- 稳定写端点          |- /uploads 资产
       |- 限流计数      |- 稳定只读端点        |- 预测图片
       |- 短租约锁      |- 跨可用区同步复制    |- 生命周期分层
       |- 流量事件缓冲  |- 自动故障切换        +-> CDN
              |              |
              +------+-------+
                     |
                     v
             [scheduler-worker 候选组]
               |- Worker-A：服务器 A
               |- Worker-B：服务器 B
               |- PostgreSQL 租约单活
               |- 持久 scheduler_tasks
               |- Outbox 消费与缓存发布
```

CDN/WAF 或云负载均衡为 `www.tw8800.com/central-api/api` 提供双源站健康检查。两台 HAProxy 负责将请求按 `leastconn` 分配给健康 API 实例。浏览器仍只访问各站点的 Compatibility Layer；`/central-api/api` 仅允许受控前端、后台和运维来源访问。

## 5. 组件职责

### 5.1 CDN/WAF

- 缓存静态 Vendor Assets、Prediction Assets 和明确列入白名单的公开 GET API。
- 缓存键至少包含站点域名、路径、规范化后的完整查询参数和响应版本。
- 不缓存登录、后台、POST、含身份状态的响应或未列入白名单的兼容接口。
- 支持按 URL 或缓存标签定向刷新，开奖后只刷新十站点相关路径，不执行全站清空。
- 对源站进行健康检查，并在服务器 A/B 之间自动切换。

### 5.2 Nginx 与 Compatibility Layer

- Nginx 保留域名、TLS、路径分发和前端入口职责。
- 浏览器侧 `/api/*` 继续进入 Next.js Compatibility Layer，保持现有响应合同和 Site Adapter 行为。
- Next.js 到 Python API 的服务端 fetch 可继续使用 `no-store`，避免 Next.js 内部产生不可控旧数据；Python API 内部由 Redis 缓存。
- 前端对浏览器的公开 GET 响应按缓存白名单输出 `public` 和 `s-maxage`，使 CDN 可以共享缓存。

### 5.3 HAProxy

- HAProxy 是无业务逻辑的 API 负载均衡器，不替换 Python API。
- 使用 `leastconn`，避免长请求或慢实例持续积压连接。
- 对 `/health/live` 执行存活检查，对 `/health/ready` 执行就绪检查。
- 连续失败时摘除实例；恢复后使用慢启动逐步接收流量。
- 设置连接、队列、响应超时和最大并发，拒绝无限堆积。

HAProxy 自身不能成为新单点：服务器 A/B 各部署一个实例，外层 CDN/WAF 或云负载均衡执行双源站切换。

### 5.4 Python API 集群

- 三个实例使用同一镜像和配置合同，不启动任何进程内调度器。
- 第一阶段服务器 A 部署两个实例，服务器 B 部署一个实例。
- 所有进程状态外置到 PostgreSQL、Redis 或对象存储；不依赖实例本地会话和动态文件。
- 公开预测请求只读取已生成的 Prediction Module，不同步执行预测算法。
- 管理写接口、开奖写入和调度写入只使用数据库写端点。
- 历史开奖、公开站点资料等缓存未命中查询可使用只读端点。

### 5.5 托管 PostgreSQL HA

- 选择跨可用区同步高可用规格，提供稳定写端点和只读端点。
- `DATABASE_WRITE_URL` 指向写端点；`DATABASE_READ_URL` 指向只读端点。
- 开奖、后台修改、Outbox、调度任务和需要读己之写的一致性请求走写端点。
- 历史开奖、公开站点资料等允许短复制延迟的查询走只读端点。
- 只读副本延迟超过 5 秒时从读池摘除；缓存命中路径不受副本切换影响。
- 自动故障切换期间，公共 P0 接口返回最近确认的 Redis/CDN 快照，不向数据库制造重试风暴。

应用本地开发继续兼容单一 `DATABASE_URL`：未配置 `DATABASE_WRITE_URL` 时回退到 `DATABASE_URL`，未配置 `DATABASE_READ_URL` 时回退到写连接。

### 5.6 托管 Redis HA

- 保存 Latest Draw、站点首页、当前预测和历史首页等热点快照。
- 保存限流令牌、短周期防击穿锁和流量事件缓冲。
- 不作为开奖事实源；权威开奖必须先提交 PostgreSQL。
- Redis 不可用时，P0 优先返回 CDN 或进程内最近确认快照；禁止所有请求直接击穿主库。
- 开发环境可使用实现相同接口的进程内缓存；分布式语义必须用真实 Redis 集成测试验证。

### 5.7 scheduler-worker 与持久任务

- 服务器 A/B 各运行一个候选 Worker，但只有获得现有 PostgreSQL worker 租约者执行任务。
- 保留 `scheduler_tasks` 和持久任务记录，不因引入 Redis而替换为临时队列。
- Worker 处理开奖、预测生成、缺失预测审计、Outbox、缓存预热、缓存失效和资料清理。
- Redis 分布式短锁只用于缓存重建等非权威互斥，不能代替开奖任务的 PostgreSQL 租约与持久锁。

### 5.8 对象存储

- 新生成 Prediction Assets 和上传文件写入 S3 兼容托管对象存储。
- 数据库保存稳定对象键或公开 URL，不保存实例本地绝对路径。
- `/uploads/*` 在迁移期保留旧路径兼容，通过网关映射至对象存储或旧文件回源。
- API 容器不再是动态资产唯一副本；任一 API 实例都能返回相同资产地址。

## 6. 开奖发布关键流程

```text
持久开奖任务到期并取得 Worker 租约
  -> 读取/生成待开奖数据
  -> 校验期号、重复开奖和数据完整性
  -> PostgreSQL 写事务：
       1. 将该期标记为 Opened Draw
       2. 写权威开奖字段
       3. 写唯一 Outbox 事件 draw-published:{lottery_type}:{term}
  -> 事务提交成功
  -> Outbox 消费者构建 Latest Draw 快照
  -> Redis 以版本化键写入新快照
  -> 原子切换 latest 指针
  -> 定向刷新十站点开奖相关 CDN 缓存
  -> 小于 10 秒完成 P0 发布
  -> 异步入队预测生成、缺失预测审计、图片生成和统计任务
```

禁止采用“先删除旧缓存，再查询数据库重建”的流程。新快照完全生成后才切换指针；旧版本保留一个短回退窗口，避免发布中间态和缓存击穿。

Outbox 事件必须有唯一业务键并支持重复消费。消费者重试只能重复写入同一版本快照，不得重复开奖。

## 7. 缓存设计

### 7.1 建议缓存键

```text
v1:draw:{lottery_type}:latest:pointer
v1:draw:{lottery_type}:{term}
v1:site:{site_key}:home:{published_version}
v1:site:{site_key}:prediction:{term}:{published_version}
v1:draw:{lottery_type}:history:{year}:{page}:{page_size}
v1:site:{site_key}:notice:{version}
```

缓存键使用 `Site Key`，不得用可混淆的域名字符串或客户端可覆盖的 `web` 参数替代站点身份。

### 7.2 建议 TTL 与边缘策略

| 数据 | Redis | CDN 响应建议 |
|---|---:|---|
| 最新开奖 | 5 分钟并由事件刷新 | `s-maxage=2, stale-while-revalidate=8` |
| 站点首页聚合 | 5 分钟并由事件刷新 | `s-maxage=15, stale-while-revalidate=45` |
| 当前预测 | 10-30 分钟并由生成事件刷新 | `s-maxage=15, stale-while-revalidate=45` |
| 历史开奖 | 30 分钟 | `s-maxage=60-300` |
| 公告与站点链接 | 5-15 分钟 | `s-maxage=60-300` |

TTL 是兜底回收机制，开奖和预测更新主要依赖事件发布和定向失效。所有公开缓存必须继续执行 Future Issue 脱敏；未开奖真值绝不能进入 Redis 或 CDN。

### 7.3 预热时间表

- T-10 分钟：预热十站点首页、开奖页、当前预测、公告和站点配置。
- T-2 分钟：生成并发布“待开奖”安全快照；提高 P0 监控频率。
- T0：开奖事务提交后执行版本化快照发布。
- T+1 分钟：验证十站点 CDN 回源与新期号一致。
- T+5 分钟：执行预测缺失审计，逐步恢复正常限流和后台任务优先级。

## 8. 限流、熔断与降级

### 8.1 优先级

| 等级 | 请求 | 策略 |
|---|---|---|
| P0 | 最新开奖、首页开奖摘要、下期时间 | 最高优先级，缓存快照优先 |
| P1 | 当前预测、近期历史开奖 | 缓存优先，允许短时旧数据 |
| P2 | 搜索、复杂筛选、文章统计 | 严格限流，必要时拒绝 |
| P3 | 报表导出、批量管理、非必要图片生成 | 开奖窗口暂停或低优先级排队 |

### 8.2 限流维度

- CDN/WAF：来源 IP、站点域名、路径、User-Agent 和异常请求模式。
- HAProxy：连接数、请求队列、后端并发和超时。
- Python API：Site Key、接口类别和请求身份。
- Redis：滑动窗口或令牌桶计数；限流 Redis 故障时采用进程内保守阈值。

最终数值由压测确定。初始验证可从 Latest Draw 每 IP 每分钟 20 次、预测每 IP 每分钟 60 次、复杂查询每 IP 每分钟 10 次开始，但不能未经压测直接作为生产最终值。

### 8.3 降级顺序

1. 正常：CDN -> Compatibility Layer -> Redis -> 只读副本。
2. Redis 故障：CDN/进程最近确认快照；禁止热点请求全部击穿数据库。
3. 只读副本故障：对 P0/P1 返回缓存；仅少量受控查询回退写端点。
4. 主库切换：继续返回已确认快照，暂停非必要写入，等待托管数据库写端点恢复。
5. 严重过载：仅保障 P0；P1 返回旧缓存；P2/P3 快速失败或暂停。

所有降级响应必须携带 `updated_at` 或等价更新时间，不得将旧结果伪装为新一期。

## 9. 流量事件与异步任务

`POST /api/public/traffic-events` 当前同步写入 PostgreSQL。开奖窗口改为：

- 按站点与事件类型采样；具体采样率由压测和报表精度要求确定。
- 将事件批量缓冲到 Redis，由 Worker 分批写入数据库。
- Redis 不可用时允许丢弃 Traffic Event；不得影响用户读取开奖。
- Traffic Metrics 明确属于近似统计，不作为计费、开奖或预测正确性的事实源。

开奖与预测继续使用 PostgreSQL 持久任务，不依赖可丢失的 Redis 队列。

## 10. 前后端部署分组与新增站点

### 10.1 分组逻辑

- 前端按现有站点部署分布保留：服务器 A/B 各承载五个站点；站点通过 Host、Site Key、Vendor Assets 和 Site Adapter 隔离。
- 后端按运行职责隔离：无状态 Python API 集群、单活持久 Worker、托管数据服务和对象存储。
- 不按站点复制 Python API、数据库、Redis 或 Worker。
- 特别高流量站点未来可获得独立 Compatibility Layer 实例或 CDN 规则，但仍使用统一公共数据平台。

### 10.2 新增站点配置面

新增 Site 时需要：

1. 在现有站点注册表/`managed_sites` 中创建 Site 与稳定 Site Key。
2. 配置域名、Lottery Type、Vendor Assets、Site Adapter 和 Prediction Module 授权。
3. 在 CDN/WAF 添加域名、证书、公开 GET 缓存白名单和限流策略。
4. 在前端节点添加 Host 路由和站点构建/运行配置。
5. 将首页、开奖、预测接口加入预热清单和十秒发布验证。
6. 添加该站点的生成、缺失告警、Compatibility Layer 合同和未来真值脱敏测试。

无需为新 Site 新建 Python API、数据库或调度器。

## 11. 本地开发与环境分层

### 11.1 配置回退合同

| 能力 | 本地快速开发 | 本地集成 | 生产 |
|---|---|---|---|
| 数据库 | Windows 原生 PostgreSQL，现有 `DATABASE_URL` | 同左 | 托管 HA 写/读端点 |
| 缓存 | 进程内缓存适配器 | Redis 容器 | 托管 Redis HA |
| 资产 | `backend/data/Images` | MinIO/S3 测试桶 | 托管对象存储 |
| API | 单实例 `127.0.0.1:8000` | 单实例 | 三实例 + HAProxy |
| Worker | 按需单独启动 | 单候选 Worker | 双候选、租约单活 |

配置解析规则：

```text
DATABASE_WRITE_URL -> 未配置则 DATABASE_URL
DATABASE_READ_URL  -> 未配置则写连接
CACHE_BACKEND      -> development 默认 memory，production 必须 redis
STORAGE_BACKEND    -> development 默认 filesystem，production 必须 s3
```

本地继续使用现有命令，不需要模拟 CDN、HAProxy 或 PostgreSQL 自动切换：

```powershell
python backend/src/app.py --host 127.0.0.1 --port 8000
pnpm dev:frontend
pnpm dev:backend-admin
```

修改缓存原子发布、读写分离、对象存储或故障恢复时，必须进入本地集成或预发布环境验证，不能以进程内替身的结果代替分布式测试。

## 12. Prediction Assets 生命周期与磁盘管理

- `lottery_draws` 和权威开奖历史永久保留。
- Prediction Module 的历史数据库记录保留可查询状态。
- Prediction Assets 生成后立即进入对象存储；本地只允许有限临时工作目录。
- 超过 180 天的 Prediction Assets 迁移至对象存储低频层；临时缓存和无引用中间文件删除。
- 删除前必须通过数据库对象键或资产清单确认无当前页面引用，禁止按文件名模糊删除。
- 对象存储生命周期任务和服务器清理任务必须输出审计记录、删除数量、释放空间和失败清单。

磁盘告警：

| 使用率 | 动作 |
|---:|---|
| 70% | 邮件预警，检查日志、备份、预测临时目录和 Docker 占用 |
| 80% | 高优先级告警，执行受控清理并停止低优先级资产任务 |
| 90% | 严重告警，暂停非必要图片生成和低优先级任务，保障开奖链路 |

每天检查磁盘、inode、Docker 日志、备份大小、临时资产和对象存储同步积压。清理任务不得删除数据库、当前 Prediction Module 使用的资产或未完成同步的本地文件。

## 13. 发布与迁移步骤

### 阶段 0：基线与保护

1. 记录正常时段和 22:32 前后的 QPS、P95/P99、数据库连接、慢查询和端到端开奖发布时间。
2. 为服务器 A/B 上所有业务容器配置 CPU、内存和日志限制，尤其隔离服务器 B 上的 startrace 服务。
3. 建立磁盘、API、Worker、开奖和预测缺失告警。
4. 对现有 API 合同和 Future Issue 脱敏建立回归基线。

### 阶段 1：应用可横向扩展

1. 新增 liveness/readiness/dependency 健康接口。
2. 移除 API 实例本地动态状态依赖。
3. 引入数据库读写端点配置，但本地保持 `DATABASE_URL` 回退。
4. 新建受控应用节点 Compose/覆盖配置，明确允许服务器 B 运行一个无状态 API 与一个候选 Worker，但不允许其运行 Liuhecai PostgreSQL、PgBouncer、Redis、迁移或后台管理服务。
5. 部署三 API 实例和双 HAProxy，先在预发布环境完成负载与故障测试。

### 阶段 2：托管数据服务

1. 建立托管 PostgreSQL HA、Redis HA 和对象存储。
2. 完成数据库备份、校验、迁移和回滚预案；生产迁移必须单独获得服务器操作授权。
3. 接入 Redis 缓存适配器、Outbox 和版本化发布。
4. 将动态 Prediction Assets 迁移至对象存储并保留旧路径兼容。

### 阶段 3：边缘缓存与降级

1. CDN/WAF 按白名单启用公开 GET 缓存，不得笼统缓存所有 `/api/*`。
2. 接入多源站健康检查、定向刷新和限流。
3. 实现开奖窗口预热、Redis/数据库故障降级和流量事件采样。

### 阶段 4：切流与演练

1. CI 构建同一 API 镜像；迁移只运行一次且必须向后兼容。
2. 以 5%、25%、50%、100% 逐级切流，观察每级 P95、错误率和缓存命中率。
3. 演练 API 实例故障、服务器 A/B 故障、Redis 切换、数据库主库切换、只读副本延迟和对象存储超时。
4. 未满足服务目标或发布不变量时立即停止放量并回滚应用流量；不得回滚已确认的开奖事实。

## 14. 发布审查门槛

任何影响预测生成、开奖、调度、缓存发布、公共 API 或数据脱敏的改动，发布前必须执行：

```powershell
pwsh -File .\skills\prediction-release-review\scripts\run-regression.ps1
```

必须同时提供：

- `generation` 通过证据；
- `missing-alert` 通过证据；
- `scheduled-draw` 通过证据；
- `public-redaction` 通过证据；
- 新增多实例、Redis、Outbox、对象存储、读写分离和降级路径的专项测试；
- 预发布环境的并发与故障切换结果。

测试未全部通过，不得批准、合并或部署相关变更。现有服务器上的发布、迁移、重启和配置修改仍需在每次操作前获得明确授权。

## 15. 运维监控

### 15.1 指标

- CDN：命中率、回源率、各 Site 流量、限流和 WAF 拦截。
- HAProxy：活动连接、请求队列、实例健康、重试、摘除与慢启动。
- API：各接口 QPS、P50/P95/P99、5xx、超时、缓存命中来源和数据库回退次数。
- Redis：命中率、内存、淘汰、慢命令、连接、复制和故障切换。
- PostgreSQL：写/读连接、复制延迟、锁等待、慢 SQL、事务失败和故障切换。
- Worker：租约持有者、心跳、任务积压、重试、失败、缺失预测和 Outbox 延迟。
- 开奖：任务到期、主库提交时间、Redis 发布时间、十站点可读时间和期号一致性。
- 资产：上传失败、对象存储延迟、180 天生命周期执行结果、本地临时目录和磁盘使用率。

### 15.2 开奖窗口值班看板

22:20 至 22:45 至少显示：

- 最新 Opened Draw 期号和主库提交时间；
- Redis latest 指针版本；
- 十站点 CDN/Compatibility Layer 返回期号；
- API P95/P99、错误率和缓存命中率；
- Worker 租约、任务积压、预测缺失和邮件告警状态；
- 数据库主节点、只读副本延迟和 Redis 主节点状态；
- 两台服务器 CPU、内存、网络、磁盘和容器重启状态。

## 16. 验收场景

1. 平时流量 50 倍压测下，缓存命中请求 P95 小于 150 ms，整体 P95 小于 500 ms。
2. 同一时刻十站点轮询 Latest Draw，数据库查询量不会随用户请求线性增长。
3. 任一 Python API 实例停止后，HAProxy 自动摘除，用户无明显中断。
4. 服务器 A 故障时，服务器 B 与 CDN/托管服务继续提供最近确认开奖；反向场景同样成立。
5. PostgreSQL 自动提升完成时间不超过 60 秒，已提交开奖不丢失。
6. Redis 故障时不发生主库请求风暴，P0 返回最近确认快照。
7. 同时启动两个 Worker 时只有租约持有者开奖，接管后不重复开奖。
8. Prediction Module 生成失败不阻塞开奖发布，并产生持久失败记录与邮件告警。
9. Future Issue 的结果字段不进入任何公共响应、Redis、CDN、日志或异常。
10. 新增 Site 只增加注册、前端/CDN配置、预热清单和测试，不新增专属后端。
11. 超过 180 天的 Prediction Assets 正确分层或清理，权威开奖和历史预测记录不丢失。
12. 磁盘达到 70%、80%、90% 时分别触发预定告警与降级动作。

## 17. 非目标

- 不在本阶段将现有 PostgreSQL 持久任务替换为 Kafka、RabbitMQ 或 Celery。
- 不拆分为按站点部署的后端服务或数据库。
- 不要求本地开发运行生产级高可用拓扑。
- 不改变现有 Compatibility Layer 的公共响应合同。
- 不将 Redis 或 CDN 作为开奖事实源。
- 不在本设计阶段执行任何生产部署或远程配置修改。
