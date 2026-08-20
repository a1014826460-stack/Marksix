# 香港彩/澳门彩开奖延迟修复会话交接

更新时间：2026-08-20（Asia/Hong_Kong）

## 用户确认范围

- 不调整香港彩的计划开奖时间。
- 香港彩、澳门彩抓到完整新期开奖数据后，立即公开开奖，不再缓存等待下一轮自动开盘。
- 精准任务遇到主源旧期，持续以 5 秒追赶。
- 接入并测试 csjid 备用源。
- `draw_time` 统一按北京时间解释；延迟指标统一换算后计算。

## 远端只读排查结果

中心节点：`207.56.3.82:29618`，项目目录：`/root/Marksix`。

- 2026-08-19 澳门彩（日志 UTC，香港/北京=UTC+8）：
  - `13:32:00` 精准抓取：主源仍为旧期 `2026230`。
  - `13:32:19` 自动抓取：新期已写入，但日志为 `draw cached and waiting for precise open`。
  - `13:32:31` 自动开盘：才设为 `is_opened=1`。
- 根因：自动抓取入库后没有调用 `_open_specific_records()`；精准任务主源旧期后直接 deferred；备用源为空。
- 运行配置已经存在：`crawler.crawl_interval_chase=5`、`crawler.crawl_interval_near_draw=10`。

## csjid 备用源实测

2026-08-20 本地请求均 HTTP 200：

- 澳门 `lotCode=MACAO_2033`：`preDrawIssue=2026231`，`preDrawCode=39,46,23,11,08,13,20`，`preDrawTime=2026-08-19 21:32:32`。
- 香港 `lotCode=10048`：`preDrawIssue=2026090`，`preDrawCode=39,41,8,9,7,14,49`，`preDrawTime=2026-08-18 21:34:59`。
- JSON 合同：`result.data.preDrawIssue/preDrawCode/preDrawTime`，时间是北京时间。

生产环境用 Secret 注入，禁止提交完整 apiKey：

```ini
DRAW_HK_BACKUP_COLLECT_URL=https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=10048&apiKey=<SECRET>
DRAW_MACAU_BACKUP_COLLECT_URL=https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033&apiKey=<SECRET>
```

## 已完成本地改动（未提交、未部署）

基准提交：`be46bfb`。

- `.env.example`：新增两个备用源 Secret 占位变量。
- `backend/src/crawler/result_crawler.py`：
  - 支持 csjid 嵌套 JSON 标准化；
  - csjid 请求不附加 lnlllt 的 `lottery_id/action` 参数。
- `backend/src/crawler/scheduler.py`：
  - `_draw_latency_seconds()` 把北京时间 `draw_time` 转 UTC 再计算延迟；
  - 完整期号 `2026091` 解析为 term `91`；
  - 精准主源旧期时启用 chase mode；若有备用源，立即检查备用源；备用源命中后完整记录也从备用源读取；
  - 自动抓取入库/更新后立即开盘、发布 outbox，写入 `auto_open` 审计记录和 `public_open_delay_seconds`；
  - chase mode 且备用源存在时，自动抓取优先备用源。
- 测试：
  - 修改 `backend/src/tests/unit/test_hk_macau_precise_open_state.py`；
  - 新增 `backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py`。
- 计划：`docs/superpowers/plans/2026-08-20-hk-macau-immediate-draw-publication.md`。

## 已验证命令

```powershell
python -m pytest backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py backend/src/tests/unit/test_hk_macau_precise_open_state.py backend/src/tests/unit/test_scheduler_draw_publication.py -q
```

结果：`16 passed in 4.37s`。

```powershell
pwsh -File .\scripts\check-no-secrets.ps1
```

结果：`Secret scan passed.`

`git diff --check` 通过。

## 当前工作树

```text
 M .env.example
 M backend/src/crawler/result_crawler.py
 M backend/src/crawler/scheduler.py
 M backend/src/tests/unit/test_hk_macau_precise_open_state.py
?? backend/src/tests/unit/test_scheduler_hk_macau_fast_open.py
?? docs/superpowers/plans/2026-08-20-hk-macau-immediate-draw-publication.md
```

本交接文件创建后将额外显示为未跟踪文件。

## 新会话继续步骤

1. 读取本文件及实施计划。
2. 审查 scheduler 的自动抓取 HK/Macau 双彩种遍历和备用源优先选择。
3. 建议补充：csjid `preDrawCode` 为空时不允许开盘；主源恢复后 chase mode 关闭的测试。
4. 跑完整后端或 crawler/alert/outbox 相关测试。
5. 提交本地代码。
6. 只有用户明确再次授权时才操作服务器：先备份，注入两个 `DRAW_*_BACKUP_COLLECT_URL` Secret，重建 `python-api`、`scheduler-worker`，执行迁移检查、健康检查和开奖窗口验收。
7. 上线验收：上游返回新期至 `is_opened=1`/outbox 发布应不超过 5 秒；记录 `public_open_delay_seconds` 与来源新期到达时延。