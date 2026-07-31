# 台湾金手指（twjsz666）前端预测模块设计

## 1. 目的与边界

本文以 `frontend/public/vendor/twjsz666/index.html` 和
`frontend/public/vendor/twjsz666/site-data-adapter.js` 的现有 DOM contract 为唯一
基线，说明首页目前可由后端资料渲染的预测模块。页面继续采用供应商 HTML 的
布局；适配器只写既有文本叶节点、既有黄色命中节点和既有期号槽，不创建、移动或
替换 DOM。

- 站点：`twjsz666`，默认彩票：台湾彩（`lottery_type=3`），并支持澳门彩（2）与香港彩（1）。
- 预测统一入口：`GET /api/sites/twjsz666/prediction-modules`。
- 统一开奖入口：`GET /api/sites/twjsz666/draw`；它属于开奖模块，不作为预测模块资料来源。
- 历史请求上限为本页所需完整期组数且不超过 20；客户端按 `issue` 去重后才写入。
- 下面标为“可用”的模块是当前 `SECTION_CONTRACTS` 中 `classification: mapped` 的 19 项。
  `一头一码（24码中特）` 当前为 `unavailable`，不能拿近似模块伪造资料；文末保留其
  目标 API 与前端 contract，供后端机制完成后接入。

## 2. 预测模块清单

| TITLE | 页面展示位置（稳定锚点） | 后端 moduleKey | 核心业务逻辑 |
| --- | --- | --- | --- |
| 单双各四肖 | `#pttj`，`.duilianpt` 九个 `<tr>` | `danshuang4xiao` | 每期输出单肖四肖与双肖四肖；仅特别号生肖决定命中。 |
| 发财⑨肖 | 标题“发财⑨肖”的 `.box.pad` | `9xzt` | 输出最多九个生肖 token 的历史预测及特别号结果。 |
| 三头四尾 | 标题含“三头”的 `.box.pad` | `three_head_four_tail` | 从结构化 `heads`、`tails` 分别取三头与四尾，保留原表格分栏。 |
| 平特一肖 | 标题“平特一肖”的 `.box.pad` | `pt1xiao` | 每期一个生肖预测；特别号生肖相同即命中。 |
| 四字解平特肖 | 标题“四字解平特肖”的 `.box.pad` | `sizixuanji` | 输出四字资料解析出的生肖 token，不把原始 JSON/分隔符写入页面。 |
| 精准台湾高手 | 标题“精准台湾高手”的 `.box.pad` | `expert_publications` | 从 `content.publications` 逐条填既有 `<li>`，显示来源期号。 |
| 双波中特 | 标题“必发双波”的 `.box.pad` | `shuangbo` | 组合两个波色 token，以 `+` 保留双波表达并根据特别号波色判定。 |
| 家禽VS野兽 | 标题“家禽VS野兽”的 `.box.pad` | `title_14` | 输出后端定义的家禽/野兽分类 token；特别号生肖按分类判定。 |
| 平特③肖 | 标题“平特③肖”的 `.box.pad` | `pt3xiao` | 输出三肖集合，特别号生肖在集合中则命中。 |
| ④肖⑧码 | 标题“④肖⑧码”的 `.box.pad` | `4xiao8ma` | 分别读取 `xiao`（四肖）与 `code`（八码），按供应商既有行槽展示。 |
| 大小中特 | 标题“大小中特”的 `.box.pad` | `daxiao` | 读取 `daxiao`，统一显示为“大数”或“小数”，以特别号大小判定。 |
| 七尾中特 | 标题“七尾中特”的 `.box.pad` | `title_74` | 输出七个尾数 token；特别号尾数命中时高亮原有叶节点。 |
| 平特一尾 | 标题“平特一尾”的 `.box.pad` | `pt1wei` | 读取 `tail`，输出一个尾数，按特别号尾数判定。 |
| 精选22码 | `#jx22ma` 对应标题“精选22码”的 `.box.pad` | `selected_22_codes` | 最多展示 22 个号码；结果仅比较特别号号码。 |
| 绝杀二肖 | 标题“绝杀二肖”的 `.box.pad` | `juesha2xiao` | 输出两个排除生肖；特别号不在排除集合中才为正确。 |
| 绝杀①半波 | 原模板标题“绝杀①波”的 `.box.pad`，运行时校正为“绝杀①半波” | `jueshabanbo` | 输出一个排除半波（如红单、蓝双）；特别号不在该半波中才为正确。 |
| 绝杀①尾 | 标题“绝杀①尾”的 `.box.pad` | `juesha1wei` | 输出一个排除尾数；特别号尾数不等于该值才为正确。 |
| 稳杀⑦码 | 标题“稳杀⑦码”的 `.box.pad` | `steady_kill_7_codes` | 输出最多七个排除号码；特别号不在集合中才为正确。 |
| 一句话中特网码 | 标题“一句话中特网码”的 `.box.pad` | `yijuzhenyan` | 使用 `sentence` 或 `prediction.text` 的可读文本，移除传输分隔符。 |

