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

## 五之二、基线数字（2026-09-27 整改后，用于「warn 不得增加」的对比）

线上 `audit-prediction-display.py`（口径：计算样式+字面量双判高亮、verdict 取最右判定字、R5 只算预测行、
R8 统一性告警）：

| site | rows | error | warn | 备注 |
| --- | ---: | ---: | ---: | --- |
| shengshi8800 | 440 | 0 | 11 | R4×4（`#yxym`/`#top_xiao_code` 类「准但无高亮」）+ R5×6 + R8×1 |
| twcaibawang | 292 | 0 | 8 | R5×5 + R8×3（均需人工判定真伪） |
| twsaimahui | 652 | 0 | 35 | R4×10（`A级大公开` 营销行）+ R5×18 + R8×7；`.box.l23`（10码中特全错）属号码集合展示顺序问题的**下游现象**，见「五之五」 |
| twjinniu | 469 | 0 | 1 | R4×1（`一肖一码`，站点按产品要求「不中不显示对错」） |
| twcf888 | 451 | 0 | 19 | R4×6（平特/绝杀类命中项无高亮）+ R5 |
| twssz | 289 | 0 | 52 | R4 较多，属基线 |
| twbst528 | 468 | 0 | 74 | R4×70，属基线 |
| twjsz666 | 276 | 0 | 9 | R5×9 |
| twwanli | 202 | 0 | 1 | R5×1 |
| twsyw | 545 | 0 | 7 | R4×7（`#top_xiao_code` 命中行无高亮） |

> 上表是 **2026-09-28 `641dfe9` 发布后**的线上实测（`python scripts\audit-prediction-display.py --json ...`）：
> **10/10 站点 `error=0`、`js_errors=0`**，共 4084 行、217 条 warn（全为 R4/R5/R8）。
> 同批生产判定真值校验（`scripts/audit-verdict-truth.py` 对生产库）`rows=22039 error=0`。
> 更早一轮的 warn 数字（shengshi8800=3、twssz=98 等）是用**较弱的行切分/判定口径**测出来的，
> 与上表不可直接比较——这正是「warn 不得增加」要按同口径对比的原因。


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

## 六、常见根因速查

| 现象 | 常见根因 | 处理 |
| --- | --- | --- |
| 「错」的期仍有黄底 | 高亮取自供应商静态 HTML 的命中标记；或整行/整模块共用一个命中状态；或「一期」被拆成多个单元格/相邻 `<tr>`，只改了其中一块 | 高亮条件必须与本期判定绑定；渲染前先清除旧高亮；审计脚本会把同辈/相邻行合并后再判 |
| 某一期 `开:？00错` | 模块在找不到开奖号码对应项时用了占位串 | 固定显示本期真实特码，判定照常 |
| 未开奖期仍显示「中/对/错」 | 判定只看候选命中，没有先判 `isOpened` | 未开奖一律不输出判定，也不高亮 |
| 命中却没有黄底 | 高亮条件与判定用了两个不同的数据源（本地复算 vs 接口 `is_correct`） | 统一以接口 `is_correct` 为准 |
| 全场都是同一个分组（全左肖/全阳肖…） | 生成侧每期只输出一个标签 + 没有相邻期约束 | 把该 mode 加入 `THREE_PERIOD_UNIQUE_MODE_IDS`，并保证候选标签能枚举出两组 |
| 号码集合类每期前几位固定 | 不是轮转问题，是「热度排名」被跨站/跨期重复计数钉死（见「五之五」） | 加入 `UNORDERED_NUMBER_SET_MODE_IDS`（停用位置轮转 + 一次性展示置换） |
| 分组说明少一组 | 前端只按「本期恰好抽到哪组」拼说明；或 `fixed_data` 该行被停用 | 用固定分组兜底 + 打开 `fixed_data.status` |
| 页面出现 `["` `"]` | JS 直接 `d.content.split(',')` 或 `print` 了原始 JSON | 改用 `safeParseJSON` / 正确解析后取标签 |
| 整块模块空白 + JS 报错 | `JSON.parse` 遇到非 JSON 的 content 抛错 | 用 `safeParseJSON` 兜底，并给出兜底渲染分支 |
| 判定恒「对」或恒「错」 | 判定字段取错（拿码串比生肖）、`content_parser` 认不出正文标签（如波色）、候选集为空 | 用 `audit-verdict-truth.py` 对生产库复算，先定位是数据、映射还是渲染问题 |
| 高亮文件名没变导致改动不生效 | bundle 站点文件名是内容哈希且长缓存 | 必须 `--rebuild --apply` 重建（文件名会变） |
