# 站点 7 / 8 / 12 / 13 预测模块展示违规排查与修复

范围：`twjinniu`(web 7) / `twcf888`(web 8) / `twwanli`(web 12) / `twsyw`(web 13)。
未触碰 `backend/src/**` 的落库预测数据，未 commit / 未部署。站点 9 / 10 / 11 与 4 / 5 / 6 未改动。

规范依据：`docs/prediction-display-standard.md`（S1–S8）。判定口径依据：`backend/docs/prediction-module-rules.md`。

---

## 一、结论摘要

- 审计脚本 `error=0` **不等于**没问题：本轮 4 个站点里唯一一条 **error 级**违规
  （判定「错」仍保留黄色高亮，S3）审计脚本完全看不到，根因是供应商静态结构把
  「期号行」和「结果行」拆成了两个 `<tr>`，脚本按行取叶子时永远取不到含 `开:` 的那一段。
- 本轮共修复 4 个文件、12 处展示缺陷，覆盖：
  - 判定「错」仍带黄底（S3，error 级）：twjinniu、twcf888
  - 命中高亮打在错误的分组列上（S2/S4）：twwanli `单双各四肖`
  - 命中没有判定文字 / 判定文字写死（S1）：twjinniu `前后24码`、twwanli `琴棋书画`
  - 分组内容整列丢失（S6 同类）：twwanli `天地生肖`
  - 未开奖仍给判定 / 占位串残留（S1）：twjinniu `前后24码`、`一句话中特码`
  - 原始 JSON 残留兜底（S5）：twwanli / twsyw `labels()`
- 未解决项全部集中在**共用层**：mode 38（双波中特）`is_correct = null`（后端机制配置），
  以及 `frontend/lib/prediction-contract.ts` 被并行任务改出的 token 回归（不由本任务接手）。

---

## 二、改动文件清单

| 文件 | 增/删行 | 影响站点 | 说明 |
| --- | --- | --- | --- |
| `frontend/lib/twjinniu-homepage.ts` | +25 / −7 | 仅 twjinniu(7) | 站点私有 HTML 生成器 |
| `frontend/public/vendor/twcf888.com/index.html` | +6 / −4 | 仅 twcf888(8) | 站点私有渲染脚本（内联） |
| `frontend/public/vendor/twwanli/site-data-adapter.js` | +33 / −9 | 仅 twwanli(12) | 供应商 DOM 适配层 |
| `frontend/public/vendor/twsyw/site-data-adapter.js` | +3 / −1 | 仅 twsyw(13) | 供应商 DOM 适配层 |

改动行号（`git diff -U0` 定位）：

- `twjinniu-homepage.ts`：新增 `renderResultJudgeBox()`（L276–293）；`renderSixiaoBama` L438；`renderPingteXiao` L676；`renderPingteWei` L721；`renderShisiMazhong` L1288；`renderYijuhuaZhongtema` L1312；`renderQianhou24ma` L1397–1398。
- `twcf888.com/index.html`：L1222 删除 `isKill` 特例；L1224 起 `highlightOn` 收敛为「只有命中才高亮」。
- `twwanli/site-data-adapter.js`：`labels()` L64；`writeRow()` L98/L110（新增 `hitSlot`）；`renderHeavenEarth` L205；`renderMusicChess` L229；`renderOddEvenFourXiao` L243。
- `twsyw/site-data-adapter.js`：`labels()` L39。

> 说明：`frontend/app/api/kaijiang/[[...path]]/route.ts`、`frontend/lib/prediction-contract.ts`、
> `frontend/lib/site-api-service.ts` 等**多站共用文件本轮一律未改**。

---

## 三、逐站逐模块：修复前 → 修复后

### twjinniu（web 7）

**1. `#sxbm` 四肖八码（`renderSixiaoBama`）— S3 error 级**

```text
修复前(线上 270 期)：开:<span style="color:#F00; background-color:#FFFF00;">37马<font color="#000">错</font></span>
修复后(本地 189 期)：开:<span style="color:#F00;">09狗</span><font color="#000">错</font>
修复前(线上 269 期)：开:<span ... background-color:#FFFF00;">46鸡<font color="#000">错</font></span>
命中/未开奖：       命中 → 黄底只包住「45狗」，「对」不带黄底；未开奖 → 开:<span style="color:#F00;">?????</span>
```
根因：模板里 `background-color:#FFFF00` 无条件写在「开：判定」外层 `<span>` 上，与 `isCorrect` 无关。

