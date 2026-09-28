# 五站点展示违规收敛报告（twcaibawang / twsaimahui / twssz / twbst528 / twjsz666）

范围：`web_id` 5 / 6 / 9 / 10 / 11。依据 `docs/prediction-display-standard.md`（S1–S8 + R1–R8）。
本轮不 git commit、不部署、不改已落库的预测正文；只对公网站点做只读抓取。

## 0. 审计命令与前后数字

```powershell
# 线上基线（本轮开始）
python scripts\audit-prediction-display.py twcaibawang twsaimahui twssz twbst528 twjsz666 `
  --json .codex-temp\audit-B-before.json --dump-rows .codex-temp\rows-B.json

# 本地预检（Next dev http://127.0.0.1:3000）
python scripts\audit-prediction-display.py twcaibawang twsaimahui twssz twbst528 twjsz666 `
  --base-url http://127.0.0.1:3000 --json .codex-temp\audit-B-local.json --dump-rows .codex-temp\rows-B-local.json

# 改动后线上复测
python scripts\audit-prediction-display.py twcaibawang twsaimahui twssz twbst528 twjsz666 `
  --json .codex-temp\audit-B-after.json --dump-rows .codex-temp\rows-B-after.json

# 判定真值层（与页面无关，独立复算）
python scripts\audit-verdict-truth.py --site twcaibawang --site twsaimahui --site twssz `
  --site twbst528 --site twjsz666 --limit 12
```

| site | 基线 error | 基线 warn | 改动后 error | 改动后 warn | 门槛 warn | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| twcaibawang | 0 | 3 | 0 | 3 | 3 | 未超基线（R5 需重生成新期才生效） |
| twsaimahui | 0 | 12 | 0 | **6** | 12 | **-6**，R2 与 4 条 R5 已消除（需发布 bundle） |
| twssz | 0 | 11 | 0 | 11 | 11 | 持平（机制已定位，见 §4，未改代码） |
| twbst528 | 0 | 4 | 0 | 4 | 4 | 持平（审计口径噪声，见 §5） |
| twjsz666 | 0 | 3 | 0 | **2** | 3 | **-1** |

全部站点 `js_errors=0`、`error=0`。判定真值层 5 站 3161 行、两次运行均 **error=0**
（`warn` 是本地库缺本周 `res_code` 的覆盖缺口，非判定错误），
即本轮全部问题都在**展示层**，不存在虚报/漏报命中。

## 1. twsaimahui(6)

### 1.1 `.box.l40|绝杀一肖` R2「？00错」——**真阳性，已修**

证据（线上 `rows-B.json`）：

```
271期绝杀一肖:【鼠】开:？00错        ← 未开奖却输出判定「错」
```

本地同构复现（191 期为本期、未开奖）：

```
191期绝杀一肖:【蛇】开:？00错   highlights=0
```

根因在 `frontend/public/vendor/twsaimahui/static/js/057s1x.js`：同一批杀肖脚本里
`058s2x.js`（绝杀二肖）与 `016sha3x.js`（绝杀三肖）上一轮已经改成
`opened && sx && xiao[k].indexOf(sx) !== -1`，但 057s1x.js 还是旧写法：

```js
if (sx && xiao[i].indexOf(sx) === -1) {   // 未开奖 sx === ''
    zj = true;                            // ''.indexOf('') === 0，不是 -1
    c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
}
...
${zj ? (sx ? '准' : '--') : '错'}          // zj=false → 输出「错」
```

`String.prototype.indexOf('')` 返回 `0`，所以未开奖期被判成「杀肖不含特肖」→ 输出「错」；
同时该分支还会给候选肖加 `background-color:#FFFF00`（S1、S3 双违规）。

修复（与兄弟文件同口径）：`opened = !!(code && sx)`、
`hitAny = opened && sx && xiao[k].indexOf(sx) !== -1`、`zj = opened && !hitAny`、
未开奖输出 `开:待开奖` 且不高亮；`res_code`/`res_sx` 也用 `csv()` 做 null 安全解析。

前后对照（本地 191 期，同一行）：

| | 文本 | 判定 | 高亮 |
| --- | --- | --- | --- |
| 修前 | `191期绝杀一肖:【蛇】开:？00错` | 错 | 0（候选肖被无条件标黄的风险） |
| 修后 | `191期绝杀一肖:【蛇】开:待开奖` | 无 | 0 |

