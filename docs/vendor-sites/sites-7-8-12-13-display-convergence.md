# 站点 7 / 8 / 12 / 13 剩余展示违规收敛报告

范围：`twjinniu`(web 7) / `twcf888`(web 8) / `twwanli`(web 12) / `twsyw`(web 13)。
依据：`docs/prediction-display-standard.md`（S1–S8 + R1–R8）、`backend/docs/prediction-module-rules.md`（判定口径）。
未 commit / 未部署 / 未改已落库预测正文；线上只做只读抓取。

---

## 一、结论摘要

本轮共确认 **6 条真阳性**（1 条是共用文件层面的系统性判定缺陷，影响 31 个模块实例）与 **21 条审计口径假阳性**。

| 站点 | 处理 | 真阳性 | 假阳性（不动代码，仅登记） |
| --- | --- | ---: | ---: |
| twcf888 | 平特命中项高亮 + 绝杀一波判定取反 | 2 类 | R8×4 |
| twjinniu | 三肖15码展示/判定口径对齐 | 1 | — |
| twwanli | `#yxym` 波色候选取值 | 1 | R8×3 |
| twsyw | `#nannv` 展示候选、`#kill1tou` 展示全部候选头 | 2 | R8×24 |

附带发现（未在用户清单内，但属真实缺陷，已一并修复）：
**共用文件 `frontend/lib/prediction-contract.ts` 的判定交叉校验把 31 个模块实例的「真命中」强制改写成「错」**
（四站 `title_5` 天地生肖、`sanxiao15ma` 三肖15码、`9xiao12ma`、`dxztt1`、`title_246`、`title_251`、
`daxiao_2tou`、`title_83`、`title_142`、`qianhou_texiao`、`sizixuanji`、`title_15` 等），
直接违反「判定必须与真实开奖一致」。

---

## 二、关键根因：共用文件的判定交叉校验误判（真缺陷）

`frontend/lib/prediction-contract.ts::reconcileVerdict()` 用「候选集合是否命中真实开奖」交叉校验上游判定：
上游 `is_correct=true` 而候选集合里找不到开奖目标时，强制改写成 `false`。
但站点页分支只把 `raw.content` 交给候选集合构造器，而**很多玩法的候选列不是 `content`**：

| 玩法 | 候选所在列 |
| --- | --- |
| 天地生肖（mode 5） | `xiao`（2 肖），`content` 只是静态的「天肖/地肖」整组定义 |
| 三肖15码中特（mode 72） | `xiao`（9 肖）+ `code`（15 码），`content` 为 null、`prediction_text` 只有号码串 |
| 单双公式（mode 15）/ 四字玄机 | `title` / `jiexi` |
| 单双四肖一类 | `xiao_1` / `xiao_2` 两列 |
| 家禽野兽 | `jia` / `ye`；黑白肖 `hei` / `bai`；波色 `wave` |

后果：`verifyVerdictAgainstCandidates` 返回 `contradicted`，`reconcileVerdict` 把 `is_correct` 从 `true` 改成 `false`，
页面显示「错」。扫描脚本（`.codex-temp/scan_reconciled.py`，比对 `result.isCorrect` 与 `raw.is_correct`）实测：

```text
.codex-temp/modules-live-twjinniu.json  sanxiao15ma  三肖15码中特   changed=8   sample=[('2026270', True, False), …]
.codex-temp/modules-live-twjinniu.json  title_5      天地生肖       changed=1
.codex-temp/modules-live-twsyw.json     title_5      天地生肖       changed=1
.codex-temp/modules-live-twwanli.json   title_5      天地生肖       changed=1
.codex-temp/modules-live-twcf888.json   title_5/title_15/sizixuanji/9xiao12ma/dxztt1/title_246/title_251/daxiao_2tou …
modules_changed=31
```

进程内复算证据（`python .codex-temp/verify_tj_mechanism.py`，直接调后端函数）：

```text
2026270 api_is_correct=False recomputed=True  special=37马
    loader_text='虎,马,龙,鼠,猪,牛,猴,鸡,兔'   ← mode 72 的候选列 xiao
    outcome='单数|大数|单|大|3头|3头单|7尾|7|蓝波|合双|合数大|家禽|马|37|火|书|6段'
```

`mismatches=10/19`（本地库）与 `8/20`（线上库）全部是「后端真判 true、接口被改判 false」。

### 修复

`frontend/lib/prediction-contract.ts` 新增 `verdictCandidateColumns()` 白名单
（`content/xiao/code/xiao_1/xiao_2/hei/bai/jia/ye/jiexi/title/wave/tail/tou/wei/dx/ds`），
只补**候选列**、**刻意不含** `res_code/res_sx/res_color/result_text/is_correct`，
避免候选集合自动包含开奖结果而退化成恒真。`prediction.extra` 与 `prediction.tokens` 的对外形状均未改。

