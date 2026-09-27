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
这类标题行里的「中」会被误判成判定。

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
| shengshi8800 | 440 | 0 | 3 | R5×2 + R8×1（八肖中特 6 期全准，8/12 命中率下属正常波动） |
| twcaibawang | 292 | 0 | 2 | R5×2 |
| twsaimahui | 652 | 0 | 22 | R5×15 + R8×7；R8 中 `.box.l23`（10码中特全错）仍是**待查实缺陷**；`#hao012`（六肖三码全错）已于 2026-09-28 修复，见本表下方「#hao012 修复记录」 |
| twjinniu | 469 | 0 | 2 | R5×1 + R8×1 |
| twcf888 | 451 | 0 | 3 | R8×3（均需人工判定真伪） |
| twssz | 289 | 0 | 98 | R4 较多，属基线 |
| twbst528 | 468 | 0 | 2 | |
| twjsz666 | 276 | 0 | 26 | |
| twwanli | 202 | 0 | 0 | 参考实现 |
| twsyw | 545 | 0 | 0 | 参考实现 |

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

## 五之三、R8 告警的正确用法


R8（某模块 ≥5 期已开奖行判定全同）**只是提示**，必须人工判定属于哪一类：

1. **正常**：候选集本来就大（八肖中特 8/12、稳杀10码、绝杀七码等），连对/连错在概率内；
   用独立重算验证每期确实算对即可（例：twsaimahui `.box.l45` 绝杀七码 9 期「准」，特码均不在杀号集合内）。
2. **缺陷**：候选集退化成固定前缀/空集、判定口径写死、`is_correct` 恒真或恒假。
   典型证据是「每期展示值前面挂着同一段」或「连错期数远超概率」。

---

## 六、常见根因速查

| 现象 | 常见根因 | 处理 |
| --- | --- | --- |
| 「错」的期仍有黄底 | 高亮取自供应商静态 HTML 的命中标记；或整行/整模块共用一个命中状态 | 高亮条件必须与本期判定绑定；渲染前先清除旧高亮 |
| 某一期 `开:？00错` | 模块在找不到开奖号码对应项时用了占位串 | 固定显示本期真实特码，判定照常 |
| 全场都是同一个分组（全左肖/全阳肖…） | 生成侧每期只输出一个标签 + 没有相邻期约束 | 把该 mode 加入 `THREE_PERIOD_UNIQUE_MODE_IDS`，并保证候选标签能枚举出两组 |
| 分组说明少一组 | 前端只按「本期恰好抽到哪组」拼说明；或 `fixed_data` 该行被停用 | 用固定分组兜底 + 打开 `fixed_data.status` |
| 页面出现 `["` `"]` | JS 直接 `d.content.split(',')` 或 `print` 了原始 JSON | 改用 `safeParseJSON` / 正确解析后取标签 |
| 整块模块空白 + JS 报错 | `JSON.parse` 遇到非 JSON 的 content 抛错 | 用 `safeParseJSON` 兜底，并给出兜底渲染分支 |
| 高亮文件名没变导致改动不生效 | bundle 站点文件名是内容哈希且长缓存 | 必须 `--rebuild --apply` 重建（文件名会变） |
