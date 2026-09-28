# twssz（web_id 9 / https://www.twssz.com/twssz）预测模块展示整改报告

- 范围：twssz 单站（`frontend/public/vendor/twssz/index.html`、`frontend/public/vendor/twssz/site-data-adapter.js`）
- 规范依据：`docs/prediction-display-standard.md`（S1–S8 + R1–R8）
- 未改共用文件（`frontend/app/api/kaijiang/[[...path]]/route.ts`、`frontend/lib/prediction-contract.ts`、
  `frontend/public/vendor/_shared/**`），`prediction.tokens` 对外形状不变；未改 `backend/src/**`。
- 未 git commit、未部署、未改已落库预测数据。

---

## 一、需求 1：全部模块文字居中 + 只允许命中项标黄

### 1.1 改动文件与关键 diff

**A. `frontend/public/vendor/twssz/index.html`**

1. `<head>` 末尾新增展示规范样式表 `<style id="twssz-prediction-display-standard">`（改动主体）：

```css
[data-prediction-section], [data-prediction-section] *,
[data-prediction-row],     [data-prediction-row] *,
[data-prediction-center],  [data-prediction-center] *,
.dz_content08ab2d, .dz_content08ab2d *,
.contentbox_01 .bbzhong122, .contentbox_01 .bbzhong122 *,
.contentbox_01 .bizhong1,   .contentbox_01 .bizhong1 *,
#con_jihuadanshuang50000ww_1, #con_jihuadanshuang50000ww_1 *,
#con_jihuadanshuang50000ww_2, #con_jihuadanshuang50000ww_2 *,
#table1, #table1 * { text-align: center !important; }

/* A级猛料：改前 标题 10pt(13.33px) / 正文 12px；改后 标题 17px / 正文 16px */
[data-prediction-section="grade-a"] .dbt1, [data-prediction-section="grade-a"] .dbt1 span { font-size: 17px !important; }
[data-prediction-section="grade-a"] .dbt2, [data-prediction-section="grade-a"] .dbt2 span, [data-prediction-section="grade-a"] .dbt2 font,
[data-prediction-section="grade-a"] .dbt3, [data-prediction-section="grade-a"] .dbt3 span, [data-prediction-section="grade-a"] .dbt3 font { font-size: 16px !important; }
@media screen and (max-width: 480px) {   /* 375px：单列堆叠，保证放大后不换行、不溢出 */
  [data-prediction-section="grade-a"] table, tbody, tr, td { display: block; width: auto !important; box-sizing: border-box; }
  [data-prediction-section="grade-a"] table { border: 1px solid #000; }
  [data-prediction-section="grade-a"] td { border-bottom: 1px solid #ddd; }
}
```

> 说明：供应商模板里 40 处内联 `text-align: left`、大量 `<p align="center">`（UA 值 `-webkit-center`）
> 都靠 `!important` 覆盖；`[data-prediction-center]` 由适配层在渲染后给**真正包住预测模块的祖先
> 容器**（`.box.pad` / `.contentbox_01` / `.dz_content08ab2d` / `.Contentbox50000` / `#table1` …）
> 打标记，页脚（属性知识 / 免责声明）与图纸导航因为不含预测模块而完全不受影响。

2. 模块标题栏黄字去黄（19 处 `<font color="#FFFF00">…</font>` → `color="#FFFFFF"`，
   均位于蓝底标题条内，改后为白字蓝底，观感不变）；`.bbzhong122-tit { color:#ff0 }`、`.bizhong1-tit { color:#ff0 }`
   两处 CSS 改为 `#ffffff`。

**B. `frontend/public/vendor/twssz/site-data-adapter.js`**

| 位置 | 改动 |
| --- | --- |
| `COMPLETE_SECTION_MAPPINGS` | `pt1wei` / `pt1xiao` 增加 `hitScope:"drawn"`（平特类与整期 7 个开奖号码比）；`title_143` 增加 `mergeTokens:true`（兼容层把 `蓝波` 拆成 `蓝`+`波`，合并成一个波色候选） |
| 新增 `tokenNumberList` / `candidateHit` / `structuredCandidates` / `structuredHit` / `writeStructuredLine` | 逐项命中判定：`scope="special"` 与特码/特肖比，`scope="drawn"` 与整期号码/生肖比 |
| `renderStructuredHistory`（三头中特 / 平特一尾 / 平特一肖 / 综合资料 / 四肖中特 / 一波中特） | ① 删掉 `markHitLeaf(valueSlot, true)` 的**整行标黄**；② 改为「一个候选一个 span」，只有命中的那个 span 带黄底；③ 渲染前无条件 `clearRowHighlight(node)` 清掉供应商样例黄标；④ 新增「无元素子节点的值行」兜底（修一波中特最新一期整行空白） |
| 新增 `writeLeafValues` | 复用供应商既有叶子写值（保留红字/字号），只让等于命中项的叶子带黄底，并把 `必中二头：2,3` 的逗号补回叶子之外的文本节点 |
| `renderOneHeadHistory`（一头一码） | 先 `clearRowHighlight(card)` 清掉样例黄标与「空 span 黄底」；左侧头位按特码头逐项点亮，右侧 6 码按特码逐项点亮 |
| `renderAaaGradeHistory`（AAA级大公开） | **修 bug**：原来只在「判定为错」的期清样例黄标，命中的期会把**样例那一期的别的生肖**留在屏上（实测 269 期开鸡46 却高亮「羊」）。现在无条件先清，再按本期特肖点亮 |
| `renderDoubleWaveHistory`（双波10码） | 波色名与冒号分离：黄底只包 `蓝波`，冒号留在文本节点 |
| `renderFifteenCodeHistory`（15码中特） | 号码与点号分离：黄底只包 `10`，不再连尾随的 `.` 一起点亮 |
| `renderDanShuangHistory` / `renderAiForumHistory` | 写值前 `clearRowHighlight`，清掉供应商模板遗留的**空 span 黄底** |
| 新增 `markPredictionContainers` | 渲染结束后给预测内容的祖先容器打 `data-prediction-center="true"`（居中口径只覆盖真实预测容器） |
| 删除无引用的 `rowSummary` | 死代码 |