契约测试新增 3 条断言（`frontend/test/prediction-verdict-truth-contract.ts`）：
`xiao` 列候选的真实命中必须保持 `true`、`title_5` 同理、候选列确实不含真实开奖时仍必须改判为 `false`。

```text
node frontend/test/run-prediction-verdict-truth-contract.mjs   → prediction verdict truth contract passed
node frontend/test/run-prediction-token-shape-contract.mjs     → passed (20 个模块)   ← tokens 形状未变
node frontend/test/run-prediction-contract-dedup.mjs           → passed
```

> `run-prediction-modules-route-contract.mjs` 在 HEAD 与工作区都因 runner 无法解析
> `@/sites/*/site.manifest`（data: URL 里没有别名解析）而失败，**属既有问题，与本轮改动无关**
> （已用 `git stash` 在 HEAD 上复现同样报错）。

类型检查 `node node_modules/typescript/bin/tsc --noEmit -p frontend/tsconfig.json` 全仓只有 2 个错误，
**两个都在 HEAD 上已存在**（已用 `git stash` 逐文件复现），本轮未引入新错误：

```text
frontend/app/api/kaijiang/[[...path]]/route.ts(2275,29) TS2345   ← 该文件本轮未改（git status 干净）
frontend/test/prediction-verdict-truth-contract.ts(233,17) TS2322 ← HEAD 位置；本轮插入的新断言把它挤到 352 行，代码未动
```

---

## 三、逐站逐条：真 / 假判定与证据

### 3.1 twcf888（web 8）

#### (1) R4×16「平特命中行没有黄色高亮」——**真阳性，已修**

涉及：`#pred-amgst-470|平特三肖连`、`#pred-jhq-43|平特两肖`、`#pred-jhq-54`/`#pred-gs-54|平特一尾`。

证据链：
1. **审计口径证明「确实没有黄底」**：`ROW_SCRIPT` 的行合并规则是
   `if (!/开|開/.test(childText) && countYellow(child) === 0) continue;`，
   即「没有 `开` 字且没有黄底」的同辈才被跳过。这些候选块被跳过 → 说明它**一个 `#FFFF00` 都没有**。
2. **线上 DOM 对照**（`python .codex-temp/probe_dom.py twcf888 --ids pred-jhq-54 …`）：

```html
<!-- 270期：判「对」，但候选项无任何黄底 -->
<tr><td class="twcf888-module-row"><p …>270期【平特一尾】开 <font color="#FF0000">马37对</font></p>
    <p …><font color="#0000FF">0</font></p></td></tr>
<!-- 269期：判「对」，因为特码本身尾数命中，才碰巧有黄底 -->
<tr><td class="twcf888-module-row"><p …>269期【平特一尾】开 <font color="#FF0000">鸡46对</font></p>
    <p …><font color="#0000FF"><span style="background-color:#FFFF00;…">6</span></font></p></td></tr>
```

3. **根因**：`formatPredictionContent()` 的 `matchedLabel` 只用 `resultCode`（特码）与 `resultZodiac`（特肖）去比对候选；
   而平特口径是「**开奖 7 个号码里任一号码**的生肖/尾数落在候选集合内」
   （`backend/docs/prediction-module-rules.md`：43 `zodiac_flat` / 54 `tail_flat` / 470 `zodiac_flat`）。
   270 期候选 `0尾`，37 不是 0 尾（`matchedLabel` 失败），但 30 是 0 尾 → 判定「对」却无高亮。

修复（`frontend/public/vendor/twcf888.com/index.html`）：
新增 `flatMatchedFlags(modeId, list, row)` ——
`FLAT_ZODIAC_MODES=[43,470]` 用 `raw.res_sx` 的 7 个开奖生肖、`FLAT_TAIL_MODES=[54]` 用 `raw.res_code` 的 7 个开奖尾数，
返回与候选列表等长的布尔数组，只高亮真正落在开奖集合里的那一项（可多项）。

修复前后对照（本地 / 线上）：

| 位置 | 修复前 | 修复后 |
| --- | --- | --- |
| `#pred-jhq-54` 平特一尾 | 线上 270期【平特一尾】开 马37**对** ｜ 候选 `0` 无高亮 | 本地 190期【平特一尾】开 狗45**对** ｜ 候选 `<span bgcolor #FFFF00>5</span>` |
| 同上（未命中） | — | 本地 189期【平特一尾】开 狗09**错** ｜ 候选 `4` **无高亮**（S3 保持） |
| `#pred-amgst-470` 平特三肖连 | 线上 270期【平特三肖连】开 马37**对** ｜ 候选全无高亮 | 本地 190期 候选 `狗蛇虎` → **只 `狗`、`蛇` 有黄底，`虎` 无** |
| `#pred-jhq-43` 平特两肖 | 线上 270期【平特两肖】开 马37**对** ｜ 候选全无高亮 | 本地 190期 候选 `猴狗` → 两项都命中 7 码生肖，`猴`、`狗` 都有黄底 |

