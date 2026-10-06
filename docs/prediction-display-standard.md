# 预测模块展示规范与例行检查工作流

适用：本站全部 10 个前台站点（`web_id` 4–13）的所有预测模块。
目的：把「判定正确显示准/对、错误显示错、未开奖不显示判定；命中的生肖/号码/段数/文字黄色高亮，
未命中一律不高亮；静态文本与分组说明正常显示」固化成可自动检查的规则，避免同类缺陷反复出现。

---

## 一、展示规范（硬性规则）

| 编号 | 规则 | 说明 |
| --- | --- | --- |
| **S1** | 判定文字只允许三种状态 | 命中 → `准`（或 `对`，同一站点内保持一致）；未命中 → `错`；**未开奖 → 不显示任何判定文字** |
| **S2** | 只有命中才高亮 | 命中项的生肖 / 号码 / 段位 / 五行 / 头尾 / 波色 / 天地肖 / 文字映射加 `background-color: #FFFF00` |
| **S3** | 未命中绝不保留高亮 | 判定为「错」的那一期，整行（整期）不得出现任何 `#FFFF00`。**不能沿用供应商静态 HTML 里的高亮** |
| **S4** | 逐期独立判定 | 一行里拼了多期（如 `270期…错269期…错`）时，必须按期分别判定与高亮，不能整行共用一个状态 |
| **S5** | 不外泄原始数据 | 页面可见文本不得出现 `["`、`"]`、`\`、JSON 花括号或未解析的 `标签\|值` 原始串 |
| **S6** | 静态文本正常显示 | 分组说明（左肖/右肖、阴肖/阳肖、文肖/武肖、有肖/无肖、吉美/凶丑、肥肖/瘦肖、胆大/胆小…）**两组都要显示**，不能只显示本期恰好抽到的那一组 |
| **S7** | 展示值不得长期重复 | 同一模块相邻 **3 期以上**展示值完全相同即为异常（二选一模块最容易出现） |
| **S8** | 页面无 JS 报错 | 任何 `pageerror` 都视为缺陷（会连带整块模块不渲染） |

判定口径与后端机制一致性以 `backend/docs/prediction-module-rules.md` 为准；
生成的唯一性规则见 `backend/src/prediction_generation/diversity.py`。

---

## 二、自动审计工具

脚本：`scripts/audit-prediction-display.py`（Python + Playwright，chromium 路径已内置）。

```powershell
# 全站审计（约 10–15 分钟），输出 md + json 报告，退出码 1 表示有 error
python scripts\audit-prediction-display.py --json .codex-temp\audit-all.json

# 单站点
python scripts\audit-prediction-display.py twsaimahui --json .codex-temp\audit-tsam.json

# 发布前本地预检：把线上域名换成本地 next dev
python scripts\audit-prediction-display.py twsaimahui --base-url http://127.0.0.1:3000 --json .codex-temp\audit-local.json
```

报告里的检查项与上面的规范一一对应：

| 规则 | 字段 | 级别 | 含义 |
| --- | --- | --- | --- |
| R1 | `raw_json_leak` | error | 可见文本残留原始 JSON 片段（S5） |
| R2 | `verdict_pending` | error（占位+命中）/ warn（占位+未命中） | 未开奖却给判定（S1） |
| R3 | `highlight_miss` | error | 判定「错」但仍有一处黄色高亮（S3） |
| R4 | `highlight_hit` | warn | 命中却没有高亮（S2/S4） |
| R5 | `repeat_run` | warn | 连续 ≥3 期展示值相同（S7） |
| R6 | `empty_legend` | error | 分组说明后面为空（S6） |
| R7 | `verdict_missing` | warn | 已开奖但缺判定文字（S1） |
| R8 | `verdict_all_same` | warn | 某模块 ≥5 期已开奖行判定全同（整列全对/全错） |

**行的切分口径（2026-09-28 起加固）**：供应商经常把「一期」拆到多个元素里，例如

```html
<tr><td>270期【绝杀二肖】开 马37错</td><td>鸡,马</td></tr>          <!-- 高亮在第二个 <td> -->
<tr><td>268期:平特一肖〖羊羊羊〗</td></tr><tr><td>开：<b bgcolor=#FFFF00>11猴</b>错</td></tr>
```

旧版只取「叶子行」，永远看不到 `开:` 与那块高亮，**R3（error 级）会整类漏报**。现在会在叶子的
祖先链（最多 4 层）上把「本节点之后、不含期号的同辈」和「相邻的不含期号的 `<tr>`」合并成一行，
遇到下一个期号立刻停止。合并后第一次自动抓到 twcf888 `#pred-jsb-*` 绝杀类、twjinniu
`#sxbm`/`#pmzq`、shengshi8800 `#yxym`/`#dxzt` 等 30+ 处真实违规。

> 副作用：合并可能把旁边的装饰性黄底（模块标题栏红底黄字、静态公告、图片素材）带进来造成**假阳性**。
> 处置办法是先看 `--dump-rows` 明细或写一个容器级只读探针确认「这块黄底是否属于本期的这一行」；
> 确属装饰的不要改代码，把它记录为脚本待收敛项。

**判定文字的取法（2026-09-28 起加固）**：① 只看「最后一个 `开/開`」之后的部分（模块名里也有「中」）；
② 取**最靠右**的判定字（模块名里也有判定字，如 twcaibawang 的「输尽光」含「输」）；
③ 行内没有 `开/開` 时，只有判定字出现在**行尾**才认账，否则「270期七肖中特：www.xxx.com长期跟踪」
这类标题行里的「中」会被误判成判定；
④ 先把「中奖 / 不中奖」这类状态文案去掉（twjinniu 的 `开奖【www.xxx.com】中奖` 会被读成命中）。

**R4 的豁免**：排除型（杀号）玩法的「准」= 杀掉的集合里没有开奖目标 = **本来就没有可高亮的命中项**，
所以模块文本里含 `绝杀|绝禁|绝版杀|输尽光|必杀|杀N` 时不再报 R4。豁免按**模块级**判断
（只要该模块任意一行自报是杀号玩法就整模块跳过），因为合并后的行常常只剩「N期 开:xx准」，
标签在没被并进来的兄弟元素里；未开奖行（占位）同样不报 R4；`module == "?"` 的行不报 R4
（拿不到容器就无法可靠归因高亮）。

**模块归属（2026-09-28 二次加固）**：容器 id/class 常常是**多个玩法共用**的——
twssz 的 `.box.pad`、twjsz666 的 `#yxym`、twsyw 的 `#table7` 底下都挂了十几个玩法。
只按容器分组会把不同玩法混成一个模块，让 R4/R5/R8 全部失真。现在模块键 = `容器 + "|" + 行内标签`，
标签取「最后一个期号」之后到第一个 `【『（(《`、`开` 或 `:：;；` 之间的短文本（取不到再退回方括号内容）。
效果：同一批站点 warn 从 217 → 84，且保留下来的都是真信号。

**R5 的展示值（2026-09-28 二次加固）**：先去掉行内标签，再取括号内容作为展示值——
`270期 双波 【蓝波,绿波】 开:…` 比较的是 `蓝波,绿波` 而不是每期都一样的 `双波`；
`270期 文武生肖:文肖 开:…` 比较的是 `文肖`。若某 token 在该模块里出现频率 ≥40%（且模块 ≥6 行），
判定它是模块名/列头并跳过（真正的「相邻 3 期同值」不可能占掉整个模块 40% 的行）。

**标题行不能并入预测行**：twsyw 等站点是「面板标题行 `<tr>` + 预测行 `<tr>`」结构，
标题里的模块名与黄色文字会被当成判定与命中高亮（假阳性）。审计脚本用
`data-prediction-title="true"`（页面显式标注）或行内含 `[data-lottery-title]/[data-site-domain]`
识别标题行并跳过；新站点渲染时应给标题行补上 `data-prediction-title="true"`。


**高亮识别口径（2026-09-27 起加固）**：同时用两种口径判定「这一行有没有黄色高亮」——

1. 元素**计算样式**（`getComputedStyle`）：能抓到用 `class='stylesb'`、`bgcolor` 属性或内联
   `style` 造成的黄底，也能抓到 `color:#FFFF00` 的黄色文字；
2. 行 HTML 里的 `#FFFF00` **字面量**（兼容边角情况）。

两条取较大值。计算样式口径只统计「相对父节点**新增**」的黄色，所以整个容器/整块面板的黄底
不会被算成行内高亮；反之，供应商静态模板里预埋的黄标一定会被算进去（这正是 R3 要抓的）。

**R5 的降噪口径**：只统计含「开/開」的真实预测行（文章列表、导航里的「N期 已更新」不算）；
展示值若被 `【…】`/`《…》`/`（…）` 整个包住（例如 `270期 【逢买必中】 开:…`），说明这一行
只有模块名、没有可比较的展示值，直接跳过。降噪前后的同一批站点：twcf888 47→0、twcaibawang 8→2、
shengshi8800 9→5、twjinniu 10→1 条 warn，而 `#dxzt` 这类真正的「3 期同一个值」仍然保留。

**验收门槛：`error=0` 且 `js_errors=0`。** warn 需要人工判断，但数量不得比上一轮增加。

---

## 三、固定 workflow（每次改动后 / 每次上线前，照抄执行）

### 0. 一次性准备

```powershell
# 后端（开发环境，避免污染生产语义）
$env:LIUHECAI_RUNTIME_ENV='development'
python backend\src\app.py --host 127.0.0.1 --port 8000 --db-path "postgresql://postgres:***@127.0.0.1:5432/liuhecai"
# 前端
cd frontend; node node_modules\next\dist\bin\next dev --webpack --hostname 127.0.0.1 --port 3000
```

### 1. 源码级 lint（改完渲染脚本先跑，秒级反馈）

```powershell
python scripts\lint-prediction-renderers.py <site>          # 单站点
python scripts\lint-prediction-renderers.py                 # 全部站点
```

抓到 `hardcoded_verdict`（写死准/错）、`unsafe_json_parse`、`raw_content_split`、
`static_sample_result`（写死 `开:猫00` 这类样例）时**先修源码再进第 2 步**。

### 2. 本地预检（结构规则 R1–R7）

```powershell
python scripts\audit-prediction-display.py <site> --base-url http://127.0.0.1:3000 --json .codex-temp\audit-local.json
```

要求 `error=0`、`js_errors=0`，且 warn 不高于上一轮。bundle 站点改了源 JS 必须重建：

```powershell
python scripts\bundle-twsaimahui-modules.py --rebuild --apply   # 其他 bundle 站点用各自的脚本
```

### 3. 判定真值校验（数据/契约层，不依赖页面）

```powershell
python scripts\audit-verdict-truth.py --site <site> --json .codex-temp\verdict-truth.json
```

对每一行重新计算「候选项是否命中真实开奖」，与行内 `is_correct` 比对。出现
`is_correct=1` 但实际没命中（虚报）或反之，**必须修判定逻辑，不能靠前端补丁掩盖**。

同一条命令还能报「已开奖但 `res_code` 为空」的缺口（页面会显示 `??` 占位，那是数据缺口不是渲染 bug）：

```powershell
python scripts\audit-verdict-truth.py --check-missing-res-code
# 补齐（默认 dry-run，加 --apply 才写库；逐列只填空值，绝不触碰预测正文）
cd backend/src; python ..\scripts\backfill_created_result_catchup.py --db-path $env:DATABASE_URL
cd backend/src; python ..\scripts\backfill_created_result_catchup.py --db-path $env:DATABASE_URL --apply
```


### 4. 判定语义抽查（页面显示 vs 真实开奖）

结构审计抓不到「整列全对 / 整列全错 / 判定口径与玩法不符」。每个改动的模块至少抽查 3 期：

- 用 Playwright 覆盖该站接口的 `is_correct`，把某期强改为命中/未命中，重新渲染；
- 断言：命中那期**只有命中项**有黄色高亮且显示「准/对」；未命中那期**零黄色高亮**且显示「错」；
- 未开奖期不显示判定、不高亮。

仓库里可复用的样板：`.codex-temp/crosscheck_verdicts_live.py`（tw8800 逐期复算）、
`.codex-temp/twbst528_probe_r3.py`（覆盖接口做命中/未命中对照）。

### 5. 提交

```powershell
git add -A; git commit -m "fix(<site>): <一句话说明>"; git push origin main
```

（需要用户当次授权；授权不跨轮次继承。）

### 6. 发布（见 `DEPLOY.md`「部署工作流（含跳板机）」）

先中心节点、后前端节点；两个节点都用 `git merge --ff-only`，失败即停。

### 7. 线上验收（十站点全量）

```powershell
python scripts\audit-prediction-display.py --json .codex-temp\audit-live.json
python scripts\audit-verdict-truth.py --json .codex-temp\verdict-truth-live.json
```

`== total error=0` 且 `js_errors=0` 才算通过；把两份报告归档到
`docs/vendor-sites/<site>-*.md`，并在 `DEPLOY.md` 追加发布记录（提交号、备份目录、
逐站 error/warn/js_errors 数字、遗留项）。

### 8. 回归

```powershell
cd backend/src; python -m pytest -q
node frontend/test\<站点契约>.mjs
```


---

## 四、新站点接入 checklist

1. **站点注册**：`frontend/sites/<siteKey>/site.manifest.ts` 填 `domains` / `routePath` / `webId` / `siteId`；
   `backend/src/domains/prediction/site_page_dependencies.py` 登记页面依赖（脚本 → endpoint → mode_id）。
2. **模块授权**：`public.site_prediction_modules` 只授权页面**实际启用**的模块；
   用 `python backend/scripts/reconcile_site_prediction_modules.py` 审计后再 `--apply`。
3. **渲染方式判定**（决定改哪里）：
   | 形态 | 判断方法 | 改动位置 |
   | --- | --- | --- |
   | legacy 单页 + 独立 JS | `frontend/public/vendor/<site>/static/js/*.js` 调 `/api/kaijiang/*` | 直接改该 JS |
   | legacy + bundle | 目录里有 `bundles.json` / `bundle-<hash>.js` | **改源 JS 后必须重建 bundle**（见下） |
   | legacy + iframe | 首页只有 `<iframe src="/vendor/<site>/index.html">` | 审计/预检要打开 iframe 地址 |
   | React 组件 | `frontend/components/<site>/*.tsx` | 改 TSX，跑 `npx tsc --noEmit` |
4. **bundle 站点重建**（文件名是内容哈希 + 长缓存，**必须改名**才能击穿缓存）：
   ```powershell
   python scripts\bundle-twsaimahui-modules.py --rebuild --apply
   ```
   其他 bundle 站点同理，用各自的 bundle 脚本。