### 2.1 已识别但当前不可用的模块

| TITLE | 位置 | 当前状态 | 后端补齐条件 |
| --- | --- | --- | --- |
| 一头一码（www.twjsz666.com）24码中特 | `#yxym .bizhong1` 九张双栏卡 | `unavailable` | 必须提供“1/2/3/4 头”及四组各六码的同一期结构化数据；`9xzt` 等生肖模块不得替代。 |

“正版图库”“属性知识”“最快开奖”是静态栏目，不属于预测 API；“小康早到来”与
“买码之前先上”是组合卡，在每个子字段具备明确 moduleKey 前不得标注为可用预测。

## 3. 后端 API 设计

### 3.1 所有预测模块的统一批量接口

`GET /api/sites/twjsz666/prediction-modules`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `lottery_type` | integer | 是 | `3` 台湾彩、`2` 澳门彩、`1` 香港彩。 |
| `history_limit` | integer | 是 | 请求历史期数；客户端取页面最大完整期组数，服务端限制为 `1..20`。 |
| `include_vendor` | boolean / `0`、`1` | 否 | 默认 `1`；兼容资料合并开关。前端不能以该参数回填供应商静态快照。 |

响应外层：

```json
{
  "ok": true,
  "site": {
    "site_key": "twjsz666",
    "site_id": 11,
    "web_id": 11,
    "lottery_type": 3,
    "domain": "www.twjsz666.com",
    "render_mode": "iframe-vendor"
  },
  "data": {
    "canonical_modules": []
  }
}
```

每个 `canonical_modules[]` 元素：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `moduleKey` | string | 与上表严格一致的后端模块键。 |
| `title` | string | 后端模块名称，只作资料标识，不用于推断 DOM。 |
| `displayKind` | string | 例如 `tokens`；前端仍以本站 named renderer 决定布局。 |
| `rows` | array | 该模块的历史预测行，按最新期到较早期返回。 |
| `rows[].issue` | string | 规范化期号；同模块内必须唯一。 |
| `rows[].prediction.text` | string | 可读摘要，不能含未解析 JSON。 |
| `rows[].prediction.tokens` | string[] | 已分组预测 token。 |
| `rows[].prediction.extra` | object | 结构化扩展字段，如 `xiao`、`code`、`tail`、`wave`、`content`。 |
| `rows[].raw` | object | 兼容原始字段；仅供已声明 formatter 读取。 |
| `rows[].result.isOpened` | boolean | 是否已开奖；否时前端显示 `开:待开奖`。 |
| `rows[].result.code` | string | 特别号号码；允许传输 CSV，但服务端应规范为最后一个号码。 |
| `rows[].result.zodiac` | string | 特别号生肖；允许传输 CSV，但服务端应规范为最后一个生肖。 |
| `rows[].result.isCorrect` | boolean/null | 该模块确定性命中结果；`null` 为待开奖或不适用。 |

### 3.2 模块字段、来源与计算规则

每一项均使用 3.1 的同一 URL 和 `GET` 方法；下表定义每个模块的必需 `moduleKey`、
行 payload 与服务端计算规则。因此不存在为单一模块复制一套路径的需求。