#### (2) R8×5 —— 4 条正常、1 条**真缺陷（已修）**

逐期独立复算（`.codex-temp/dump_module.py` + `seq` 序列，19~20 期窗口）：

| 模块 | 序列（对/错） | 结论 |
| --- | --- | --- |
| `#pred-amgst-470` 平特三肖连 | 19 期全对 | **正常**：3 肖平特命中率 `1-(9/12)^7≈84%`，逐期复算一致（如 2026270 候选 牛猴蛇，开奖 7 肖 兔猴蛇虎牛兔马 → 三项全中） |
| `#pred-amgst-50` 一句中特（mode 50） | 对错对错对错对对对错对对对对对对对对错 | **正常**：候选 7 肖，命中率 ~99%；7 连对在概率内。⚠️但 `prediction-module-rules.md` 把 mode 50 登记为 `blocked_pending_rule`，实际却在输出 `is_correct`，属文档/机制登记不一致（遗留项 6-3） |
| `#pred-jhq-88` 准杀7码（mode 88） | 19 期 18 对 1 错 | **正常**：杀 7/49，命中率 42/49=85.7% |
| `#pred-gs-143` 一波中特（mode 143） | 错错错错错对错对错错错对对错对错错对错 | **正常**：264~270 连错 7 期，`(2/3)^7=5.8%`；逐期复算一致（如 270 候选 红波、特码 37=蓝波 → 错） |
| `#pred-jsb-143` 绝杀一波（mode 143） | 同上一列，7 连错 | **真缺陷** ↓ |

`#pred-jsb-143` 真缺陷证据：`frontend/lib/twcf888-articles.ts` 把两个**玩法相反**的栏目映射到同一个 mode 143：

```ts
{ id: "2290", title: "绝杀一波", group: "jsb", modeId: 143, … }
{ id: "3049", title: "一波中特", group: "gs",  modeId: 143, … }
```

供应商静态样例（同一仓库 `frontend/public/vendor/twcf888.com/index/index/jsb/id/2290.html`）给出权威口径：

```text
2026156期 绝杀一波【蓝波】 开 24羊 对     ← 24=红波，未杀中 → 对
2026152期 绝杀一波【蓝波】 开 25马 错     ← 25=蓝波，杀中了 → 错
2026151期 绝杀一波【绿波】 开 05虎 错     ← 05=绿波，杀中了 → 错
```

即「绝杀一波 的准 = 特码波色 **不在**被杀波色里」，与 mode 143 `is_correct=true`（特码波色 **在**候选里）互为取反。
原实现直接沿用 mode 143 的判定 → 7 期全「错」，而真实应为全「对」。

修复：catalog 新增 `verdictInverted?: boolean`（仅 2290），
`frontend/lib/twcf888-homepage.ts` 透出 `verdict_inverted`，
渲染层 `effectiveVerdictRow()` 取反并禁止参与高亮（杀号命中时开奖目标本就不在候选里，没有可高亮的命中项）。

修复前后对照（本地）：

| 期号 | 修复前（沿用 mode 143） | 修复后（绝杀口径取反） |
| --- | --- | --- |
| 190期（杀 红波，开 45=红波） | 对 ❌ | **错** ✅ |
| 189期（杀 红波，开 09=蓝波） | 错 ❌ | **对** ✅ |
| 188期（杀 绿波，开 38=绿波） | 对 ❌ | **错** ✅ |

### 3.2 twjinniu（web 7）

#### (3) R4×1 `#twjinniu-sanxiao-15ma|七肖中特 命中却无高亮`——**真阳性，已修**

证据：
1. 线上 269期：`269期七肖中特：…长期跟踪 开:46鸡对`，`highlights=0`。
2. 后端数据（`modules-live-twjinniu.json::sanxiao15ma` 2026269）：`xiao=马,鼠,蛇,猪,虎,羊,龙,鸡,兔`，
   特肖 `鸡` 位于 **index 7（第 8 位）**，特码 `46` 不在 `code` 里 → `is_correct=true`。
3. 渲染代码 `renderSanxiao15ma()`：`isCorrect` 用 `zodiacs.includes(...)`（全部 9 肖），
   但展示只给 `xiao7/xiao5/xiao3 = zodiacs.slice(0,7/5/3)`，`renderZ` 又只在这些子集里找命中项
   → **命中项落在第 8、9 位时永远不可见**，出现「显示对、整行零高亮」。
