# 台湾创富网（twcf888）平特一肖（mode 103）说明

## 模块定位

- 首页分区锚点：`#pred-jhq-103`（`frontend/public/vendor/twcf888.com/index.html` 的 `jhq` 分组卡片）。
- 前台标题：`平特一肖`；原始 mode_id：`103`。
- 后端数据：动态机制 `title_103`（`mode_payload_tables.title = 三期平特1肖`，`modes_id = 103`），
  站点 `web_id = 8`，`public.mode_payload_103` 为供应商原始资料，`created.mode_payload_103` 为本站生成行。
- 判定语义：**特码生肖等于所报生肖即命中**（与 `pt1xiao` / mode 56 相同），基础命中率 1/12 ≈ 8%。

## 前台展示（2026-09-23 修正）

- 原始资料的 `content` 只有单个生肖（例如 `蛇`）。首页分组卡片此前直接输出单字，现按原站样式输出三连生肖：
  `266期【平特一肖】开 ???????` 下一行显示 `【鼠鼠鼠】`。
- 命中（`is_opened && is_correct === true`）时保留供应商黄色背景：
  `【<span style="background-color:#FFFF00">龙龙龙</span>】`；未命中只显示红色 `【蛇蛇蛇】`。
- 实现位置：`frontend/public/vendor/twcf888.com/index.html` 的 `formatPredictionContent()` 中
  `meta.modeId === 103` 分支（与 `buildModeSpecificPrediction()` 的同类分支保持一致）。
- 契约测试：`frontend/test/twcf888-ptyx-display-contract.mjs`。

## 后端生成：为什么该模块长期“全部未中”

1. **判定口径**：平特一肖按特码生肖判定，单肖自然命中率只有 1/12；即使资料完全正常，也会有
   约 92% 的期数显示“错”。
2. **缺少受控生成规则（本次修复）**：`domains/prediction/generation_rules.py` 的
   `_RULE_BY_MODE_ID` 原先没有 `103`，`get_generation_rule()` 返回 `blocked_pending_rule`，
   `_build_persisted_future_control()` 直接返回 `None`，因此该模块的台湾彩未来期不会生成
   规则校验候选，只能按基础概率命中。现已按 `zodiac` 规则登记（与 mode 56 一致），并在
   `backend/docs/prediction-mechanisms.md` 记录。
3. **生产观测（2026-09-23，`/api/twcf888/site-page?lottery_type=3&mode_ids=103`）**：
   近 19 期已开奖行命中 2 期（≈ 11%，符合 1/12 基线）；同一窗口内
   mode 49 = 13/19、mode 66 = 10/19、mode 69 = 5/19、mode 54 = 3/19、mode 5 = 4/19、mode 51 = 4/19，
   分别贴近日肖/尾/波各自的随机基线（75% / 50% / 25% / 10% / 50% / 33%），而 site-page 行均为
   平台生成行（`source_record_id` 为空，每日 12:10 生成）。这说明**已登记规则**的模块在生产上
   也没有呈现出受控命中率，需要进一步核对中心节点的 `prediction_generation_controls` 账本、
   `prediction.simulation.*` 配置与每日批量生成路径（需要服务器授权后执行）。