5. **首轮审计**：`python scripts\audit-prediction-display.py <site>` → 把 error 清零。
6. **判定口径**：在 `backend/docs/prediction-module-rules.md` 对应 mode 行确认
   `rule` 与 `outcome semantics`，前端判定必须与之一致（平特看 7 个开奖号码、绝杀看「不在候选内」等）。
7. **分组说明**：凡是「二选一 / 多选一」的生肖或号码分组，两组都必须渲染；
   固定分组值以 `public.fixed_data` 为准，且 `status` 必须为 1。

---

## 五、十个站点的渲染形态（维护参考）

| site | web_id | 前台地址 | 渲染方式 | 备注 |
| --- | ---: | --- | --- | --- |
| shengshi8800 | 4 | `/vendor/shengshi8800/embed.html?type=3&web=4…` | legacy 单页 + 独立 JS | 统一判定模块 `legacy-prediction-verdict.js` |
| twcaibawang | 5 | `/twcaibawang` | React 组件 | `TwcaibawangHomeClient.tsx`；另有 vendor 聚合接口 |
| twsaimahui | 6 | `/vendor/twsaimahui/index.html`（首页用 iframe 包） | legacy + **bundle** | 改源 JS 后必须 `--rebuild --apply` |
| twjinniu | 7 | `/twjinniu` | React 组件 + 文章页 | |
| twcf888 | 8 | `/twcf888` | React 组件 + 文章页 | |
| twssz | 9 | `/twssz` | legacy + `site-data-adapter.js` | DOM 适配层，高亮要在适配层判定 |
| twbst528 | 10 | `/twbst528` | legacy + `site-data-adapter.js` + 文章页 | 常见「一行多期」结构，必须逐期判定 |
| twjsz666 | 11 | `/twjsz666` | legacy + `site-data-adapter.js` + 文章页 | |
| twwanli | 12 | `/twwanli` | React 组件 | |
| twsyw | 13 | `/twsyw` | 页面自渲染 | 首轮审计 0 违规，可作参考实现 |

## 五之二、基线数字（2026-09-28 二轮收敛后，用于「warn 不得增加」的对比）

线上 `audit-prediction-display.py`（口径：计算样式+字面量双判高亮、模块=容器+行内标签、
行切分并入纯候选格与后续兄弟行、判定字取「最后一个开/開」之后 16 字窗口、R5 取括号内容并跳过 ≥40% 的标签、
R4/R8 对杀号类/聚合卡片/无归属行豁免）：

| site | rows | error | warn | 备注 |
| --- | ---: | ---: | ---: | --- |
| shengshi8800 | 447 | 0 | 1 | R8×1（`#yxym` 是共用内层 div，归属近似） |
| twcaibawang | 292 | 0 | 3 | R5×1（mode 52 四字玄机，已修代码，下期生效）+ R8×2 |
| twsaimahui | 652 | 0 | 5 | R8×5（全部经复算属概率内 / 历史期号码集合顺序下游） |
| twjinniu | 469 | 0 | 0 | — |
| twcf888 | 451 | 0 | 5 | R8×5（平特/杀号类连对，概率内） |
| twssz | 282 | 0 | 3 | R8×3（逐期复算命中，正常） |
| twbst528 | 468 | 0 | 2 | R5×1（生成侧相邻期）+ R8×1 |
| twjsz666 | 276 | 0 | 0 | — |
| twwanli | 202 | 0 | 1 | R8×1 |
| twsyw | 545 | 0 | 6 | R5×1（生成侧）+ R8×5（`#table7` 是十几张表共用的同一个 id，统计假象） |

> 上表是 **2026-09-28 `d58865f` 发布后**的线上实测：**10/10 站点 `error=0`、`js_errors=0`**，
> 共 4084 行、**27 条 warn**。同批生产判定真值校验 `rows=22024 error=0`。
> 两轮对比：第一轮(`641dfe9`) 217 条 → 第二轮(`d58865f`) 27 条。数字变化里有一部分是**口径加固**带来的
> （`.box.pad`/`#yxym`/`#table7` 这类多玩法共用容器被正确拆开、判定字窗口收窄），
> 所以「warn 不得增加」必须**用同一版口径**比较，不要跨口径对数字。


补充（2026-09-28，标题行不再并入预测行之后重测）：最新期**未开奖**时本地预检 `rows=545 error=0 warn=15`、
线上 `rows=545 error=0 warn=7`；两者 `js_errors=0`。表内 twsyw 的 `warn=0` 是更早一轮的记录，
当前 R4（`#top_xiao_code` 命中行无高亮）与 R5（`#daxiao`/`#table7` 连续期同值）属基线，详见下方「五之四」。

源码 lint 基线（`lint-prediction-renderers.py`，160 文件）：error 45 / warn 34。其中需要注意的真阳性：
`shengshi8800/handleSelect.js:729/731` 的 `getResult()` 写死「准」（**当前无调用方，属死代码**，但
不要复活它）、`shengshi8800` 25 处裸 `JSON.parse(d.content)`（content 为中文串时会抛错导致整块模块空白）、
`twsaimahui/001sb.js:16` 直接上屏 `d.content.split(',')`。

## 五之二·补、#hao012（twsaimahui 六肖三码）修复记录（2026-09-28）

现象：`012liuxiao.js` 渲染的 `#hao012` 最近 6 期全部显示「错」，用户投诉「为什么全部都是错的」。

根因（与首轮推测不同，已实测确认）：

1. **候选并没有缺失**。该模块的候选来自 `getXiaoma2?num=6` → mode 27（`mode_payload_tables` 标题「6肖12码」，
   正文形如 `["狗|09,21,33,45", …]` 六肖 × 每肖候选码），本地页面在修复前就能渲染出
   `必中六肖：…`、`精选12码：…`。
2. **判定取错了字段**。commit `7f98c78` 给该模块加判定时，把候选塞进了一个「肖名 + 码串交替」的数组，
   却用 `xiao[k + 1]`（也就是**码串**）去 `indexOf(特肖)` 判命中——生肖不可能出现在号码串里，
   于是 `zjXiao` 恒为 `false`；再加上码组全部拼成一个数组后用 `m < 3` 当「前三码」，
   两个分支恒不成立，判定恒为「错」。`#hao012` 因此永远是「错」。

修复：

- `frontend/public/vendor/twsaimahui/static/js/012liuxiao.js`：分别保存「肖名」与「该肖码组」
  （`xiao` / `codesByXiao`），特肖用肖名匹配、特码用严格相等匹配；三码 = 首个候选肖码组的前三码。
  **判定口径未改**（特肖 ∈ 六肖 或 特码 ∈ 前三码 → 准）。
- `backend/src/legacy/frontend_compat.py::_ENDPOINT_MODE_IDS`：登记
  `("getxiaoma2","6")→27`、`("getxiaoma2","4")→51`、`("getxiaoma2","7")→22`。
  属于**映射加固**：`num` 的 6/4/7 恰好也是 `mode_payload_6/4/7` 的表号，
  兼容层的「直表名优先」解析会把 `num=6` 解析成 `mode_payload_6`（三国中特）而不是 mode 27；
  新前台 Next 路由当前硬编码 27 所以不受影响，但这是随时会复发的隐患。
- 重建 vendor bundle（`scripts/bundle-twsaimahui-modules.py --rebuild --apply`），bundle 文件名变化必须同步 `index.html`。

验证：`#hao012` 6 期页面文本 vs 本地 DB 独立复算 **0 不一致**（190 准 / 189 错 / 188 准 / 187 错 / 186 错 / 191 未开奖无判定）；
`audit-prediction-display.py twsaimahui --base-url http://127.0.0.1:3000` → `rows=655, error=0, js_errors=0, warn=24`；
`#hao012` 的 R8 告警（6 期全同）已消失，残留的 R5 是该模块正文以标签「六肖三码」开头的抽取噪声，非真实缺陷。

契约测试：`frontend/test/twsaimahui-012-liuxiao-display-contract.mjs`（路由映射 + 映射函数 + 渲染器真跑）、
`backend/src/tests/unit/test_legacy_frontend_compat_xiaoma2.py`（endpoint→mode 解析 + 响应字段合同）。

## 五之四、twsyw 未开奖期「仍显示判定 + 仍有黄底」的复核结论（2026-09-28）

现象：本地 dev 最新期 2026191 未开奖时，`audit-prediction-display.py twsyw --base-url http://127.0.0.1:3000`
报 `error=11`（R2×10 + R3×1），样例形如 `2026191期 开:待开奖 台湾彩 (双波中特)` 判定「中」、
`2026191期 开:待开奖 台湾彩 (平特5不中)` 判定「不中」且「未开奖行仍有黄色高亮」。

复核结论：**页面本身没有缺陷，是审计工具的行合并把「面板标题行」当成了预测行的一部分。**

- 页面上 31 条待开奖行的自身文本里**没有任何**判定字（`verdict_of` 全为空）、
  `data-prediction-hit` 属性全为 `null`、行内黄色高亮计数全为 `0`；
- 后端接口对 `draw_is_opened=false` 的行一律返回 `is_correct: null`（本地实测 41 条待开奖行全部为 null），
  供应商静态 HTML 里的 `#FFFF00` 只存在于标题行；
- twsyw 的表结构是「标题行 `<tr>` + 预测行 `<tr>` 交替」，标题行恰好是每个模块**首行预测行的前一个兄弟行**；
  `ROW_SCRIPT` 的兄弟行合并（为兼容 `<td>270期…错</td><td>鸡,马</td>` 这类拆单元格写法）于是把标题并了进来：
  标题里的模块名（大小中特 / 九肖中特 / 赢家12码 / 平特5不中）被 `verdict_of` 当成判定字，
  标题的黄字（`color:#FFFF00`）被 `countYellow` 当成行内高亮。已开奖的「错」行会同样误报 R3
  （线上 2026270 期 `#fslx/#m24/#table7` 共 6 条 R3 就是这么来的）。

修复：`ROW_SCRIPT` 新增 `isTitleRow()`，遇到标题行不并入预测行也不计其高亮；识别口径为
`data-prediction-title="true"`（页面可显式标记，twsyw 已给 24 个面板标题行 + 8 个顶部表头行打上）
或行内含供应商标题占位 `[data-lottery-title]` / `[data-site-domain]`。9 个抽检站点
（twcaibawang/twjinniu/twcf888/twssz/twbst528 等）实测**没有**被合并的标题行节点，规则不影响它们。

验收数字（2026-09-28）：

| 口径 | 修复前 | 修复后 |
| --- | --- | --- |
| 本地预检（最新期**未开奖**） | `rows=545 error=11 warn=16 js_errors=0` | `rows=545 error=0 warn=15 js_errors=0` |
| 线上（最新期**已开奖**） | `rows=545 error=6 warn=7 js_errors=0`（6 条全是 R3 假阳性） | `rows=545 error=0 warn=7 js_errors=0` |

未开奖时的本地 11 条 = R2×10 + R3×1；线上已开奖时的 6 条全是 R3。
两个口径的根因相同，都来自「标题行被并进预测行」：前者标题里的「中/赢/不中」被当成判定字（R2），
后者标题的黄字被当成命中高亮（R3）。

逐行对照确认**只有 24 行**发生变化（每个模块首行少掉了并进来的标题文本与 2 处标题黄色），
其余 521 行的文本/高亮/判定完全一致：32 条待开奖行的自身文本判定字个数 `11→0`、
带黄底的行数 `24→0`。

## 五之三、R8 告警的正确用法


R8（某模块 ≥5 期已开奖行判定全同）**只是提示**，必须人工判定属于哪一类：

1. **正常**：候选集本来就大（八肖中特 8/12、稳杀10码、绝杀七码等），连对/连错在概率内；
   用独立重算验证每期确实算对即可（例：twsaimahui `.box.l45` 绝杀七码 9 期「准」，特码均不在杀号集合内）。
2. **缺陷**：候选集退化成固定前缀/空集、判定口径写死、`is_correct` 恒真或恒假。
   典型证据是「每期展示值前面挂着同一个固定段」或「连错期数远超概率」。

---

## 五之六、三个「判定恒真/恒假」的模块（2026-09-28 第三轮）

本轮固定了三个「整列判定全同」的真实缺陷，全部根因都在**判定口径/取值空间**，不在渲染：

### 1) twjsz666 `#yxym`「三头四尾」(mode 492) 8 期全「错」

- **根因**：`public/api.py::_check_correct_by_mechanism` 对自定义 `hit_checker` 传的是
  `_compute_outcome_from_row` 的**通用复合串**（`双数|大数|…|2头|6尾|蓝波|…`），而
  `three_head_four_tail_hit` 的契约是**机制专属 outcome** `头:2头|尾:6尾`。通用串里的
  `双数`/`蓝波` 等永远不在候选集合里 → 判定恒为 `False`。
- **口径**：该玩法标签带 `头:` / `尾:` 两个维度前缀，`category_service.classify_prediction_config`
  归类为 `PredictionCategory.MIXED`，按 `backend/CLAUDE.md`「MIXED 的业务命中语义为
  任一维度命中即算命中」→ **特码头或特码尾任一落入对应候选即命中**。
  供应商静态样本同口径（053期 `三头【4.1.3】四尾【1.4.9.2】开09鸡对`：只有尾命中仍标「对」；
  052期只有尾 `3尾` 命中同样标「对」）。修正前 `three_head_four_tail_hit` 是「头与尾同时命中」，
  与上述约束冲突，`rule_revision` 由 1 升到 2 以区分控制表里的旧验证结果。
- **修法**：`backend/src/public/api.py`（自定义 checker 改用 `config.outcome_loader` 的真实命中目标；
  无连接时 `predict.common.table_exists` 退化为「表不存在」，头/尾标签由 `res_code` 直接推导，
  与 `fixed_data` 的 `头`/`尾` 映射等价）、`backend/src/predict/mechanisms.py`、
  `backend/src/domains/prediction/generation_rules.py`、`frontend/lib/prediction-contract.ts`
  （`verifyVerdictAgainstCandidates` 增加头尾维度分支，避免 `reconcileVerdict` 把「对」改写成「错」）、
  `frontend/public/vendor/twjsz666/site-data-adapter.js`（高亮范围限定到候选单元格，只点亮命中的
  头/尾，不再去点亮 `开:37马对` 里的开奖号码）。
- **验证**：本地 dev 8 期已开奖行「页面判定 vs 独立复算」**0 不一致**（6 对 / 2 错），
  黄底只出现在命中的那一维度上（1 或 2 处）。