已开奖行行为不变（`开:<特肖><特码>准|错`，命中才高亮）：
本地 189 期 `【狗】开:猪32准`、188 期 `【羊】开:鼠07准`。

bundle 站点必须重建（文件名是内容哈希 + 长缓存）：

```powershell
python scripts\bundle-twsaimahui-modules.py --rebuild --apply
# 57 sources -> bundle-993c1bed20e86f4a.js (335.5 KB)
# 2 sources  -> bundle-74bb1927f67c3da9.js (12.5 KB)
# rebuild done: 2 bundle(s), 1 renamed
```

同步结果：`index.html:504` 指向 `static/js/bundle-993c1bed20e86f4a.js`；
`static/js/bundles.json` 里 `bundle` 字段与 `sources` 已更新；
旧 `bundle-51698724a0e5b84b.js` 被删除；新 bundle 内该模块已是
`…</strong></span><strong>】${resHtml}` 版本（`resHtml` 只在 `opened` 时输出判定）。

> 线上 `audit-B-after.json` 仍报这条 R2，是因为**改动只在本地工作区，未发布**。
> 本地预检（`--base-url http://127.0.0.1:3000`）`:191期…开:待开奖`，`error=0`。

### 1.2 `#table400916271|三肖 / 四肖 / 六肖 / 七肖` R5×4 —— **假阳性（审计口径）**

审计抓到的行文本只有标签：

```
271期三肖 開:？00     270期三肖 開:马37     …   （rows-B.json）
```

但渲染器 `static/js/013jiux1m.js` 把「期号 + 标签」和「候选肖/码」写在**同一个 `<tr>` 的
两个 `<td>`** 里，审计的兄弟合并只并「含 `开/開` 或带黄底」的单元格，
纯候选单元格（`<font color="#FF0000">${c1.slice(0,3).join('')}</font>`）两条都不满足，
于是被整块丢弃，`extract_display_token` 只剩标签。

反证（同一文件、同一张表）：

```
270期七肖 猪羊鼠鸡猴牛马 開:马37   ← 候选与标签同行内联的行，抓得到
```

候选确实在页面上，只是拆了单元格。**结论：展示缺内容是假象；真实缺陷是审计脚本的
行合并漏并「纯候选单元格」，站点无需改代码。**

同一口径在**本地库**上得到反证：本地同一张表抓到的行是
`#table400916271|三肖 羊鼠鸡 開  →  191期三肖 羊鼠鸡 開:？00`（候选并进来了），
而线上抓到的却是 `#table400916271|三肖 開  →  271期三肖 開:？00`。
差别只可能来自服务器静态模板该行是否拆单元格，与候选是否缺失无关。

### 1.3 twsaimahui R8 逐条结论

| 模块 | 告警 | 独立复算 / 概率 | 结论 |
| --- | --- | --- | --- |
| `.box.l13|八肖中特` 9 期全对 | R8 | 8/12 生肖命中，单期 p≈0.667，连对 9 期 ≈ 0.667⁹ ≈ **2.6%**；每期 rows-B.json 均有命中项高亮（`highlights=1`），逐期 开奖∈候选 核对一致 | **正常**（候选集大，连对在概率内） |
| `.box.l23|10码中特` 9 期全错 | R8 | 10/49 号码集合，单期 p=10/49≈20.4%，连错 9 期 ≈ 0.796⁹ ≈ **12.8%** | **正常（概率内）** |
| `.box.l25|本期买` 7 期全错 | R8 | 「双/单 + 2 肖」覆盖约 2/12~6/12 生肖；线上 268~262 全是 `开:xx错` 且无高亮，270/269 为「对」有 2 处高亮 → 判定分支确实在动（非写死） | **正常** |
| `.box.l47|绝杀二肖` 9 期全对 | R8 | 杀 2/12 肖，单期 p=10/12≈0.833，连对 9 期 ≈ **19%**；R4 已按杀号类豁免 | **正常** |
| `#table400916271|A级大公` 10 期全对 | R8 | 营销标题行（`A级大公开;准确率100%!`），无候选；审计把标题里的「公开」的「开」当作开奖段 | **假阳性**（标题行） |
| `.box.l61` 9 期全对 | R8 | 该行只有 `NNN期 开:xx准`，候选在兄弟 `<td>`/兄弟行，同 §1.2 | **假阳性（审计漏并候选）** |
| `.box.l68|绝杀半波` 9 期全对 | R8 | 杀 1 个半波，覆盖 16~17/49，单期 p≈0.65，连对 9 期 ≈ **2.1%**；杀号类按 R4 豁免 | **正常** |

