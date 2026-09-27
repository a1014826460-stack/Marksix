# 台湾彩霸王（twcaibawang）前台判定与命中高亮整改

站点：`twcaibawang`（`site_id = 5`、`web_id = 5`、域名 `www.twcaibawang.com`）。
前台是 React 渲染（`frontend/components/twcaibawang/TwcaibawangHomeClient.tsx`），
不是 legacy JS shell；模块数据来自 `public_site_page` 与 `vendor/homepage-modules` 两个接口。

## 一、本轮需求

1. 指定 13 个模块：**命中的**映射文字（波色 / 生肖 / 号码 / 五行 / 段数 / 头尾 / 天地肖）
   必须标黄，判定文字统一为 **对 / 错**；三期类模块未命中显示 **中0期**。
2. `9肖中特`：命中生肖标黄（判定同样是对 / 错）。
3. `绝杀一波` 在页面上出现了两次，删除最后一份。
4. `琴棋书画` 改为「两行分组说明 + 每期一行」的新格式。
5. `四字玄机`（mode 52）：补 49 组备选 title + jiexi，并保证相邻五期不重复。

## 二、13 个模块的整改明细

| 模块 | mode / 数据源 | 判定口径（本地复算，与展示内容逐一对齐） | 高亮对象 |
| --- | --- | --- | --- |
| 双波 | 38 / site-page | 特码波色 ∈ 预测的两个波 | 命中的波名 |
| 双波12码 | 38 / vendor `shuangbo_12ma` | 特码波色 ∈ 预测的两个波 | 命中的波名 + 该波内的特码 |
| 24码 | 34 / site-page | 特码 ∈ 24 码 | 命中的号码 |
| 必杀一肖 | 472 / site-page | 特肖 ≠ 被杀肖（杀中即对） | 被杀肖（杀中时） |
| 绝杀一波 | 58 / site-page | 特码不在被杀半波的号码内，且不属于该半波 | 被杀半波 + 被杀号码（杀中时） |
| 四段中特 | 479 / site-page | 特码落在所预测的任一段位内 | 命中的段位 |
| 稳杀10码 | 481 / site-page | 特码不在被杀 10 码内 | 被杀 10 码（杀中时） |
| 四行中特 | 482 / site-page | 特码落在所预测的任一五行内 | 命中的五行 |
| 四头中特 | 483 / site-page | 特码头数落在所预测的任一档内 | 命中的头档 |
| 六肖十八码 | 484 / site-page | 特肖 ∈ 候选 6 肖 | 命中的生肖 + 命中的号码 |
| 天地两肖 | 5 + 251 / vendor `tiandi_2xiao` | 特肖 ∈ 天地组（天肖/地肖各 6 肖）**或** 两肖 | 命中的天地肖 或 命中的那个肖 |
| 公开一肖一码 | 49 + 151 / vendor `public_yixiao_yima` | 特肖 == 推荐肖 **或** 特码 == 推荐码（沿用后端口径） | 各档命中肖 / 命中码 + 推荐一肖一码 |
| 三期4肖 | 197 / site-page | 窗口内已开奖各期特肖落在候选 4 肖里的期数 | 命中的候选肖；未命中显示 `中0期`，窗口未开奖才显示 `中几期` |
| 9肖中特 | 49 / site-page（通用渲染） | 特肖 ∈ 候选 9 肖 | 命中的生肖 |

实现要点：

- 新增共用助手：`waveLabelOfCode` / `halfWaveLabelOfCode`（号码 → 波色 / 半波）、
  `specialPartsOf`（解析 `马37` 与 `开37马` 两种结果写法）、
  `resolveJudgement`（接口能给结论就用接口，接口为 `null` 时用本地复算）、
  `labelForCode`（在 `标签|号码` 条目里找出包含特码的那一档）、
  `renderJudgeResult`（统一输出「对 / 错」）。
- `双波` / `双波12码` / `六肖十八码` 的接口 `is_correct` 是 `null`，
  旧实现直接把它当 `false`/`true` 用，导致「恒显示对」；现按上表本地复算。
- `24码` 原先整行期号被无条件黄底、且没有判定文字；现改为只高亮命中号码并输出对/错。
- `四段中特` 原先把标签与「特码头数」比较（永远不相等），`四行中特` 同理，
  现改为「条目号码列表是否包含特码」。