### 2) twbst528 `#banbodanshuang_shu`（杀两半波，mode 490）与 twjsz666「绝杀①半波」(mode 58) 5/8 期全「对」

- **根因**：半波玩法的候选标签是 `蓝双` / `绿单` 这类**半波标签**，而
  `_compute_outcome_from_row` 只输出 `蓝波` 与 `双` 两个原子，`蓝双` 不是任何原子的子串 →
  `excludes_hit` 恒等于 `True`，判定写死为「对」。
- **修法**：`_compute_outcome_from_row` 补半波原子 `{波色}{单双}`（与 `public.fixed_data`
  的 `波色单双` 映射一致，01–49 全量校验）。
- **验证**：线上 5 期里 3 期实际应为「错」（270 `蓝双+蓝单` 开 37=蓝单、268 `蓝双+绿单` 开 11=绿单、
  267 `蓝双+红双` 开 24=红双）；本地 dev 修复后 5 期 0 不一致（190/188/187/186 错、189 对）。

### 3) twbst528「三期计划」同一期号出现三条重复行

- **根因**：`site-data-adapter.js::renderCompositeLines` 在模块比小节少时用
  `Math.min(Math.max(moduleIndex,0), moduleList.length-1)` **回退到最后一个模块**。面板有 6 个小节
  （一波中特/单双计划/平特计划/3.肖中特/必出3码/平尾计划），只传了 4 个模块 → 后两个小节
  （必出3码、平尾计划）重复渲染「3.肖中特」的数据，同一期号在同一容器里出现三条相同行
  （线上 `271期【虎鸡蛇】开:待开奖` × 3）。
- **修法**：越界小节一律渲染「暂无后端资料」，不再回退；同时把 `平尾计划` 显式接到已授权的
  `pt1wei`，「必出3码」站点没有授权 3 码玩法 → 用 `null` 占位（不再套用别的玩法数据）。
- **验证**：同一份本地数据/后端下，预检 warn 由 3 降到 2，`?|兔牛猴 连续 3 期展示值相同
  sample=191,191,191` 消失；`--dump-rows` 里不再有同期号重复行。

### 口径核对工具同步

`scripts/audit-verdict-truth.py` 的真值模型对「多段复合 outcome」机制（`头:X|尾:Y`）过去拿整串去和
候选标签取交集，恒为「未命中」，会把修好后的「对」误报成 `false_hit`。现在这类机制按
**分段集合 + 任一维度命中**判定，并用机制自己的 `content_parser` 解析候选。
两个站点复算 `rows=2498 error=0`。

---

## 五之五、号码集合类玩法「每期前几位固定」（2026-09-28）

现象：twsaimahui「10码中特」（mode 116）每期开头都是 `01.17.…`；`#hao012` 一类模块看起来「每期一样」。

**根因（复核后推翻了「位置轮转」的初判）**：号码类 content 是普通逗号串（不是 JSON 数组），
`prediction_generation/diversity.py::parse_array_content()` 解析失败直接原样返回，所以
`unique_first_two` 的交换/左移**从未在这些 mode 上执行**。真正的原因是生成侧
`predict.common.score_labels(strategy="hot")` 的 `history` 取自
`predict_repository.load_recent_result_rows(limit=10)`——**不按 web、也不按期号去重**，
`history[-5:]` 常常只覆盖 1~2 个真实期号，同一号码的 counts 被多站行重复累加；
号码类 content 就是「按热度排名拼串」，于是同一批号码被钉死在最前面（实测 web6 最近 40 期
mode 116 的位置 1 = `01` 占 38/40，mode 88 的位置 1/2 只在 `{01,17}` 之间互换）。

**处理**：`diversity.py` 新增 `UNORDERED_NUMBER_SET_MODE_IDS = {9, 65, 88, 116}`
与 `unordered_set_display_order()`——对这些 mode **停用位置轮转**，改为按
`sha256(mode:年:期:站:成员)` 做一次性展示置换（局部 `random.Random`，不污染全局随机态；
与上一期顺序撞车时错开一位）。判定语义逐值验证不变（`contains_hit`/`excludes_hit` 对 01–49
全部取值双向比对一致）。mode 34 故意不含（登记了跨站前缀宽度契约，改顺序会让已预约签名脱钩）。

细节与实测见 `backend/docs/number-set-display-order-fix-report.md`。

---

## 五之七、tw8800 杀类模块判定取反值（2026-09-28）

需求：tw8800（shengshi8800）首页四个排除玩法——欲输尽光三肖 / 绝杀三肖（均 mode 42）、
绝杀一尾（mode 20）、绝杀半波（mode 58）——判定必须取反值：**特码落入候选（杀失败）显示「错」，
未落入（杀中）才显示「准」**。

复核结论：mode 42 / 20 在 `legacy-prediction-verdict.js` 里已是排除口径（落入候选 -> `miss`），
无需改动；**mode 58 方向全反**——共享号码池分支按「特码是否在候选内」给 `ok`，半波标签回退
`halfWaveByLabel` 也是普通命中口径，与后端 `jueshabanbo`（`excludes_hit`，见
`backend/docs/prediction-module-rules.md` mode 58 `half_wave_exclusion`）相反。实测（真实 content
`["红单|01,07,…"]`，开 13 在红单池）显示「准」、开 12（红双，不在池）显示「错」，两个方向都颠倒。

**处理**（仅前端 legacy 判定，单一入口）：

- `shengshi8800/static/js/legacy-prediction-verdict.js`：mode 58 从共享命中分支拆出，
  新增 `halfWaveExclusionVerdict()`——候选含号码池按 `numberInGroups` 判落入，
  纯半波标签（厂商旧样本 `["红双"]` 形态）按 `halfWaveByLabel` 判落入，再统一取反
  （落入 -> `miss`「错」，未落入 -> `ok`「准」）；`pending`（未开奖不显示）与 `unknown` 语义不变。
- `shengshi8800/static/js/022jsbb.js`：高亮改为与本期判定绑定（`__verdict === 'ok'` 才黄底，
  「错」时整行零黄底），与 020ssx / 024jsyw 同口径；原先按「开码不在杀号池」逐项独立高亮，
  多候选时会出现「错」仍带黄底。

**验证**：Node 直载脚本复算 14 例全过——mode 58 两种 content 形态 × 杀中/杀未中/未开奖，
mode 42 / 20 反值回归，mode 5 / 34 / 38 / 57 命中类回归；渲染模拟确认「错」零黄底、「准」黄底。
后端 mode 58 判定已在「五之六 2)」修复（半波原子），前后端口径现已一致。

---

## 五之八、tw8800 三期中特恢复固定「中1期」（2026-09-28）

需求：三期中特（mode 197，`023sqzt.js`）此前被改成真实统计「中N期」（窗口内已开奖各期
特肖落在候选 4 肖的期数），一个都未命中会显示「中0期」、中两期显示「中2期」。
确认**厂商原文就是固定文案**（`let term = '中1期'; if (!sx) term = '中几期'`）——
已开奖窗口一律显示「中1期」，从不显示中0期/中2期/中3期；真实统计不符合厂商营销展示。

**处理**：`023sqzt.js` 恢复固定口径——窗口内已有开奖（`period_zodiacs` 非空）显示 `中1期`，
一期都没开奖保持 `中几期`；命中生肖标黄的逻辑保留（`period_zodiacs` 仍由 compat 路由
`sanqiWindowZodiacs()` 提供，用于高亮与是否已开奖判断）。契约测试
`frontend/test/shengshi8800-display-verdict-contract.mjs` 的「中N期」用例同步改为固定口径
（断言已开奖窗口必须显示「中1期」，且不得再统计真实期数）。
`docs/vendor-sites/shengshi8800-pool-label-remediation.md` 第 3 节已记录反转。

**验证**：`node frontend/test/shengshi8800-display-verdict-contract.mjs` 通过
（15 个展示脚本覆盖）；`023sqzt.js` 语法检查通过。

---

## 五之九、twsaimahui 家野两肖（`.l1`）/ 四肖三期内必出（`.l21`）修复记录（2026-09-28）

### 1) `061jy2x.js`（mode 251 家野两肖）：格式与高亮

**现象**：`270期家畜野兽:【虎马兔牛猴鸡+虎马兔牛猴鸡】 开:马37准` —— 两段完全相同（同一批 6 肖），
组名丢失。

**数据来源核查**：`getJyxiao2` → **mode 251「家野两肖」**。该表**没有 `content` 列**，
后端列是 `title`（= `家禽|牛,马,羊,鸡,狗,猪`，即「组名|组成员」，`predict/mechanisms.py`
已显式支持 `title` 作为 content 列的替代表）与 `xiao`（= **两肖**；供应商原始
`public.mode_payload_251`（web 1/5）的 `xiao` 宽度**恒为 2**，如 `蛇,龙`）。
历史 `mapJyxiao2()` **丢掉了 `title`**，并用 `xiao` 合成 `["马|","虎|",…]`（竖线后为空码，因为该表
没有 `code` 列），于是组名消失、同一批 6 肖被渲染两遍 —— 这是展示缺陷的直接根因。

**数据侧根因（已修）**：生成侧宽度推断用 `parse_pipe_label_content(title)`，把 `家禽|牛,马,羊,鸡,狗,猪`
的**分类成员**按逗号拆成 6 个候选标签，于是 `created.mode_payload_251` 每期写进 `xiao` 的是 6 肖
（所有 web / 所有 type 共 200+ 行全部如此）。修法：宽度改取 `xiao` 列（该玩法的候选列）的样本众数，
与 mode 142（表内标题「家野2肖（家野选1，生肖选2）」）完全一致 → `label_count=2`。
**已落库的预测正文不改**（`xiao` 列仍是 6 肖），由兼容层按字段语义取前 2 项。

**修法**：
- `frontend/app/api/kaijiang/[[...path]]/route.ts`（**共用文件**）：`mapJyxiao2()` 改为
  `content ← ["组名|组成员"]`（来自 `row.title`）、`xiao ← 两肖`（按字段语义宽度 2 截取）；
  既有字段名与顺序不变。
- `frontend/public/vendor/twsaimahui/static/js/061jy2x.js`：渲染 `【组名+两肖】`，
  判定 = 特肖 ∈ 组成员 ∪ 两肖（命中的是两肖里的某一个 → 高亮该生肖；命中的是组内成员 →
  高亮组名，与 `040jiaye.js` 的高亮口径一致）；未命中零黄底；未开奖显示 `开:待开奖`，
  不显示判定也不高亮。家禽/野兽固定分组以 `public.fixed_data`（sign=`家禽|野兽`，
  id 16/17，status=1）为准。

### 2) `023sanqibizhong.js`（mode 197 四肖三期内必出）：每期各自显示判定

**现象**：一个三期窗口只有一个 3 行表，只有窗口内**最新已开奖那一期**有开奖段，另外两期空白；
且开奖串取的是**第一项**（`res_code[0]`/`res_sx[0]`），于是把平码当成特码（线上 269-271
窗口显示 `开:兔28错`，真实是 `270 开:马37`）。

**数据来源核查**：`mode_payload_197` 是**每期一行**存储（列 `start`/`end` 标识所属窗口），
每行自带该期真实开奖；最新窗口只有 1 行（其余期尚未生成），历史窗口 3 行。
`filterSanqiDisplayRows()` 过去按 `start-end` 分组后**只保留一行**（窗口内最新已开奖期），
其余两行被丢弃。

**修法**：
- `route.ts`（**共用文件**）：`filterSanqiDisplayRows()` 新增把整个窗口的逐期结果带出
  （新函数 `sanqiWindowPeriods()`），`mapSanqiTwsaimahui()` **只新增** `periods`
  字段（按期中升序的 `{term,res_code,res_sx}` 数组）；`getSanqiXiao4new` 对 web=6
  把取数 `limit` 由 8 提到 10（1+3+3+3，覆盖 4 个**完整**窗口；其它站点仍是 8）。
  既有 `content`/`name`/`res_code`/`res_sx` 字段与语义完全保留。
- `frontend/public/vendor/twsaimahui/static/js/023sanqibizhong.js`：按 `periods` 逐期渲染
  （每行 `期号 | 候选4肖 | 开:<特肖><特码>准/错`，候选单元格每期独立高亮，避免整行共用一个
  命中状态）；特码/特肖取开奖串**最后一项**；未开奖期显示 `开:待开奖`、不给判定、不高亮。

**验收（本地 dev）**：

| 口径 | 命令 | rows | error | warn | js_errors |
| --- | --- | ---: | ---: | ---: | ---: |
| 线上（旧代码 = 修复前） | `audit-prediction-display.py twsaimahui --json .codex-temp\audit-tsam-live.json` | 652 | 0 | 5 | 0 |
| 本地修复后 | `audit-prediction-display.py twsaimahui --base-url http://127.0.0.1:3000 --json .codex-temp\audit-tsam-fix.json --dump-rows .codex-temp\rows-tsam-fix.json` | 655 | 0 | 2 | 0 |

逐期独立复算（真值取 `public.lottery_draws.numbers` + `public.fixed_data` sign=`生肖`）：
两个模块各 9 期已开奖行，页面判定与高亮 **0 不一致**（准 → 恰好 1 处黄底；错/未开奖 → 0 处）。

契约测试：`frontend/test/twsaimahui-jy2x-sanqi-display-contract.mjs`（两个渲染器真跑 + 路由字段来源）、
`backend/src/tests/unit/test_jyxiao2_xiao_width.py`（mode 251 候选宽度 = `xiao` 列）；
`frontend/test/twsaimahui-api-audit.mjs` 的 `getSanqiXiao4new` 期望字段已加入 `periods`。

---

## 五之十、tw8800 经典24码三行布局 + 家野中特高亮绑定判定（2026-09-29）

**需求**

1. 经典24码：24 码由两行（12+12）改为**三行（8+8+8）**，每行保留 `{}`。
2. 家野中特：只允许**命中的那一组组名**（`家禽` / `野兽`）黄底，其余文字（`〈〈` `〉〉`、
   期号、判定字、开奖号码）一律不黄；未命中 / 未开奖零黄底。

**改动**