4. 用户问的「186期同类行为」：本地 before 审计的 R4 样例正是 `186期…开:42`，**同一根因**，已一并覆盖。

修复（`frontend/lib/twjinniu-homepage.ts::renderSanxiao15ma`）：
- 判定收敛为 mode 72 的官方规则「**特肖 ∈ 全部候选生肖**」（原实现多了一条
  `|| code15.includes(result.code)` 的或运算，与 `prediction-module-rules.md`
  「72 | sanxiao15ma | special zodiac is in any candidate」不一致；
  实测 20 期数据里「特码命中而特肖不命中」的分歧行为 0，改动无语义回归）；
- 候选生肖超过 7 个时补一行 `(N.)肖特:` 展示**完整候选集合**，保证命中项一定在页面上。

修复前后对照（本地）：

```text
修复前 190期  (7.)肖特:鼠狗虎马蛇龙兔  (5.)肖特:鼠狗虎马蛇  (3.)肖特:鼠狗虎  开:45狗对   ← 命中的狗在(7.)里，碰巧可见
       186期  (7.)肖特:马猪蛇鼠虎猴龙  (5.)肖特:马猪蛇鼠虎  (3.)肖特:马猪蛇  开:42…      ← 命中项是第 8/9 位 → 零高亮（R4）
修复后 190期  (7.)肖特:鼠[狗]虎马蛇龙兔 … (9.)肖特:鼠[狗]虎马蛇龙兔猪羊  开:45狗对   ← 补了 (9.) 行
       189期  (7.)肖特:羊马蛇虎猪[狗]龙   (9.)肖特:羊马蛇虎猪[狗]龙猴兔   开:09狗对
       191期  (9.)肖特:猪羊马虎蛇猴狗龙鸡                               开:待开奖   ← 未开奖：无判定、无高亮
       （`[x]` = 黄底单元格）
```

### 3.3 twwanli（web 12）

#### (4) R8 `#yxym|波色 暂无后端资料 5 期全对`——**真阳性，已修**

证据（线上 DOM，修前）：

```html
<tr><td class="td1"><span data-prediction-issue>2026270期:波色</span></td>
    <td class="td2"><span data-prediction-content="" data-prediction-hit="true">暂无后端资料</span></td>
    <td class="td3"><span data-prediction-result>开:37马对</span></td></tr>
```

- **不是后端缺数据**：mode 38（双波中特）本期有数据，`tokens=["蓝波","绿波"]`、`is_correct=true`；
- **是渲染层取错列**：`renderOneCodeOneXiaoTable()` 的波色行读取 `rawValue(source,"wave")`，
  但 mode 38 的候选在 token 正文（`蓝波,绿波`）里，`raw.wave` 不存在 → 取到空 → 落兜底串「暂无后端资料」；
- 同时 `writeRow(..., hit=true)` 把黄底打在整段兜底串上 → **兜底串被高亮 + 给「对」**，违反 S1/S2/S5。

修复（`frontend/public/vendor/twwanli/site-data-adapter.js`）：
候选列回落到 `labels(source)`（按 `,，、空白` 拆词去重取前 2 个）；
真取不到候选时**不给判定、不高亮**（只显示兜底串）；
`writeRow()` 新增 `contentHtml` 参数 + `highlightOnly()`，命中时只给命中的那个波色上黄底。

修复前后对照：

```text
修前(线上 2026270)  2026270期:波色 暂无后端资料[黄底]  开:37马对
修后(本地 2026190)  2026190期:波色 <红波>[黄底]+绿波    开:45狗对      ← 45=红波
修后(本地 2026189)  2026189期:波色 <蓝波>[黄底]+红波    开:09狗对      ← 09=蓝波
修后(本地 2026186)  2026186期:波色 绿波+<蓝波>[黄底]    开:42牛对      ← 42=蓝波
```

#### (5) R8 `#ybzt` / `#tdsx` / `#3tzt` 各 5 期全错——**假阳性（审计口径），不改代码**

容器级复算（19 期窗口，`backend/public/api` 的 `is_correct`）：

