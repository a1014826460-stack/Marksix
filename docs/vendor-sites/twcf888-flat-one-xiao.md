# 台湾创富网（twcf888）平特一肖（mode 103）说明

## 模块定位

- 首页分区锚点：`#pred-jhq-103`（`frontend/public/vendor/twcf888.com/index.html` 的 `jhq` 分组卡片）。
- 前台标题：`平特一肖`；原始 mode_id：`103`。
- 后端数据：动态机制 `title_103`（`mode_payload_tables.title = 三期平特1肖`，`modes_id = 103`），
  站点 `web_id = 8`，`public.mode_payload_103` 为供应商原始资料，`created.mode_payload_103` 为本站生成行。
- 判定语义：**平特口径** —— 开奖 7 个号码对应的生肖中任一命中预测生肖即算命中
  （2026-09-23 按用户要求由“特码生肖口径”改为平特口径，对所有站点的平特一肖同样生效）。

## 前台展示（2026-09-23 修正）

- 原始资料的 `content` 只有单个生肖（例如 `蛇`）。首页分组卡片此前直接输出单字，现按原站样式输出三连生肖：
  `266期【平特一肖】开 ???????` 下一行显示 `【鼠鼠鼠】`。
- 命中（`is_opened && is_correct === true`）时保留供应商黄色背景：
  `【<span style="background-color:#FFFF00">龙龙龙</span>】`；未命中只显示红色 `【蛇蛇蛇】`。
- 实现位置：`frontend/public/vendor/twcf888.com/index.html` 的 `formatPredictionContent()` 中
  `meta.modeId === 103` 分支（与 `buildModeSpecificPrediction()` 的同类分支保持一致）。
- 契约测试：`frontend/test/twcf888-ptyx-display-contract.mjs`。

## 后端判定与生成

1. **判定口径（本次修正）**：平特一肖按平特口径判定。`PredictionConfig.flat_zodiac = True`、
   `outcome_loader = all_zodiacs_from_row`、`hit_checker = flat_zodiac_hit`；
   `public/api._check_correct_by_mechanism()` 会把开奖 7 个生肖并入候选标签。
   覆盖 `pt1xiao`（mode 56）与所有 title 命中 `平特X肖` 的动态机制（含 mode 103 / `title_103`）。
   注意连期窗口表经 `_make_window_config()` 包装时曾丢失该标记（已用 `dataclasses.replace` 修复）。
2. **受控生成规则**：`_RULE_BY_MODE_ID` 原先没有 `103`，`get_generation_rule()` 返回
   `blocked_pending_rule`，未来期不会生成规则校验候选，只能按基础概率命中。现 mode 56 与 103
   都登记为 `zodiac_flat`，真实目标取 `DrawTruth.draw_zodiacs`（开奖 7 个生肖）。
3. **实测效果**（同一批生产行，用新规则重算）：
   - mode 103（twcf888 平特一肖）：旧口径 2/19 → 平特口径 **12/19**；265 期 `蛇`（特码 猪08）由“错”变为“对”。
   - mode 56（twcf888 公式平特肖）：旧口径 3/19 → 平特口径 **12/19**。
4. **仍未闭环的生成问题**：生产上台湾彩未来期号码可能在预测生成之后被改写。2026-09-23 19:17（北京时间）
   管理员 `PUT /api/admin/draws/105948` 改写了 266 期号码（生成时间是当日 12:10），
   而 mode 56 近 10 期里有 5 期的 `prediction_generation_controls.verified_hit` 与最终开奖号码不再一致。
   建议：未来期号码在当日预测生成后不要再改（或在改写后触发该期重新生成），否则受控命中会被作废。