### 1.2 模块 → 计算样式 `text-align` 对照表（Playwright 实测）

- 视口 900×1200 与 375×900 **结果完全一致**：共 **52 个 `data-prediction-section` 模块，非居中 0 个**
  （改前：52 个模块中 51 个非居中）。
- 每个模块取至少 1 行（`data-prediction-row`）读 `getComputedStyle(row).textAlign`，全部为 `center`。

| 模块（data-prediction-section） | 容器 | 抽样行 | 行计算 text-align | 抽样行文本 |
| --- | --- | --- | --- | --- |
| `grade-a` | <DIV> | `TABLE` | **center** | 台湾 A级猛料大公开 270期 七肖 :兔猴羊龙猪牛虎 平特 : 『鼠鼠鼠』开：马37  |
| `sanxiao_siwei_xiao` | <DIV> | `TR` | **center** | 191期 开 待开奖 |
| `ma24` | <DIV> | `TD` | **center** | 39 |
| `title_66-0` | <DIV> | `DIV` | **center** | 台湾 15码中特 270期必中三尾：6-8-2 270期必中五尾：6-8-2-9-1 必 |
| `title_66-1` | <DIV> | `DIV` | **center** | 台湾 15码中特 269期必中三尾：0-9-5 269期必中五尾：0-9-5-6-2 必 |
| `title_66-2` | <DIV> | `DIV` | **center** | 台湾 15码中特 268期必中三尾：4-6-3 268期必中五尾：4-6-3-2-9 必 |
| `title_66-3` | <DIV> | `DIV` | **center** | 台湾 15码中特 267期必中三尾：0-6-9 267期必中五尾：0-6-9-3-2 必 |
| `title_66-4` | <DIV> | `DIV` | **center** | 台湾 15码中特 266期必中三尾：9-0-6 266期必中五尾：9-0-6-8-3 必 |
| `title_66-5` | <DIV> | `DIV` | **center** | 台湾 15码中特 265期必中三尾：1-7-6 265期必中五尾：1-7-6-9-4 必 |
| `title_66-6` | <DIV> | `DIV` | **center** | 台湾 15码中特 264期必中三尾：8-4-2 264期必中五尾：8-4-2-9-6 必 |
| `title_66-7` | <DIV> | `DIV` | **center** | 台湾 15码中特 263期必中三尾：2-6-9 263期必中五尾：2-6-9-5-8 必 |
| `daxiao` | <TABLE> | `TR` | **center** | 270期: 特码大小 【大大大】 开:马37对 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 270期 AAA级大公开;准确率绝对100%;大胆下注! 270期⑨肖中特:兔猴羊龙猪牛 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 269期 AAA级大公开;准确率绝对100%;大胆下注! 269期⑨肖中特:猴鸡龙羊猪蛇 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 268期 AAA级大公开;准确率绝对100%;大胆下注! 268期⑨肖中特:龙蛇猴鸡猪虎 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 267期 AAA级大公开;准确率绝对100%;大胆下注! 267期⑨肖中特:鸡羊猪鼠龙马 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 266期 AAA级大公开;准确率绝对100%;大胆下注! 266期⑨肖中特:猪龙猴羊鼠虎 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 265期 AAA级大公开;准确率绝对100%;大胆下注! 265期⑨肖中特:羊猪龙鸡兔狗 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 264期 AAA级大公开;准确率绝对100%;大胆下注! 264期⑨肖中特:鸡猪兔猴龙牛 |
| `aaa-grade` | <TABLE> | `TABLE` | **center** | 263期 AAA级大公开;准确率绝对100%;大胆下注! 263期⑨肖中特:猪蛇鸡羊猴鼠 |
| `title_48-ai` | <DIV> | `TR` | **center** | 270期 ＜嫩＞ 生肖:猴鸡兔龙猪牛 11.10.04.03.08.06.05.01 波 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 270期 【野兽+鼠猴】 开 马37对 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 269期 【野兽+猴鼠】 开 鸡46对 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 268期 【家禽+虎猪】 开 猴11对 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 267期 【家禽+牛鼠】 开 羊24错 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 266期 【野兽+蛇猴】 开 鸡10对 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 265期 【家禽+羊蛇】 开 猪08对 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 264期 【家禽+牛兔】 开 兔04对 |
| `pt2xiao` | <TABLE> | `TABLE` | **center** | 263期 【家禽+牛虎】 开 马37对 |
| `3tou-三头中特` | <DIV> | `TR` | **center** |  |
| `juesha2xiao` | <TABLE#table1> | `FONT` | **center** | 狗45错 |
| `juesha1wei` | <DIV> | `TR` | **center** | 9尾 琴棋书画 马37对 |
| `pt1wei-平特一尾` | <DIV> | `TR` | **center** | 270期 平特一尾：1尾 开：马37错 |
| `pt1xiao-平特一肖` | <DIV> | `TR` | **center** | 270期 平特一肖：龙 开：马37错 |
| `title_48` | <TABLE> | `TR` | **center** | 270期 ╔8肖16码╗开 马37对 |
| `wuzhong5ma` | <TABLE> | `TR` | **center** | 191期 『内幕⑤不中』开 待开奖 |
| `title_5` | <TABLE> | `TR` | **center** | 270期: 天地 【天肖+兔鸡】 开:马37错 |
| `juesha2xiao-steady` | <P> | `P` | **center** | 191期 绝杀二肖: 【虎猴】开:待开奖 |
| `3hang-综合资料` | <DIV> | `TR` | **center** | 270期 综合资料：金·土·木 开：马37错 |
| `pt3xiao` | <TABLE> | `TR` | **center** | 191期 ╔三肖六码╗开 待开奖 |
| `shuangbo` | <TABLE> | `TR` | **center** | 270期 『双波10码』开 马37对 |
| `title_47-四肖中特` | <DIV> | `TR` | **center** | 270期 四肖中特：牛·猴·鸡·龙 开：马37错 |
| `danshuangtema` | <DIV#con_jihuadanshuang50000ww_1> | `P` | **center** | 270期《双》马37错 |
| `title_143-一波中特` | <DIV#con_jihuadanshuang50000ww_2> | `P` | **center** | 191期 一波中特：蓝波 开：待开奖 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 270期必中一头：2 270期必中二头：2,3 270期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 269期必中一头：2 269期必中二头：2,0 269期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 268期必中一头：2 268期必中二头：2,3 268期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 267期必中一头：4 267期必中二头：4,3 267期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 266期必中一头：1 266期必中二头：1,0 266期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 265期必中一头：2 265期必中二头：2,4 265期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 264期必中一头：4 264期必中二头：4,0 264期 |
| `3tou-head` | <DIV> | `DIV` | **center** | 一头一码（twssz.com） 263期必中一头：4 263期必中二头：4,0 263期 |



