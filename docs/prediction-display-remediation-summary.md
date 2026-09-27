# 十站点预测模块展示违规：问题清单、根因与整改台账

- 范围：10 个前台站点（`web_id` 4–13）的全部预测模块
- 验收：2026-09-28，发布提交 `641dfe9`（中心节点 + 前端节点）
- 结果：**线上 10/10 站点 `error=0`、`js_errors=0`**；**生产判定真值 `rows=22039 error=0`**

---

## 一、用户报的每一条 → 根因 → 处置

| # | 现象 | 根因 | 处置 |
| --- | --- | --- | --- |
| 1 | 「错」的期仍有黄色高底 | 供应商静态 `index.html` 每一行自带样例黄底（`background-color:#FFFF00` / `color="#FFFF00"`），适配器只覆写文字、从不清理行内样式 | 适配器渲染前按祖先链清黄标；高亮只在命中分支产出（twssz 6→0、twjsz666 9→0、twbst528 2→0） |
| 2 | 命中却没有高亮 / 高亮打在错的一组 | 高亮条件与判定用了两个数据源（本地复算 vs 接口 `is_correct`），或整行共用一个命中状态 | 高亮统一绑定本期 `is_correct`；`writeRow()` 增加 `hitSlot` 按命中组落点（twwanli `#dssx`） |
| 3 | 判定恒「对」或恒「错」 | 判定字段取错（拿**码串**去 `indexOf(特肖)` → 恒 false）、`content_parser` 认不出正文标签（波色）、候选集为空 | twsaimahui `012liuxiao.js` 拆出 `codesByXiao`；mode 38 改用 `parse_literal_label_content`；`frontend_compat` 补 `getXiaoma2` 映射 |
| 4 | 板块「全部都是错的」 | 一部分是判定 bug（#3），一部分是真实中奖率低 + 展示退化（#5） | 用 `audit-verdict-truth.py` 对生产库复算定位，不再靠猜 |
| 5 | 10码/16码「每期前几位都一样」 | **不是**位置轮转：号码类 content 是逗号串，轮转从未生效；真因是热门号统计 `load_recent_result_rows(limit=10)` 不按 web/期号去重 → 同一批号码被钉死在前几位 | 新增 `UNORDERED_NUMBER_SET_MODE_IDS = {9,65,88,116}`，停用位置轮转、改为按成员集合一次性展示置换（判定逐值验证不变） |
| 6 | 未开奖期仍显示「中/赢」、仍有黄底 | 判定只看候选命中，没有先判 `isOpened`；另有审计把「面板标题行」并进预测行造成的假阳性 | 未开奖一律不输出判定、不清不亮；审计加 `isTitleRow`、页面标题行加 `data-prediction-title="true"` |
| 7 | 分组说明少一组（看起来「全是左肖/阳肖」） | 前端只按「本期恰好抽到哪组」拼说明；`fixed_data` 该行被停用（生产 3 行 `status=0`） | 固定分组兜底 + 生产把 `fixed_data` 全部启用（199/199） |
| 8 | 页面出现 `["` `"]` 原始 JSON | JS 直接 `d.content.split(',')` 或 `JSON.parse` 未兜底 | 20 个模块改 `safeParseJSON` + 形状守卫；`["'` 清洗兜底 |
| 9 | 某期显示 `开:？00错` / `??` | ① 渲染用了占位串；② `created.mode_payload_*` 里「已开奖但 `res_code` 为空」的数据缺口（生产 14745 处） | 渲染改真实开奖；新增 `backend/scripts/backfill_created_result_catchup.py`，生产补齐 **174 个期号 / 61622 行**（只填空值，不碰预测正文） |
| 10 | 一期里的判定与高亮「各算各的」 | 供应商把「一期」拆到多个单元格 / 相邻 `<tr>`，旧审计只取叶子行，**R3（error 级）整类漏报** | 审计改为在祖先链上合并同辈 + 下一个相邻行；加固后新暴露并修复 twcf888 24 处、twjinniu 17 处、shengshi8800 11 处、twcaibawang 2 处 |

---

## 二、根因分类（便于以后定位）

1. **供应商静态样例残留**：黄底/样例开奖号写死在 `index.html` 或模板字符串里，适配器只改文字。
2. **判定与高亮两套来源**：`is_correct` 与本地复算不一致，或高亮条件独立于判定。
3. **判定字段取错 / 解析器不认正文形态**：码串当生肖串、波色标签当生肖、`num` 直表名劫持 endpoint。
4. **生成侧退化**：热门号统计跨站跨期重复计数；二选一模块没有相邻期唯一性约束。
5. **数据缺口**：`created` 结果字段未回填（历史自动回填整批失败留下的）。
6. **审计工具自身盲区**：只取叶子行、判定字被模块名污染、标题行被并入 —— 会造成「看起来 0 违规」的假安全感。