| TITLE | `moduleKey` | 必需字段 | 数据来源 / 计算规则 |
| --- | --- | --- | --- |
| 单双各四肖 | `danshuang4xiao` | `prediction.tokens` 或 `extra.single_xiao`、`extra.double_xiao`；`result.zodiac`、`isCorrect` | 预测生成器产生单肖四个、双肖四个；按特别号生肖的单双属性与所属集合计算。 |
| 发财⑨肖 | `9xzt` | `tokens`（最多 9） | 后端生成九肖集合；特别号生肖属于集合即命中。 |
| 三头四尾 | `three_head_four_tail` | `extra.content` JSON：`heads:string[]`、`tails:string[]` | 生成三头与四尾，分别上限 3、4；特别号头/尾按规则比对。 |
| 平特一肖 | `pt1xiao` | `tokens`（1 个） | 生成一个生肖，等于特别号生肖为命中。 |
| 四字解平特肖 | `sizixuanji` | `tokens` | 四字资料生成的生肖 token；不得把未解析内容直接返回页面。 |
| 精准台湾高手 | `expert_publications` | `extra.content` JSON：`publications:string[]` | 站点授权资料源按期生成文章条目；一条 API 行对应一组既有 `<li>`。 |
| 双波中特 | `shuangbo` | `tokens`（2 个波色）或 `extra.wave` | 生成两个波色；特别号波色属于集合即命中。 |
| 家禽VS野兽 | `title_14` | `tokens` 或 `extra.category` | 后端维护生肖到家禽/野兽的映射，以特别号生肖分类判定。 |
| 平特③肖 | `pt3xiao` | `tokens`（3 个） | 生成三肖集合，特别号生肖属于集合即命中。 |
| ④肖⑧码 | `4xiao8ma` | `extra.xiao:string[]`（4）、`extra.code:string[]`（8） | 生成四肖与八码；号码/生肖字段保持分组。 |
| 大小中特 | `daxiao` | `extra.daxiao`：`大`/`小` | 以特别号大小分段（规则由后端开奖配置定义）计算。 |
| 七尾中特 | `title_74` | `tokens`（7 个尾数） | 生成七尾集合；特别号号码末位属于集合即命中。 |
| 平特一尾 | `pt1wei` | `extra.tail` | 生成一个尾数；特别号末位相同即命中。 |
| 精选22码 | `selected_22_codes` | `tokens`（最多 22 个两位号码） | 生成 22 码集合；特别号号码属于集合即命中。 |
| 绝杀二肖 | `juesha2xiao` | `extra.xiao`（2 个） | 生成排除生肖；特别号不在集合中为正确。 |
| 绝杀①半波 | `jueshabanbo` | `tokens`（1 个半波标签） | 生成排除半波；特别号的波色单双组合不等于该值为正确。 |
| 绝杀①尾 | `juesha1wei` | `extra.tail`（1 个） | 生成排除尾数；特别号末位不等于该值为正确。 |
| 稳杀⑦码 | `steady_kill_7_codes` | `tokens`（最多 7 个号码） | 生成排除号码；特别号不在集合中为正确。 |
| 一句话中特网码 | `yijuzhenyan` | `extra.sentence` 或 `prediction.text` | 后端生成一句可读资料；不得给前端原始分隔符或 JSON。 |

### 3.3 一头一码（24码中特）拟补齐接口

当该机制完成后，仍使用统一 URL，但返回一个新增模块：

```json
{
  "moduleKey": "one_head_one_code_24",
  "title": "一头一码24码中特",
  "rows": [{
    "issue": "2026180",
    "prediction": {
      "extra": {
        "heads": ["3", "3,4", "3,4,2", "3,4,2,1"],
        "code_groups": [["39", "11", "09", "40", "18", "45"], ["27", "24", "21", "33", "12", "09"], ["03", "34", "26", "32", "48", "47"], ["15", "14", "44", "42", "16", "30"]],
        "recommended_head": "3"
      }
    },
    "result": { "isOpened": false, "code": "", "zodiac": "", "isCorrect": null }
  }]
}
```

服务端必须对每期同时生成四组“头”与四组六码，不得以 9 肖、22 码或任意近似模块
拼装。命中号码或头只能使用原模板已有的黄色 `<span>` 叶节点。

## 4. 前端展示数据格式

### 单双各四肖：原始 HTML 基线

以下片段直接来自当前 `index.html`，仅作为 DOM/样式基线；其中固定期号是供应商快照，
运行时必须由后端 `issue` 覆盖，不能继续作为展示资料。

```html
<tr>
                    <td>
                        <font color="#000000">060期:单肖</font>
                        <span class="zl">【鸡羊猪牛】</span>
                        <font color="#000000">双肖</font>
                        <span class="zl">【龙狗虎猴】</span>
                    </td>
                </tr>
```