**2. `#pmzq` 平特一肖 / 平特一尾（`renderPingteXiao` / `renderPingteWei`）— S3**

```text
修复前(线上 268 期)：268期:平特一肖〖羊羊羊〗开：<span style="background-color:#FFFF00; color:#F00;"><font>11猴错</font></span>
修复后(本地 187 期)：187期:平特一肖〖蛇蛇蛇〗开：<span style="color:#F00;">29虎</span><font color="#000">错</font>
命中(本地 188 期)：  188期:平特一肖〖蛇蛇蛇〗开：<span style="color:#F00;background-color:#FFFF00;">38蛇</span><font color="#FF0000">对</font>
```

**3. `#twjinniu-qianhou-24ma` 前后24码（`renderQianhou24ma`）— S1**

```text
修复前：270期：…开<font color="#FF0000">37马</font><font color="#000000">错准</font>   ← 未命中期同时印「错」「准」
修复后：185期：…开<font color="#FF0000">20猪</font><font color="#000000">错</font>
修复前(未开奖)：开?????准                                    ← 未开奖给了「准」
修复后(未开奖)：开?????
```

**4. `#twjinniu-shisi-mazhong` 14码中特（`renderShisiMazhong`）— S1**

```text
修复前：270期:==14码中特==开37马        ← 不给判定
修复后：190期:==14码中特==开45狗对 / 未命中 开21狗错
```

**5. `#twjinniu-yijuhua-zhongtema` 一句话中特码（`renderYijuhuaZhongtema`）— S1 占位串**

```text
修复前(未开奖)：開:?00
修复后(未开奖)：開:待开奖
```

量化（`错行内黄底单元`，`#sxbm` + `#pmzq`）：**线上 15 → 本地 0**。

### twcf888（web 8）

**6. 绝杀 / 排除类模块（`formatPredictionContent`）— S3**

```text
修复前(线上 270 期 #pred-jsb-473 绝杀二肖)：270期【绝杀二肖】开 马37错  黄底「鸡,马」
修复后(本地 190 期 #pred-jsb-473)：         190期【绝杀二肖】开 狗45错  无任何黄底
修复前(线上 269 期 #pred-jsb-95 绝杀二尾)： 269期【绝杀二尾】开 鸡46错  黄底「6」
修复后(本地 189 期 #pred-jsb-95)：         189期【绝杀二尾】开 狗09错  无任何黄底
修复前(线上 270 期 #pred-jsb-472 绝杀一肖)：270期【绝杀一肖】开 马37错  黄底「马」
修复后(本地 190 期 #pred-jsb-472)：        190期【绝杀一肖】开 狗45错  无任何黄底
修复前(线上 265 期 #pred-jsb-41 绝杀一头)：265期【绝杀一头】开 猪08错  黄底「0」
修复后(本地)：                             无任何黄底
```
根因：`var highlightOn = isKill ? (is_correct === false) : (is_correct === true);`
—— 绝杀类刻意在「杀错」时点亮被开出的那一项，直接违反 S3。已统一收敛为「只有命中才高亮」；
绝杀命中时开奖值本就不在候选集里，因此命中行不会残留任何黄底。

量化（同 6 个模块，错行带黄底）：**线上 13 → 本地 0**。

### twwanli（web 12）

**7. `#dssx` 单双各四肖（`renderOddEvenFourXiao` + `writeRow`）— S2/S4 高亮错位**

```text
修复前(线上 270 期)：第一列「猴,鸡,龙,牛」黄底=true，第二列「虎,马,兔,蛇」黄底=false
                      而开奖是 37马，马在**第二组**里 → 命中的一组没点亮，没命中那组被点亮
修复后(本地 186 期)：第一列「猴,鸡,猪,马」黄底=false，第二列「兔,牛,鼠,狗」黄底=true
                      开奖 42牛，牛在第二组 ✓
```
根因：`writeRow()` 恒把 `data-prediction-hit` 打在 `[data-prediction-content]`（第一列），
新增 `hitSlot` 参数按「特肖落在哪一组」决定高亮列。

**8. `#tdsx` 天地生肖（`renderHeavenEarth`）— 分组内容整列丢失（S6 同类）**

