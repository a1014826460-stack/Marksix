# daily_prediction 定时任务验证测试指南

> 版本：1.0
> 测试日期：2026-05-14
> 对应规范：[核心开奖机制规范](./核心开奖机制规范.md)

---

## 一、测试目标

验证 `daily_prediction` 作为系统唯一的自动预测生成入口，能够在预定时间正常触发并按预期生成正确的预测数据。

---

## 二、先决条件

1. HTTP 服务器和调度器正在运行（`python backend/src/app.py`）
2. 数据库中有可访问的 `lottery_draws` 记录（至少存在已开奖的记录）
3. `lottery_types` 表中 HK(1)/Macau(2)/Taiwan(3) 的 `status=1`
4. `managed_sites` 表中至少有一个 `enabled=1` 的站点
5. 可以查看调度器日志和 `system_config` 表

---

## 三、测试用例

### TC-1：任务是否正确创建

**目标**：验证启动时 `_ensure_daily_prediction_task` 正确创建了 `daily_prediction` 任务。

**步骤**：
1. 重启服务器
2. 查询数据库：
   ```sql
   SELECT task_key, task_type, run_at, status, schedule_scope
   FROM scheduler_tasks
   WHERE task_type = 'daily_prediction'
   ORDER BY id DESC LIMIT 1;
   ```

**预期结果**：
- `task_type` = `daily_prediction`
- `task_key` 格式：`daily_prediction:auto:2026-05-14`（日期为当天）
- `status` = `pending`
- `schedule_scope` = `auto`

---

### TC-2：任务是否在预定时间触发

**目标**：验证任务在 `daily_prediction_cron_time`（默认 12:00 北京时间）被调度器拾取并执行。

**步骤**：
1. 确认当前时间：`SELECT value_text FROM system_config WHERE key = 'daily_prediction_cron_time';`
2. 查看 `scheduler_tasks` 表该任务的 `run_at` 字段，确认其为当天 12:00 北京时间对应的 UTC 时间
3. 将 `run_at` 手动改为当前时间前 30 秒：
   ```sql
   UPDATE scheduler_tasks SET run_at = datetime('now', '-30 seconds')
   WHERE task_type = 'daily_prediction' AND status = 'pending';
   ```
4. 等待 30-60 秒后查看调度器日志，搜索关键字 `DailyPrediction`

**预期结果**：
- 日志中出现 `Task acquired: type=daily_prediction key=daily_prediction:auto:...`
- 日志中出现 `AutoPred starting for lt=1 trigger=auto`
- 日志中出现 `AutoPred starting for lt=2 trigger=auto`
- 日志中出现 `AutoPred starting for lt=3 trigger=auto`
- `scheduler_task_runs` 表新增记录，`status='completed'`

---

### TC-3：启动补跑逻辑

**目标**：验证如果当天 12:00 已过且尚未执行，启动时会立即补跑。

**步骤**：
1. 确认当前北京时间已过 12:00
2. 手动删除今天的 `daily_prediction` 任务（如果存在）：
   ```sql
   DELETE FROM scheduler_tasks WHERE task_type = 'daily_prediction' AND task_key LIKE '%:2026-05-14';
   ```
3. 重启服务器
4. 立即查看日志

**预期结果**：
- 日志中出现 `Daily prediction missed today, running catch-up`
- 依次对 lt_id=1,2,3 执行了预测生成
- 新任务已自动创建：`task_key` 格式为 `daily_prediction:auto:2026-05-15`（明天）

---

### TC-4：预测数据是否正确生成

**目标**：验证 `_run_auto_prediction` 生成的预测数据内容正确。

**步骤**：
1. 确保至少有一个已开奖的 draw 记录：
   ```sql
   SELECT lottery_type_id, year, term, numbers, is_opened
   FROM lottery_draws WHERE is_opened = 1 ORDER BY id DESC LIMIT 5;
   ```
2. 触发 `daily_prediction`（按 TC-2 步骤 3 手动加速触发）
3. 等待任务完成（日志中出现 `AutoPred OK`）
4. 查询生成的预测数据：
   ```sql
   -- 检查下一期预测是否已生成
   SELECT t.name AS type_name, d.year, d.term, COUNT(*) AS pred_count
   FROM lottery_draws d
   JOIN lottery_types t ON d.lottery_type_id = t.id
   WHERE d.is_opened = 0
   GROUP BY t.name, d.year, d.term;

   -- 检查 created 模式下是否有新数据
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'created' AND table_name LIKE 'mode_payload_%'
   ORDER BY table_name;
   ```
5. 抽查一条预测记录：
   ```sql
   SELECT * FROM created.mode_payload_<table_name>
   WHERE year = <下一期年份> AND term = <下一期期数>
   LIMIT 5;
   ```

**预期结果**：
- 每个 `enabled=1` 的 site 对应一条下一期预测记录
- `res_code` 字段为空或逗号分隔（因为是未来预测，开奖结果未出）
- `pred_code` 字段有预测号码数据

---

### TC-5：回填是否正确

**目标**：验证回填功能更新了最近开奖期数的 `res_code`。

**步骤**：
1. 手动构造一条已知开奖结果：记下最新一期 `is_opened=1` 的 `year`、`term`、`numbers`
2. 在 `created.mode_payload_*` 中找到同 `year+term` 的记录：
   ```sql
   SELECT * FROM created.mode_payload_<table>
   WHERE year = <year> AND term = <term> AND lottery_type_id = <type>
   LIMIT 3;
   ```