```text
#ybzt  一波中特(title_143)  错错错错错对错错错错错对对错对错错错错   5 连错后命中；命中率 1/3 → (2/3)^5=13%
#tdsx  天地生肖(title_5)    错错错错错对错错错错错错错错错错错错对   候选 2 肖、命中率 2/12 → 5 连错概率 40%
#3tzt  三头中特(3tou)       错错错错对错对对对错对对对对对对对对对   5 连错后 2026266 命中（audit 也列出了 `#3tzt|1头-0头-4头 1 期对`）
```

根因是审计的**模块归属被行合并规则劈成两半**：命中行的 content 带黄底 → 被并入、拿到行内标签，
未命中行的 content 既无 `开` 也无黄底 → 被跳过、丢掉标签，于是这两个分组各自「全同」。
**没有任何一期真实判定写死或候选集失效。**

### 3.4 twsyw（web 13）

#### (6) R5 `#table7|三头资料 连续 3 期展示值相同 '3头'`——**真阳性（且被低估为 3 期，实为 4 期），已修**

容器级探针（线上 `#kill1tou`）：

```text
2026270期三头资料：3头开:37马对   ← 37 是 3 头
2026269期三头资料：3头开:46鸡错   ← 46 是 4 头（这一行未命中 → 无黄底 → 被审计跳过）
2026268期三头资料：3头开:11猴对
2026267期三头资料：3头开:24羊对
```

即 270/269/268/267 **四期**展示值都是 `3头`（S7 违规），审计只数到 3 期。
根因：`renderKill1tou()` 用 mode `3tou`（三头中特）供数，但只渲染 `headLabels(row,1)`（第一个候选头），
而判定口径是「特码头 ∈ **3 个**候选头」——展示与判定用了两个不同的数据源。

修复：展示全部 3 个候选头，命中时只给命中的那个头上黄底（同一逻辑在 `#santou` 早已如此）。

修复前后对照（本地）：

```text
修前 190期 三头资料：3头                       开:45狗对 (3头黄底)
修后 190期 三头资料：<4头>[黄底].2头.3头        开:45狗对
修后 189期 三头资料：3头.<0头>[黄底].4头        开:09狗对
修后 是 本地 before 审计里的三条 R5（'2头'×3、'0头'×3、'1头'×4）全部消失
```

#### (7) R8×24「整列全错 / 整列全对」——**全部假阳性（审计口径），不改代码**

19 期窗口内逐模块复算，**每个模块都是命中/未命中混合**：

```text
#fslx 家禽野兽            HIT/MISS → 错错对对对对错错对错错错对对错错对对对
#winner12 赢家12码        错错对对错对错错错错对对错错错错对对对
#m24 24码                错错对对错对错错错错对对对错错错对对对
#jiaye4xiao 家野四肖      对错对错对对错对错错错错错错错错错错错
#dssx 单双四肖            对对对错对对错对对错错错对对错对对对错
#daxiao 大小中特          对对错错对错错对对错对错错对错对对错对
#nannv 男女中特（title_5） 错错错错错对错错错错错错错错错错错错对     ← 候选 2/12，2 次命中完全正常
#table7|五尾资料 / 九肖资料 / 琴棋书画资料 / 绝杀三肖 / 合数单双资料 / 四段资料 … 均为混合
```

`#table7 共 116 期全错` 更是**定义上的必假**：`#table7` 是 twsyw 页面里 **13 张不同表格复用的同一个 id**
（`grep -c 'id="table7"' frontend/public/vendor/twsyw/index.html` → 13），
审计的容器归属把它们并成一个模块；再加上未命中行丢掉标签，`#table7`（无标签）这一组
就是「十几个玩法的未命中行并集」，必然全部是「错」。逐个玩法核对的清单见上表与附录。

**`#daxiao` 全错 与 `#daxiao|大` 全对 同时存在的结构说明**：
它们**不是**两个玩法，而是同一个 `#daxiao` 区段（`大小中特`，mode `daxiao`）被审计的模块归属劈成了两半——

- `#daxiao|大` = 「本期候选是 `大` 且命中」的行（带黄底 → 被并入 → 从 `2026270期 大 开:37马对` 里取到行内标签 `大`）；
- `#daxiao|小` = 「本期候选是 `小` 且命中」的行（同上，标签 `小`）；
- `#daxiao`（无标签）= 「未命中」的行：content 只有 `大`/`小` 一个字符，既无 `开` 字也无黄底 → 被行合并规则跳过
  → 这一行拿不到标签 → 落到容器级 `#daxiao` 分组。因为该分组只剩未命中行，必然「全错」。

同一结构解释了 twsyw 的 `#winner12` / `#m24` / `#fslx` / `#dssx` / `#jiaye4xiao` / `#nannv`
与 twwanli 的 `#ybzt` / `#tdsx` / `#3tzt`：**每一条「N 期全错」都能在对应模块里找到它的「N 期全对」另一半。**

#### (8) `#nannv`（男女中特）展示候选——**真阳性（展示缺陷），已修**

线上 DOM 修前：