```text
修复前(线上 2026270)：2026270期  天肖                          开:37马错
修复后(本地 2026190)：2026190期  【天肖+龙狗】                  开:45狗对
                     2026191期  【地肖+猪兔】                  开:待开奖
```
根因：只渲染 `labels(row)`（＝`天肖`/`地肖`），从未渲染 `raw.xiao`（本期 2 个候选生肖）。
现在与 twcf888 同口径 `【组名+候选肖】`。

**9. `#qqsh` 琴棋书画（`renderMusicChess`）— S1 命中无判定**

```text
修复前(线上 2026270)：2026270期: 琴棋书画→画琴书 开:马37
修复后(本地 2026190)：2026190期: 琴棋书画→琴画棋 开:45狗对
```
根因：结果串写死为 `"开:" + parts.zodiac + parts.code`，从不追加判定；改用 `resultText(source)`。

**10. `labels()` 兜底清洗（S5）**

```text
输入 token: ["天肖|兔,马,猴,猪,牛,龙"]
修复前取值: ["天肖      ← 直接渲染到页面
修复后取值: 天肖
```

### twsyw（web 13）

**11. `labels()` 兜底清洗（S5）** — 与 twwanli 相同，防止 token 形态变化时把 `["` 渲染出来。

**12. 未修复**：`#shuangbo`（双波中特）/ `#hblvxiao`（双波+一波）20 行全部没有判定文字，
根因见第五节第 1 条（mode 38 `is_correct = null`）。该模块不属于适配层能独立修正的范围。

---

## 四、审计数字（命令 + 前后）

命令：

```powershell
# 线上（只读）
python scripts\audit-prediction-display.py twjinniu twcf888 twwanli twsyw --json .codex-temp\audit-7-8-12-13.json
# 本地预检（编译工作树）
python scripts\audit-prediction-display.py twjinniu twcf888 twwanli twsyw `
  --base-url http://127.0.0.1:3000 --json .codex-temp\audit-local-781213-after.json
```

| 时点 | twjinniu | twcf888 | twwanli | twsyw |
| --- | --- | --- | --- | --- |
| 线上基线（本任务开始时脚本版本，error/warn/js /rows） | 0 / 10 / 0 / 469 | 0 / 20（实测 39）/ 0 / 387 | 0 / 1 / 0 / 202 | 0 / 0 / 0 / 545 |
| 线上基线（含新 R8 的当前脚本，修复前） | 0 / **2** / 0 / 469 | 0 / **3** / 0 / 451 | 0 / 0 / 0 / 202 | 0 / 0 / 0 / 545 |
| 本地（修复后，当前脚本） | 0 / **2** / 0 / 469 | 0 / **7** / 0 / 451 | 0 / 0 / 0 / 202 | 0 / 0 / 0 / 545 |

数字说明（必须一起看，否则会误判）：

1. **两行基线不是同一版脚本**。审计脚本在本任务进行中被并行任务改过（新增 R8、并给 R5 加了
   「该行必须含 `开/開`」的过滤），所以 warn 从 10/39/1 掉到 2/3/0 —— 这是**规则收紧**，
   不是站点变好。
2. **error / js_errors 四个站点全程都是 0**，修复前后一致。本轮修复的 12 处缺陷里
   **没有一条**能被现有 6+2 条规则捕获（根因见第五节第 5 条）。
3. 本地 twcf888 warn 7 > 线上 3，是**本地库期数与线上不同**（本地 7 期一段、线上 8 期一段）
   导致 R8 命中更多模块，不是代码回归。
4. 本地 `twwanli/twsyw` 的数字当前受 `frontend/lib/prediction-contract.ts` 的并行改动污染
   （见第五节第 2 条），线上为准。

---

## 五、根因与未解决项

### 1)【未解决·共用数据】mode 38 双波中特 `is_correct = null` → 命中也不显示对/错

影响：twcf888 `#pred-amgst-38`、`#pred-jhq-38`（各 8 期无判定）、twwanli `#hblvxiao`、
twsyw `#shuangbo` / `#hblvxiao`。

复现（本地 Python API 进程内，只读）：

```text
key=shuangbo mode=38
  content_parser = parse_zodiac_content   →  labels = ()
  outcome       = ...|蓝波|...
  _check_correct_by_mechanism → None      （content_labels 为空即返回 None）
key=title_143（一波中特，同属波色口径）
  content_parser = parse_literal_label_content → labels = ('蓝波','绿波') → True
```