### 1.3 用户点名容器 → 计算样式 `text-align`（Playwright 实测）

### 表2 用户点名容器 → 计算样式 text-align

| 选择器 | 元素 | text-align | 容器内预测行 text-align |
| --- | --- | --- | --- |
| `.box.pad` | <DIV> | **center** | center |
| `.box.pad` | <DIV> | **center** | — |
| `.box.pad` | <DIV#legacy-attribute-anchor> | **start** | — |
| `.box.pad` | <DIV> | **start** | — |
| `.contentbox_01` | <DIV> | **start** | — |
| `.contentbox_01` | <DIV> | **center** | center |
| `.contentbox_01` | <DIV> | **center** | — |
| `.dz_content08ab2d` | <DIV> | **center** | center |
| `.dz_content08ab2d` | <DIV> | **center** | — |
| `#table1` | <TABLE#table1> | **center** | center |
| `#con_jihuadanshuang50000ww_1` | <DIV#con_jihuadanshuang50000ww_1> | **center** | center |
| `#con_jihuadanshuang50000ww_2` | <DIV#con_jihuadanshuang50000ww_2> | **center** | center |
| `.Contentbox50000` | <DIV#con_jihuadanshuang50000ww_1> | **center** | center |
| `.Contentbox50000` | <DIV#con_jihuadanshuang50000ww_2> | **center** | center |
| `.bbzhong122` | <DIV> | **center** | — |
| `.bizhong1` | <DIV> | **center** | — |
| `.zt24mtr` | <TR> | **center** | center |



> `.box.pad` / `.contentbox_01` 中 **不含预测模块** 的两处（页脚「属性知识」锚点容器、顶部导航容器）
> 保持 `start`——它们不是预测模块，按需求不应被改动。其余全部为 `center`。

### 1.4 黄底元素对照表（改后：每个黄底元素都是本期命中项）

### 表3 黄底元素对照表（改后 · 900px；375px 完全相同）