```html
2026270期 天地生肖资料：天肖：兔马猴猪牛龙   开:37马错   ← 天肖组里明明含 马，却显示「错」
2026269期 天地生肖资料：天肖：兔马猴猪牛龙   开:46鸡错
2026268期 天地生肖资料：地肖：蛇羊鸡狗鼠虎   开:11猴错
```

- `renderNannv()` 用 `heavenly(row)` 渲染的是 `raw.content`（**静态的天地分组定义**，整组 6 肖），
  而 mode 5 的真实候选是 `raw.xiao`（本期 2 肖，后端就是按它判定的）；
- 后果：展示值几乎恒定（只有「天肖/地肖」两种，S7），且「天肖：兔马猴猪牛龙」里含开奖特肖 马 却给「错」，
  判定与展示无法对应，命中也没有可高亮的候选项。

修复：与 twwanli `#tdsx` 同口径渲染 `【天肖/地肖 + 本期 2 个候选生肖】`，只给命中的生肖上黄底。

修复前后对照（本地）：

```text
修前 2026190期 天地生肖资料：天肖：兔马猴猪牛龙      开:45狗错
修后 2026190期 天地生肖资料：【天肖+<狗>[黄底]猴】    开:45狗对
修后 2026188期 天地生肖资料：【天肖+龙<蛇>[黄底]】    开:38蛇对
修后 2026189期 天地生肖资料：【天肖+龙蛇】            开:09狗错    ← 未命中：零黄底
```

> 本地 before 审计里 `#nannv|天地生肖资料 连续 3 期展示值相同 '地肖：蛇羊鸡狗鼠虎'` 的 R5 也随之消失。

---

## 四、改动文件清单

| 文件 | 性质 | 站点 | 说明 |
| --- | --- | --- | --- |
| `frontend/lib/prediction-contract.ts` | **共用文件** | 全部 10 站 | 新增 `verdictCandidateColumns()` 候选列白名单，站点页判定交叉校验不再把候选列不在 `content` 的真命中改判为「错」；`prediction.tokens` / `prediction.extra` 形状未变 |
| `frontend/test/prediction-verdict-truth-contract.ts` | 测试 | — | 新增 3 条断言（`xiao` 真命中保持 true、`title_5` 同上、候选列确实不含开奖时仍须改判） |
| `frontend/public/vendor/twcf888.com/index.html` | 站点私有 | 8 | 新增 `FLAT_ZODIAC_MODES`/`FLAT_TAIL_MODES`/`flatMatchedFlags()`，平特 43/54/470 按 7 个开奖号码定位命中项高亮；新增 `effectiveVerdictRow()` 支持 `verdictInverted`；取反栏目不参与高亮 |
| `frontend/lib/twcf888-articles.ts` | 站点私有 | 8 | 文章栏目定义新增 `verdictInverted?: boolean`（仅 `2290 绝杀一波`）；`buildArticleRows()` 按栏目收敛判定后再渲染 |
| `frontend/lib/twcf888-homepage.ts` | 站点私有 | 8 | `Twcf888HomepageCard` 透出 `verdict_inverted` |
| `frontend/lib/twjinniu-homepage.ts` | 站点私有 | 7 | `renderSanxiao15ma()`：判定收敛为「特肖 ∈ 全部候选生肖」、补 `(N.)肖特` 完整候选集合行 |
| `frontend/public/vendor/twwanli/site-data-adapter.js` | 站点私有 | 12 | `writeRow()` 新增 `contentHtml`；新增 `escapeHtml()`/`highlightOnly()`/`specialWave()`；`renderOneCodeOneXiaoTable()` 波色行候选回落到 token 正文、命中只高亮该波色、无数据不给判定不高亮 |
| `frontend/public/vendor/twsyw/site-data-adapter.js` | 站点私有 | 13 | `writeRow()` 新增 `contentHtml`；新增 `escapeHtml()`/`highlightOnly()`/`rawField()`/`specialParts()`/`chosenZodiacs()`；`renderNannv()` 改渲染真实候选生肖；`renderKill1tou()` 改展示全部 3 个候选头 |

**未改**：`frontend/app/api/kaijiang/**`、`backend/src/**`、`scripts/audit-prediction-display.py`（按用户要求不动审计脚本）、已落库预测正文。

> 工作区存在并行任务对 `frontend/public/vendor/shengshi8800/**`、`twsaimahui/**`、`twssz/**`、
> `docs/prediction-display-standard.md` 的改动，与本轮改动文件无重叠；本轮未使用任何会波及它们的
> git 操作（before/after 对照用的是按路径备份/还原，见 `.codex-temp/swap_mine.py`）。

---

## 五、审计命令与前后数字