---

## 三、交付物

| 交付物 | 路径 | 说明 |
| --- | --- | --- |
| 展示规范 + 固定 workflow | `docs/prediction-display-standard.md` | S1–S8 硬性规则、R1–R8 检查项、八步 workflow、新站点接入 checklist、十站点渲染形态、常见根因速查 |
| 展示审计工具 | `scripts/audit-prediction-display.py` | Playwright 实开页面；高亮用「计算样式 + 字面量」双口径；行切分合并同辈/相邻行；判定取最右/行尾；`--json/--dump-rows/--base-url/--headed` |
| 判定真值校验 | `scripts/audit-verdict-truth.py` | 对库里每一行复算「候选是否命中真实开奖」，与 `is_correct` 比对；`--check-missing-res-code` 报回填缺口 |
| 源码级 lint | `scripts/lint-prediction-renderers.py` | L1–L6：写死判定字、裸 `JSON.parse`、`content.split` 直上屏、静态样例开奖、无条件高亮、占位+判定 |
| 结果字段补齐 | `backend/scripts/backfill_created_result_catchup.py` | 一次性补齐「已开奖但 `res_code` 为空」的历史行（默认 dry-run） |
| 站点整改报告 | `docs/vendor-sites/twsaimahui-prediction-display-fix.md`、`docs/vendor-sites/sites-7-8-12-13-prediction-display-fix.md` | 逐条真/假判定、前后文本对照、复算表 |
| 号码集合展示顺序 | `backend/docs/number-set-display-order-fix-report.md` | 根因复核、置换算法、判定语义不变的证据 |
| 发布记录 | `DEPLOY.md`「十站点预测模块展示规范整改」 | 提交链、备份目录、生产数据操作、验收数字 |

---

## 四、验收证据

### 4.1 线上展示审计（`audit-prediction-display.py`，Playwright 实开）

| 站点 | rows | js_errors | error | warn |
| --- | ---: | ---: | ---: | ---: |
| shengshi8800 | 440 | 0 | 0 | 11 |
| twcaibawang | 292 | 0 | 0 | 8 |
| twsaimahui | 652 | 0 | 0 | 35 |
| twjinniu | 469 | 0 | 0 | 1 |
| twcf888 | 451 | 0 | 0 | 19 |
| twssz | 289 | 0 | 0 | 52 |
| twbst528 | 468 | 0 | 0 | 74 |
| twjsz666 | 276 | 0 | 0 | 9 |
| twwanli | 202 | 0 | 0 | 1 |
| twsyw | 545 | 0 | 0 | 7 |
| **合计** | **4084** | **0** | **0** | **217** |

### 4.2 生产判定真值（`audit-verdict-truth.py` 在 `python-api` 容器内对生产库）

`rows=22039  error=0  warn=2865  info=0`（10/10 站点 `error=0`）——
生产库里没有任何一行 `is_correct` 与「候选项命中真实开奖」相矛盾。

### 4.3 回归

- `cd backend/src; python -m pytest -q` → **1021 passed, 17 skipped, 1 failed**；
  唯一失败 `test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`
  是**改动前就存在**的（`deploy/nginx.conf` 缺 `proxy_pass .../health/live;`，本轮未触碰 `deploy/`）。
- 前端契约：`run-prediction-token-shape-contract.mjs`（20 模块）、`run-prediction-verdict-truth-contract.mjs`、
  `twsaimahui-012-liuxiao-display-contract.mjs`、`twcaibawang-verdict-contract.mjs` 全部通过。

---

## 五、遗留（已知、非 error、已记录）

1. **R4 类 warn（命中却没高亮）**：shengshi8800 `#yxym`/`#top_xiao_code`、twsaimahui `#table400916271`
   （「A级大公开;准确率100%!」营销行）、twcf888 `#pred-amgst-470`/`#pred-jhq-43`（平特多肖）、
   twssz/twbst528 的批量 R4。属于「多肖/多码命中时该高亮哪一个」的产品口径问题，未纳入本轮硬性要求。
2. **`#twjinniu-yixiao-yima`**：站点按产品要求「不中不显示对错」，未改。
3. **`shengshi8800/handleSelect.js` 的 `getResult()`** 仍写死「准」，但**已无调用方**（死代码，勿复活）。
4. **生产仍有 40 个期号 / 610 处** `res_code` 缺口——这些期号在 `lottery_draws` 里没有开奖号码或未开奖，
   补齐脚本已跳过；属上游数据问题。
5. **更深的生成侧问题**：`load_recent_result_rows(limit=10)` 的跨站/跨期重复会让所有「热度」玩法退化，
   影响面超出展示层，需要独立回归后再动。
6. **mode 34 等带跨站前缀契约的号码集合玩法**若也要改展示顺序，需先把前缀语义从「排名前 N 位」
   改为「展示前 N 位」并复审已预约签名。