| 模块 | 该行判定 | 黄底元素文本 | 归属判定 |
| --- | --- | --- | --- |
| `grade-a` | （本格无判定文字，见卡片级判定） | **马** | 命中项：特肖 马 |
| `grade-a` | 对 | **鸡** | 命中项：特肖 鸡 |
| `grade-a` | 对 | **猴** | 命中项：特肖 猴 |
| `grade-a` | 对 | **猴** | 命中项：特肖 猴 |
| `grade-a` | 对 | **羊** | 命中项：特肖 羊 |
| `grade-a` | 对 | **猪** | 命中项：特肖 猪 |
| `grade-a` | 对 | **08** | 命中项：特码 08 |
| `grade-a` | 对 | **兔** | 命中项：特肖 兔 |
| `grade-a` | 对 | **04** | 命中项：特码 04 |
| `grade-a` | 对 | **兔** | 命中项：特肖 兔 |
| `grade-a` | 对 | **04** | 命中项：特码 04 |
| `grade-a` | 对 | **马** | 命中项：特肖 马 |
| `title_66-4` | （本格无判定文字，见卡片级判定） | **10** | 本期特码未从行文本取到（人工核对） |
| `title_66-4` | （本格无判定文字，见卡片级判定） | **10** | 本期特码未从行文本取到（人工核对） |
| `title_66-6` | （本格无判定文字，见卡片级判定） | **04** | 本期特码未从行文本取到（人工核对） |
| `title_66-6` | （本格无判定文字，见卡片级判定） | **04** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **鸡** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **鸡** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **鸡** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **鸡** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猴** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猴** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猴** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猴** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **羊** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **羊** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **羊** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **羊** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猪** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猪** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猪** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **猪** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **兔** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **兔** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **兔** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **兔** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **马** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **马** | 本期特码未从行文本取到（人工核对） |
| `aaa-grade` | 对 | **马** | 本期特码未从行文本取到（人工核对） |
| `3tou-三头中特` | 对 | **2头** | 命中项：特码头 2头 |
| `3tou-三头中特` | 对 | **1头** | 命中项：特码头 1头 |
| `3tou-三头中特` | 对 | **0头** | 命中项：特码头 0头 |
| `3tou-三头中特` | 对 | **3头** | 命中项：特码头 3头 |
| `pt1wei-平特一尾` | 对 | **0尾** | 命中项：平特尾（候选尾 0尾，特码 46 或整期号码含该尾） |
| `pt1wei-平特一尾` | 对 | **3尾** | 命中项：平特尾（候选尾 3尾，特码 10 或整期号码含该尾） |
| `pt1wei-平特一尾` | 对 | **1尾** | 命中项：平特尾（候选尾 1尾，特码 08 或整期号码含该尾） |
| `pt1wei-平特一尾` | 对 | **7尾** | 命中项：平特尾（候选尾 7尾，特码 37 或整期号码含该尾） |
| `pt1xiao-平特一肖` | 对 | **鸡** | 命中项：特肖 鸡 |
| `pt1xiao-平特一肖` | 对 | **虎** | 平特类命中项：候选肖 虎 落在本期开奖生肖集合内（pt1xiao-平特一肖 为平特玩法） |
| `pt1xiao-平特一肖` | 对 | **兔** | 平特类命中项：候选肖 兔 落在本期开奖生肖集合内（pt1xiao-平特一肖 为平特玩法） |
| `pt1xiao-平特一肖` | 对 | **马** | 平特类命中项：候选肖 马 落在本期开奖生肖集合内（pt1xiao-平特一肖 为平特玩法） |
| `pt1xiao-平特一肖` | 对 | **狗** | 平特类命中项：候选肖 狗 落在本期开奖生肖集合内（pt1xiao-平特一肖 为平特玩法） |
| `pt1xiao-平特一肖` | 对 | **羊** | 平特类命中项：候选肖 羊 落在本期开奖生肖集合内（pt1xiao-平特一肖 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **马** | 平特类命中项：候选肖 马 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **鸡** | 平特类命中项：候选肖 鸡 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **猴** | 平特类命中项：候选肖 猴 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **11** | **需复核**：11 ≠ 特码 12 |
| `title_48` | （本格无判定文字，见卡片级判定） | **羊** | 平特类命中项：候选肖 羊 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **鸡** | 平特类命中项：候选肖 鸡 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **10** | **需复核**：10 ≠ 特码 08 |
| `title_48` | （本格无判定文字，见卡片级判定） | **猪** | 平特类命中项：候选肖 猪 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **08** | 命中项：特码 08 |
| `title_48` | （本格无判定文字，见卡片级判定） | **兔** | 平特类命中项：候选肖 兔 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_48` | （本格无判定文字，见卡片级判定） | **04** | **需复核**：04 ≠ 特码 10 |
| `title_48` | （本格无判定文字，见卡片级判定） | **马** | 平特类命中项：候选肖 马 落在本期开奖生肖集合内（title_48 为平特玩法） |
| `title_5` | 对 | **猪** | 命中项：特肖 猪 |
| `title_5` | 对 | **马** | 命中项：特肖 马 |
| `3hang-综合资料` | 对 | **金** | 命中项：五行 金（特码 46 属 金） |
| `3hang-综合资料` | 对 | **土** | 命中项：五行 土（特码 24 属 土） |
| `3hang-综合资料` | 对 | **金** | 命中项：五行 金（特码 10 属 金） |
| `3hang-综合资料` | 对 | **水** | 命中项：五行 水（特码 08 属 水） |
| `3hang-综合资料` | 对 | **火** | 命中项：五行 火（特码 37 属 火） |
| `3hang-综合资料` | 对 | **土** | 命中项：五行 土（特码 45 属 土） |
| `3hang-综合资料` | 对 | **土** | 命中项：五行 土（特码 09 属 土） |
| `3hang-综合资料` | 对 | **火** | 命中项：五行 火（特码 38 属 火） |
| `3hang-综合资料` | 对 | **土** | 命中项：五行 土（特码 42 属 土） |
| `3hang-综合资料` | 对 | **土** | 命中项：五行 土（特码 21 属 土） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **狗** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **蛇** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **马** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **龙** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **蛇** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **02** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **鼠** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **07** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **牛** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **兔** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **16** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **马** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **猪** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **01** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **20** | 本期特码未从行文本取到（人工核对） |
| `pt3xiao` | （本格无判定文字，见卡片级判定） | **猴** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **蓝波** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **红波** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **绿波** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **11** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **红波** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **24** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **蓝波** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **10** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **红波** | 本期特码未从行文本取到（人工核对） |
| `shuangbo` | （本格无判定文字，见卡片级判定） | **08** | 本期特码未从行文本取到（人工核对） |
| `title_47-四肖中特` | 对 | **鸡** | 命中项：特肖 鸡 |
| `title_47-四肖中特` | 对 | **鸡** | 命中项：特肖 鸡 |
| `title_47-四肖中特` | 对 | **猪** | 命中项：特肖 猪 |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **3** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **3** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **3** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **2** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **2** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **24** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **1** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **1** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **1** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **1** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **10** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **0** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **0** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **0** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **04** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **3** | 本期特码未从行文本取到（人工核对） |
| `3tou-head` | （本格无判定文字，见卡片级判定） | **3** | 本期特码未从行文本取到（人工核对） |



补充说明（表 3 中标注「人工核对」的行，逐条复核结论如下，均为命中项）：

| 位置 | 复核结论 |
| --- | --- |
| `title_66-4` = `10` ×2、`title_66-6` = `04` ×2 | 266 期特码 10、264 期特码 04，15 码与九码两张号码表各自点亮同一个特码 → 命中项 ✔ |
| `aaa-grade` 24 处（269 鸡 / 268 猴 / 267 羊 / 265 猪 / 264 兔 / 263 马） | 每张卡的 ⑨⑧⑦⑥肖都只点亮**本卡那一期的特肖**，四处一致 → 命中项 ✔（正是本轮修掉的样例残留 bug） |
| `pt3xiao`、`shuangbo`、`title_48`、`title_143`、`3tou-head` | 探针取到的是「候选格」，判定文字在配对的表头行/卡片行上；`title_48` 的 `11/10/04` 分别是 268/266/264 期的特码（探针从候选串里误取了 `12/08/10` 当特码，属探针口径问题，已逐期核对） → 命中项 ✔ |

### 1.5 改前 / 改后对照（同一份数据、同一套探针；「改前」用 `git show HEAD:…` 路由回放原文件）

### 表4 改前 / 改后黄底元素对照

| 口径 | 模块数 | 非居中模块数 | 黄底元素总数 | js_errors |
| --- | ---: | ---: | ---: | ---: |
| before 900px | 52 | 51 | 153 | 0 |
| before 375px | 52 | 51 | 153 | 0 |
| after 900px | 52 | 0 | 128 | 0 |
| after 375px | 52 | 0 | 128 | 0 |

**被清理掉的黄底（改前有 · 改后没有）**

| 改前黄底元素 | 数量 | 分类 |
| --- | ---: | --- |
| `bg|FONT|title_143-一波中特|186期 一波中特：蓝·波 开：牛42对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|FONT|title_143-一波中特|188期 一波中特：绿·波 开：蛇38对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|FONT|title_143-一波中特|189期 一波中特：蓝·波 开：狗09对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|FONT|title_66-4|10.` | 2 | 命中项 + 标点（冒号/点号被一起点亮） |
| `bg|FONT|title_66-6|04.` | 2 | 命中项 + 标点（冒号/点号被一起点亮） |
| `bg|SPAN|3hang-综合资料|184期 综合资料：木·土·水 开：狗21对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|186期 综合资料：土·木·水 开：牛42对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|188期 综合资料：火·金·水 开：蛇38对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|189期 综合资料：火·土·水 开：狗09对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|190期 综合资料：土·金·水 开：狗45对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|263期 综合资料：土·金·火 开：马37对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|265期 综合资料：火·土·水 开：猪08对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|266期 综合资料：金·木·水 开：鸡10对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|267期 综合资料：土·木·水 开：羊24对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3hang-综合资料|269期 综合资料：金·土·火 开：鸡46对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3tou-head|(空)` | 8 | 空 span 残留黄底（写值清空文字但没清背景） |
| `bg|SPAN|3tou-三头中特|263期 三头中特：4头·0头·3头 开：马37对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3tou-三头中特|264期 三头中特：4头·0头·1头 开：兔04对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3tou-三头中特|266期 三头中特：1头·0头·4头 开：鸡10对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|3tou-三头中特|267期 三头中特：4头·3头·2头 开：羊24对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|aaa-grade|牛` | 4 | 供应商样例命中标记（属样例那一期，不是本期命中项） |
| `bg|SPAN|aaa-grade|羊` | 8 | 供应商样例命中标记（属样例那一期，不是本期命中项） |
| `bg|SPAN|aaa-grade|虎` | 1 | 供应商样例命中标记（属样例那一期，不是本期命中项） |
| `bg|SPAN|aaa-grade|龙` | 4 | 供应商样例命中标记（属样例那一期，不是本期命中项） |
| `bg|SPAN|danshuangtema|(空)` | 3 | 空 span 残留黄底（写值清空文字但没清背景） |
| `bg|SPAN|pt1wei-平特一尾|263期 平特一尾：7尾 开：马37对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1wei-平特一尾|265期 平特一尾：1尾 开：猪08对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1wei-平特一尾|266期 平特一尾：3尾 开：鸡10对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1wei-平特一尾|269期 平特一尾：0尾 开：鸡46对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1xiao-平特一肖|264期 平特一肖：羊 开：兔04对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1xiao-平特一肖|265期 平特一肖：狗 开：猪08对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1xiao-平特一肖|266期 平特一肖：马 开：鸡10对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1xiao-平特一肖|267期 平特一肖：兔 开：羊24对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1xiao-平特一肖|268期 平特一肖：虎 开：猴11对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|pt1xiao-平特一肖|269期 平特一肖：鸡 开：鸡46对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|shuangbo|红波:` | 3 | 命中项 + 标点（冒号/点号被一起点亮） |
| `bg|SPAN|shuangbo|绿波:` | 1 | 命中项 + 标点（冒号/点号被一起点亮） |
| `bg|SPAN|shuangbo|蓝波:` | 2 | 命中项 + 标点（冒号/点号被一起点亮） |
| `bg|SPAN|title_143-一波中特|187期 一波中特：红·波 开：虎29对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|title_143-一波中特|190期 一波中特：红·波 开：狗45对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|title_47-四肖中特|265期 四肖中特：鸡·蛇·猪·狗 开：猪08对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|title_47-四肖中特|266期 四肖中特：蛇·猪·鸡·猴 开：鸡10对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|title_47-四肖中特|269期 四肖中特：蛇·鸡·狗·羊 开：鸡46对` | 1 | 整行黄底（把期号 + 模块名 + 开奖结果一起点亮） |
| `bg|SPAN|title_48-ai|(空)` | 6 | 空 span 残留黄底（写值清空文字但没清背景） |
| `fg|DIV|3tou-head|一头一码（twssz.com）` | 8 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-0|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-1|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-2|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-3|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-4|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-5|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-6|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|DIV|title_66-7|台湾 15码中特` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|FONT|ma24|台湾精选` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|FONT|（模块标题栏）|只是有点帅` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|FONT|（模块标题栏）|台湾精选` | 9 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|FONT|（模块标题栏）|台湾精选『综合绝杀』` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|FONT|（模块标题栏）|精准天地+两肖` | 1 | 模块标题黄色文字（模块名不允许高亮） |
| `fg|FONT|（模块标题栏）|躺平稳赚` | 2 | 模块标题黄色文字（模块名不允许高亮） |

**新增的黄底（改后才有 = 逐项命中高亮）**

| 改后黄底元素 | 数量 |
| --- | ---: |
| `bg|FONT|3tou-head|0` | 3 |
| `bg|FONT|3tou-head|1` | 4 |
| `bg|FONT|3tou-head|3` | 3 |
| `bg|FONT|aaa-grade|兔` | 4 |
| `bg|FONT|aaa-grade|猪` | 4 |
| `bg|FONT|aaa-grade|猴` | 4 |
| `bg|FONT|aaa-grade|羊` | 4 |
| `bg|FONT|aaa-grade|马` | 3 |
| `bg|FONT|aaa-grade|鸡` | 4 |
| `bg|FONT|title_66-4|10` | 2 |
| `bg|FONT|title_66-6|04` | 2 |
| `bg|SPAN|3hang-综合资料|土` | 5 |
| `bg|SPAN|3hang-综合资料|水` | 1 |
| `bg|SPAN|3hang-综合资料|火` | 2 |
| `bg|SPAN|3hang-综合资料|金` | 2 |
| `bg|SPAN|3tou-head|04` | 1 |
| `bg|SPAN|3tou-head|10` | 1 |
| `bg|SPAN|3tou-head|2` | 2 |
| `bg|SPAN|3tou-head|24` | 1 |
| `bg|SPAN|3tou-head|3` | 2 |
| `bg|SPAN|3tou-三头中特|0头` | 1 |
| `bg|SPAN|3tou-三头中特|1头` | 1 |
| `bg|SPAN|3tou-三头中特|2头` | 1 |
| `bg|SPAN|3tou-三头中特|3头` | 1 |
| `bg|SPAN|pt1wei-平特一尾|0尾` | 1 |
| `bg|SPAN|pt1wei-平特一尾|1尾` | 1 |
| `bg|SPAN|pt1wei-平特一尾|3尾` | 1 |
| `bg|SPAN|pt1wei-平特一尾|7尾` | 1 |
| `bg|SPAN|pt1xiao-平特一肖|兔` | 1 |
| `bg|SPAN|pt1xiao-平特一肖|狗` | 1 |
| `bg|SPAN|pt1xiao-平特一肖|羊` | 1 |
| `bg|SPAN|pt1xiao-平特一肖|虎` | 1 |
| `bg|SPAN|pt1xiao-平特一肖|马` | 1 |
| `bg|SPAN|pt1xiao-平特一肖|鸡` | 1 |
| `bg|SPAN|shuangbo|红波` | 3 |
| `bg|SPAN|shuangbo|绿波` | 1 |
| `bg|SPAN|shuangbo|蓝波` | 2 |
| `bg|SPAN|title_143-一波中特|红波` | 2 |
| `bg|SPAN|title_143-一波中特|绿波` | 1 |
| `bg|SPAN|title_143-一波中特|蓝波` | 2 |
| `bg|SPAN|title_47-四肖中特|猪` | 1 |
| `bg|SPAN|title_47-四肖中特|鸡` | 2 |

**关键变化**：黄底元素 **153 → 128**；非居中模块 **51 → 0**；`js_errors` 始终为 0。
其中 **32 处模块标题黄色文字**、**17 处空 span 残留黄底**、**17 处供应商样例生肖**、
**27 处整行黄底**、**5 处「命中项+标点」**被清除；同时新增 **41 处逐项命中高亮**（3tou-head 头/码、
三头中特头位、平特一尾尾数、平特一肖肖、综合资料五行、四肖中特肖、一波中特波色、AAA 特肖）。

追回的整行黄底统计（改前会把「期号 + 模块名 + 开奖结果」一起点亮）：
综合资料 10 行、平特一肖 6 行、平特一尾 4 行、三头中特 4 行、四肖中特 3 行、一波中特 5 行。

---

## 二、需求 2：【A级猛料大公开】字号放大

渲染器：`site-data-adapter.js::renderGradeHistory` / `markGradeHits` / `gradeResultText`；
字号由 `index.html` 的 `.bbzhong122/.dbt*` 内联样式决定，本轮用展示规范样式表覆盖。

改前 / 改后 computed `font-size`（Playwright `getComputedStyle`）：

| 元素 | 改前（900px） | 改后（900px） | 改前（375px） | 改后（375px） | 倍数 |
| --- | --- | --- | --- | --- | --- |
| `.dbt1`（标题条单元格） | 12px | **17px** | 12px | **17px** | ×1.42 |
| `.dbt1 span`（「台湾 A级猛料大公开」） | 13.3333px（10pt） | **17px** | 13.3333px | **17px** | ×1.28 |
| `.dbt2` / `.dbt3`（七肖/四肖/三肖/二肖 + 平特/⑩码/⑧码/⑤码 单元格） | 12px | **16px** | 12px | **16px** | ×1.33 |
| `.dbt2 font` / `.dbt3 font`（肖名/码名叶子） | 12px | **16px** | 12px | **16px** | ×1.33 |
| `.dbt2 span` / `.dbt3 span`（内层说明 span） | 12px / 13.3333px | **16px** | 12px / 13.3333px | **16px** | ×1.33 / ×1.20 |
| `.dbt9`（平特 『XXX』开：…） | 13.3333px | **16px** | 13.3333px | **16px** | ×1.20 |

不换行、不溢出实测（`Range.getClientRects()` 按行聚类计行数）：

| 视口 | 表格宽 | 单元格宽（改前 → 改后） | 换行单元格数 |
| --- | ---: | --- | ---: |
| 900×1200 | 800px | `.dbt2` 362 / `.dbt3` 437（不变） | **0** |
| 375×900 | 371px | `.dbt2` 168 → **369**；`.dbt3` 202 → **369**（≤480px 单列堆叠） | **0** |

- 375px 单选：改前靠 12px 刚好塞进 168/202px 两列；直接放大到 16px 会让「⑩码 :42.02…46」这类
  10 码行折行（实测 13px 就折行）。因此 `@media (max-width:480px)` 把该卡改为**单列堆叠**，
  每格独占 369px，16px 下实测 `lines=1`、无横向溢出。
- 卡片其它布局（红色标题条、单元格边框、颜色）保持不变。

---

## 三、需求 3：异常检查

### 3.1 审计命令与前后数字

```powershell
# 线上
python scripts\audit-prediction-display.py twssz --json .codex-temp\audit-twssz-anomaly.json --dump-rows .codex-temp\rows-twssz-anomaly.json
# 本地预检
python scripts\audit-prediction-display.py twssz --base-url http://127.0.0.1:3000 --json .codex-temp\audit-twssz-anomaly-local.json --dump-rows .codex-temp\rows-twssz-anomaly-local.json
# 判定真值（独立复算，不依赖页面）
python scripts\audit-verdict-truth.py --site twssz --json .codex-temp\verdict-truth-twssz.json
# 源码 lint
python scripts\lint-prediction-renderers.py twssz
```

| 口径 | rows | error | warn | js_errors |
| --- | ---: | ---: | ---: | ---: |
| 线上 · 改前（基线） | 282 | 0 | 3 | 0 |
| 本地 · 改前（基线） | 282 | 0 | 3 | 0 |
| **线上 · 改后** | **282** | **0** | **3** | **0** |
| **本地 · 改后** | **282** | **0** | **3** | **0** |

- warn 三条与基线**逐字相同**（均为 R8）：`.box.pad|七肖`、`.box.pad|╔8肖16码╗`、`.box.pad|内幕⑤不中`（本地为
  `.contentbox_01|╔三肖六码╗`）。**warn 未增加**。
- `audit-verdict-truth.py --site twssz`：`rows=2236 error=0 warn=168 info=0`（warn 全部是
  「该期无开奖索引 / 内容不可解析」的无法判定项，非虚报或漏报）。
- `lint-prediction-renderers.py twssz`：`error=1 warn=0`，与改前一致（`writePairedHeader(header, row, "『内幕⑤不中』", "准")`
  的写死判定字，**既有问题、本轮未引入也未修**）。

### 3.2 逐条检查结论

R1–R8 告警：

| 规则 | 结果 |
| --- | --- |
| R1 raw_json_leak | 0（无 `["` `"]` `\"` 残留） |
| R2 verdict_pending | 0（未开奖期不给判定、不高亮） |
| R3 highlight_miss | **0**（判「错」的行零黄底） |
| R4 highlight_hit | 0（半自动核对见 3.3） |
| R5 repeat_run | 0 |
| R6 empty_legend | 0 |
| R7 verdict_missing | 脚本未实现该检查；人工核对见 3.3 |
| R8 verdict_all_same | 3 条 warn（与基线相同，见 3.3 判定项） |
| js_errors | 0（900px / 375px 均 0） |