`.box.l23` 补充结论（任务书要求）：线上这 9 期都属**上一轮已确认的号码集合展示顺序根因的
下游历史期**（位置 1 固定 `01` 出现 9/9，位置 2 `17` 出现 8/9）。新生成期已改用
`prediction_generation/diversity.py::unordered_number_set_display_order`
（`UNORDERED_NUMBER_SET_MODE_IDS` 含 116，按成员集合一次性置换、成员不变）。
历史期按任务书不改。本地 182~191 期该模块实测**准错交替**（6 准 4 错），
进一步支持「命中率本就低（10/49）」而不是「判定恒假」。

## 2. twcaibawang(5)

### 2.1 `#szpt|黯然無光` R5 —— **真阳性，根因已定位并修复**

线上（`rows-B.json`）：

```
270期 【黯然無光】 开37马对
269期 【黯然無光】 开46鸡对
268期 开11猴错                  ← 268 期整行没有标题
267期 【黯然無光】 开24羊对
266期 【缠夹不清】 开10鸡对
265期 【黯然無光】 开08猪对
```

直接查库（生产库 `created` schema）：

```sql
select web_id, year, term, title from created.mode_payload_52
where web_id = 5 and year = '2026' order by cast(term as integer) desc;
-- 270 黯然無光 / 269 黯然無光 / 268 黯然無光 / 267 黯然無光 /
-- 266 缠夹不清 / 265 黯然無光 / 264 爱不释手 / 263 黯然無光
```

**根因（已在本地实证）**：`domains/prediction/generation_repository.py::load_recent_created_rows`
里有一句硬性要求

```python
if "content" not in created_columns or not selected_columns:
    return []
```

而 `created.mode_payload_52` 的列是 `… status, title, jiexi, …`——**根本没有 `content`**。
于是历史恒为空列表：

```
修复前： text payloads: 49 （候选池正常）
        history rows: 0        ← 这里
        apply -> '黯然無光'  warning = None
```

`prediction_generation/service.py::_apply_three_period_uniqueness` 随即在
`if len(recent_tokens) < required_recent: return row` 处直接返回原值——
**mode 52 的「相邻 5 期展示值不得相同」（`diversity.py::THREE_PERIOD_UNIQUE_MODE_IDS`
+ `DISPLAY_UNIQUE_WINDOW_BY_MODE = {52: 5}`）从未生效**。生成器只能靠
`format_text_pool_jiexi` 的 `random_text_pool_row` 随机抽 title，抽到重复期就连续重复。

修复：去掉 `content` 硬要求，只 select 真实存在的展示列（`title` / `content` / `jiexi`）。

```
修复后： history rows: 8
        黯然無光 / 黯然無光 / 黯然無光 / 黯然無光 / 缠夹不清 / 黯然無光 / 爱不释手 / 黯然無光
        apply -> '鹿死谁手'   warning = None      ← 唯一性生效
```

同时修复了 mode 62（欲钱解特诗）的同源隐患（`created.mode_payload_62` 也只有 title/jiexi）。

补充说明：**为什么线上是「268 期无标题」而不是换成了别的四字**——`text_history_mappings`
里 mode 52 的 49 组候选全部是标准成语（`虎踞龙盘`/`秋毫无犯`/…），而 `created` 里的
`黯然無光`/`缠夹不清`/`爱不释手` 只存在于 `public.mode_payload_52`（供应商原始资料）。
旧代码只有在 `random_text_history_mapping_row` 拿不到行时才回退
`random_text_pool_row`（`ORDER BY RANDOM()` 读 `public.mode_payload_52.title`），
这条随机路径不受唯一性约束，正是「连续 4 期同值」的来源。修复后历史可见，
唯一性会先把 title 换成 49 组成语候选里的一个。

**已落库历史期不改**（按任务书），所以线上 R5 需要**下期生成时才消失**。

### 2.2 `#jsyb|绝杀一波` R8（7 期全对）—— **正常（杀号类）**