| 既有展示字段 | API 字段 | 填充规则 |
| --- | --- | --- |
| `060期:单肖` 文本叶节点 | `rows[].issue` | 规范化为 `第{issue}期:单肖`；一行只消费一个 distinct issue。 |
| 首个 `.zl` | `extra.single_xiao` 或已分组 `tokens` | 固定为四个单肖，保留 `【】`。 |
| `双肖` 后的 `.zl` | `extra.double_xiao` 或已分组 `tokens` | 固定为四个双肖，保留 `【】`。 |
| 黄色 `<span style="background-color: #FFFF00">虎</span>` | `result.zodiac`、`result.isCorrect` | 开奖且特别号生肖命中时，只将已有命中生肖叶节点标黄；未命中/待开奖/切换彩票时清除黄色状态。 |

刷新时机：初次进入与三彩票 tab 切换时调用统一预测接口；同彩票缓存有效期内使用缓存，
迟到响应只能写回其自身缓存，不能覆盖当前彩票。接口错误时清除动态叶节点并显示该区块
明确空态；不能回显供应商的 `060期` 等静态文本。

### 一头一码（www.twjsz666.com）24码中特：原始 HTML 基线

以下片段直接来自当前 `index.html`，完整保留 `bizhong1-l` 与 `bizhong1-r` 双栏结构。

```html
<div class="bizhong1">
    <div class="bizhong1-tit">一头一码（www.twjsz666.com）24码中特</div>
    <div class="bizhong1-box">
        <div class="bizhong1-l">
            <ul>
                <li>060期必中一头：<font color="#FF0000" size="4"><font>3</font></font></li>
                <li>060期必中二头：<font color="#FF0000" size="4"><font>3</font>,<font>4</font></font></li>
                <li>060期必中三头：<font color="#FF0000" size="4"><font>3</font>,<font>4</font>,<font>2</font></font></li>
                <li>060期必中四头：<font color="#FF0000" size="4"><font>3</font>,<font>4</font>,<font>2</font>,<font>1</font></font></li>
            </ul>
        </div>
        <div class="bizhong1-r">
            <ul>
                <li>①<font color="#FF0000" size="4"><font>39</font>.<font>11</font>.<font>09</font>.<font>40</font>.<font>18</font>.<font>45</font></font></li>
                <li>②<font color="#FF0000" size="4"><font>27</font>.<font>24</font>.<font>21</font>.<font>33</font>.<font>12</font>.<font>09</font></font></li>
                <li>③<font color="#FF0000" size="4"><font>03</font>.<font>34</font>.<font>26</font>.<font>32</font>.<font>48</font>.<font>47</font></font></li>
                <li>④<font color="#FF0000" size="4"><font>15</font>.<font>14</font>.<font>44</font>.<font>42</font>.<font>16</font>.<font>30</font></font></li>
            </ul>
        </div>
    </div>
    <div class="bizhong1-foot">本期推荐一头：<font color="#FF0000" size="6">（<font>3</font>头）</font></div>
</div>
```

| 既有展示字段 | `one_head_one_code_24` 字段 | 填充规则 |
| --- | --- | --- |
| 左栏四个 `<li>` | `rows[].issue`、`extra.heads[0..3]` | 分别写“一头”至“四头”，每项保留各自 `<font>` 叶节点与逗号。 |
| 右栏四个 `<li>` | `extra.code_groups[0..3]` | 每组必须恰好六个两位号码，按既有 `①` 至 `④` 和 `.` 分隔写入。 |
| `.bizhong1-foot` | `extra.recommended_head` | 显示当期推荐一头。 |
| 既有黄色 span | `result.code`、`result.isCorrect` | 已开奖时仅对命中特别号号码或对应头的现有叶节点高亮。 |

当前没有上述完整后端 payload，故前端必须清空该卡所有静态期号、号码、对错和黄色残留，
显示“资料同步中/暂无后端资料”的命名空态；后端补齐前不得填入其他模块资料。

### 发财⑨肖：原始 HTML 基线

```html
<tr>
                <td>
                    <font color="#000000">060期: </font>
                    <span class="zl">【鼠羊鸡狗猪猴牛马虎】</span>
                    <font color="#000000">开：资料同步中</font></td>
            </tr>
```