结构性异常（Playwright 探针 + 网络监听，900px 与 375px 各跑一遍）：

| 检查项 | 结果 |
| --- | --- |
| 未开奖期却给判定 | 0 |
| 判定为「错」却有黄底 | 0 |
| 一行多期 / 期号错位 | 0（每行只含一个期号） |
| 模块横向溢出 | 0（`scrollWidth ≤ clientWidth+2`） |
| 图片缺失（可见且 `naturalWidth=0`） | 0 |
| HTTP ≥400 / 请求失败 | 0 |
| 页面 JS 报错 | 0 |

### 3.3 本轮修掉

1. **整行黄底**（S2/S3 违规，最严重）：三头中特 / 平特一尾 / 平特一肖 / 综合资料 / 四肖中特 / 一波中特
   把「期号 + 模块名 + 开奖结果 + 候选」整行点亮 → 改为只点亮命中的那一项（共 32 行）。
2. **AAA级大公开 样例命中残留（判定与高亮不同源）**：`applyRowHighlight` 只在「判定为错」的期清黄标，
   命中的期把供应商样例那一期的**别的生肖**留在屏上（实测 269 期开鸡 46，「羊」却是黄的）。
   → 每张卡先无条件清样例黄标，再按本期特肖点亮；17 处错误生肖消失，24 处正确特肖点亮。