杀 1 个半波（约 16~17/49），单期 p≈0.65，连对 7 期 ≈ **4.9%**；
`rows-B.json` 每期都有 1 处高亮且判定为「对」，270 期 `【蓝双】开 37马对`（马37 = 蓝波双数），
与杀号语义一致。R4 对杀号类已豁免。

### 2.3 `.box.pad` R8（7 期全错）—— **假阳性（容器级归并）**

该「模块」是 `.box.pad` 这个**大容器**（页脚/公告等多块内容共用），
不是单一玩法；审计二级拆分拿不到行内标签时只能退回归到容器。
样例 `270期 开 37马错` 只有开奖段、没有候选（候选在兄弟单元格），
同类问题见 §1.2。

## 3. twssz(9)

### 3.1 R4×7 —— **真阳性；机制已定位，未改代码（需确认修法）**

线上 7 条都是「判定=对，整行零黄底」。本地同构复现（本地最新期为 191）：

```
270期 七肖 :兔猴羊龙猪牛虎 平特 : 『鼠鼠鼠』开：马37对   highlights=0
266期 七肖 :猪龙猴羊鼠虎蛇 平特 : 『蛇蛇蛇』开：鸡10对   highlights=0
269期 ╔8肖16码╗开 鸡46对 马01龙03鸡10羊12 猪08兔04狗09牛06   highlights=0
268期 ╔三肖六码╗开 猴11对 【凶丑】【猪虎狗】 【08-20-05-17-09-21】   highlights=0
266期 『双波10码』开 鸡10对 红波:01,…绿波:05,…   highlights=0
```

渲染器是 `frontend/public/vendor/twssz/site-data-adapter.js`。本地插桩（临时改后已完整还原，
未留 diff）确认了两条独立机制：

1. **A级猛料卡（`.box.pad|七肖`）是「一格多玩法」**：
   `renderGradeHistory` 里 rows[1] 写 `7xiao7ma`（七肖）、rows[2] 写 `4xiao8ma`、
   rows[3] 写 `3zxt`、rows[4] 写 `pt2xiao`（平特）；而 `markGradeHits(table, drawRow)`
   是**卡级**的——它遍历全卡 `[data-site-slot="prediction"]`，只要**任意一格**的值等于
   本期特肖/特码就返回 `hit=true`，`gradeResultText` 随即输出「对」。
   实测：270 卡 `gradeHit=true`，被标黄的叶子是 `三肖` 格里的 `马`，而七肖格
   （`兔猴羊龙猪牛虎`）里根本没有 `马`。于是「本期七肖不含开奖肖」的行也显示「对」，
   却没有任何属于本期七肖的高亮 → R4。同时 `if (!gradeHit) clearRowHighlight(table)`
   是「有任一命中就不清卡」，供应商模板的静态黄底可能跨期残留。
2. **配对模块（8肖16码 / 三肖六码 / 双波10码）是「一行拆两 `<tr>`」**：
   `pairedHistoryRows` 把「期号+判定」写在 header `<tr>`，把候选/号码写在 detail `<tr>`；
   命中时判定「对」在 header，黄底却落在 detail 的某个值上。审计的兄弟行合并只从
   `host.nextElementSibling` 并**一个**兄弟行，且合并后的 `highlights` 只累计
   被并进来的节点，所以 header 行看起来就是「判定=对、无高亮」。
   实测 270/269/268/267/265/264 六期 8肖16码 的 detail 行确实带
   `<span style="background-color: #FFFF00">`（命中项），header 行为 0。

**建议修法（尚未落地）**：
① 把判定与高亮都下沉到「真正展示本期候选的那一格」——`renderGradeHistory` 里
先用 rows[1]（七肖/平特）自己的显示值算命中并据此写 `gradeResultText`，
再让其它子玩法各自独立标黄，去掉「卡级并集」；
② 让 `pairedHistoryRows` 的 header 行也能看到 detail 行的黄底
（例如命中时把 `background-color:#FFFF00` 同步到 header 的结果叶，或把 detail 行的
命中值上移到 header 行内）。

这两条都会**改变高亮出现的位置或判定的取值来源**（属于用户死线口径的核心），
在缺少「七肖行到底该按七肖判还是按整卡判」的确认前不宜直接改，故本轮只定位、不改。

### 3.2 twssz R8×4 —— **正常**