| 文件 | 改动 |
| --- | --- |
| `frontend/public/vendor/shengshi8800/static/js/019ma24.js` | 号码行 `slice(0,12)` + `slice(12)` → `slice(0,8)` / `slice(8,16)` / `slice(16)` |
| `frontend/public/vendor/shengshi8800/static/js/004jyzt.js` | 高亮改由 `window.legacyPredictionVerdict.verdictOf(63, d)` 决定（`__hit`），并按「本组池是否含特肖/特码」选组；黄底 span 只包住组名 |
| `frontend/test/shengshi8800-display-verdict-contract.mjs` | 新增渲染层真跑断言（三行分段、命中 1 处黄底、错/未开奖 0 处黄底） |

**根因（家野中特）**：旧写法 `xiaoV[i].indexOf(code)` 把**特码号码**拿去匹配**生肖池**
（mode 63 的 content 是 `["家禽|牛,马,羊,鸡,狗,猪"]`），条件恒为假 → **「准」期永远没有黄底**；
同时它与判定不是一个数据源，属于「命中却没有黄底」这一类（§六 速查）。

**验收（本地 vm 真跑渲染器，非静态断言）**

| 场景 | 期号数据 | 渲染结果 |
| --- | --- | --- |
| 24码命中 | 开奖 `蛇24`，24 在候选内 | 三行 `{01..08}` / `{09..16}` / `{17..24}`，黄底**恰好 1 处**且只有 `24` |
| 24码未命中 | 开奖 `龙49` | 三行相同，黄底 **0 处**，显示「错」 |
| 家野中特命中 | `["家禽\|牛,马,羊,鸡,狗,猪"]`，开奖 `羊22` | `火爆家野〈〈`**家禽**`〉〉准羊22`，黄底**恰好 1 处**且只有 `家禽` |
| 家野中特未命中 | 同上，开奖 `鼠05` | 黄底 **0 处**，显示「错」 |
| 家野中特未开奖 | `res_sx = ",,,,,,"` | 黄底 **0 处**，不显示判定 |
| 家野中特命中野兽组 | `["野兽\|鼠,虎,兔,龙,蛇,猴"]`，开奖 `蛇12` | 黄底**恰好 1 处**且只有 `野兽` |

**已知未改（本次范围外）**：`004jyzt.js` 的未开奖行仍沿用该站原有占位串 `？00`（与
`019ma24.js` 等同一风格），本次只收敛高亮，不改开奖段文案。

---

## 五之十一、twjsz666 全模块居中 + 命中高亮只落候选（2026-09-29）

**需求**：① 全部模块文字居中；② 只有命中的生肖/数字/波色/大小/头尾文字可以标黄，
其余文字（期号、`开:22羊对` 开奖段、判定字、模块标题）一律不许黄。

**改动**

| 文件 | 改动 |
| --- | --- |
| `frontend/public/vendor/twjsz666/site-data-adapter.js` | `markPredictionRow()` 的高亮范围由「整行」改为**候选节点**（元素或数组，`[]` = 无候选）；`hitTokenGroups()` 补「波色/大小」两个维度；排除玩法 `noHighlight`；`四字解平特肖` 候选补回解肖生肖；`一头一码` 24 码卡补绑定预测行；已存在槽位高亮加 `data-prediction-hit-slot` 并在重置时清除 |
| `frontend/public/vendor/twjsz666/index.html` | 买码之前先上 9 卡 × 2 单元格内联左对齐 → 居中（18 处）；`.bizhong1-tit` 黄字 `#ff0` → `#fff` |
| `frontend/public/vendor/twjsz666/static/css/style.css` | 新增预测模块统一居中块；`.qxtable.left` 左对齐 → 居中 |
| `frontend/public/vendor/twjsz666/15*.html`（14 个子页） | 正文容器内联 `text-align:unset` → `center` |
| `frontend/test/twjsz666-display-contract.py` | 新增：本地静态服务 + 桩数据 + Playwright 真渲染断言（居中 / 黄底落点 / 逐行判定 / 字幕 / 子页） |

**根因**：`highlightToken()` 在行内按**文档顺序取第一个匹配**。预测格里没有该字时
（波色玩法、大小玩法、七尾、四字解、绝杀类、以及 DOM 里开奖段排在候选之前的 ④肖⑧码），
黄底就落到同一行的开奖段上；命中 token 里原本也没有「波色/大小」两类，所以这两类玩法
必然飘到开奖段。旧实现只有「三头四尾」传了候选范围。

**验收（合成数据真渲染，`python frontend/test/twjsz666-display-contract.py`）**

| 项目 | 结果 |
| --- | --- |
| 非居中文字 | 0（含 14 个文章子页） |
| 黄底总数 / 落在期号槽或开奖段的 | 20 / **0** |
| 未命中(+)未开奖行残留黄底 | 0（未命中行 32 行） |
| 命中却零黄底 | 0（命中行 16 行；排除玩法按规范豁免） |
| 杂散黄底/黄字（供应商残留、标题黄字） | 0 |
| 逐模块命中字幕 | 15 条断言（大小中特=`小数`、双波=`绿波`、七尾=`2`、四字解=`羊`、24码卡=`22` …） |

**本轮同站点发现的既有异常（未在本轮改动范围）**

1. `twjsz666-subpage-contract.mjs` 失败：14 个子页共 59 处引用
   `static/picture/c73120ca0585a192625208b7bcdfd1bd.jpg`，仓库里实际文件是
   `…bd2.jpg`（多一个 `2`）→ 图片链接 404。HEAD 版本同样如此，属既有缺陷。
2. `twjsz666-section-inventory-contract.mjs` 失败：契约写死「25 个可见 list-title」，
   HEAD 与当前实测都是 **24**（契约数字过期，非渲染回归）。
3. `twjsz666-adapter-contract.mjs` 失败：契约禁止 `document.createElement` / `appendChild`，
   但 `highlightToken()` 一直用它们包高亮 span（HEAD 同样命中）→ 契约与实现早已冲突。
4. `scripts/lint-prediction-renderers.py twjsz666` 有 3 条 `unsafe_json_parse`（error 级），
   均为既有 `try { JSON.parse } catch` 兜底写法，HEAD 同为 3 条，本轮未新增。

---

## 五之十二、twwanli 全模块居中/放大字号 + 三项判定口径修正（2026-09-29）

**需求**：① 全部模块文字居中；② 只有命中的生肖/数字/波色文字标黄；③ 放大「预测内容」
字号突出显示；④【精准五行】270 期 `金+土+木` 开 37 马应为「对」；⑤【买啥开啥】
〈〈家禽〉〉开 37 马应为「准」；⑥【天地生肖】`【天肖+兔鸡】` 开 37 马应为「对」；
⑦ 检查其他站点同类模块的判定。

### 判定口径修正（根因 + 改动）

| 模块 | 根因 | 改动 |
| --- | --- | --- |
| 精准五行 / 三行中特 / 四行中特（mode 53 等） | `public/api.py` 里维护了一份**过期硬编码五行表**（37 → 火），与 `public.fixed_data` / `mode_payload_53` 的号码分组（**37 → 木**）冲突；且该表只覆盖 48 码（49 缺失）。按生肖看马是火肖，于是「木」不入预测三行 → 应「对」判「错」 | 新增权威常量 `predict.common.ELEMENT_NUMBER_GROUPS`（金10/木10/水8/火12/土9 = 49，与 fixed_data 一致），`build_element_number_map()` 直接返回它，`public/api.py` 改为引用同一来源（删除过期表） |
| 买啥开啥（twwanli `#msks`，source `title_14`） | 旧判定拿**本期 jia/ye 抽出的 4+4 子集**反查「哪一列含特肖」，特肖没被抽中就得到空分类 → 误判「错」。另一个隐患：展示值取的是**按特别生肖推导的开奖分类**，展示值本身就是答案 → 一旦按全组判定就会恒为「准」 | ① `public/api.py` 的注记同时产出 `domestic_wild_prediction_category`（**预测**分类，取自正文 `家禽\|…`）与原有 `domestic_wild_category`（开奖分类），适配器展示与判定一律用**预测**分类；② 判定改用 `fixed_data` 的**家禽/野兽全组**（家禽=牛马羊鸡狗猪 / 野兽=鼠虎兔龙蛇猴）：预测分类 === 特肖所属固定分类 → 准；③ 黄底从「准/错」字移到命中的分类名 |
| 天地生肖（twwanli `#tdsx`，source `title_5`） | vendor/接口的 `is_correct` **只比对 `xiao` 那 2 肖**，天地组（6 肖）永远不参与判定 → 「天肖里含开奖特肖却显示错」 | 适配器本地复算并集：特肖 ∈ 天地组 ∪ 两肖 → 对；只点亮命中的那一项（组名或某个肖）。与 twcaibawang 既有的并集口径一致 |

### 展示项（items 1–3）

- `index.html` 的共享样式块：所有 `[data-prediction-issue/content/content-secondary/result]`
  一律 `text-align:center`（原来只挑 `#tdsx/#pt1xiao/#qqsh/#sdzt` 四个模块）；
  `[data-prediction-content]` 字号 `26px` 加粗、`-secondary` `22px` 加粗。
- 6 个文章子页（`21/22/25-28.html`）的内联样式块同步居中 + 放大。
- 高亮本来就是**标记制**（`[data-prediction-hit="true"]{background:#FFFF00}`，模板里没有预埋
  黄底），所以「其余文字不黄」只需保证标记只打给命中项；本轮把「买啥开啥」的黄底从判定字
  移到分类名，并让「天地生肖」用 `highlightOnly` 只标命中项。

### 验收

- 新增 `frontend/test/twwanli-display-contract.py`（本地静态服务 + 桩数据 + Playwright 真渲染）：
  0 处槽位非居中、预测内容字号恒为 26px、0 处杂散黄底；买啥开啥 270 期「预测〈〈家禽〉〉+37马」
  → 准且只黄「家禽」、**269 期「预测〈〈野兽〉〉+37马」（该行开奖分类是家禽）→ 错零黄底**
  ——这条专门锁定「展示/判定都用预测分类，不会偏向恒准」；天地生肖 270 期「天肖+兔鸡」+37马
  → 对且只黄「天肖」、269 期「地肖+兔鸡」+37马 → 错零黄底、267 期「天肖+兔鸡」+22鸡
  → 对且只黄「鸡」；精准五行 270 期显示「金+土+木 / 开:37马对」。
- 新增 `backend/src/tests/unit/test_element_number_groups.py`（7 条）：49 码无重叠、
  37→木 / 49→土 / 04→金、`api._ELEMENT_MAP` 与权威来源一致、复合 outcome 含「木」且不含「火」、
  天地分组与各站 sx.html 一致。
- 后端 `python -m pytest tests/unit -q`：**1 failed, 1086 passed**；唯一失败是既有的
  `test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`
  （与本轮无关，改动前同样失败）。

### item 7：使用同类模块的其他站点核查结论

| 模块 | 站点 | 现状 |
| --- | --- | --- |
| 五行（mode 53 / `3hang`） | 所有走接口 `is_correct` 的站点（twbst528 150.html、twwanli、twjinniu 蓝图、tw8800 `013shzt.js`、twsaimahui `025sanhang.js` …） | **本轮后端修正一次性覆盖**（判定读时复算）。旧站 legacy 脚本（tw8800/twsaimahui）对 mode 53 不输出判定字，无需另改 |
| 天地生肖（mode 5 / `title_5`） | twcaibawang（已本地并集判定）、**twwanli（本轮已修）**、**twsyw `#nannv`（本轮已修 + 新增契约）**、twssz / twbst528 的天地资料卡 | twsyw 原先 `isHit = source.result.isCorrect` → 天地组命中显示「错」；已改为「天地组(6肖) ∪ 两肖」并集判定，只标命中项，契约 `frontend/test/twsyw-display-contract.py`（含反向验证：改回旧口径会 4 项 FAIL）。twssz / twbst528 的天地卡仍依赖接口判定，**待修** |

### 新发现的一类缺陷：展示候选 ⊂ 判定候选（twsyw 全站扫描，2026-09-29）

「展示的候选是某份资料的**子集**，判定却用**整份**资料」——命中落在被裁掉的那部分时，会出现
「显示对却没有黄底」或「另一个维度命中却显示错」。twsyw 适配器扫出以下位置（**尚未修**）：

| 位置 | 展示的候选 | 判定所用候选 |
| --- | --- | --- |
| `renderTopXiaoCode`（`#top_xiao_code`） | 9xzt 取前 8/5/3/1 肖、ma24 取前 10/6/1 码 | 9xzt=9 肖 / ma24=24 码（56 行共用整份） |
| `renderQixiao`（`#qixiao`） | 9xzt 前 7 肖 | 9xzt=9 肖 |
| `renderGold6xiao` | 9xzt 前 6 肖 + pt1xiao 前 1 肖 | 只取 9 肖 |
| `renderWinner12` / `renderFiveNoHit` | selected_22_codes 前 12 / 前 5 码 | 22 码 |
| `renderLianma` | ma24 前 12 码 + 四段 | 只取 24 码 |
| `renderKill3wei` | title_66 前 3 尾 | 5 尾 |
| `renderDanshuang` | 合数单双 + 合数大小（双维度展示） | 只取 title_132 |
| `renderHblvxiao` | 双波 + 一波（双维度展示） | 只取双波 |
| `renderCompositeKill` | 绝杀三肖+五尾+三头+合数单双（四路） | 只取第一个可用 source |

已核对**一致、无问题**：`#fslx`/`#jiaye`（title_14 展示的 jia∪ye 两列即判定候选集，与 twwanli
`#msks` 的「分类二选一」语义不同，**不应**照搬家禽/野兽全组口径）、`#m24`、`#jiuxiao`、`#dssx`、
`#santou`、`#kill1tou`、`#pt1wei`、`#qiw`、`#shuangbo`、`#daxiao`、`#chengyu`、`#jiaye4xiao`、`#kill4xiao`。
| 家禽/野兽（mode 14 / `title_14`） | twwanli `#msks`（本轮已修）、twjsz666 `156.html`、twbst528 `144.html`、twjinniu | 其它站点的卡片语义若是「8 肖候选」而非「分类二选一」，则应按机制自身口径（特肖 ∈ 8 肖）判定，**不能**照搬家禽/野兽全组口径 —— 需按站点卡片语义逐个确认 |

### 五行口径彻底统一：mode 53 / 482 正文号码清单改写（2026-09-29）

**问题**：后端判定一直用 **号码五行**（`public.fixed_data` `sign='五行'`，37 → 木），而
`created.mode_payload_53`（三行中特）/ `created.mode_payload_482`（四行中特）里**已落库的正文**
号码清单是按 **生肖五行**（`sign='五行肖'`，马为火肖）拼出来的 —— 同一特码可能「判定命中」却在
展示的候选组里找不到，或反之（例：45 的号码五行是木，旧正文把它写进【土】）。