映射：第一段 `<font>` 写 `issue`；`.zl` 写 `9xzt` 的九肖 token；末尾 `<font>` 写特别号
`resultText`。已开奖命中生肖仅使用现有黄色 `<span>`，无数据则清空三者的动态文本。

### 三头四尾：原始 HTML 基线

```html
<tr>
                    <th width="14%">
                        <font color="#0000FF">060期</font></th>
                    <th>
                        <span class="zl">三头【0.3.2】四尾【0.5.6.2】</span></th>
                    <th width="16%">
                        <font color="#0000FF">开:资料同步中</font></th>
                </tr>
```

映射：三列依次写 `issue`、`extra.content.heads[0..2]` 与 `tails[0..3]`、特别号结果；头和尾
保留原有“`三头【】四尾【】`”语义及 `.` 分隔。

### 平特一肖：原始 HTML 基线

```html
<tr>
                <td>
                    <font color="#000000">060期:平特一肖</font>
                    <span class="zl">
                            <font color="#0000FF">【鼠鼠鼠】</font></span>
                    <font color="#000000">开资料同步中</font></td>
            </tr>
```

映射：期号/标签叶节点写 `issue`，蓝色 `.zl` 写 `pt1xiao.tokens`，结尾写特别号结果；命中生肖
复用已有黄色叶节点。

### 四字解平特肖：原始 HTML 基线

```html
<tr>
                    <th width="14%">
                        <font color="#000000">060期</font></th>
                    <th>
                        <span class="zl">【杯弓蛇影】</span></th>
                    <th width="16%">
                        <font color="#000000">开:资料同步中</font></th>
                </tr>
```

映射：三列依次写 `issue`、`sizixuanji.tokens` 解析值和特别号结果，保留 `【】` 与三栏表格。

### 精准台湾高手：原始 HTML 基线

```html
<li>
                    <a target="_blank" href="167.html">060期: 临高高手
                        <span class="ci"><font color="#FF6600">【4头中特】</font></span>独家奉献</a>
                </li>
```

映射：每个既有 `<li>` 只写一个 `expert_publications.extra.content.publications[index]`；期号来自
同一行 `issue`。保留现有链接、`span.ci`、颜色和列表数量，不新增文章节点。

### 双波中特：原始 HTML 基线

```html
<tr>
                <td>
                    <font color="#000000">060期:双波</font>
                    <span class="zl">
                            <font color="#0000FF">【红波+绿波】</font></span>
                    <font color="#000000">开资料同步中</font></td>
            </tr>
```

映射：`issue`、`shuangbo.tokens[0..1]`、特别号结果依次填入；两种波色始终用既有 `+` 与 `【】`。

### 家禽VS野兽：原始 HTML 基线

```html
<tr>
                    <td width="23%">
                        <font color="#800000">060期</font></td>
                    <td style="color: #000; ">
                        家:<span class="zl" style="color:#f00;">鸡牛羊</span>
                        野:<span class="zl" style="color:#f00;">龙鼠蛇</span>
                    </td>
                    <td width="28%">
                        <font color="#800000">开:资料同步中</font></td>
                </tr>
```

映射：首列写 `issue`，两个 `.zl` 分别写 `title_14` 的家禽/野兽字段，末列写特别号结果；不能把两类
合并成一个无标签字符串。

### 平特③肖：原始 HTML 基线

```html
<tr>
                    <td>
                        <font color="#000000">060期: 平特③肖</font>
                        <span class="zl">【羊猴牛】</span>
                        <font color="#000000">大奉送！</font></td>
                </tr>
```

映射：期号写 `issue`，`.zl` 写 `pt3xiao.tokens[0..2]` 并保留 `【】`；末尾固定文案不作为 API 数据。

### ④肖⑧码：原始 HTML 基线

```html
<tr>
                    <td>
                        <font color="#000000">060期: </font><font color="#0000ff">④肖⑧码</font> &nbsp;<font color="#000000"> 开资料同步中?</font>
                        <br>
                        <span class="zl">合肖（狗鸡蛇龙）<br>45.08.32.20.09.26.14.33</span>
                    </td>
                </tr>
```

映射：期号和结果写首行 `<font>` 槽，`4xiao8ma.extra.xiao[0..3]` 与 `code[0..7]` 分别写 `.zl` 内
`<br>` 前后两个既有行，不得压平成一行。