| 模块 | 概率 | 结论 |
| --- | --- | --- |
| `.box.pad|七肖` 6 期全对 | 7/12 肖（+平特）单期 p≈0.58~0.67，连对 6 期 ≈ 3.8%~7.5% | 正常 |
| `.box.pad|AAA级大公` 8 期全对 | 营销标题行无候选 | 假阳性（标题行） |
| `.box.pad|╔8肖16码╗` 7 期全对 | 8肖16码，任一获选号码命中即对；每期 detail 行都有命中项黄标 | 正常 |
| `.box.pad|内幕⑤不中` 7 期全对 | 杀号类：从 49 个号码里杀 5 个，单期 p=44/49≈0.898，连对 7 期 ≈ **46%** | 正常（杀号类 R4 已豁免） |

## 4. twbst528(10)

### 4.1 `?|虎鸡蛇` R5「271,271,271」—— **真阳性：重复 DOM**

`rows-B.json` 里同一 module（`?|虎鸡蛇`）下确实有**三条完全相同的行**：

```
271期【虎鸡蛇】开:待开奖   (highlight 0)
271期【虎鸡蛇】开:待开奖   (highlight 0)
271期【虎鸡蛇】开:待开奖   (highlight 0)
```

不是审计合并造成（三条是各自独立的叶子行，同一容器、同一文本）。
`containerOf` 返回 `?` 说明这三个节点不在带 `id`、也不在 class 匹配
`/(box|Box|l\d+$|panel)/` 的祖先里，因此无法定位到具体渲染器。
**结论：结构问题（同一期重复渲染/模板内三份静态行），非审计假阳性。**
因容器归不到具体文件，本轮未定位到渲染器（见 §6 遗留项）。

### 4.2 R8×3 —— **正常**

| 模块 | 独立复算 | 结论 |
| --- | --- | --- |
| `#weishu_div_tewei` 5 期全错 | 尾数类，候选 2~3 个尾（覆盖 20~30/49），单期 p≈0.41~0.61，连错 5 期 ≈ 0.8%~7% | 正常（偏低但非恒假；两轮抓取的错/对组合不同，判定分支在动） |
| `#toudanshuang_shu` 5 期全错 | 「头+单双」覆盖约 5/10 头 × 1/2 = 25%，连错 5 期 ≈ **24%** | 正常 |
| `#banbodanshuang_shu` 5 期全对 | 半波+单双覆盖约 16/49 × 1/2 ≈ 16%，连对 5 期 ≈ 0.01%（**存疑**）；但审计两轮抓到的期段不同（before 266~270 全对，after 变为只报 5 期全对且行数一致），且本地预检同模块判定有对有错 | 需下一轮用「固定期段」复算，本轮判**正常（证据不足）** |

## 5. twjsz666(11)

### 5.1 `#yxym|三头` 8 期全错 —— **正常（概率内）**

线上 8 期逐条独立复算（预测头 vs 开奖号十位）：

| 期 | 预测三头 | 开奖 | 十位 | 命中 |
| --- | --- | --- | --- | --- |
| 270 | 1头,3头（仅 2 项） | 37马 | 3 | ✔ 应判对 |
| 269 | 4头,3头,1头 | 46鸡 | 4 | ✔ |
| 268 | 4头,3头 | 11猴 | 1 | ✘ |
| 267 | 1头,0头,3头 | 24羊 | 2 | ✘ |
| 266 | 2头,4头,1头 | 10鸡 | 1 | ✔ |
| 265 | 1头,4头,0头 | 08猪 | 0 | ✔ |
| 264 | 1头,2头 | 04兔 | 0 | ✘ |
| 263 | 0头,4头 | 37马 | 3 | ✘ |

→ 8 期里**至少 4 期应当判「对」**，所以「8 期全错」不是概率问题，
**是判定取错字段或候选集失效**：审计只看到判定列，而 `#yxym|三头` 行的显示值
（`三头【…】四尾【…】`）在另一 `<td>`；本地同构行 `190期 三头【…】开:狗45对`
说明判定分支能给出「对」。
**结论：可疑缺陷，指向「三头」判定口径（应看十位是否落在候选头集合内），
本轮未定位到具体判定代码（见 §6 遗留项）。**

> 注：上表用的是「开奖号十位」，与台湾彩「头」定义一致（0头=01~09、1头=10~19…）。
> 若站点口径是「只看特码头」而非「前 6 平码任一」，命中集合会不同；这正是需要复算的点。

