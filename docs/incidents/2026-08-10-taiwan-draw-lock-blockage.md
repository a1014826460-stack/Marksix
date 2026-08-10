# 2026-08-10 台湾彩开奖锁阻塞事故复盘

## 状态

- 事故时间：2026-08-10 22:32（Asia/Hong_Kong）
- 影响彩种：台湾彩
- 影响范围：到期 Opened Draw 切换、后续开奖写入与依赖该状态的后续流程
- 已恢复事实：`2026/222` 是该时刻的真实到期期号；其 `is_opened` 已恢复为 `1`，对应 `taiwan_precise_open` 持久任务已完成。
- 本文不记录 Future Issue 的号码、结果或其他可被误用为开奖真值的数据。

## 事实与边界

`2026/222` 的 `draw_time` 为 `2026-08-10 22:32:00`。持久任务
`taiwan_precise_open:2026-08-10` 已被拥有 PostgreSQL worker 租约的
`scheduler-worker` 在 22:32 后认领，因此故障不是任务丢失、Worker
未运行、Redis 故障或 Outbox 故障。

期号 `2026/223` 不属于该时刻的到期期号；它应为下一日的 Future Issue。
事故排查还发现未来期序列存在缺口。Future Issue 中的预置号码不构成
开奖真值，不能通过手工把它标为已开奖来“修复”当前开奖。

## 直接原因

开奖任务已进入 `running`，随后在以下权威写入处阻塞：

```sql
UPDATE lottery_draws
SET is_opened = 1, updated_at = ...
WHERE id IN (...)
```

PostgreSQL 中存在一个来自应用网络的会话，在写入 `system_config` 后保持
`idle in transaction` 超过 32 分钟。该未结束事务持有事务锁；开奖更新
等待该锁，后续对同一开奖记录的写入也逐级排队。任务处于 `running` 时，
既有调度重试不会接管它，因此公开读取继续返回上一期。

处置只终止了已确认的、空闲且超时的阻塞会话。锁释放后，原持久开奖任务
继续提交；没有手工伪造开奖结果、没有将 Future Issue 提前公开，也没有
回滚已确认开奖事实。

## 根因

1. **事务生命周期缺陷**：某条 `system_config` 写入调用链没有在请求或任务
   边界可靠地提交或回滚，留下 `idle in transaction` 会话。
2. **开奖写入允许无限锁等待**：权威开奖事务缺少短 `lock_timeout` 与有限
   `statement_timeout`，使任务卡在 `running`，而不是显式失败并进入持久重试。
3. **关键任务可观测性不足**：健康检查证明 Worker 租约有效，但没有把
   “到期开奖任务长时间 running”“锁等待”“idle in transaction”作为阻断性
   健康信号和告警。
4. **未来期完整性未作为不变量**：台湾未来期补齐按数量满足，而没有验证从
   最新 Opened Draw 后开始的连续期号和连续开奖日期，导致 Future Issue 可有
   缺口。

## 不可破坏的不变量

1. 开奖只由持久 `scheduler_tasks`、worker lease 和 PostgreSQL 权威事务完成。
2. 开奖事务提交时，Opened Draw 状态与唯一 Outbox 事件必须原子可见；缓存、
   CDN、预测、流量和图片任务不能阻塞或回滚该提交。
3. Future Issue 只能用于生成预测和管理员编辑；`is_opened=0` 的号码、生肖、
   波色及命中信息绝不能进入公共响应、缓存、CDN、日志、异常或事故文档。
4. 每个启用彩种从最新 Opened Draw 的下一期开始，必须有连续的 Future Issue
   覆盖最小保留窗口；缺期是 P0 数据完整性故障，不得以跳过期号处理。
5. 每个启用 Site 的每个必需 Prediction Module 都必须为目标 Future Issue
   生成非空预测。预测失败必须有持久失败记录与告警，但不能阻塞开奖。

## 防复发要求

### 事务与锁

- 所有数据库写入路径必须在请求/任务边界明确 commit 或 rollback；禁止把
  连接带出事务作用域。
- 生产 PostgreSQL 必须配置 `idle_in_transaction_session_timeout`；应用必须
  在超时后正确重试或报告失败。
- 开奖、Outbox、调度状态写入必须使用有限的 `lock_timeout` 和
  `statement_timeout`。锁超时必须使任务留下失败原因并进入既有持久重试，
  不得无限 `running`。

### 调度与数据完整性

- 到期开奖任务在时限内未完成、或 `running` 超过 60 秒，必须报警并标记依赖
  健康为失败。
- 开奖窗口前后必须检测 `idle in transaction`、锁等待链、最久事务年龄、到期
  任务和 Outbox 积压。
- 台湾未来期补齐与每日审计必须验证连续期号、连续日期、正确 `next_term`/
  `next_time` 和最小覆盖数量；仅统计未来行数不合格。

### 发布审查与验收

- 凡改动数据库连接、`system_config`、调度器、开奖、Future Issue 补齐、预测、
  Outbox、缓存或公共 API，必须遵守
  `skills/prediction-release-review/SKILL.md` 的事故附加门槛。
- 必须新增并通过：事务锁超时重试、长期 running 任务、连续 Future Issue 缺口、
  开奖后预测生成，以及 Future Issue 脱敏回归。
- 线上演练必须证明：阻塞事务不会令开奖永久卡住；任务能以不重复开奖的方式
  失败、重试、恢复；整个过程不公开 Future Issue 真值。

## 复盘结论

本事故的优先级顺序固定为：**权威开奖按时且只执行一次**，然后是**下一期预测
完整生成与缺失告警**，最后才是缓存、流量统计和非关键资料。任何便利性改动都
不得破坏这三个边界，更不得通过提前公开 Future Issue 来掩盖故障。