**统一口径**：

| 层面 | 改动 |
| --- | --- |
| 号码分组常量 | `predict.common.ELEMENT_NUMBER_GROUPS`（金10/木10/水8/火12/土9 = 49）是唯一权威来源；禁止用 `sign='五行肖'` 推导号码清单 |
| 生成侧 | `predict/mechanisms.py`：`TABLE_FIXED_MAPPING_KEYS["mode_payload_53"]` 由 `五行肖` 改为 `五行`；`3hang` / `sihangzhongte` / `_make_source_column_element_config` 的 `labels_loader` 与 explanation 同步改为 `五行` |
| 已落库正文 | 新增 `backend/scripts/repair_mode53_element_content.py`：把两表正文里**每个五行标签后的号码清单**重写为号码五行清单（标签、条目顺序、期号与其它列一律不动）。默认 `--dry-run`，`--apply` 才写；带 `--manifest`（id/原正文/新正文，即回滚依据）与 `--rollback`；写入走 `utils/created_prediction_store.py::update_created_content_row`，`WHERE id/ctid + 原正文` 比较-交换，并发写入只会影响 0 行 |
| 展示侧 | 正文清单与后端 outcome 同源后，twbst528 适配器里「按本行清单复算」的结果与「接口判定取反」一致（`killedSetContainsTarget` 由「绕开口径冲突」变为「一致性护栏」） |

**为什么不用回填判定**：`is_correct` 是**读时复算**（`serialize_public_history_row`），后端修正
自动覆盖全部历史期；本次写库只改展示用的号码清单。

**本地验收（dev 库 + `127.0.0.1:3000`）**：

- 修复前 `created.mode_payload_53` 1148/1151 行、`created.mode_payload_482` 741/741 行是旧口径，
  `public.mode_payload_53` 206/206 行本来就是新口径（= 目标格式样板）。
- 修复后逐行校验 1892 行：每个标签的清单**完全等于**权威号码五行清单（`json` 合法、条目数 3/4 正确）；
  「有序标签序列分布」与修复前逐项一致（53：157/138/105/…，482：15/13/11/…）→ 证明只改了号码清单。
- 幂等：再次 `--dry-run` 显示「将修改 0 行」。
- 展示审计（HEAD 版审计脚本）：twbst528 本地 `error=0 warn=2`，与修复前持平。
- 泛化扫描：全库只有这两张表含旧口径清单，其它 mode_payload 表（98/137/269/334/350）早已是新口径。

---

## 五之十三、twbst528 七项展示改造（2026-09-30）

站点：`twbst528`（web_id 10）主页 `frontend/public/vendor/twbst528/index.html` +
适配器 `frontend/public/vendor/twbst528/site-data-adapter.js`。

| # | 需求 | 实现 |
| --- | --- | --- |
| 1 | 【八肖来袭】→【七肖来袭】 | `index.html` / `index1.html` 板块标题改名；适配器 `sectionByTitle("七肖来袭")`，数据源仍是 mode 44（`7xiao7ma`） |
| 2 | 【平特①肖】/【绝杀①肖】内容显示改「生肖×3」（鸡鸡鸡） | `renderPingteYixiaoHistory`（命中整段标黄）、`renderJueshaYixiaoHistory`（排除型零黄底）都按供应商模板的重复三次写法 |
| 2b | **所有平特**按七个开奖号码判定 | 新增平特判定引擎：`fullDrawnCodes` / `fullDrawnZodiacs`（按长度取最长的开奖串，兼容 `raw.res_code` 与嵌套 `raw.raw.res_code`）、`flatZodiacHit`（生肖 ∈ 七肖）、`flatTailHit`（尾数 ∈ 七码尾数）、`withFlatVerdict` + `applyFlatVerdicts`（渲染前对 `pt1xiao/pt1wei/pt2xiao/pt3xiao` 统一改写判定） |
| 2c | 平特命中项可能是**平码** | `withFlatVerdict` 在行上挂 `flatDraw`，`highlightTokens` 增加「候选 ∈ 七个开奖值」命中分支，避免「命中却零黄底」（R4） |
| 2d | 【绝杀①肖】判定口径 | 用户确认**保持**「按最后一个开奖号码（特码）判定」，不做七码复算（只在测试里加反向断言锁死） |
| 3 | 【天地+②肖】【18码中特】无后端资料 | 18码中特 进 `EMPTY_PANEL_TITLES`（蓝图 `blocked_requires_backend_work`）；天地+②肖 先进 `UNBACKED_PANELS`（按模块行数动态隐藏）。两者都只隐藏、保留 DOM 与 `data-prediction-empty` 标记。**同日晚些的第二轮把天地+②肖的数据源由 0 行的 `tiandi_2xiao` 改为 `title_5`（mode 5 天地生肖）并恢复显示 —— 见本节的「补充」小节** |
| 4 | 【独家公式】排版 | 去掉模板占位字母 `T`（`T37`）与烤死的「整体准确率：96.96%。参弃随意」；每行统一 `第N期 开：20-19-38-35-23-42-45狗 【单数】√`；√/x 取**维度判定** `raw.formula[kind].is_correct`（行级 `result.isCorrect` 在该供应商模块里恒为 null，旧实现因此把命中行也显示成 `x`）；标黄只落维度值（单数/大数/命中的那个尾数数字） |
| 5 | 【家野中特】显示家禽/野兽 | 数据源由「平特2肖（mode 43）」换成站内已授权的 mode 14「家禽野兽」（`title_14`）；`domesticWildGroups` 兼容两种 tokens 形态（组名单独成项 / 用 `;` 粘在上一肖后），显示 `家禽：猪鸡羊马+野兽：猴龙鼠兔`，标黄只落开出的那个特肖 |
| 6 | 【码友三（10码中特）】→【码友三（六肖中特）】 | 卡片标题改名（数据源本来就是 `6xzt` = mode 46 六肖中特，旧标题与正文不符） |
| 7 | 【暴富⑦肖】去号码、只留生肖 | `renderBaofuQixiaoHistory` 由 `tokens(row).join("")`（会输出 `猪\|08猴\|11…` 原始串）改为 `zodiactsOf(row).join("")`；【七肖来袭】同口径 |

**验收（本地，未部署）**：

- 展示审计：`python scripts\audit-prediction-display.py twbst528 --base-url http://127.0.0.1:3000`
  → `rows=383 js_errors=0 error=0 warn=2`（与改动前持平，warn 仍是两条既有 R5 连期重复）。
- 渲染契约：`twbst528-display-contract.mjs`（新增第 19 节：七码引擎/三次显示/独家公式排版/
  家野中特数据源/暴富⑦肖纯生肖/动态隐藏）、`twbst528-live-mapping-contract.py`
  （修复既有红色项：天地+②肖 与 18码中特 改为断言整块隐藏、一肖一码/⑤肖⑩码 同；
  新增平特七码口径、暴富⑦肖纯生肖、码友三改名、独家公式排版断言）、
  `twbst528-tiandi-display-contract.py`（天地板块按行数动态隐藏后仍通过：夹具给了行 → 面板照常渲染）。
- 后端：`cd backend/src; python -m pytest -q` → `1159 passed / 13 skipped / 2 failed`，
  两个失败与改动前一致（`test_nginx_exposes_exact_liveness_and_readiness_proxies`；
  `test_postgres_scheduler_task_is_exclusively_acquired_and_recovers_after_lock_timeout` 并发偶发）。

### 补充（同日第二轮）：分类中特板块的「借模块」错位（2026-09-30）

**报障现象**：【左右中特】内容显示「天肖/地肖」、【日夜特肖】内容显示「前肖/后肖」。

**根因**：这两个板块的数据源在适配器里被绑成了**别的玩法**的模块，而本站没有它们自己的分类数据：

| 板块 | 改前绑的模块 | 该模块正文标签 | 本站数据 |
| --- | --- | --- | --- |
| 左右中特 | `title_5` = mode 5 天地生肖 | 天肖/地肖 | 有（但属于天地口径） |
| 日夜特肖 | `qianhou_texiao` = mode 219 前后特肖 | 前肖/后肖 | 有（但属于前后口径） |
| 阴阳⑧码中特 | `title_48` = mode 48 8肖中特 | 8 个生肖 | 有（但属于 8 肖口径） |
| 前后中特 | `qianhou_texiao` = mode 219 前后特肖 | 前肖/后肖 | ✅ 口径本来就一致 |

库内核对（dev 库 `created.mode_payload_*`）：`mode_payload_152`（左右肖）只有 web 1/4/6/7/8，
**没有 web=10**；`mode_payload_164`（日夜肖）在按站点生成的数据表里**全站 0 行**；
阴阳肖同样没有 web=10 的生成行 → 这三个板块**不可能**显示正确的左/右、日/夜、阴/阳。

**处理**（用户确认）：

1. **左右中特 / 日夜特肖 / 阴阳⑧码中特 → 整块隐藏**：不再借别的模块，进 `EMPTY_PANEL_TITLES`
   （`data-prediction-empty` + `display:none`，保留 DOM，后端补数据后可还原映射）。
2. **天地+②肖 改绑 `title_5`**：`title_5` 就是 mode 5「天地生肖（天地选1，生肖选2）」——
   正文 `["地肖|蛇,羊,鸡,狗,鼠,虎"]` + `xiao` 两肖，正是面板图例/样例的 `天肖+狗鼠` 形状，
   web=10 有真实历史行；此前绑的供应商模块 `tiandi_2xiao` 全站 0 行，面板只能隐藏。
   判定仍由 `tiandiJudgement()` 本地复算（**特肖 ∈ 天地组 ∪ 两肖**），不靠接口那套「只比两肖」的口径；
   `tiandiJudgement` 现在同时认两种字段形状（`tiandi`+`xiao_pair` / 正文标签+`xiao`）。
3. **`UNBACKED_PANELS` 改为 `{title: "天地+②肖", moduleKey: "title_5"}`**：按行数动态隐藏，
   `title_5` 有行就渲染、没行才隐藏。

**契约测试同步**：

- `twbst528-tiandi-display-contract.py`：夹具从 `tiandi_2xiao`（`raw.tiandi`/`raw.xiao_pair`）
  改为 `title_5`（正文标签 + `raw.xiao`），断言不变（天地组∪两肖、只标命中项、错/未开奖零黄底）。
  该契约的「杂散黄底」探针补上**可见性口径**（`getClientRects().length > 0`）——被隐藏板块里
  烤死的模板黄底样例不是页面展示，与 `scripts/audit-prediction-display.py` 的 ROW_SCRIPT 同口径，
  否则新隐藏的三个板块的静态样例会被误报成 12 处杂散黄底。
- `twbst528-display-contract.mjs`：新增 10b 节（天地+②肖必须绑 `title_5`、前后中特绑
  `qianhou_texiao`、三个无数据板块不得再接模块渲染），并更新隐藏清单断言。
- `twbst528-live-mapping-contract.py`：新增 `title_5`/`qianhou_texiao` 的真实形状夹具，
  断言天地+②肖**可见**（`地肖+猴猪`、特肖不命中 → `开:36马错`、零黄底），
  三个无数据板块整块隐藏。

**验收**：`rows=371 js_errors=0 error=0 warn=2`（与改前同类持平，warn 仍是既有 R5 两条）；
页面实测天地+②肖 = `地肖+猪兔 / 天肖+龙狗 / 天肖+龙蛇 …`（对/错按天地组∪两肖，命中项标黄），
前后中特 = `前肖/后肖`，左右中特/日夜特肖/阴阳⑧码中特 `display:none`。

**遗留（本轮未动）**：twbst528「红蓝绿肖」仍原样显示 `绿肖|羊,龙,牛,狗` 这类 `标签|值` 串
（同类 S5 观感问题，非 error）；左右中特 / 日夜特肖 / 阴阳⑧码中特 要恢复显示，需先为 web=10
生成并授权左右肖（mode 152）/ 日夜肖 / 阴阳肖数据。

---

## 五之十四、平特（x平特x）口径全站核查（2026-09-30）

**需求**：所有「x平特x」预测模块的命中判定都要跟**本期七个开奖号码**比，不是只看最后一个特码/特尾；
并要求核查十个站点。用户报障样例：`271期成语平特尾:【六道轮回】 开:猴35错` —— 第 271 期第一个
开奖号码是 36（尾 6），与「六」一致，应判「准」。

### 判定基准（权威）与三类数据来源

| 判定来源 | 站点 | 核查方式 |
| --- | --- | --- |
| 后端 `is_correct`（`predict.common.flat_zodiac_hit` / `flat_tail_hit`，config `flat_zodiac` / `flat_tail`） | twssz、twjsz666、twwanli、twcaibawang(部分)、twcf888 | `python scripts\audit-verdict-truth.py --mode-id 43 --mode-id 54 --mode-id 56 --mode-id 103 --mode-id 173 --mode-id 470` → 十站点 `error=0`（judged=2450） |
| 站点自己的 legacy JS | shengshi8800（`legacy-prediction-verdict.js` 的 `flatZodiacVerdict`/`flatTailVerdict`）、twsaimahui（`getZjIndex(..., 整期串)`） | 源码审阅 + 渲染层契约 |
| 站点适配器 / Next 侧渲染器 | twbst528（平特七码引擎，2026-09-30 上一轮）、twsyw、twjinniu（`flatZodiacHit`/`flatTailHit`）、twcaibawang（`TwcaibawangHomeClient`） | 源码审阅 + 各站契约 |

### 本轮修的三处（twsaimahui 两文件 + twsyw 两面板）

| 站点 | 模块 | 问题 | 修法 |
| --- | --- | --- | --- |
| twsaimahui | `068chengyupw.js` 成语平特尾 | 只比**特码**尾数（`tail === num`）→ 命中落在平码上的期一律判「错」 | 遍历 `codeSplit` 比末位数字；命中时标黄**预测的成语**（命中的可能是平码，标黄特码会给出假命中标记） |
| twsaimahui | `022pt1w.js` 平特一尾 | 用子串包含判定：候选尾 1 会被 19（十位 1）误命中 | 只比号码**末位数字** |
| twsyw | `#gold6xiao` 黄金六肖的「平特一肖资料」那一路 | 用**特肖**比对（`oneHit = inList(one, specialZodiac)`） | 改为与**七个开奖号码的生肖**比对，命中项点亮该候选（九肖那一路仍按中特口径） |
| twsyw | `#five_no_hit` 平特5不中 | 只比**特码**：`特码 ∈ 前 5 码` | 按站点负责人确认的**不中语义 + 平特口径**：展示的前 5 码在本期**七个开奖号码**里**一个都不出现**才算「对」，出现任意一个即「错」；排除型零黄底（行内没有 `res_code` 时回退特码） |