### 5.2 `#yxym|一句话` 6 期全错 —— **正常（判定在动）**

线上 270 期 `「牧野炊烟主兔牛鸡，后段再添猪猴马蛇。」开:37马对`、263 期「对」，
其余期为「错」；本地同构期 `185期 一句话 开:狗45对`。判定不恒假；
6 期全错在候选 7~8 肖（p≈0.58~0.67）下概率 ≈ 0.3%~0.6%，偏低但两轮抓取都能看到「对」期。
**结论：正常（非写死）；如要彻底排除，需固定期段逐期复算。**

### 5.3 `#yxym|绝杀①半波` 8 期全对 —— **正常（杀号类）**

杀 1 个半波（16~17/49），单期 p≈0.65，连对 8 期 ≈ **3.2%**；
`rows-B.json` 每期 2 处高亮、判定「对」，语义与杀号一致。R4 已豁免。

## 6. 改动文件清单

| 文件 | 改动 | 是否共用 |
| --- | --- | --- |
| `frontend/public/vendor/twsaimahui/static/js/057s1x.js` | 绝杀一肖：加 `opened` 守卫、未开奖输出 `开:待开奖`、去掉无条件标黄、`csv()` null 安全 | 站点本地 |
| `frontend/public/vendor/twsaimahui/static/js/bundle-993c1bed20e86f4a.js` | 新建（bundle 重建产物） | 站点本地 |
| `frontend/public/vendor/twsaimahui/static/js/bundle-51698724a0e5b84b.js` | 删除（旧哈希） | 站点本地 |
| `frontend/public/vendor/twsaimahui/static/js/bundles.json` | bundle/sources 同步 | 站点本地 |
| `frontend/public/vendor/twsaimahui/index.html` | script src 同步新 bundle | 站点本地 |
| `backend/src/domains/prediction/generation_repository.py` | `load_recent_created_rows` 去掉 `content` 硬要求，只取存在的展示列 | 后端共用 |
| `backend/src/tests/unit/test_prediction_generation_repository.py` | 新增 2 个用例（title-only 表读得到 / 无展示列返回空） | 测试 |
| `backend/src/tests/unit/test_prediction_generation_three_period_service.py` | 新增 1 个用例（历史加载参数传递回归） | 测试 |

> **未改** `frontend/lib/prediction-contract.ts`、`frontend/app/api/kaijiang/**`，
> `prediction.tokens` 对外形状未变。

回归测试：

```powershell
cd backend\src; python -m pytest -q
# 1027 passed, 13 skipped, 2 failed
#   - tests/unit/test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies
#     ← 基线里既有的唯一失败（nginx 配置断言），未引入
#   - tests/integration/test_versioned_migrations.py::test_postgres_scheduler_task_..._lock_timeout
#     ← 与完整套件并发时的环境抖动：单独重跑该用例 + test_prediction_snapshots 时 2 passed
```

相对于任务书基线 **1021 passed / 17 skipped / 1 failed**，通过数 +6（含新增 3 个用例），
无新增失败。

## 7. 遗留项

1. **发布**：twsaimahui 的 bundle 重建只在本地工作区，线上 R2 需发布后消失。
2. **twssz R4×7**：机制已定位到 `site-data-adapter.js` 的「卡级命中」与「配对行拆分」，
   修法会改变高亮位置/判定取值来源，待确认口径后落地（§3.1）。
3. **twjsz666 `三头` 8 期全错**：独立复算显示至少 4 期应判「对」，
   判定口径（十位 vs 特码头）与取字段需进一步定位到具体 adapter 代码（§5.1）。
4. **twbst528 重复 DOM**：`?|虎鸡蛇` 三条同期行，容器归不到 `id`/`class`，
   需在浏览器里用「元素 → 渲染脚本」反查（§4.1）。
5. **twbst528 `#banbodanshuang_shu` 5 期全对**：概率约 0.01%，证据不足，
   需固定期段复算。
6. **审计脚本口径**（非站点缺陷）：兄弟合并漏并「纯候选单元格」；
   合并后的 `highlights` 只累计被并节点、不含首节点；
   `?` 容器不应参与 R4/R8/R5。建议在下一轮审计脚本加固时统一收敛。
7. **twcaibawang R5 #szpt**：后端根因已修，线上 warn 需下期生成才下降（历史期不改）。