数据侧证据（线上 `/api/twcf888/site-page?mode_ids=38`）：8 期 `is_correct` 全部为空，
而按 `backend/docs/prediction-module-rules.md` 「38 | shuangbo | 双波中特 | wave |
special number wave is in any candidate」本应可算。例如 2026270：候选「蓝波,绿波」，
特码 37 为蓝波 → 应判「对」。

**未修改**：根因在 `backend/src/predict/mechanisms.py` 的 mode 38 配置
（`content_parser` 用了生肖解析器，应为标签解析器，参照 mode 143），属多站共用后端文件，
需与主线一起评审发布；本任务的授权范围只到前端 vendor 适配层与 `route.ts` 映射函数。
若在 vendor 适配层各自补算，会造成 3 个站点 3 套波色判定口径，与规范「判定口径以后端机制为准」冲突，
因此**刻意不改**，在此登记。

### 2)【未解决·跨任务】`frontend/lib/prediction-contract.ts` token 回归

工作树里该文件已被并行任务修改（新增 `expandPredictionTokens` / `collectCandidateTokens`），
本地编译实测 token 形状相对 HEAD 退化：

| 模块 | HEAD / 线上 | 工作树 / 本地 |
| --- | --- | --- |
| `title_5` | `['天肖\|兔,马,猴,猪,牛,龙']` | `['["天肖\|兔,马,猴,猪,牛,龙"]','["天肖','兔',…]` |
| `sixiao_sima` | `['蛇\|02','马\|01','鸡\|10','牛\|06']` | `['["猪\|08", "龙\|03", …]','["猪','08"','"龙']` |
| `9xzt` | `['猴','鸡','鼠','牛','虎','马']` | `['猴,蛇,猪,鼠,马,狗,龙,虎,羊']`（整串） |
| `danshuang4xiao` | 8 个独立生肖 | 1 个整串 |

后果：twwanli / twsyw 适配层会渲染出 `["天肖` 之类的原始 JSON 残留（S5），逐肖列表退化为整串。
**本任务不改该文件**（已与主协调方确认由并行任务收敛）。twwanli / twsyw 的 `labels()`
已加 `[]"'` 清洗作为兜底，两种 token 形态都能正确显示。

### 3)【未解决·产品口径】整列无判定的模块

- twjinniu `#twjinniu-yixiao-yima`：源码注释明确「该玩法由用户明确要求『不中不显示对错』」，
  命中才显示「中奖」。属**用户指定行为**，仅命中时才有黄底，未命中无黄底 —— 不违反 S2/S3，
  但与 S1「未命中 → 显示错」不一致，未改。
- twjinniu `#twjinniu-baxiao-shiliuma` / `#twjinniu-fivea-dagongkai` / `#table155` /
  `#twjinniu-yijuhua-zhongtema`：已开奖期也没有对/错。`yijuhua` 对应 mode 50
  （`blocked_pending_rule`，无判定口径）；其余三个模块只高亮候选、不给判定。
  需要产品口径确认后再补，未改。
- twwanli `#msks`（买啥开啥）：显示的是**开出的**家禽/野兽类别 + 一份重复判定，
  3 期连续相同（线上旧脚本 R5 命中），属玩法设计而非判定写死，未改。

### 4)【建议·流程】审计脚本的行级盲区

`#sxbm`（四肖八码）这类供应商结构把「期号行」与「结果行」放在**两个 `<tr>`** 里，
`ROW_SCRIPT` 取叶子时永远取不到含 `开:` 的那一段，因此 R3（error 级）永远不触发。
建议二选一：

- 渲染侧：把期号与结果合并进同一个 `<tr>`（twjinniu `renderSixiaoBama` 现在是两个 `<tr>`）；
- 审计侧：对同一 `<table>` 内相邻 `<tr>` 做拼接后再判定。

本轮以「修渲染 + 自建容器级只读校验脚本」弥补（见 `.codex-temp/list_yellow_units.py`）。

### 5)【建议·流程】R5 / R8 误报（已逐条取证）