### 保留不动的两处（数据侧问题，改展示只会更错）

| 站点 | 模块 | 现状 | 为什么不动 |
| --- | --- | --- | --- |
| twcaibawang | `#szpt` 四字平特 | 绑 `sizixuanji`（mode 52 四字玄机，判定 = 特肖 ∈ `jiexi` 池） | `jiexi` 池是**7 个生肖**（如实测 `虎马兔龙牛羊狗`）：7 肖池对上 7 个开奖号码，平特口径的命中率 ≈ 99.6%，改完会变成「恒对」；要真正做平特需数据侧提供「四字 → 单肖」的候选 |
| twjsz666 | `四字解平特肖` | 同上（同一 mode 52、同一 7 肖池） | 同上 |

### 验收

- `python scripts\audit-verdict-truth.py`（六个平特 mode，十站点）：`error=0 / judged=2450 / 误差率 0.0000%`。
- 展示层复算筛查（playwright 抓十站点页面 + 用真实开奖库复算）：所有「x平特x」行与七码口径一致；
  逐站行数：shengshi8800 14 / twcaibawang 16 / twsaimahui 54 / twjinniu 16 / twcf888 45 /
  twssz 24 / twbst528 5（论坛标题行，非预测行）/ twjsz666 32 / twwanli 0（面板文本不含「平特」）/
  twsyw 20。
- 新增契约：`frontend/test/twsaimahui-flat-verdict-contract.mjs`（源码 + vm 真跑渲染器）；
  `frontend/test/twsyw-display-contract.py` 的 `#five_no_hit` / `#gold6xiao` 夹具改为带 `res_code`
  的平特口径用例（「平特5不中」按不中语义：候选落在七个开奖号码里 → 「错」且零黄底；
  「命中来自平码、特码不在候选里」的用例留给黄金六肖那一路）。
- 展示审计：`twsaimahui`、`twsyw` 本地 `error=0 js_errors=0`；
  `node frontend/test/twsaimahui-bundle-contract.mjs`（bundle 已重算）等契约全绿。

### 遗留

1. **四字平特 / 四字解平特肖**（twcaibawang `#szpt` / twjsz666 四字解平特肖）绑的是 mode 52 四字玄机，
   `jiexi` 候选池是 **7 个生肖**：7 肖池对上 7 个开奖号码，七码口径命中率 ≈ 99.6%（恒对）。
   **站点负责人 2026-09-30 决定：保持现状（仍按特肖 ∈ `jiexi` 池判定），本项记为数据侧问题** ——
   要真正做成平特需数据侧提供「四字 → 单肖」的候选。
2. **twsaimahui 平特一尾（`022pt1w`）的正文形态**：payload 形如 `["9尾,4尾,…,1尾|"]` 时，
   渲染器只取标签首字符（首个尾数），其余尾数既不展示也不参与判定；后端 `tail_atom_labels`
   已在真值审计侧摊平，展示侧若要逐尾展示需另开一轮。

**已决（本条不再是遗留）**：twsyw `#five_no_hit` 的标题/语义冲突 —— 负责人确认按「不中」语义，
即「展示的 5 码在七个开奖号码里一个都不出现才算『对』」，实现见上表。

---

## 五之十五、twbst528 三个中特面板判定口径修正（2026-10-01）

**需求（用户报障，274/273 期，原话「判断机制存在问题」）**：

| 面板 | 线上显示 | 用户判定 |
| --- | --- | --- |
| 【吉美丑凶】 | 274 期 `丑凶肖【牛蛇鼠】 开:24羊对`；273 期 `吉美肖【鸡牛龙】 开:19鼠对` | 「对」不对，应为「错」 |
| 【③肖防③码】 | 274 期 `牛蛇鼠+牛,蛇,鼠 开:24羊对`；273 期 `鸡牛龙+鸡,牛,龙 开:19鼠对` | 「对」不对，应为「错」 |
| 【前后中特】 | 274 期 `后肖 开:24羊错`；273 期 `前肖 开:19鼠错` | 「错」不对，应为「对」 |

### 根因：这三个面板被套上了**数据源模块**的判定口径

三个面板展示的都是「本期押的生肖 / 前后分组」，但判定分别取自两个数据源模块的接口值：

| 面板 | 数据源 | 接口判定口径 | 后果 |
| --- | --- | --- | --- |
| 吉美丑凶 | `pt3xiao`（mode 470 平特3肖） | **七码平特**（三个生肖里有一个以平码开出即「对」） | 三肖面板 20 期里 19 期恒「对」；274 期开 24 羊，牛/蛇/鼠 以平码开出 → 显示「对」 |
| ③肖防③码 | 同上 | 同上 | 同上（274 期同样显示「对」） |
| 前后中特 | `qianhou_texiao`（mode 219 前后特肖） | `contains_hit`，只比 `xiao` 列的 **2 个生肖** | 面板展示的是「后肖」（马羊猴鸡狗猪），开奖特肖是羊却判「错」 |

这两个口径本身没错（分别对应【平特③肖连】静态文章与「前后特肖」的 2 肖玩法），错在**面板**：
面板列出的候选就是本期要押的生肖/分组，判定必须与**自己列出的候选**自洽。

### 权威口径：供应商模板的对/错列（逐期可复核）

`frontend/public/vendor/twbst528/index.html` 里供应商自带的样例行给出口径 = 「特肖 ∈ 展示候选」：

| 面板 | 样例行 | 样例判定 |
| --- | --- | --- |
| 吉美丑凶 | 323 期`【吉美】【马鸡龙】`开 12 马；320 期`【凶丑】【虎猴鼠】`开 34 猴；319 期`【凶丑】【鼠猴狗】`开 47 羊；322 期`【凶丑】【虎猪猴】`开 36 马、321 期`【吉美】【龙鸡羊】`开 41 牛 | 对 / 对 / 错 / 错 / 错 —— 与「特肖 ∈ 三个展示生肖」完全一致 |
| 前后中特 | 323/322/320/319 期`后肖`开 12/36/34/47 马马猴羊；321 期`后肖`开 41 牛 | 对 / 对 / 对 / 对 / 错 —— 与「特肖 ∈ 前/后肖分组」完全一致（`前肖:鼠牛虎兔龙蛇`、`后肖:马羊猴鸡狗猪`） |

（③肖防③码 模板样例 5 行全写「对」，且 321 期与同站其它面板结论矛盾，属营销样例，不可作判据；
本面板按面板名与展示形态取「特肖 ∈ 三肖 ∪（有真号码时）特码 ∈ 三防码」。）

### 改动（`frontend/public/vendor/twbst528/site-data-adapter.js`）

1. **`pt3xiao` 退出平特七码表** `FLAT_MODULE_KINDS`：本站首页没有「平特③肖」面板，它只喂
   【吉美丑凶】【③肖防③码】两个中特面板；需要七码口径的【平特③肖连】走
   `static-article-data-adapter.js`（未改动，接口判定 = 后端七码口径）。
2. 新增「面板级中特口径」区块（与 `tiandiJudgement` 同一先例）：`displayedZodiacList` /
   `displayedNumberList` / `specialZodiacOf` / `specialCodeOf` / `zodiacPanelJudgement` /
   `sanxiaoFangSanmaJudgement` / `qianhouGroup` / `qianhouJudgement`，
   拿不到开奖或候选时返回 `null` 沿用接口判定（不凭空造「错」）。
3. 【吉美丑凶】：`zodiacPanelJudgement(row, 3, 3, 6)`（三肖 + `三肖六码` 形态的 6 码），
   结果格写本地判定；候选格先 `clearMarkers(cells[1], true)` 拆掉模板预埋黄底，再用
   `writePlainLine` 写**纯文本叶子**（该格是 `.mtbl td:nth-child(2)`，新建宿主 span 会被
   `home.css` 兜底染成芥末黄 `#d1be18`），命中项用 inline `#FFFF00` marker 单点标出。
4. 【③肖防③码】：判定接 `sanxiaoFangSanmaJudgement`（生肖 + 真号码防码），
   卡片头的开奖段一并改写为本地判定（否则头部仍是接口的平特口径）；候选行传命中 token 标黄。
5. 【前后中特】：改用专属 `renderQianhouZhongteHistory`（不再走 `renderCategoryHistory`），
   判定 = 特肖 ∈ 从行内容 `content` 解析出的分组成员（缺成员才退回面板图例 `QIANHOU_GROUP`），
   命中点亮分组名「前肖 / 后肖」。模块绑定仍是 `qianhou_texiao`。

### 验收（本地，未部署）

- `node frontend/test/twbst528-display-contract.mjs`：新增第 20 节（中特口径 + 拆包 +
  只标命中项），并修正旧的「pt3xiao 走七码」「前后中特绑 `renderCategoryHistory`」两条断言。
- **新增** `python frontend/test/twbst528-zhongte-verdict-contract.py`（Playwright + 桩 payload，
  离线）：把两个数据源模块的 `is_correct` **故意设成接口口径的错误答案**，逐行断言 274/273 期
  两个「错」、272 期「对」并只亮「猴」、`三肖六码` 形态按码命中只亮「23」、前后中特 274/273
  两个「对」并亮「后肖/前肖」、272 期「错」、行内容非标准分组（只列「马,羊」）必须按内容判
  「错」；并断言全页零幽灵标记、零杂散黄底（含 `.mtbl td:nth-child(2) span` 的芥末黄兜底）。
- `python frontend/test/twbst528-live-mapping-contract.py`：`pt3xiao` / `qianhou_texiao` 夹具
  改为真实形态（三肖「牛蛇鼠」、正文`前肖|…`），并显式断言 509 期三块面板都必须「错」。
- `python frontend/test/twbst528-tiandi-display-contract.py`、
  `python frontend/test/twbst528-zonghe-juesha-contract.py`、
  `node frontend/test/twbst528-live-mapping-contract.mjs`、
  `node frontend/test/twbst528-static-article-contract.mjs`：全绿。
- 真实本地数据端到端（自建探针读页面 + 用同源 payload 复算）：吉美丑凶 5 行、③肖防③码 5 行、
  前后中特 5 行，共 15 行判定与高亮全部一致（190/188/187 期「对」且各 1 处黄底，
  189/186 期「错」零黄底；前后中特 186–190 期特肖狗/狗/蛇/虎/牛 均不在展示分组内 → 全「错」）。
- 展示审计：`python scripts/audit-prediction-display.py twbst528 --base-url http://127.0.0.1:3000`
  → `rows=371 js_errors=0 error=0 warn=15`。

### 遗留与说明

1. **审计 warn 2 → 15**：新增的 13 条全是 `R4 highlight_hit`，全部归到共享桶 `.center.f13`
   （[③肖防③码] 候选格是 `.center.f13.black.l150`，审计按容器 class 归并模块）。
   R4 的门槛是「同桶内已有高亮行才检查」，③肖防③码 现在会正确标黄 → 门槛被打开，
   于是同桶里**既有**的 13 行「判定对却零黄底」被报出。这 13 行属于另外 11 个面板：
   多为排除型（绝杀①肖/绝杀①波/绝杀⑩码/绝杀一肖一尾/杀肖杀码/杀两半波/本期输尽光 —— 杀中本就没有
   可点亮项，零黄底是设计正确，属审计误报），少数是命中型面板的既有高亮缺口
   （⑥肖12码 / 8肖16码 / 四肖八码 / 梭哈⑦尾 / 火爆④头 / 四段中特 / 胆大胆小 / 七尾四行 /
   四季九肖 / 一句中平特 / 黑白三肖）。**本轮不处理**（各面板命中项语义不同，另开一轮）。
   `error=0 / js_errors=0` 门槛保持。
2. 【③肖防③码】的码组数据源仍是 `pt3xiao`（只有生肖、没有号码），展示退化成
   `牛蛇鼠+牛,蛇,鼠`。判定已按「展示即候选」处理（生肖名不产生号码，只用三肖判定）；
   要显示真实防码需要数据侧提供「三肖 + 三码」模块。
3. 【平特③肖连】（153/31/41/57.html 静态文章）继续走七码平特口径，与本站 `平特①肖`/`平特一尾`
   一致，本轮未改动。

### 同日第三轮：三块面板改绑**权威 mode**（155 / 117 / 133）+ 数据链路

用户随后指定数据源：「吉美丑凶 改为使用后端预测模块 mode_id=155、前后中特 mode_id=133、
③肖防③码 mode_id=117」，并要求「注意判断的正确性和前端显示预测内容的合理性」。
上表三块面板当时仍在**借**别的模块的行（`pt3xiao` / `qianhou_texiao`），本轮换成语义对应的权威 mode，
并把数据链路一起补齐（本地 dev 库此前这三个 mode 对 web=10 一行都没有）。

| 面板 | 新数据源 | 正文形态 | 展示 | 判定 |
| --- | --- | --- | --- | --- |
| 吉美丑凶 | 155「吉美凶丑（2选1，全肖）」`jimei_xiongchou` | `["凶丑肖|鼠,牛,虎,猴,狗,猪"]` | `凶丑肖【鼠牛虎猴狗猪】` | 特肖 ∈ 该分组（同后端：outcome 把特肖映射成分组名 + `contains_hit`） |
| 前后中特 | 133「前后生肖」`qianhou_shengxiao` | `["后肖|马,羊,猴,鸡,狗,猪"]` | `后肖` | 特肖 ∈ 该分组 |
| ③肖防③码 | 117「3肖4码」`sanxiao_siwei_xiao` | `["虎|05","马|01","狗|09"]` | `虎马狗+05.01.09` | 特肖 ∈ 3 肖（同后端 `hit_checker=contains_hit`、`RULE_BY_MODE_ID[117]=zodiac`）；**码组只展示**，号码半区在平台里属于 mode 123「4尾8码」 |

后端/数据链路改动（这一轮必须做，否则三块面板会因为没有行而整块空掉）：

1. **机制配置**（`backend/src/predict/mechanisms.py`）：新增 `jimei_xiongchou`（155）与
   `qianhou_shengxiao`（133）两个静态配置，与 mode 480「凶吉六肖」同族（候选 = 分组名、
   `label_count=1`、`content_formatter` 输出 `分组名|成员生肖`），并新增
   `special_jimei_from_row` / `special_qianhou_from_row`（特肖 → 分组名，成员表取自
   `fixed_data` sign='凶丑吉美生肖' / '前后肖'，同一份静态表兜底）、`format_jimei_groups` /
   `format_qianhou_groups`。