```powershell
# 线上（只读，改动前的基线复核）
python scripts\audit-prediction-display.py twcf888 twjinniu twwanli twsyw --json .codex-temp\audit-A-before.json --dump-rows .codex-temp\rows-A.json
# 本地预检（对照用：临时把 7 个改动文件还原到 HEAD，见 .codex-temp/swap_mine.py）
python scripts\audit-prediction-display.py twcf888 twjinniu twwanli twsyw --base-url http://127.0.0.1:3000 --json .codex-temp\audit-A-local-before.json
# 本地预检（改动后，最终）
python scripts\audit-prediction-display.py twcf888 twjinniu twwanli twsyw --base-url http://127.0.0.1:3000 --json .codex-temp\audit-A-local-final.json --dump-rows .codex-temp\rows-A-local-final.json
```

### 5.1 数字对照

| 时点 | twcf888 | twjinniu | twwanli | twsyw |
| --- | --- | --- | --- | --- |
| **线上基线（`audit-A-before`，与任务给定一致）** rows | 451 | 469 | 202 | 545 |
| 线上基线 error / js_errors / warn | 0 / 0 / **21** | 0 / 0 / **1** | 0 / 0 / **4** | 0 / 0 / **25** |
| **本地 before（同口径、同期号集）** rows | 451 | 469 | 202 | 545 |
| 本地 before error / js_errors / warn | 0 / 0 / **11** | 0 / 0 / **2** | 0 / 0 / **1** | 0 / 0 / **11** |
| **本地 after（最终）** rows | 451 | 469 | 202 | 545 |
| 本地 after error / js_errors / warn | 0 / 0 / **6** | 0 / 0 / **1** | 0 / 0 / **0** | 0 / 0 / **7** |
| 相对基线 | **−15** | 0（换了一条） | **−3** | **−18** |
| 相对同口径本地 before | **−5** | **−1** | **−1** | **−4** |

- `error=0`、`js_errors=0` 四站全部满足；每站 warn 均**不高于**给定基线，且相对同口径本地 before **全部下降**。
- 线上基线与本地数字不可直接比（期号集不同：线上 2026271~2026252，本地 2026191~2026172），
  因此额外做了「本地 before（HEAD 渲染 + 同期号集）」作为公平对照。

### 5.2 剩余 warn 的逐条判定

| 站点 | 剩余 warn | 判定 |
| --- | --- | --- |
| twcf888 ×6 | `#pred-amgst-26`/`#pred-jhq-26` 琴棋书画、`#pred-amgst-470` 平特三肖连、`#pred-jsb-98` 绝杀一行、`#pred-jhq-43` 平特两肖、`#pred-gs-100` 稳中七肖，各「7 期全对」 | R8 统一性提示。均为高命中率玩法（琴棋书画候选 9/12、平特 3 肖 ~84%、平特 2 肖 ~69%、7 肖 ~96%）在 7 期窗口内全部命中，属概率内；逐期复算与后端一致 → **正常** |
| twjinniu ×1 | `#twjinniu-sanxiao-15ma|七肖中特 7 期全对` | **正常**（mode 72 候选 9/12，命中率 75%，7 连对概率 13%）。这条是 R4 修复的副产物：原来 R4（命中无高亮），现在命中行拿到了高亮与标签，同一批行才被识别为「全对」；数量与基线持平 |
| twwanli ×0 | — | 修完 `#yxym|波色` 后清零 |
| twsyw ×7 | `#table7|合数单双资料` R5×2、`#table7|琴棋书画资料` R5×1、`#daxiao|大`/`#daxiao|小`/`#table7|合数单双资料`/`#table7|琴棋书画资料` R8×4 | R5 两条是**真实 S7**（生成侧相邻期唯一性），见遗留项 6-4；R8×4 是审计口径假阳性（同模块混合判定被劈成两半） |

---

## 六、遗留项

1. **整块黄底（S2 颗粒度）**：`[data-prediction-hit="true"]{background-color:#FFFF00}` 打在 content 整段上，
   `#winner12`/`#m24`/`#fslx`/`#dssx`/`#daxiao`/`#jiaye4xiao`/`#santou` 等模块在命中期会把**没命中的候选项一起点亮**。
   本轮只把用户点名的 `#yxym|波色`、`#nannv`、`#kill1tou` 改成逐项高亮；其余模块要按各玩法把 content 拆成原子，
   属较大改造，未做（审计的 R3/R4 也抓不到这种颗粒度问题）。
2. **`#kill1tou` 面板语义**：面板标题（供应商模板）是「绝杀一头」，数据源却是 mode `3tou`（三头中特，命中口径）。
   本轮已让展示与判定一致（展示全部 3 个候选头 + 命中高亮），
   但「绝杀」语义与数据源不匹配仍需产品/模板层决策（要么换数据源，要么改标题）。