3. **空 span 残留黄底**：`3tou-head` 8 处、`danshuangtema` 3 处、`title_48-ai` 6 处。供应商模板把黄底 span
   预埋在文案里，写值只清空了文字、没清背景，审计的计算样式口径仍把它算作「本行有高亮」（R3 假阴性风险）。
4. **命中项连标点一起点亮**：`<font>10.</font>`（15码中特）、`<span>蓝波:</span>`（双波10码）→ 黄底只包数字/波色名。
5. **模块标题黄色文字**：19 处标题条 `<font color="#FFFF00">` + `.bbzhong122-tit` / `.bizhong1-tit` 的 `color:#ff0`
   （共 32 处命中「模块名不允许高亮」）→ 改为白色（蓝底/绿底标题条，观感与改前一致）。
6. **一波中特最新一期整行空白（数据缺失型展示缺陷）**：`#con_jihuadanshuang50000ww_2` 的第一个 `<p>` 只有裸文本、
   没有可复用的 `font/span` 叶子，`history-value` 槽取不到 → 191 期（待开奖）不显示、其余期次整体上移一格。
   现在这种「有文字但无元素子节点」的行回退为行自身当值槽（并打持久标记，避免首次清空后判断失效）。
   实测第一行已变为 `191期 一波中特：蓝波 开：待开奖`（不显示判定、不高亮）。