2. **受控生成规则**（`domains/prediction/generation_rules.py`）：155/133 登记
   `rule_id="zodiac_group"`（真实目标 = 特肖所属**分组名**，否则「候选是分组名」的玩法每期都会被判不中）；
   117 沿用已登记的 `zodiac`。`rule_documentation` 增补该 rule_id 的说明，`backend/docs/prediction-module-rules.md`
   已按渲染器重算。
3. **站点授权**（`domains/prediction/site_page_dependencies.py`）：twbst528 首页清单加入
   155/117/133；219「前后特肖」在本站已无页面引用，移出清单（其站点授权行仍在库里，只不再进清单）。
4. **迁移 33** `sync_twbst528_zhongte_mode_authorization`：建 `created.mode_payload_155/133/117`
   三张 payload 表 + 同步站点 10 的授权行（`sync_site_prediction_modules` 只写站点 10，
   不复制任何其它站点的历史）。
5. **展示层**（`frontend/public/vendor/twbst528/site-data-adapter.js`）：`groupMembers` /
   `groupMemberJudgement`（155/133 通用，成员从行内容解析）/ `sanxiaoSiweiJudgement`（117），
   替换上一轮的 `zodiacPanelJudgement` / `sanxiaoFangSanmaJudgement`；`displayedNumberList`
   改为按 `|` 之后逐个取码（供应商样本 `牛|17,05` 这类一肖两码不能整串当数字）。
   `XIONGJI_GROUP` 同时收「凶丑肖」（mode 155 正文）与「丑凶肖」（本站面板/模板文案）——
   只认一种写法会让另一组候选丢成员、判定退回接口值（实测 268/271 期）。
6. **生成侧三期唯一**（`prediction_generation/diversity.py`）：133 与 155 同族（2 选 1 全肖、
   正文单个分组标签），加入 `THREE_PERIOD_UNIQUE_MODE_IDS`，避免同一分组连续多期（本地实测
   未纳入时出现过连续 5 期「后肖」）。

#### 验收（本地，未部署）

- `python frontend/test/twbst528-zhongte-verdict-contract.py`（新增/重写，桩 payload）：
  三个模块的 `isCorrect` **故意填成与本地判定相反**的值，逐行断言 155 的 274 期「吉美肖 + 开 24 羊 → 对」、
  272 期「凶丑肖 + 开 12 羊 → 错」、270 期「丑凶肖」写法同样解析成员；133 的 274/273 期「对」、
  272 期「错」、270 期「行内容只列马,羊 → 错」；117 的 274 期「虎马狗 + 开 37 马 → 对」、
  273 期「错」、272 期「码组含 05、开 05 虎 → 仍判错（号码半区不参与判定）」；
  以及全页零幽灵标记 / 零杂散黄底。
- `node frontend/test/twbst528-display-contract.mjs`：第 20 节重写为「绑定 155/117/133 + 口径函数 +
  旧函数不得残留 + 别名字典」。
- `python frontend/test/twbst528-live-mapping-contract.py`：三个新模块夹具 + 509 期「错」断言。
- 其余 twbst528 契约（tiandi / zonghe / static-article / live-mapping.mjs）全绿。
- 真实本地数据端到端：三彩种各生成 8 期历史 + 1 期未来期（web=10，共 27 行/模块），
  面板逐行显示与判定一致（`凶丑肖【鼠牛虎猴狗猪】 开:11猴对`、`虎马狗+05.01.10 开:37马对`、
  `后肖 开:37马对` …）。
- 展示审计：`rows=371 js_errors=0 error=0 warn=16`（13 R4 + 3 R5）。R4 同上一轮（共享桶 `.center.f13`
  的归并产物）；新增的 R5 是 `?|吉美肖` 桶：审计按「行内标签」把同一分组的期次归到一个模块，
  于是「同组多期」天然同值 —— 三期唯一规则已保证没有**连续** 3 期同值，属审计口径产物。
- **审计等待窗口**：twbst528 线上首屏（供应商聚合 ~756 KB）约 39 s 才渲染预测行，而审计脚本
  默认只等 12 s → 线上审计会只扫到供应商模板行（`rows` 偏少、出现模板 `开:????准` 的假 error）。
  本轮给 `scripts/audit-prediction-display.py` 加了可选 `--wait-ms`（默认仍是 12000，行为不变）；
  线上复核用 `--wait-ms 95000` → `rows=371 js_errors=0 error=0 warn=15`。

#### 遗留

1. 审计 13 条 R4（见上一小节的说明）与 `?|吉美肖`/`?|绿肖`/`?|蓝单` 三条 R5 均为审计**按容器
   class / 行内标签归并模块**的产物：前者是另外 11 个面板既有的「命中无高亮」缺口（含排除型面板的
   零黄底设计），后者是 2 选 1 分组玩法的固有形态。均不改展示层，登记为已知项。
2. mode 117 的号码半区（4 码）在平台里属于 mode 123「4尾8码」，③肖防③码 面板只展示、不判定；
   若日后要按「防码命中也算对」展示，需产品侧确认口径（会与后端 `RULE_BY_MODE_ID[117]` 不一致）。

---

## 五之十六、文本类玩法「简体龙」解析缺陷 + 一肖一码派生行判定（2026-10-02）

**报障（三条，用户原话）**

| 站点 | 模块 | 现象 |
| --- | --- | --- |
| twwanli.com | 一肖一码发布区 | 2026278 期八行生肖全部 `开:03龙对` 并上黄底，其中「牛虎马鼠羊鸡猪猴」（九肖行）并不含「龙」 |
| twbst528.com | 一句中平特 | `丈夫解男肖，龙虎鼠猴牛马狗。 开:03龙错` —— 命中「龙」却判「错」 |
| twcaibawang.com | 一句真言 | `真言解肖主前：羊虎龙兔牛猴蛇 開:龙03` —— 命中「龙」却整块无高亮 |

### 根因一（后端，`一句真言` / `一句中平特` / `四字玄机` 共用）

`predict/categories/content_columns.py::parse_zodiac_chars` 的字符类写作
`[鼠牛虎兔龍蛇马馬羊猴鸡雞狗猪豬]` —— 收了繁体「龍」却**漏了简体「龙」**
（`predict/common.py` 的同类字符类是 `[…龍龙…]`，两种都收）。
mode 50「一句真言」/ mode 52「四字玄机」的候选都由它从 `jiexi` 抽取，
`contains_hit` 的 `any(label in outcome)` 于是永远匹配不到「龙」
→「开奖特肖 = 龙」的期一律判「错」（twbst528 显示错、twcaibawang 判错后不标黄）。

**修法**：字符类收敛为**唯一来源** `predict.common.ZODIAC_CHAR_CLASS`（简体 + 繁体齐全），
`content_columns.parse_zodiac_chars` / `common.parse_zodiac_content` /
`vendor/homepage_modules.py`（两处）共用，避免再出现「只收一种写法」的漂移。

### 根因二（twwanli `#yxym` 一肖一码：派生行共用一个判定 + 行宽算错）

`#yxym` 的 13 行是「9 肖中特 前 N 肖 / 精选22码 前 N 码 / 双波」的**派生行**，旧实现有三个问题：

1. 判定统一取数据源模块的 `result.isCorrect`（9 肖中特的整份 9 肖判定）→ 一肖…九肖全部显示「对」，
   连 `一肖 牛`（开 03 龙）也显示「对」；
2. 行宽按 `rowIndex - 3` 推，把 `九肖` 行算成 **8 个生肖** → 9 肖里的第 9 个（278 期是「龙」）
   被裁掉，那一行却仍按 9 肖判定上黄底（用户看到「显示里没有龙却高亮」）；
3. 命中行整格上黄底（非命中项也黄）。

**修法**（`frontend/public/vendor/twwanli/site-data-adapter.js`）：

| 项 | 改法 |
| --- | --- |
| 行宽 | **由行名决定**：`一肖`→1 … `七肖`→7、`九肖`→9（`ONE_CODE_ONE_XIAO_LABELS` + `oneCodeOneXiaoRowSpec`），不再按行号推 |
| 判定 | **逐行按本行展示的候选项复算**：号码行比特码 ∈ 前 N 码、生肖行比特肖 ∈ 前 N 肖、波色行比开奖波色 ∈ 展示的两波；拿不到开奖值才不给判定 |
| 高亮 | 只点亮**命中的那一个**候选项（`highlightOnly` / `codeLineHtml(codes, hitCode)`），槽本身不再整格上标记（S2） |
| 未开奖 | 只显示 `开:待开奖`，不给判定也不高亮（S1）；判定「错」零黄底（S3） |

### 根因三（twbst528【一句中平特】命中项没有点亮）

`renderYijuZhongpingHistory` 原先只传 3 个参数（moduleKey / 命中项解析器都缺），
命中型模块拿不到可标黄的项 → 判定「对」的行零黄底（五之十五「遗留 1」里登记的 R4 缺口）。

**修法**：新增 `yijuZhongpingHitTokens(row, text)`——判定为「对」时点亮**展示正文里真正开出的那个特肖**；
`错`/未开奖/正文里没有该特肖时零黄底；`renderThreeColumnRows(..., "yijuzhenyan", yijuZhongpingHitTokens)`。

### 验收（本地 dev 库 + `127.0.0.1:3000`，未部署）

- 后端：`cd backend/src; python -m pytest tests/unit -q` → **1212 passed / 1 failed**，
  唯一失败是既有的 `test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`（与本轮无关）。
- 新增 `backend/src/tests/unit/test_zodiac_char_parser_long.py`（7 条）：简体/繁体/混写「龙」、
  12 生肖全量、mode 50 报障行 `开 03 龙` → `is_correct=True`、候选取自不含「龙」的 `jiexi` 时仍判「错」。
- 数据侧复算（同一份 payload 用新旧字符类各算一次）：`created.mode_payload_50` 1109 行中 **58 行**、
  `mode_payload_52` 550 行中 **26 行**由「错」改判「对」，**全部是「开奖特肖 = 龙」的期，无反向翻转**。
- 接口端到端：`/api/public/site-page?site_id=8&history_limit=80&lottery_type=3` →
  175 期 `开:龙27` / `jiexi=龙虎鼠猴牛马狗` 由 `is_correct=False` 变 **`True`**；
  173 期 `开:龙15` / `jiexi` 不含龙 → 仍为 `False`。
- 渲染端到端（真页面 + Playwright 探针）：
  - twwanli `#yxym`：`191期 一肖 猴 → 开:47猴对` 只黄「猴」、`一码 31 → 错` 零黄底、
    `九肖 猴蛇猪鼠马狗龙虎羊`（**9 个生肖**）、`190期 一码 45 → 对` 只黄「45」、`一肖 猴 → 错`；
  - twbst528【一句中平特】：191/190/188/186 期「对」各点亮 1 个特肖，189/187 期「错」零黄底；
  - twcaibawang【一句真言】：270 期 `開:马37` → 点亮「马」；未命中期零黄底。
- 契约：
  - `frontend/test/twwanli-yxym-layout-contract.py`：版式（不溢出/不折错位）+ 逐行判定/黄底 +
    九肖=9；桩里的接口 `isCorrect` **故意写反**（命中行 False、未命中行 True），
    证明判定确实来自本地复算；同时断言内容槽不再整格带命中标记。
  - `frontend/test/twbst528-display-contract.mjs`：新增第 21 节 + 真实 `yijuZhongpingHitTokens` 行为断言
    （对→点亮、错/未开奖/正文无该特肖→零标记）。
  - `frontend/test/twcaibawang-verdict-contract.mjs`：新增第 7 节，真跑 `renderYijuzhenyan`
    （`羊虎龙兔牛猴蛇 + 开龙03` → 只黄「龙」；未命中/未开奖零黄底；描述性汉字不算候选）。
- 展示审计（本地 `--wait-ms 20000`）：twwanli / twbst528 / twcaibawang 全部
  `error=0`、`js_errors=0`；twbst528 `rows=371 warn=17`、twcaibawang `rows=292 warn=5`
  （全是既有的 R4/R5/R8，未随本轮增加；`一句中平特` 不再出现在 R4 里）。
- twwanli 同一份代码前后对照（本地 + 当前后端）：
  | 口径 | rows | error | warn | js_errors |
  | --- | ---: | ---: | ---: | ---: |
  | HEAD 适配器 | 195 | 0 | 1（`#hsdx｜合数大` R8） | 0 |
  | 本轮适配器 | 195 | 0 | 2（+`#yxym｜一肖` R8） | 0 |
  新增的那条 R8 是本轮修法的**必然结果**：`一肖` 行现在按自己那 1 个生肖判定，
  连续 5 期「错」的概率是 `(11/12)^5 ≈ 65%`，属五之三 R8 的第 1 类「正常（候选集本来就小）」，
  不是「判定写死」——判「对」的那些期（`一肖 猴` + 开 47 猴等）都是真的命中。

### 遗留

1. 【一句中平特】面板只显示正文（`content`），不显示 `jiexi`：命中项若**只**出现在 `jiexi` 里
   （本地实测 37/1067 行，如 `美解女肖蛇羊鸡兔。` 的 `jiexi` 多出「鼠马猪」），
   面板上没有可点亮的项 → 仍会报 R4。要彻底消除需二选一：面板补显 `jiexi`，或把判定改成
   「特肖 ∈ 展示正文的生肖」（会改判约 3.5% 的行）。
2. 【一句真言】（twcaibawang）不印「对/错」文字（供应商格式 `開:龙03`），命中与否只由黄底表达；
   若要与 twbst528 的孪生面板一致，可另开一轮补判定文字。
3. mode 52「四字玄机 / 四字平特」的 7 肖 `jiexi` 池命中率问题（五之十四 遗留 1）不变。
4. 本地 `:8000` 上曾同时存在多个历史会话遗留的旧后端进程（Windows 的 `SO_REUSEADDR` 允许重复绑定，
   请求被随机分发到旧进程，本地复验会看到修复前的判定）。本轮已停掉这些旧进程、只保留一个当前代码的
   进程；**本地复验前先确认 `:8000` 只有一份后端**。

---

## 五之十七、十站「生肖识别」同族缺陷普查 + twssz AAA / twbst528 / twcaibawang 收口（2026-10-03）

**报障**