3. **mode 50（一句真言）登记不一致**：`backend/docs/prediction-module-rules.md` 标注
   `blocked_pending_rule / blocked: missing_verified_rule`，但 `/api/.../prediction-modules` 实际输出 `is_correct`
   （twcf888 `#pred-amgst-50|一句中特` 7 期全对即由此而来）。属文档与机制登记不一致，未改。
4. **twsyw 残留 R5（真实 S7，生成侧）**：
   - `#table7|合数单双资料`：`合单/合双；合数大小资料：合数大` 连续 3 期相同（190/189/188、186/185/183）；
   - `#table7|琴棋书画资料`：`兔蛇鸡羊猴猪虎龙马` 连续 3 期相同（175/174/173）。
   已落库历史无法靠渲染修复；需在 `backend/src/prediction_generation/diversity.py` 一侧对相应 mode
   补相邻期唯一性约束（与规范「五之五」同类，但影响的是未来生成的行，不会改变本报告的审计数字）。
5. **审计脚本口径（按用户要求只登记、未改）**：本次三处误判/漏报的共同根因有两个——
   - **行合并规则漏掉未命中行的候选块**：`ROW_SCRIPT` 只并入「含 `开` 或带黄底」的同辈，
     未命中行的候选 content 两者都不满足 → 被丢弃 → 该行拿不到行内标签，
     于是「同一模块」被劈成「有标签的命中半」与「无标签的未命中半」两个分组，
     造成 twsyw 24 条 R8 假阳性、twwanli 3 条 R8 假阳性，以及 twcf888/twjinniu 的 R4 一度「看不见」；
     同时让 twsyw `#kill1tou` 的 R5 少算一期（4 期只报 3 期）。
     建议：行合并至少把「同一个 `<td>`/`<tr>` 内的全部 `[data-prediction-content]` 槽位」并入，
     不受「有无 `开` 字 / 有无黄底」限制。
   - **容器归属被重复 id 污染**：`#table7` 在 twsyw 页面被 13 张表复用 → 归属合并成一个大模块。
     建议：容器归属优先取最近的 `[data-prediction-section]`，其次才是 `id`。
6. **线上验收未做**：本轮未部署（未授权），线上 warn 需在发布后用同一脚本复测；
   `twcf888` 的 R4 线上为 16 条（本地期号集只复现 5 条），发布后应重点复核该 16 条是否清零。
7. **`frontend/tsconfig.tsbuildinfo`、`backend/src/predict/__pycache__/*`** 是构建产物，
   工作区里长期处于 modified 状态，与本轮改动无关。

---

## 七、附录：`#table7` 底下每个玩法的独立复算清单（twsyw，19 期窗口）

```text
模块(mode)                        19 期判定序列（对/错）
title_14 家禽野兽                 错错对对对对错错对错错错对对错错对对对   → 混合，非整列全同
selected_22_codes 精选22码        错错对对错对错错错错对对错错错错对对对   → 混合
ma24 24码                        错错对对错对错错错错对对对错错错对对对   → 混合
shuangbo 双波中特                 对对对错对错对错对对对对对对对对对对错   → 混合
sixiao_sima 四肖四码（#jiaye4xiao）对错对错对对错对错错错错错错错错错错错   → 混合
daxiao 大小中特                   对对错错对错错对对错对错错对错对对错对   → 混合
danshuang4xiao 单双四肖           对对对错对对错对对错错错对对错对对对错   → 混合
title_5 天地生肖（#nannv）        错错错错错对错错错错错错错错错错错错对   → 候选 2/12，2 次命中正常
title_66 5尾中特                  错对对错对对对错错错错对对错错对错对错   → 混合
9xzt 9肖中特                     对对对对对对错对对对错错对对错对对对对   → 混合
qinqi 琴棋书画                    对对对错对对对错对对对对错错错对对对对   → 混合
juesha3xiao 绝杀3肖               错对错对错对对错错对对错对对对错对对对   → 混合
title_132 合数单双                对对错对错错对对错对对对错对对对对对错   → 混合
3tou 3头中特（#kill1tou/#santou） 对错对对对对对对对错错对对对对错错对错   → 混合
title_143 一波中特                错错错错错对错对错错错对对错对错错对错   → 混合
siduanzhongte 四段中特            错对对对错对错错错对对对错错错错对对错   → 混合
```

**结论：`#table7` 底下不存在「整列全错」的真实缺陷**；
`#table7 共 116 期全错` 是「13 张表复用同一 id + 未命中行丢标签」的统计假象。
唯一确认的真实缺陷是 `#kill1tou`（`三头资料` 只展示 3 个候选头中的第一个），已修复。