- `天地两肖`：vendor 接口的 `is_correct` 只比对那两肖，天肖/地肖永远不参与判定；
  按站点语义（天地选1 + 生肖选2）改为并集判定，否则「天地肖」永远不会被高亮。

## 三、绝杀一波重复

`GENERIC_MODULES` 里有一条 `mechanismKey: "jueshabanbo"`，与 `buildPageHtml` 中
显式的 `renderJueshabanbo(...)` 各渲染一次，页面因此出现两个 `#jsyb`。
已删除 `GENERIC_MODULES` 中的那一条（即页面上后出现的那一份）。
契约测试断言 `id="jsyb"` 只能出现一次。

## 四、琴棋书画新格式

```
琴:兔蛇鸡　棋:鼠牛狗
书:虎龙马　画:羊猴猪
270期: 琴棋书画→画琴书开:马37准
269期: 琴棋书画→画琴书开:鸡46准
```

- 两行分组说明直接取接口返回的 `raw.qinqi_reference`（后端已按 `fixed_data` 的「四艺生肖」生成），
  缺失时回退到内置的固定分组。
- 每期行取 `raw.title`（如 `画,琴,书`）去掉逗号作为「画琴书」。
- 判定文字按需求样例使用 **准 / 错**（其余 12 个模块用「对 / 错」）。

## 五、四字玄机（mode 52）候选池

- 新增 `utils/rebuild_text_mappings.MODE_52_SIZIXUANJI_POOL`：49 组 `(title, jiexi)`，
  标题为四字词，解肖为 7 个生肖（配对决定命中：特肖落在解肖内即命中）。
- 写入 `public.text_history_mappings`（`mode_id = 52`）：
  `mode_payload_52` 未标记 `is_text = 1`，通用重建路径会跳过它，因此单独回填。
- 因为 `rebuild_text_history_mappings()` 会 DROP 重建该表，回填函数挂在重建流程末尾，
  保证「重建不会丢掉这批候选」；同时提供只回填这一个池的入口：

  ```powershell
  cd backend/src
  python -m utils.rebuild_text_mappings --db-path "$env:DATABASE_URL" --only-mode52
  ```

- 生成端与相邻期唯一性都从 `text_history_mappings` 读取 mode 52 候选；
  `_load_three_period_text_payloads()` 在没有映射行时回退读 `public.mode_payload_52`，
  并同时带出 `title` 与 `jiexi`（只换标题会导致命中口径与标题对不上）。
- 展示唯一窗口：`DISPLAY_UNIQUE_WINDOW_BY_MODE = {52: 5, 62: 5}`，
  即这两个模块要求**相邻连续五期**展示值不得相同（其余托管模式仍为 3 期）。

## 六、顺带修复的后端缺陷

`public/api._compute_outcome_from_row()` 输出的复合结果里缺 **段位** 标签，
导致 `四段中特`（mode 479）的 `is_correct` 恒为 `False`：
269 期特码 46 明明落在预测的 `7段` 里，接口仍返回 `false`。
现补上 `f"{((number - 1) // 7) + 1}段"`，只有带 `N段` 标签的机制会受影响（即 mode 479）。

## 七、回归验证

- 契约测试：`frontend/test/twcaibawang-verdict-contract.mjs`
  （12 个判定模块 × 对/错文案 + 高亮调用、绝杀一波唯一性、三期4肖中0期、
  琴棋书画格式、波色/半波/天地肖映射表的真实执行用例）。
- 后端单测：`backend/src/tests/unit/test_public_outcome_segment_label.py`、
  `test_rebuild_text_mappings_mode_52.py`、
  `test_prediction_three_period_unique.py`（mode 52 五期窗口）、
  `test_prediction_generation_three_period_service.py`（title/jiexi 成对）。
- 端到端：本地 `next dev` + Python API 打开 `/twcaibawang`，
  用独立复算脚本逐期比对 115 行判定文字与黄底位置（0 差异、0 JS 报错），
  复算脚本见 `.codex-temp/crosscheck_tcbw.py`（临时脚本，未纳入版本库）。
  本地数据由线上接口抓取的真实行构造（web_id=5 夹具 + `lottery_draws`），
  仅写入本地开发库。