| 站点 | 模块 | 现象 |
| --- | --- | --- |
| twjsz666.com | 一句话中特码 | `278期 一句话「枫桥夜泊先收牛兔龙，尾声补上狗羊鼠猴。」 开:03龙错` —— 候选有「龙」、开奖也是龙，仍判「错」 |
| twssz.com | AAA级大公开;准确率绝对100%;大胆下注! | ⑨⑧⑦⑥肖中特四行**既不标黄也没有对/错**，看不出本期是否命中 |

用户同时要求：把十个站点里同族的「生肖识别不了」问题一并查清，并落地上一轮留下的两个选项
（twbst528【一句中平特】改为按展示正文判定、twcaibawang【一句真言】补判定文字）。

### 1) twjsz666【一句话中特码】—— 与五之十六同一个后端根因，已随之修复

该卡片绑的也是 mode 50（`yijuzhenyan`），候选来自 `jiexi`，因此
`parse_zodiac_chars` 漏简体「龙」的缺陷（五之十六）就是它的根因；后端修好后
`is_correct=true`，`hitTokenGroups()` 拿到特肖「龙」→ 点亮正文里的「龙」。

实测（本地 web=11）：`175期 开:龙27 jiexi=鼠虎兔龙蛇猴`、`173期 开:龙15 jiexi=猴猪羊虎鼠龙马`
都已是 `is_correct=True`；页面上「对」行都点亮了对应特肖。

### 2) twssz【AAA级大公开】—— 派生行共用判定 + 缺判定文字

4 行 `⑨⑧⑦⑥肖中特` 是同一份「九肖中特」的前 9/8/7/6 肖，旧实现三处问题：
数据源是 mode 44（只有 7 肖，缺的位用固定顺序补齐）、判定与黄底取整份模块的 `is_correct`
（整份命中四行一起黄，⑥肖行没含特肖也黄）、面板没有任何对/错。

**修法**（`frontend/public/vendor/twssz/site-data-adapter.js`）：数据源改 mode 49（`9xzt`，
缺行才退回 `7xiao7ma`）；`aaaZodiacs` 取 9 肖；每行按**本行展示的前 N 肖**复算判定，
只点亮本行里真正开出的那个生肖；新增 `[data-site-slot='aaa-verdict']` 判定字
（已开奖 `对/错`、未开奖为空，S1）；标题行补开奖段 `开:03龙`；去掉会按整份判定清黄底的
`applyRowHighlight` 调用。

实测（本地 web=9）：`267期 ⑨肖中特:鸡猴猪蛇牛鼠兔狗羊 开:24羊 → 对+羊黄底`，
同行 `⑧⑦⑥肖` → **错 + 零黄底**（旧实现四行全是「对」）。

### 3) twbst528【一句中平特】：判定改为按展示正文的生肖

上一轮遗留的选项，本轮采纳：新增 `yijuZhongpingJudgement()` —— **判定与高亮共用同一处口径**
（特肖 ∈ 展示正文里的生肖），`错/未开奖` 零黄底；正文里没有生肖字时返回 `null` 沿用接口判定。
影响面与上一轮测算一致：约 3.5%（37/1067）「只在 `jiexi` 里命中」的行由「对」改判「错」，
面板从此不再出现「判定对却没有任何可点亮的项」。

### 4) twcaibawang【一句真言】：补判定文字

供应商格式只有 `開:龙03`，用户看不出对错。现在开奖段后补 `<font color="#FF0000">对</font>`
或 `<font color="#000000">错</font>`；未开奖不写判定文字（S1）。

### 5) 十站「生肖识别」同族缺陷普查

普查口径：**凡是「从文本/候选里认出生肖」的解析器，写法没列全就会静默丢生肖** ——
少一个生肖就可能把命中判成「错」（后端）、把命中项丢掉高亮、或把上游正确的「对」
在契约层强制改写成「错」。后端已收敛到唯一来源 `predict.common.ZODIAC_CHAR_CLASS`。

本轮**新增修复**：

| 位置 | 缺陷 | 修法 |
| --- | --- | --- |
| `predict/common.py` | 分组里的**错别字「免」**：`public.fixed_data`(文武肖 id 262) 与 `mode_payload_144/179` 正文写成 `["文肖|鼠,免,龙,羊,鸡,猪"]`（实测 174 行）→ 特肖=兔 时拿不到分类标签，文肖/武肖恒判「错」 | 新增 `normalize_zodiac_member()`：**只对分组里的单字成员**做 `免→兔`（自由文本里的「不免」不动），`zodiac_category_labels` 使用它 |
| `frontend/public/vendor/twsaimahui/static/js/046wenwu.js` | 同一错别字的渲染侧：`xiaoV[i].indexOf(sx)` 拿 `免` 找 `兔` 恒不命中 → 显示「错」+零黄标，且说明行照抄错别字 | 新增 `normalizeZodiacText()`（免→兔），匹配与展示都归一 |
| `frontend/lib/prediction-contract.ts::candidateZodiacAtoms` | 生肖原子只认简体：候选/正文写 `龍馬雞豬`（或错别字「免」）时交叉校验落空 → `contradicted` → `reconcileVerdict` 把上游正确的「对」**强制改写成「错」并清掉黄底**（10 站共用） | 原子字符集扩到简体+繁体+错别字并归一，与后端同口径；同时锁定「候选里真的没有该生肖时仍判 contradicted」 |

**本轮登记、暂不改（潜伏项，触发前提是候选/开奖生肖以繁体形态进入该链路；
本地/线上 payload 抽样未发现繁体生肖，故当前不产生可见错误）**：

| 位置 | 说明 |
| --- | --- |
| `shengshi8800/static/js/legacy-prediction-verdict.js:18` | 判定引擎的 `ZODIAC` 常量只认简体（`zodiacsOf` / `isZodiacToken` / mode 50、52 分支）；候选写繁体时会判「错」 |
| `twssz/site-data-adapter.js:553`（`ZODIAC_CHARS`）、`:1527`（`tiandiPair`） | 从 `result.text` / `raw.xiao` 兜底取特肖、天地两肖时只认简体 |
| `twbst528/site-data-adapter.js:1110`（`ZODIAC_CHARS/ZODIAC_CHAR_SET`） | `flatZodiacHit` / `displayedZodiacList` / `groupMembers` 的候选识别集只认简体 |
| `twwanli/site-data-adapter.js:311-312` / `:389-390` | 【买啥开啥】家禽野兽、【天地生肖】的固定分组表是简体字面量 |
| `twjinniu/index.html:392-397`（`QINQI_ART_BY_ZODIAC`） | 【琴棋书画】按简体键查艺名（同站 `lib/twjinniu-articles.ts` 已归一，两处口径不一致） |
| `twcf888.com/index.html:1346-1367` | mode 50 抽生肖、mode 26 琴棋书画分组为简体硬编码 |
| `twssz`/`twsyw` 适配器的天地肖、清屏正则 | 同上（清屏漏繁体只会短暂残留模板样例，不影响判定） |
| `twbst528/site-data-adapter.js` 一肖一码（`renderYixiaoYimaHistory`） | **B 类（派生行共用判定）**：11 行共用整份源模块 `isCorrect`。该面板绑 mode 151（全表 0 行）已被 `EMPTY_PANEL_TITLES` 整块隐藏，属潜伏项；后端补数据或放开隐藏前必须先逐行复算 |

### 验收（本地 dev + `127.0.0.1:3000`，未部署）

- 后端 `python -m pytest tests/unit -q` → **1212 passed / 1 failed**（唯一失败仍是既有的
  `test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`）。
- 新增/扩展契约：
  - `backend/src/tests/unit/test_zodiac_char_parser_long.py`：+2 条「免→兔 只作用于分组成员」；
  - `frontend/test/prediction-verdict-truth-contract.ts`：+3 条（繁体 `龍`、错别字「免」→ verified；
    真的没有该生肖 → 仍 contradicted）；
  - `frontend/test/twssz-aaa-grade-contract.py`（**新增**）：8 张卡真渲染，特肖放在第 9 位 →
    `⑨肖` 对+龙黄底、`⑧⑦⑥` 错+零黄底、未开奖卡无判定无高亮、标题行开奖段；
  - `frontend/test/twbst528-display-contract.mjs`：第 21 节改为「判定+高亮同一口径」的行为断言；
  - `frontend/test/twcaibawang-verdict-contract.mjs`：第 7 节补「对/错文字 + 未开奖不写」断言。
- 后端接口端到端：`site_id=11`（twjsz666）175/173 期 `开:龙` 由 `False` 变 `True`；
  文肖分组 `["文肖|鼠,免,龙,羊,鸡,猪"]` + 特肖「兔」现在得到 `('文肖',)`（修复前为空）。
- 页面端到端（Playwright 探针）：twssz `267期 ⑨肖 对+羊` / `⑧⑦⑥肖 错+零黄底`；
  twbst528【一句中平特】各期「对」各点亮 1 个特肖、错期零黄底；twcaibawang `開:龙03对`。
- 展示审计（本地全站 `--wait-ms 20000`）：`error=0`、`js_errors=0`（数字见本轮发布记录）。

### 已知非本轮引入的失败契约

`frontend/test/twssz-live-mapping-contract.py` 在 HEAD 上就失败
（`命中号码必须实际显示供应商既有的黄色高亮背景`，15码中特卡片）—— 与本轮改动无关，
该脚本不在 `pnpm test:display-contracts` 列表内，登记为待修。

### 审计工具收敛：判定锚点与占位窗口（2026-10-06）

本轮线上验收时 `shengshi8800` 报了 1 条 error：

```
R2 verdict_pending | #table1810|独家幽默 结果为占位（未开奖/无命中项）却显示判定「对」
sample: 279期独家幽默：開:？00 独家幽默：在网吧上网中，对方女的要他开视频，…调整对着我，…
```

**复核结论：页面没有缺陷，是审计把段子正文读成了判定。**
真页面实测（`https://www.tw8800.com/vendor/shengshi8800/embed.html?type=3&web=4…`）：
待开奖那一行自身文本只有 `279期独家幽默：開:？00`（无判定、无黄底），段子是**另一个
节点**（`…要他开视频…调整对着我…`）；`ROW_SCRIPT` 的兄弟行合并把两者并成一行后，
`verdict_of` 取「最后一个 `开/開` 之后 16 字」——最后一个「开」落在段子里的「开视频」，
窗口里就抓到了「对着我」的「对」。

修法（`scripts/audit-prediction-display.py`，两处，均已在本地用例上回归）：

1. **判定锚点收紧**：只有「后面紧跟结果引导词或结果本身」的 `开/開`
   （`[:：]`、奖/出/码、数字、`？`/`待`、生肖字、波色/大小/单双/天地/前后/五行/琴棋书画…）
   才算开奖段起点；正文里的「开视频 / 开心 / 开门」不再被当成锚点。
2. **占位结果窗口收敛**：锚点之后若是占位（`？00` / `待开奖` / `？？？`…），判定窗口只到
   占位符之后 2 字，不再读进同行的段子/谜面正文。

收敛后 11 条本地用例全过（含 `绝杀二肖 开 马37错`、`开47猴对`、`開:龙03对`、
`开奖【域名】中奖` 必须读不到判定 等反向用例）。

---

## 六、常见根因速查

| 现象 | 常见根因 | 处理 |
| --- | --- | --- |
| 「错」的期仍有黄底 | 高亮取自供应商静态 HTML 的命中标记；或整行/整模块共用一个命中状态；或「一期」被拆成多个单元格/相邻 `<tr>`，只改了其中一块 | 高亮条件必须与本期判定绑定；渲染前先清除旧高亮；审计脚本会把同辈/相邻行合并后再判 |
| 某一期 `开:？00错` | 模块在找不到开奖号码对应项时用了占位串 | 固定显示本期真实特码，判定照常 |
| 未开奖期仍显示「中/对/错」 | 判定只看候选命中，没有先判 `isOpened` | 未开奖一律不输出判定，也不高亮 |
| 命中却没有黄底 | 高亮条件与判定用了两个不同的数据源（本地复算 vs 接口 `is_correct`） | 判定与高亮必须来自**同一套口径**：一般情况下以接口 `is_correct` 为准；当接口口径与**面板展示的候选**不一致时（【天地+②肖】、以及五之十五的【吉美丑凶】【③肖防③码】【前后中特】），由面板本地复算，判定与标黄同时改用本地值 |
| 全场都是同一个分组（全左肖/全阳肖…） | 生成侧每期只输出一个标签 + 没有相邻期约束 | 把该 mode 加入 `THREE_PERIOD_UNIQUE_MODE_IDS`，并保证候选标签能枚举出两组 |
| 号码集合类每期前几位固定 | 不是轮转问题，是「热度排名」被跨站/跨期重复计数钉死（见「五之五」） | 加入 `UNORDERED_NUMBER_SET_MODE_IDS`（停用位置轮转 + 一次性展示置换） |
| 分组说明少一组 | 前端只按「本期恰好抽到哪组」拼说明；或 `fixed_data` 该行被停用 | 用固定分组兜底 + 打开 `fixed_data.status` |
| 页面出现 `["` `"]` | JS 直接 `d.content.split(',')` 或 `print` 了原始 JSON | 改用 `safeParseJSON` / 正确解析后取标签 |
| 整块模块空白 + JS 报错 | `JSON.parse` 遇到非 JSON 的 content 抛错 | 用 `safeParseJSON` 兜底，并给出兜底渲染分支 |
| 判定恒「对」或恒「错」 | 判定字段取错（拿码串比生肖）、`content_parser` 认不出正文标签（如波色）、候选集为空 | 用 `audit-verdict-truth.py` 对生产库复算，先定位是数据、映射还是渲染问题 |
| 某个生肖命中却判「错」/不标黄 | 「从文本里抽生肖」的字符类只写了繁体（`龍`）没写简体（`龙`），候选集合静默少一个 | 统一用 `predict.common.ZODIAC_CHAR_CLASS`（简体+繁体齐全），单测必须覆盖简体「龙」（见五之十六） |
| 分组类玩法某个生肖永远判「错」 | 分组正文/`fixed_data` 里的生肖是**错别字**（`文肖|鼠,免,龙,…` 的「免」= 兔） | 分组成员用 `normalize_zodiac_member()` 归一（只替换单字成员，别动自由文本）；前端同类渲染器同步（见五之十七） |
| 同一批派生行（一肖/二肖…）判定一模一样 | 派生行共用了数据源模块的整份判定 + 行宽按行号推 | 行宽由行名决定、判定逐行按本行展示的候选复算、只点亮命中的那一项（见五之十六） |
| 高亮文件名没变导致改动不生效 | bundle 站点文件名是内容哈希且长缓存 | 必须 `--rebuild --apply` 重建（文件名会变） |