7. **全部模块文字居中**：52/52 模块、点名容器（`.box.pad`、`.contentbox_01`、`#con_jihuadanshuang50000ww_1/_2`、
   `#table1`、`.dz_content08ab2d`、`.Contentbox50000`、`.bbzhong122`、`.bizhong1`、`.zt24mtr`）计算样式均为 `center`。

### 3.4 报告但未修（附原因）

| # | 问题 | 证据 | 未修原因 |
| --- | --- | --- | --- |
| 1 | **6 个模块「命中却没有黄底」（S2 历史遗留）**：`daxiao` 极品大小（2 期）、`pt2xiao` 家野二肖（7 期）、`sanxiao_siwei_xiao` 2组连肖连尾（12 期）、`danshuangtema` 单双中特（4 期用 `√` 表示命中）、`ma24` 精选24码与 `title_48-ai` AI心水（**完全不显示判定文字**，R7 类） | 改前/改后黄底统计中这些模块恒为 0；审计因「模块内无任何高亮」而不报 R4 | 这些模块**从来没有过高亮**，不属于本轮「清理错误黄底」的连带损失；逐项补高亮需要为 6 个渲染器各写一套玩法语义（24 码集合 / 连肖连尾双机制 / 家野分组 / 大小单双 / 五行式 AI 卡），改动面与回归风险都远大于需求本身。保留为已知遗留项，建议单独立项 |
| 2 | **R8 三条 warn**（七肖、8肖16码、内幕⑤不中 / 三肖六码「整列全同·命中」） | 线上/本地审计 | 与基线逐字相同、未增加。`audit-verdict-truth.py` 独立复算 `error=0`，说明判定口径与真实开奖一致；候选集本身较大（七肖 7/12、8肖 8/12、三肖六码 3 肖对整期 7 个生肖），连对在概率内。按规范「R8 只是提示」，属正常类 |
| 3 | `lint-prediction-renderers.py` 的 1 条 `hardcoded_verdict` error：`writePairedHeader(header, row, "『内幕⑤不中』", "准")` | 改前改后一致 | 既有问题：`内幕⑤不中` 是排除型玩法，「准」是固定命中标签而非读 `is_correct`；页面实际输出仍由 `openedResult()` 决定，未造成错误展示。改动它会触碰判定文案口径，超出本轮范围 |
| 4 | `ma24`（精选24码）/`title_48-ai`（AI心水玄机论坛）**不显示任何判定文字** | 逐行核对：行内只有候选，没有 `开：…对/错` | 供应商模板本身没有判定槽位；属于 R7 类展示缺口，需要新增文案（而非修 bug），且会改变页面文案口径 → 报告未修 |
| 5 | `AAA级大公开` 卡片的静态文案 `准确率绝对100%` | 卡片首行 | 供应商模板静态营销文案，**本期并未命中时也照印**；它不是本期判定（不高亮、不参与 R1–R8），属文案而非渲染缺陷 |
| 6 | `3tou-三头中特` 第 0 行恒为空白 | 探针 `row=0 text=''` | 该 `<tr>` 是供应商标题下的装饰分隔行（无「期号 + 内容槽」），审计按「含期号」口径不把它当预测行；不是候选为空 |
| 7 | 本地库数据在两次探针之间发生过变化（`pt3xiao` 188/184 期候选集合改变） | 两次探针输出对比 | 并行会话/生成侧活动所致，与本轮前端改动无关；本轮改前/改后对比改用「同一时刻 + `git show` 路由回放」口径完成，规避了该漂移 |