| 站点 | 模块 | R8/R5 报告 | 结论 | 证据 |
| --- | --- | --- | --- | --- |
| twjinniu | `#twjinniu-sanxiao-15ma` | R8：8 期全部判定为命中 | **误报** | 审计叶子 8 行的 `hasKai=False`，文本是「270期七肖中**特**：www.twtongtian.com长期跟踪」，「中」来自模块名。整行真实判定是混合：270对 269对 268对 267错 266错 265对 264错 263错 |
| twcf888 | `#gslist` | R8：10 期全部判定为命中 | **误报** | 审计叶子 16 行 `hasKai=False`，文本是文章卡片标题「270期：【逢买必中】」「270期：【准杀7码】」，「中」「准」来自标题。该容器是文章列表，不是预测行 |
| twcf888 | `#pred-amgst-470`（平特三肖连） | R8：8 期全部判定为命中 | **正常，非缺陷** | 逐个独立复算 8/8 一致：3 肖平特，只要开奖 7 个生肖里有任一候选即命中。例 2026270 候选=牛猴蛇，开奖 7 肖=兔猴蛇虎牛兔马，交集=牛猴蛇 |
| twcf888 | `#pred-jhq-88`（准杀7码） | R8：8 期全部判定为命中 | **正常，非缺陷** | 逐个独立复算 8/8 一致：特码不在 7 个杀码内即命中。例 2026270 杀码=17,22,14,42,02,09,15，特码=37，不在内 |
| twjinniu | `#twjinniu-yixiao-yima` | R5：连续 8 期展示值相同「台湾通天网 台湾一肖一码大公」 | **误报** | 「开」字来自静态标题「大公**开**」，不是开奖分隔符；该模块本身也没有变化值可比较 |
| twwanli / twsyw | — | R8=0 | 参考实现 | — |

R8 误报的共同根因：`verdict_of()` 在整行找不到 `开/開` 时会退化为「在整行里搜
`不中/错/输/赢/准/对/中`」，于是模块名/文章标题里的「中」「准」被判成判定。
建议硬化：只有当行内存在真正的开奖分隔（`开\s*[:：]` 或 `开奖`）时才允许取判定，
否则该行不计入 R8；R5 的 `开/開` 过滤同理（本次「大公开」即被误判为开奖标记）。

**生成质量附注（非展示违规）**：twcf888 `准杀7码`（mode 88）8 期杀码列表高度模板化
（每期都含 `17`、`01`、`14`），虽然逐期文本不同、未触发 S7，但候选生成质量值得主线关注。

### 6)【登记·非预测区】twcf888 静态公告块

`frontend/public/vendor/twcf888.com/index.html:335` 的 `<div class="ymgg" style="background-color: #FFFF00">`
是供应商「本站网址」公告块（非预测行），是全页唯一与判定无关的固定黄底。属页面装饰，
未改动；若规范要求整页零固定黄底，需要单独决策。

### 7)【登记·死代码】twcf888 mode 473 反向高亮

`buildModeSpecificPrediction()` 内 mode 473 仍是
`highlightValue: row.is_opened && row.is_correct === false ? resultZodiac : ""`（同样违反 S3）。
其调用方 `buildModuleCell` / `buildSsxztSection` 在当前 id 生成规则下不可达（死代码），
因此本轮未改，登记备查，避免日后接线时重新引入。

---

## 六、本地/线上验证证据（脚本均放 `.codex-temp/`，只读）

| 脚本 | 作用 |
| --- | --- |
| `.codex-temp/list_yellow_units.py` | 容器级枚举所有黄底单元并关联所在行，直接找「错行黄底」 |
| `.codex-temp/check_cf_kill.py` | twcf888 `[id^=pred-]` 模块逐行「对/错 + 黄底」 |
| `.codex-temp/show_module_local.py` | 打印模块每个 `[data-prediction-*]` 槽位的文本与黄底，用于 twwanli 高亮错位 |
| `.codex-temp/r8_verify.py` / `r8_twjinniu.py` / `r8_recompute.py` | R8 误报复刻（审计叶子 `hasKai`）+ mode 470/88 独立复算 |
| `.codex-temp/probe_mode38.py` | mode 38 `is_correct = null` 根因复现 |
| `.codex-temp/compare_tj.py` / `show_tj_open.py` | twjinniu 修复前后生成 HTML 对比 |

关键量化结论：

- twjinniu `#sxbm` + `#pmzq`：错行内黄底单元 **线上 15 → 本地 0**。
- twcf888 6 个绝杀模块：错行带黄底 **线上 13 → 本地 0**。
- twwanli `#dssx`：线上 270 期高亮在第一组（开奖马在第二组）→ 本地 186 期高亮在第二组（开奖牛在第二组）。
- 四站 `pageerror` 全程 0（线上、本地均是）。