### 大小中特：原始 HTML 基线

```html
<tr>
                    <td>
                        <font color="#000000">060期: 大小中特</font>
                        <span class="zl">【大数】</span>
                        <font color="#000000">开：资料同步中</font></td>
                </tr>
```

映射：`issue`、`daxiao.extra.daxiao`（标准化为“大数/小数”）、特别号结果依次填入。

### 七尾中特：原始 HTML 基线

```html
<tr>
                    <th>
                        <font color="#000000">060期:七尾中特</font>
                        <span class="zl">【6-2-5-7-9-1-8尾】</span>
                        <font color="#000000">开:资料同步中</font></th>
                </tr>
```

映射：期号、`title_74.tokens[0..6]`、特别号结果写入同一保留行；七尾仍以 `-` 串联并以“尾”结尾。

### 平特一尾：原始 HTML 基线

```html
<tr>
                    <td>
                        <font color="#000000">060期 平特一尾：5尾?</font></td>
                </tr>
```

映射：唯一文本叶节点按 `issue`、`pt1wei.extra.tail`、特别号结果组成，但保留供应商的“平特一尾”和
尾数标记；待开奖使用 `开:待开奖`，不能保留快照问号。

### 精选22码：原始 HTML 基线

```html
<tr>
                    <th width="13%">
                        <font color="#000000">060期</font></th>
                    <th><font color="#FF0000"><font>28</font>-<font>33</font>-<font>30</font>-<font>24</font>-<font>04</font>-<font>40</font>-<font>02</font>-<font>14</font>-<font>46</font>-<font>35</font>-<font>42</font><br><font>48</font>-<font>18</font>-<font>11</font>-<font>08</font>-<font>36</font>-<font>23</font>-<font>47</font>-<font>26</font>-<font>12</font>-<font>21</font>-<font>10</font></font></th>
                    <th width="11%">
                        <font color="#000000">特开
                            <br>资料同步中</font>
                    </th>
                </tr>
```

映射：三栏分别写 `issue`、`selected_22_codes.tokens[0..21]`、特别号结果；中栏维持原有两行与 `-`
分隔，不能把 22 码写入期号或结果栏。

### 绝杀二肖：原始 HTML 基线

```html
<tr>
                    <td>
                        <font color="#000000">060期: 绝杀二肖</font>
                        <span class="zl">
                            <font color="#0000FF">【龙.猪】</font></span>
                        <font color="#000000">开资料同步中</font></td>
                </tr>
```

映射：`issue`、`juesha2xiao.extra.xiao[0..1]`、特别号结果依次填入；两肖保留 `.` 分隔和排除命中语义。

### 绝杀①半波：原始 HTML 基线

```html
<tr>
                <td>
                    <font color="#000000">060期:绝杀①波</font>
                    <span class="zl">
                            <font color="#0000FF">【红波】</font></span>
                    <font color="#000000">开资料同步中</font></td>
            </tr>
```

映射：保留上述原始 HTML 作为结构基线，但运行时标题明确校正为“绝杀①半波”；`issue`、`jueshabanbo.tokens[0]`、特别号结果依次写入。此模块为半波排除规则，`isCorrect` 已由后端计算。

### 绝杀①尾：原始 HTML 基线

```html
<tr>
                <td>
                    <font color="#000000">060期:绝杀</font>
                    <span class="zl"><font color="#0000FF">6尾</font></span>
                    <font color="#000000">开资料同步中</font></td>
            </tr>
```

映射：`issue`、`juesha1wei.extra.tail`、特别号结果依次写入；尾数保持“尾”后缀。

### 稳杀⑦码：原始 HTML 基线

```html
<tr>
                <td>
                    <font color="#000000">060期: </font><font color="#00ff00">稳杀⑦码</font> &nbsp;<font color="#000000"> 开资料同步中</font>
                    <br>
                    <font color="#0000ff">【<font>05</font>.<font>18</font>.<font>41</font>.<font>08</font>.<font>42</font>.<font>44</font>.<font>30</font>】</font>
                </td>
            </tr>
```

映射：首行期号和特别号结果取 `issue`/`result`，第二行写 `steady_kill_7_codes.tokens[0..6]`；维持 `<br>` 与
七码 `.` 分隔。

### 一句话中特网码：原始 HTML 基线