### 3.5 与规范文档的差异（只读说明，未改文档）

- 规范「五之二」基線表记录 twssz `warn=3`，与本次实测一致；本轮未产生新的 R8/R5。
- 规范未覆盖「模块名黄色文字」这一项（S2 只规定 `background-color:#FFFF00`）。本轮按用户需求
  「模块名一律不允许高亮」把标题条的**黄色前景字**也改成白色；审计的 `countYellow` 同时统计
  `color:#FFFF00`，因此该项同时消除了 R3 的潜在假阴性。

---

## 四、遗留项与回滚

### 4.1 遗留项

1. 见 3.4 的 7 条（6 个「命中未标黄」模块、R8 三条、lint 既有 error、静态 100% 文案、装饰空行、数据漂移）。
2. `一波中特` 所在的 `#con_jihuadanshuang50000ww_2` 默认 `display:none`（需点「一波中特」页签才展开），
   本轮只保证其文字对齐与高亮口径正确，未改页签交互。
3. 本轮未跑后端测试（未改 `backend/src/**`）。

### 4.2 回滚方式

两个文件、无数据库/契约改动，回滚即可完全还原：

```powershell
git checkout -- frontend/public/vendor/twssz/index.html frontend/public/vendor/twssz/site-data-adapter.js
# 或按文件粒度
git checkout -- frontend/public/vendor/twssz/site-data-adapter.js   # 只回滚高亮/居中容器标记逻辑
```

- 样式表在 `index.html` 里以 `<style id="twssz-prediction-display-standard">` 单独成块，
  只删该块即可回退「居中 + A级猛料字号 + 窄屏堆叠」，不影响其它改动。
- 适配层新增的 `data-prediction-center` 只是属性标记，缺少对应样式时无副作用。
- 本轮未改任何共用文件、未改契约、未写库、未提交、未部署。

### 4.3 复现命令

```powershell
# 本地 dev：Next http://127.0.0.1:3000（已在跑）、Python API http://127.0.0.1:8000（已在跑）
python scripts\audit-prediction-display.py twssz --base-url http://127.0.0.1:3000 --json .codex-temp\audit-twssz-anomaly-local.json --dump-rows .codex-temp\rows-twssz-anomaly-local.json
python scripts\audit-prediction-display.py twssz --json .codex-temp\audit-twssz-anomaly.json --dump-rows .codex-temp\rows-twssz-anomaly.json
python scripts\audit-verdict-truth.py --site twssz --json .codex-temp\verdict-truth-twssz.json
python scripts\lint-prediction-renderers.py twssz
node frontend/test/run-prediction-token-shape-contract.mjs          # passed (20 个模块)
node frontend/test/run-prediction-verdict-truth-contract.mjs        # passed
# 探针（本报告的表 1–表 4 数据来源）
python .codex-temp\twssz_verify.py --out .codex-temp\twssz_verify.json
python .codex-temp\twssz_before_after.py --out .codex-temp\twssz_before_after.json
python .codex-temp\twssz_anomaly.py --out .codex-temp\twssz_anomaly.json
```