3. 如果 `res_code` 为空，触发 `daily_prediction` 后重新查询

**预期结果**：
- 同 `year+term` 的预测记录的 `res_code` 不再是空字符串，已填入开奖号码
- `res_sx`（生肖）和 `res_color`（波色）也相应填入

---

### TC-6：覆盖保护

**目标**：验证当目标期数已存在非空预测数据时，自动触发会跳过生成。

**步骤**：
1. 确认下一期预测数据已存在且 `pred_code` 非空
2. 手动修改 `daily_prediction` 任务的 `run_at` 为当前时间前 30 秒
3. 查看日志

**预期结果**：
- 日志中出现 `AutoPred SKIP lt=N: future issue YYYY/TTTT already has prediction data. Use manual trigger to overwrite.`

---

### TC-7：验证只存在两个预测生成入口

**目标**：确认除 `daily_prediction` 定时任务和管理后台手动触发外，没有其他自动生成路径。

**步骤**：
1. 在代码库中搜索预测生成调用：
   ```
   grep -rn "bulk_generate_site_prediction_data\|_run_auto_prediction\|bulk_generate_site_predictions" backend/src/
   ```
2. 排除以下合法位置：
   - `crawler/scheduler.py:1048` — `_run_daily_prediction_if_missed`（daily_prediction 补跑）
   - `crawler/scheduler.py:1283` — `TASK_TYPE_DAILY_PREDICTION` 处理器
   - `admin/prediction.py:*` — 管理后台 API 调用入口
   - `routes/admin_lottery_routes.py:*` — crawl-and-generate 路由
   - `routes/admin_site_routes.py:*` — generate-all 路由
   - `routes/admin_payload_routes.py:*` — regenerate 路由
3. 确认已废弃代码：
   ```sql
   SELECT task_key, task_type, status FROM scheduler_tasks
   WHERE task_type = 'auto_prediction' AND status IN ('pending', 'running');
   ```
   应为空。

**预期结果**：
- 所有预测生成调用要么在管理后台路由中（手动），要么在 `daily_prediction` 任务路径中（自动）
- `TASK_TYPE_AUTO_PREDICTION` 处理器已改为仅记录日志拒绝执行
- 没有任何活跃的 `auto_prediction` 类型 scheduler_task

---

### TC-8：日志链路完整性

**目标**：验证每次 `daily_prediction` 执行留下完整的日志链路。

**步骤**：
1. 触发一次 `daily_prediction`
2. 搜索日志中的关键事件序列：
   - `Task acquired: type=daily_prediction`
   - `AutoPred starting for lt=1 trigger=auto`
   - `AutoPred recent backfill lt=1: checked=...`
   - `AutoPred OK lt=1: backfilled=... generated=...`
   - （对 lt=2, lt=3 重复）
   - `Daily_prediction task completed successfully`

**预期结果**：
- 所有三个彩种依次处理
- 每个彩种打印了回填和生成的数量
- 最后一个 `_ensure_daily_prediction_task` 已调度次日任务

---

## 四、测试数据准备

```sql
-- 1. 确认彩种状态
SELECT id, name, status FROM lottery_types WHERE id IN (1, 2, 3);
-- 预期：全部 status=1

-- 2. 确认有已开奖记录
SELECT lottery_type_id, year, term, numbers, is_opened
FROM lottery_draws WHERE is_opened = 1
ORDER BY id DESC LIMIT 3;
-- 预期：每个彩种至少一条

-- 3. 确认有启用站点
SELECT id, name, enabled FROM managed_sites WHERE enabled = 1;
-- 预期：至少一条

-- 4. 确认配置正确
SELECT key, value_text FROM system_config
WHERE key IN ('daily_prediction_cron_time', 'prediction.recent_period_count', 'prediction.max_terms_per_year');
-- 预期：daily_prediction_cron_time='12:00', recent_period_count='10', max_terms_per_year='365'

-- 5. 查看当前调度任务状态
SELECT task_key, task_type, status, run_at
FROM scheduler_tasks
WHERE task_type IN ('daily_prediction', 'auto_prediction')
ORDER BY id DESC LIMIT 5;
```

---

## 五、故障排查

| 症状 | 可能原因 | 排查步骤 |
|------|---------|---------|
| 任务未触发 | 调度器未运行 | 检查服务器进程是否存在 |
| | `run_at` 未到 | `SELECT run_at FROM scheduler_tasks` 确认时间 |
| | 任务被前一次运行锁定 | `SELECT * FROM scheduler_tasks WHERE status='running'` |
| 预测数据为空 | 无已开奖 draw 记录 | `SELECT COUNT(*) FROM lottery_draws WHERE is_opened=1` |
| | 无启用站点 | `SELECT COUNT(*) FROM managed_sites WHERE enabled=1` |
| | prediction.max_terms_per_year 配置错误 | `SELECT value_text FROM system_config WHERE key='prediction.max_terms_per_year'` |
| 回填失败 | 无对应的 created 表 | 检查 `created` schema 下是否存在 `mode_payload_*` 表 |
| | year/term 不匹配 | 检查 `lottery_draws.year/term` 与 `created.mode_payload_*.year/term` 是否一致 |