```html
<tr>
                    <td>
                        <font color="#000000">060期 一句话</font>
                        <span class="zl">「马来牛来猴羊发财」</span>
                        <font color="#000000">开资料同步中</font></td>
                </tr>
```

映射：期号来自 `issue`，`.zl` 写 `yijuzhenyan.extra.sentence` 或 `prediction.text`，结尾写特别号结果；保留
中文引号，移除 API 中的 `|`、JSON 与原始数组。

### 通用刷新、异常与格式规则

1. 每次 API 返回先按 `issue` 去重，并按各模块固定历史组数填充；无行不能复制上一期。
2. 开奖行结果只取七个开奖号码中的特别号，显示 `开:号码生肖对/错`；未来期统一为 `开:待开奖`。
3. `prediction.extra` 可为 JSON、数组、CSV 或 `标签|号码`，必须由该模块 formatter 解析；页面禁止显示 `|`、`[object Object]`、原始 JSON 和拼接摘要。
4. 模块没有数据时只清空其声明的期号、预测、结果、命中槽，不改标题、表格、`br`、图片、页脚或供应商布局。
5. 每个映射模块均应有浏览器断言：三种彩票及缓存回程下的期号顺序、值槽、特别号结果、黄色命中、无静态期号哨兵和无跨彩票数据。

## 5. SKILL.md 新增内容

建议将下列正文追加至 `skills/vendor-site-onboarding/SKILL.md` 的“前端预测模块开发规范”章节；
本仓库已按相同正文落盘。

```markdown
## 前端预测模块开发规范

每个供应商站点在接入或补齐预测资料前，必须新增一份中文“前端预测模块设计文档”。文档必须以实际入口 HTML 和站点 adapter 的 section inventory 为准，逐项列出 TITLE、稳定 DOM 锚点、可用状态、moduleKey、业务语义、历史组数与命中规则；不能只按标题猜测模块含义。

### 接口约定

- 预测资料默认复用同源 `GET /api/sites/{siteKey}/prediction-modules`，请求参数至少为 `lottery_type`、`history_limit` 和可选 `include_vendor`。每一份文档必须列出所有参数、外层响应、`canonical_modules[]`、`rows[]`、`prediction`、`extra` 与特别号 `result` 字段，并为每个模块写明所需 moduleKey、专有字段、数据来源和确定性命中规则。
- 模块没有精确的成熟后端机制时，标为 `unavailable` 并定义命名空态；禁止以近似 moduleKey 伪造资料。需要新增机制时，先在设计文档定义结构化 payload、字段容量和计算规则，再实现数据库/生成器/API/站点授权。
- 必须以目标站点 `web_id`、三种彩票类型的实际数据行、同源 API payload 和浏览器 DOM 四层分别验收；另一个站点的数据行不能作为替代证据。

### DOM 槽位与展示基线

- 文档必须逐模块保留至少一个原始 HTML 展示片段，记录期号槽、预测子字段、结果槽、命中黄色叶节点、固定标签、`br` 与行/卡片容量。运行时只写既有最小叶节点，不得使用 whole-row `textContent`、`innerHTML` 或新增/移动节点破坏布局。
- 每个非同构模块使用命名 formatter 和 named renderer。解析 CSV、JSON、数组或 `标签|号码` 后再写入分组槽位；禁止展示原始分隔符、JSON、`[object Object]` 或不受控的长文本。
- 所有供应商固定期号/静态期数预测快照（包括“第xxx期”“xxx期”）必须在 mapped、composite 或 unavailable 预测区块中被后端资料替换或明确清空。该规则不删除同源 API 渲染的实时期号，也不删除统一开奖模块的实时期号。

### 刷新与测试

- 按 `lottery_type` 隔离请求、缓存、in-flight promise 与渲染状态；去重 `issue`，限制最多 20 个 distinct issues。快速切换或迟到响应不得覆盖当前彩票。
- 已开奖预测结果只显示特别号；未来期显示 `开:待开奖`。命中只能使用供应商已有黄色背景叶节点，切换、未命中和空态必须清除旧命中。
- 提交前为每个映射模块增加浏览器契约：点击三种彩票并返回缓存页，断言本模块期号/槽位/拓扑/特别号结果/命中状态，且断言无固定期号哨兵、供应商占位符、原始分隔符或跨彩票资料。
```
