# 前端 API 接口规范文档（基于 frontend 目录实扫）

> 范围：本文件基于上传包 `Zz_www.twsaimahui.com.zip` 中的 `index.html` 与 `static/js/*.js` 实际请求代码生成。`jquery.min.js`、`axios.min.js`、`vue.js` 等第三方库不作为业务接口来源。

## 1. 全局约定

### 1.1 API 基础地址

- 默认接口域名来自 `static/js/url_zlz_yuming_ht.js`：`var httpApi = 'https://admin.shengshi8800.com'`。
- `index.html` 中 Tab 切换会动态修改 `window.httpApi`：
  - Tab 0：`https://admin.shengshi8800.com`
  - Tab 1：`https://b.jsc111111.com`
- 后端需要在不同域名下提供同一套路径结构，或由网关/Nginx 转发到同一后端服务。

### 1.1.a 彩种切换参数说明

前端通过「台湾彩 / 澳门彩 / 香港彩」Tab 切换彩种。不同彩种有独立的 `apiBase`、`web`、`type` 配置。

**彩种配置表：**

| 彩种 | lotteryKey | apiBase | web | type | 说明 |
|---|---|---|---|---|---|
| 台湾彩 | `taiwan` | `https://admin.shengshi8800.com` | 6 | 3 | 默认彩种 |
| 澳门彩 | `macau` | `https://b.jsc111111.com` | 6 | 2 | 待后端确认真实 type |
| 香港彩 | `hongkong` | `https://admin.shengshi8800.com` | 6 | 1 | 待后端确认真实 type |

**切换机制：**

1. 用户点击彩种 Tab → 前端更新 `window.httpApi`、`window.web`、`window.type`
2. 选择持久化到 `localStorage.selectedLottery`
3. 内容区 `<div id="content-area">` 重置为初始 HTML，所有业务 JS 重新执行
4. 所有预测资料接口使用新的 `web`/`type`/`httpApi` 重新请求
5. 开奖 iframe 同步切换到对应彩种

**后端要求：**

- 同一个路径结构需要在不同 `apiBase` 域名下可用，或由网关/Nginx 转发到同一后端
- `type` 参数用于区分彩种，后端应根据 `type` 返回对应彩种的资料数据
- 澳门彩和香港彩的 `type` 值（2 和 1）需要后端确认是否正确

**全局状态变量：**

```js
window.appState = {
  lotteryKey: 'taiwan',     // 当前彩种标识
  httpApi: 'https://...',   // 当前 API 基础地址
  web: 6,                   // 站点 ID
  type: 3                   // 彩种类型
};
```

### 1.2 全局请求参数

> 详细参数表见下方。所有 `/api/kaijiang/*` 接口均使用 `web`、`type`、`num` 三个 Query 参数。

| 参数名 | 位置 | 是否必填 | 类型 | 示例 | 适用接口 | 说明 |
|---|---|---|---|---|---|---|
| `web` | query | 是 | integer | `6` | 全部 kaijiang + post + notice | 站点 ID，用于站点隔离 |
| `type` | query | 是 | integer | `3` | 全部 kaijiang + post | 彩种类型：1=香港彩，2=澳门彩，3=台湾彩 |
| `num` | query | 是 | integer/string | `2` | 全部 kaijiang | 模块数量或玩法参数；部分接口为特殊值如 `6/12`(一字玄机)、`9/8`(九肖一码) |
| `pc` | query | 是 | integer | `72` | 仅 `/api/post/getList` | 推荐位/分类参数，非页码 |

### 1.3 HTTP 方法和参数传递

- 当前活跃业务接口全部为 `GET`。
- 参数全部通过 QueryString 传递，没有业务请求体 Body。
- `zx.js` 使用 `axios({ method: 'get', params: {...} })`；其他资料模块使用 `$.ajax({ type: 'GET', dataType: 'json' })`。

### 1.3.a CORS 和请求头

- 当前公开资料接口**不需要 Authorization**。
- GET 请求无业务 body。
- 建议响应头 `Content-Type: application/json; charset=utf-8`。
- 如果 API 与页面不同域，后端**必须配置 CORS**，允许跨域 GET 请求。
- `ajax_interceptor.js` 中 `Authorization: Bearer token` 代码已被注释，不会实际发送。

### 1.4 通用响应结构与字段

#### 1.4.1 响应字段总表

| 字段名 | 类型 | 是否必填 | 是否可空 | 出现位置 | 示例 | 说明 |
|---|---|---|---|---|---|---|
| `term` | string | 是 | 否 | 所有 kaijiang 接口 | `"269"` | 期号，建议统一使用字符串 |
| `content` | string | 否 | 是 | 大多数 kaijiang 接口 | `"鼠,牛,虎"` 或 JSON 字符串 | 预测内容；标记为"JSON字符串"时必须返回合法 JSON 字符串 |
| `res_code` | string | 是 | 否 | 所有 kaijiang 接口 | `"01,13,22,34,45,49"` | 开奖号码，逗号分隔；未开奖返回空字符串 `""` |
| `res_sx` | string | 是 | 否 | 所有 kaijiang 接口 | `"龙,鸡,马,羊,狗,鼠"` | 开奖生肖，逗号分隔；未开奖返回空字符串 `""` |
| `xiao` | string | 否 | 否 | 特邀家野两肖(061)、单双(004)、九肖一码(013)、一字玄机(029) | `"鼠,牛,虎,兔"` | 生肖列表，逗号分隔 |
| `dan` | string | 否 | 否 | 单双四尾(003) | `"鼠,牛"` | 单数生肖列表，逗号分隔 |
| `shuang` | string | 否 | 否 | 单双四尾(003) | `"虎,兔"` | 双数生肖列表，逗号分隔 |
| `nan` | string | 否 | 否 | 男女(020) | `"鼠,牛"` | 男肖列表 |
| `nv` | string | 否 | 否 | 男女(020) | `"虎,兔"` | 女肖列表 |
| `title` | string | 否 | 否 | 成语平特尾(068)、成语平肖(066)、琴棋书画(052)、一字玄机(029) | `"成语标题"` | 标题文本，通过 `v-html` 渲染 |
| `xiao_1` | string | 否 | 否 | 特邀单双四肖(060) | `"鼠,牛,虎,兔"` | 第一组生肖 |
| `xiao_2` | string | 否 | 否 | 特邀单双四肖(060) | `"龙,蛇,马,羊"` | 第二组生肖 |
| `code` | string | 否 | 否 | 两肖+八码(069)、九肖一码(013) | `"01,02,03,05"` | 号码列表，逗号分隔 |
| `jiexi` | string | 否 | 否 | 一字玄机(029) | `"解析内容"` | 解析文本 |
| `zi` | string | 否 | 否 | 一字玄机(029) | `"示例"` | 字内容 |
| `image_url` | string | 否 | 是 | 跑马图(011)、一字玄机(029) | `"/uploads/image/example.jpg"` | 图片路径；非 `http` 开头时前端拼 `httpApi + image_url` |
| `name` | string | 否 | 否 | 三期必中(021) | `"示例名称"` | 内容名称 |
| `u6_code` | string | 否 | 否 | 六不中(019) | `"01,02,03,04,05,06"` | 六不中号码 |
| `id` | integer | 是 | 否 | 推(zx.js / post) | `1` | 文章/推荐资料 ID |
| `hei` / `bai` | string | 否 | 否 | 黑白(039) | `"01,02,03"` / `"04,05,06"` | 黑码/白码列表（兼容层内部字段，前端使用 content） |

#### 1.4.2 通用响应结构

大部分接口前端只读取 `response.data`，因此后端最低限度必须返回：

```json
{
  "data": []
}
```

资料类接口通常返回：

```json
{
  "data": [
    {
      "term": "269",
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠"
    }
  ]
}
```

注意：

- `res_code`、`res_sx` 不要返回 `null`，未开奖时返回空字符串 `""`。前端大量直接调用 `d.res_code.split(',')`、`d.res_sx.split(',')`。
- 标记为“content 为 JSON 字符串”的接口，`content` 必须是字符串形式的 JSON 数组，例如 `"[\"鼠|05,17\",\"牛|04,16\"]"`，不能直接返回数组。
- 号码建议保持两位字符串，如 `"01"`、`"09"`、`"49"`。
- 生肖建议使用简体：`龙、马、鸡、猪`；`ajax_interceptor.js` 会把部分繁体转成简体，但后端直接返回简体更稳定。

### 1.5 认证/鉴权

- 当前 `frontend` 没有启用 Token 鉴权。
- `ajax_interceptor.js` 中 `Authorization: Bearer token` 代码被注释掉了，不会实际发送。
- 后端不要强制这些公开接口带 Token，否则当前前端会请求失败。

### 1.6 错误处理约定

- jQuery 模块的错误处理基本都是 `console.error('Error:', error)`，没有 UI 提示。
- `zx.js` 的 axios 错误处理是 `console.log(err)`。
- 前端没有统一错误码体系；除了 `/api/index/notice` 会判断 `res.code == 600`，其他资料接口基本不判断 `code`。
- 建议后端失败时返回 HTTP 4xx/5xx，并使用统一 JSON：

```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 1.6.a 统一错误码规范

| HTTP 状态码 | code | 场景 | 响应 data |
|---|---|---|---|
| 200 | `0` 或 `200` | 成功 | `array` / `object` |
| 200 | `600` | 公告内容可用（仅 `/api/index/notice`） | `{ content: "..." }` |
| 400 | `400` | 参数错误 | `[]` |
| 404 | `404` | 数据不存在 | `[]` |
| 500 | `500` | 服务端异常 | `[]` |

特别说明：

- `/api/index/notice` 成功时前端要求 **code 必须等于 `600`**，否则公告不会展示。
- 其他资料接口前端基本不判断 `code`，只读取 `response.data`。
- 建议后端失败时返回 HTTP 4xx/5xx，并使用统一 JSON 结构。

### 1.7 分页、排序、筛选

- 当前活跃接口没有分页参数。
- `/api/post/getList` 使用 `pc=72` 作为推荐位/分类参数，不是页码。
- `common.js` 中存在旧的 `loadMoreTopicList()`、`doLogin()`、`doRegister()` 等函数，但当前页面没有实际初始化相关变量或触发这些旧接口，因此不列为本次后端必须实现接口。

### 1.8 排序和数据条数规则

- `data` 数组默认按 `term` 倒序返回，最新期在前。
- 如无特殊说明，每个资料接口返回最近 N 条记录（N 由后端配置或默认值决定）。
- 未开奖时 `res_code`、`res_sx` 必须返回空字符串 `""`，禁止返回 `null`。
- `term` 建议统一使用字符串类型（如 `"269"`）。

### 1.9 安全风险提醒

后端开发时请注意以下安全要求：

- `notice.content` 字段会作为 HTML 通过 `innerHTML` 直接插入页面，**必须过滤或白名单处理**。
- `post.title` 可能通过 Vue `v-html` 渲染，同样是 HTML 注入风险点。
- 必须过滤或转义以下危险内容：`<script>`、`onerror`、`onclick`、`onload`、`javascript:`、`data:text/html` 等。
- 推荐只允许白名单 HTML 标签（如 `<div>`、`<p>`、`<span>`、`<b>`、`<font>`、`<table>`、`<img>` 等），禁止所有事件处理器和脚本标签。

## 2. 接口总览

| 序号 | 模块 | 文件 | 方法 | 路径 | Query | 响应字段 | content JSON字符串 |
|---:|---|---|---|---|---|---|---|
| 1 | 特邀家野两肖 | `061jy2x.js` | GET | `/api/kaijiang/getJyxiao2` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term, xiao` | 是 |
| 2 | 左右 | `033zuoyou.js` | GET | `/api/kaijiang/getZyx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 3 | 精品六肖 | `012liuxiao.js` | GET | `/api/kaijiang/getXiaoma2` | `web={web}, type={type}, num=6` | `content, res_code, res_sx, term` | 是 |
| 4 | 阴阳 | `044yinyang.js` | GET | `/api/kaijiang/getYysx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 5 | 四肖八码 | `027six8m.js` | GET | `/api/kaijiang/getXiaoma2` | `web={web}, type={type}, num=4` | `content, res_code, res_sx, term` | 是 |
| 6 | 单双四尾 | `003ds4w.js` | GET | `/api/kaijiang/getDsWei` | `web={web}, type={type}, num=4` | `dan, res_code, res_sx, shuang, term` | 否 |
| 7 | 单双 | `071ds.js` | GET | `/api/kaijiang/danshuang` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 8 | 六肖 | `073sixiao.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=4` | `content, res_code, res_sx, term` | 否 |
| 9 | 合数单双 | `006heshuds.js` | GET | `/api/kaijiang/getHeds` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 10 | 天地 | `043tiandi.js` | GET | `/api/kaijiang/getTdsx1` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 11 | 吃肉草菜 | `049rccx.js` | GET | `/api/kaijiang/getRccx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 12 | 家野 | `040jiaye.js` | GET | `/api/kaijiang/getJyzt` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 13 | 隐刺五肖 | `042ycwx.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=5` | `content, res_code, res_sx, term` | 否 |
| 14 | 黑白 | `039heibai.js` | GET | `/api/kaijiang/getHbx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 15 | 九肖 | `014jiuxiao.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=9` | `content, res_code, res_sx, term` | 否 |
| 16 | 三肖 | `031wuxiao.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 否 |
| 17 | 特邀单双四肖 | `060ds4x.js` | GET | `/api/kaijiang/getDsnx` | `web={web}, type={type}, num=4` | `res_code, res_sx, term, xiao_1, xiao_2` | 否 |
| 18 | 跑马图/解跑马 | `011jiepaoma.js` | GET | `/api/kaijiang/getXiaoma2` | `web={web}, type={type}, num=7` | `content, image_url, res_code, res_sx, term` | 是 |
| 19 | 四肖 | `030lflx.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=4` | `content, res_code, res_sx, term` | 否 |
| 20 | 成语平特尾 | `068chengyupw.js` | GET | `/api/kaijiang/getCyptwei` | `web={web}, type={type}, num=2` | `res_code, res_sx, term, title` | 否 |
| 21 | 三期必中 | `023sanqibizhong.js` | GET | `/api/kaijiang/getSanqiXiao4new` | `web={web}, type={type}, num=7` | `content, name, res_code, res_sx` | 是 |
| 22 | 天地 | `075tiandi.js` | GET | `/api/kaijiang/getTdsx1` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 23 | 10码 | `038ma10.js` | GET | `/api/kaijiang/getCode` | `web={web}, type={type}, num=10` | `content, res_code, res_sx, term` | 否 |
| 24 | 四季肖 | `050siji.js` | GET | `/api/kaijiang/getSjsx` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 是 |
| 25 | 单双 | `004danshuang.js` | GET | `/api/kaijiang/getDsxiao` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term, xiao` | 否 |
| 26 | 20码 | `032ma20.js` | GET | `/api/kaijiang/getCode` | `web={web}, type={type}, num=20` | `content, res_code, res_sx, term` | 否 |
| 27 | 一波 | `036ma12.js` | GET | `/api/kaijiang/getYbzt` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 否 |
| 28 | 四尾八码 | `026siw8m.js` | GET | `/api/kaijiang/getWeima2` | `web={web}, type={type}, num=4` | `content, res_code, res_sx, term` | 是 |
| 29 | 16码 | `035ma16.js` | GET | `/api/kaijiang/getCode` | `web={web}, type={type}, num=16` | `content, res_code, res_sx, term` | 否 |
| 30 | 一字平肖 | `065yiziptx.js` | GET | `/api/kaijiang/getPingte` | `web={web}, type={type}, num=1` | `content, res_code, res_sx, term` | 否 |
| 31 | 风小子六肖 | `047liuxiao.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=6` | `content, res_code, res_sx, term` | 否 |
| 32 | 文武 | `046wenwu.js` | GET | `/api/kaijiang/getWwx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 33 | 大小中特 | `002daxiao.js` | GET | `/api/kaijiang/getDxzt` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 34 | 有无 | `045youwu.js` | GET | `/api/kaijiang/getYwx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 35 | 三连肖 | `067sanzipw.js` | GET | `/api/kaijiang/getPingte` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 否 |
| 36 | 林北 | `062linbei6x.js` | GET | `/api/kaijiang/getZhongte` | `web={web}, type={type}, num=6` | `content, res_code, res_sx, term` | 否 |
| 37 | 文房四宝 | `053wfsb.js` | GET | `/api/kaijiang/getBmzy` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 是 |
| 38 | 杀一肖 | `057s1x.js` | GET | `/api/kaijiang/getShaXiao` | `web={web}, type={type}, num=1` | `content, res_code, res_sx, term` | 否 |
| 39 | 两肖+八码 | `069lxbm.js` | GET | `/api/kaijiang/getX2jiam8` | `web={web}, type={type}, num=2` | `code, content, res_code, res_sx, term` | 否 |
| 40 | 平特一尾 | `022pt1w.js` | GET | `/api/kaijiang/getPtWei` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 41 | 两头 | `072liangtou.js` | GET | `/api/kaijiang/getTou` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 42 | 杀七码 | `056s7m.js` | GET | `/api/kaijiang/getShama` | `web={web}, type={type}, num=7` | `content, res_code, res_sx, term` | 否 |
| 43 | 杀两肖 | `058s2x.js` | GET | `/api/kaijiang/getShaXiao` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 否 |
| 44 | 风雨雷电 | `051fyld.js` | GET | `/api/kaijiang/getFyld` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 是 |
| 45 | 一字玄机 | `029yizixuanji.js` | GET | `/api/kaijiang/getYzxj` | `web={web}, type={type}, num=6/12` | `jiexi, res_code, res_sx, term, xiao, zi` | 否 |
| 46 | 成语平肖 | `066chengyupx.js` | GET | `/api/kaijiang/getCypt` | `web={web}, type={type}, num=2` | `res_code, res_sx, term, title` | 否 |
| 47 | 六不中 | `019liubuzhong.js` | GET | `/api/kaijiang/rd70i73lziizczak/0gmqnw/1` | `-` | `res_code, res_sx, term, u6_code` | 否 |
| 48 | 男女 | `020nn4x.js` | GET | `/api/kaijiang/getNnnx` | `web={web}, type={type}, num=4` | `nan, nv, res_code, res_sx, term` | 否 |
| 49 | 九肖一码 | `013jiux1m.js` | GET | `/api/kaijiang/getXysxma` | `web={web}, type={type}, num=9/8` | `code, res_code, res_sx, term, xiao` | 否 |
| 50 | 三头中特 | `024santou.js` | GET | `/api/kaijiang/getTou` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 是 |
| 51 | 三行 | `025sanhang.js` | GET | `/api/kaijiang/getXingte` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 是 |
| 52 | 双波 | `001sb.js` | GET | `/api/kaijiang/sbzt` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 否 |
| 53 | 杀一头 | `018sha1tou.js` | GET | `/api/kaijiang/getShatou` | `web={web}, type={type}, num=1` | `content, res_code, res_sx, term` | 是 |
| 54 | 美丑 | `041meichou.js` | GET | `/api/kaijiang/getJmxc` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 55 | 杀三尾 | `015sha3w.js` | GET | `/api/kaijiang/getShaWei` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 是 |
| 56 | 绝杀三肖 | `016sha3x.js` | GET | `/api/kaijiang/getShaXiao` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term` | 否 |
| 57 | 肥瘦 | `034feishou.js` | GET | `/api/kaijiang/getFsx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 58 | 平特一肖 | `074ptyx.js` | GET | `/api/kaijiang/getPingte` | `web={web}, type={type}, num=1` | `content, res_code, res_sx, term` | 否 |
| 59 | 胆大胆小 | `037dandaxiao.js` | GET | `/api/kaijiang/getDxd` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 60 | 红蓝绿肖 | `048hllx.js` | GET | `/api/kaijiang/getHllx` | `web={web}, type={type}, num=2` | `content, res_code, res_sx, term` | 是 |
| 61 | 琴棋书画 | `052qqsh.js` | GET | `/api/kaijiang/qqsh` | `web={web}, type={type}, num=3` | `content, res_code, res_sx, term, title` | 否 |
| 62 | 推 | `zx.js` | GET | `/api/post/getList` | `web={web}, type={type}, pc=72` | `id, title` | 否 |
| 63 | 杀半波 | `054sbanbo.js` | GET | `/api/kaijiang/getShaBanbo` | `web={web}, type={type}, num=1` | `content, res_code, res_sx, term` | 是 |
| 64 | 杀半单双 | `055sbands.js` | GET | `/api/kaijiang/getShaBds` | `web={web}, type={type}, num=1` | `content, res_code, res_sx, term` | 是 |
| 65 | 公告弹窗 | `index.html` | GET | `/api/index/notice` | `web={web}` | `content` | 否 |

### 2.1 共享请求参数规范

以下参数在几乎所有的 `/api/kaijiang/*` 接口中出现：

| 参数名 | 位置 | 是否必填 | 类型 | 示例 | 说明 |
|---|---|---|---|---|---|
| `web` | query | 是 | integer | `6` | 站点 ID |
| `type` | query | 是 | integer | `3` | 彩种/资料类型。台湾彩=3，澳门彩=2，香港彩=1（待后端确认） |
| `num` | query | 是 | integer/string | `2` | 模块数量或玩法参数，根据具体模块而定 |

特殊 `num` 值：

| 接口路径 | num 取值 | 说明 |
|---|---|---|
| `/api/kaijiang/getYzxj` | `6` 或 `12` | 一字玄机有6条和12条两种模式 |
| `/api/kaijiang/getXysxma` | `9` 或 `8` | 九肖一码有两种数量模式 |
| `/api/kaijiang/rd70i73lziizczak/0gmqnw/1` | 无 | 六不中，路径固定，无 Query 参数 |

### 2.2 共享响应字段规范

大多数资料接口共享相同的基础响应字段：

| 字段名 | 类型 | 是否必填 | 是否可空 | 示例 | 说明 |
|---|---|---|---|---|---|
| `term` | string | 是 | 否 | `"269"` | 期号 |
| `content` | string | 否 | 否 | `"鼠,牛,虎"` 或 JSON 字符串 | 预测内容。标记为「content JSON字符串」的接口必须返回合法 JSON 字符串，不能直接返回数组 |
| `res_code` | string | 是 | 否 | `"01,13,22,34,45,49"` | 开奖号码，逗号分隔，两位字符串 |
| `res_sx` | string | 是 | 否 | `"龙,鸡,马,羊,狗,鼠"` | 开奖生肖，逗号分隔，建议使用简体 |

**关键约束：**

- `res_code`、`res_sx` **不允许返回 `null`**，未开奖时必须返回空字符串 `""`。
- 标记为「content 为 JSON 字符串」的接口，`content` 必须是字符串形式的 JSON，例如 `"[\"鼠|05,17\",\"牛|04,16\"]"`，不可以直接返回数组。
- 号码建议保持两位字符串，如 `"01"`、`"09"`、`"49"`。
- 生肖建议使用简体：`龙`、`马`、`鸡`、`猪`（`ajax_interceptor.js` 会自动将繁体转简体，但后端直接返回简体更稳定）。

## 3. 模块接口明细

### 3.1 特邀家野两肖

- 来源文件：`061jy2x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getJyxiao2`
- 完整请求示例：`/api/kaijiang/getJyxiao2?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "xiao": "鼠,牛,虎,兔"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.2 左右

- 来源文件：`033zuoyou.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZyx`
- 完整请求示例：`/api/kaijiang/getZyx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.3 精品六肖

- 来源文件：`012liuxiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getXiaoma2`
- 完整请求示例：`/api/kaijiang/getXiaoma2?web={web}&type={type}&num=6`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `6`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.4 阴阳

- 来源文件：`044yinyang.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getYysx`
- 完整请求示例：`/api/kaijiang/getYysx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.5 四肖八码

- 来源文件：`027six8m.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getXiaoma2`
- 完整请求示例：`/api/kaijiang/getXiaoma2?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.6 单双四尾

- 来源文件：`003ds4w.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getDsWei`
- 完整请求示例：`/api/kaijiang/getDsWei?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "dan": "鼠,牛,虎,兔",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "shuang": "鼠,牛,虎,兔",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.7 单双

- 来源文件：`071ds.js`
- 方法：`GET`
- 路径：`/api/kaijiang/danshuang`
- 完整请求示例：`/api/kaijiang/danshuang?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.8 六肖

- 来源文件：`073sixiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.9 合数单双

- 来源文件：`006heshuds.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getHeds`
- 完整请求示例：`/api/kaijiang/getHeds?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.10 天地

- 来源文件：`043tiandi.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getTdsx1`
- 完整请求示例：`/api/kaijiang/getTdsx1?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.11 吃肉草菜

- 来源文件：`049rccx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getRccx`
- 完整请求示例：`/api/kaijiang/getRccx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.12 家野

- 来源文件：`040jiaye.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getJyzt`
- 完整请求示例：`/api/kaijiang/getJyzt?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.13 隐刺五肖

- 来源文件：`042ycwx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=5`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `5`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.14 黑白

- 来源文件：`039heibai.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getHbx`
- 完整请求示例：`/api/kaijiang/getHbx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.15 九肖

- 来源文件：`014jiuxiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=9`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `9`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.16 三肖

- 来源文件：`031wuxiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.17 特邀单双四肖

- 来源文件：`060ds4x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getDsnx`
- 完整请求示例：`/api/kaijiang/getDsnx?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "xiao_1": "鼠,牛,虎,兔",
      "xiao_2": "鼠,牛,虎,兔"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.18 跑马图/解跑马

- 来源文件：`011jiepaoma.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getXiaoma2`
- 完整请求示例：`/api/kaijiang/getXiaoma2?web={web}&type={type}&num=7`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `7`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "image_url": "/uploads/image/mock/example.jpg",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.19 四肖

- 来源文件：`030lflx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.20 成语平特尾

- 来源文件：`068chengyupw.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getCyptwei`
- 完整请求示例：`/api/kaijiang/getCyptwei?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "title": "成语示例"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.21 三期必中

- 来源文件：`023sanqibizhong.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getSanqiXiao4new`
- 完整请求示例：`/api/kaijiang/getSanqiXiao4new?web={web}&type={type}&num=7`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `7`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "name": "示例内容",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.22 天地

- 来源文件：`075tiandi.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getTdsx1`
- 完整请求示例：`/api/kaijiang/getTdsx1?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.23 10码

- 来源文件：`038ma10.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getCode`
- 完整请求示例：`/api/kaijiang/getCode?web={web}&type={type}&num=10`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `10`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.24 四季肖

- 来源文件：`050siji.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getSjsx`
- 完整请求示例：`/api/kaijiang/getSjsx?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.25 单双

- 来源文件：`004danshuang.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getDsxiao`
- 完整请求示例：`/api/kaijiang/getDsxiao?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "xiao": "鼠,牛,虎,兔"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.26 20码

- 来源文件：`032ma20.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getCode`
- 完整请求示例：`/api/kaijiang/getCode?web={web}&type={type}&num=20`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `20`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.27 一波

- 来源文件：`036ma12.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getYbzt`
- 完整请求示例：`/api/kaijiang/getYbzt?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.28 四尾八码

- 来源文件：`026siw8m.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getWeima2`
- 完整请求示例：`/api/kaijiang/getWeima2?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.29 16码

- 来源文件：`035ma16.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getCode`
- 完整请求示例：`/api/kaijiang/getCode?web={web}&type={type}&num=16`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `16`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.30 一字平肖

- 来源文件：`065yiziptx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getPingte`
- 完整请求示例：`/api/kaijiang/getPingte?web={web}&type={type}&num=1`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `1`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.31 风小子六肖

- 来源文件：`047liuxiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=6`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `6`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.32 文武

- 来源文件：`046wenwu.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getWwx`
- 完整请求示例：`/api/kaijiang/getWwx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.33 大小中特

- 来源文件：`002daxiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getDxzt`
- 完整请求示例：`/api/kaijiang/getDxzt?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.34 有无

- 来源文件：`045youwu.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getYwx`
- 完整请求示例：`/api/kaijiang/getYwx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.35 三连肖

- 来源文件：`067sanzipw.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getPingte`
- 完整请求示例：`/api/kaijiang/getPingte?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.36 林北

- 来源文件：`062linbei6x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getZhongte`
- 完整请求示例：`/api/kaijiang/getZhongte?web={web}&type={type}&num=6`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `6`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.37 文房四宝

- 来源文件：`053wfsb.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getBmzy`
- 完整请求示例：`/api/kaijiang/getBmzy?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.38 杀一肖

- 来源文件：`057s1x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShaXiao`
- 完整请求示例：`/api/kaijiang/getShaXiao?web={web}&type={type}&num=1`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `1`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.39 两肖+八码

- 来源文件：`069lxbm.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getX2jiam8`
- 完整请求示例：`/api/kaijiang/getX2jiam8?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "code": "01,02,03,04,05,06",
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.40 平特一尾

- 来源文件：`022pt1w.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getPtWei`
- 完整请求示例：`/api/kaijiang/getPtWei?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.41 两头

- 来源文件：`072liangtou.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getTou`
- 完整请求示例：`/api/kaijiang/getTou?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.42 杀七码

- 来源文件：`056s7m.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShama`
- 完整请求示例：`/api/kaijiang/getShama?web={web}&type={type}&num=7`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `7`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.43 杀两肖

- 来源文件：`058s2x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShaXiao`
- 完整请求示例：`/api/kaijiang/getShaXiao?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.44 风雨雷电

- 来源文件：`051fyld.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getFyld`
- 完整请求示例：`/api/kaijiang/getFyld?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.45 一字玄机

- 来源文件：`029yizixuanji.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getYzxj`
- 完整请求示例：`/api/kaijiang/getYzxj?web={web}&type={type}&num=6/12`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `6/12`。
- 成功响应示例：
```json
{
  "data": [
    {
      "jiexi": "示例内容",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "xiao": "鼠,牛,虎,兔",
      "zi": "示例内容"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.46 成语平肖

- 来源文件：`066chengyupx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getCypt`
- 完整请求示例：`/api/kaijiang/getCypt?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "title": "成语示例"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.47 六不中

- 来源文件：`019liubuzhong.js`
- 方法：`GET`
- 路径：`/api/kaijiang/rd70i73lziizczak/0gmqnw/1`
- 完整请求示例：`/api/kaijiang/rd70i73lziizczak/0gmqnw/1`
- 请求参数：
无 Query 参数或路径固定。
- 成功响应示例：
```json
{
  "data": [
    {
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "u6_code": "01,02,03,04,05,06"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.48 男女

- 来源文件：`020nn4x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getNnnx`
- 完整请求示例：`/api/kaijiang/getNnnx?web={web}&type={type}&num=4`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `4`。
- 成功响应示例：
```json
{
  "data": [
    {
      "nan": "鼠,牛,虎,兔",
      "nv": "鼠,牛,虎,兔",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.49 九肖一码

- 来源文件：`013jiux1m.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getXysxma`
- 完整请求示例：`/api/kaijiang/getXysxma?web={web}&type={type}&num=9/8`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `9/8`。
- 成功响应示例：
```json
{
  "data": [
    {
      "code": "01,02,03,04,05,06",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "xiao": "鼠,牛,虎,兔"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.50 三头中特

- 来源文件：`024santou.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getTou`
- 完整请求示例：`/api/kaijiang/getTou?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.51 三行

- 来源文件：`025sanhang.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getXingte`
- 完整请求示例：`/api/kaijiang/getXingte?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.52 双波

- 来源文件：`001sb.js`
- 方法：`GET`
- 路径：`/api/kaijiang/sbzt`
- 完整请求示例：`/api/kaijiang/sbzt?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.53 杀一头

- 来源文件：`018sha1tou.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShatou`
- 完整请求示例：`/api/kaijiang/getShatou?web={web}&type={type}&num=1`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `1`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.54 美丑

- 来源文件：`041meichou.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getJmxc`
- 完整请求示例：`/api/kaijiang/getJmxc?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.55 杀三尾

- 来源文件：`015sha3w.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShaWei`
- 完整请求示例：`/api/kaijiang/getShaWei?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.56 绝杀三肖

- 来源文件：`016sha3x.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShaXiao`
- 完整请求示例：`/api/kaijiang/getShaXiao?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.57 肥瘦

- 来源文件：`034feishou.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getFsx`
- 完整请求示例：`/api/kaijiang/getFsx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.58 平特一肖

- 来源文件：`074ptyx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getPingte`
- 完整请求示例：`/api/kaijiang/getPingte?web={web}&type={type}&num=1`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `1`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.59 胆大胆小

- 来源文件：`037dandaxiao.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getDxd`
- 完整请求示例：`/api/kaijiang/getDxd?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.60 红蓝绿肖

- 来源文件：`048hllx.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getHllx`
- 完整请求示例：`/api/kaijiang/getHllx?web={web}&type={type}&num=2`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `2`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.61 琴棋书画

- 来源文件：`052qqsh.js`
- 方法：`GET`
- 路径：`/api/kaijiang/qqsh`
- 完整请求示例：`/api/kaijiang/qqsh?web={web}&type={type}&num=3`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `3`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "鼠,牛,虎",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269",
      "title": "成语示例"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.62 推

- 来源文件：`zx.js`
- 方法：`GET`
- 路径：`/api/post/getList`
- 完整请求示例：`/api/post/getList?web={web}&type={type}&pc=72`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `pc`：文章/推荐位分类参数；固定值 `72`。
- 成功响应示例：
```json
{
  "data": [
    {
      "id": 1,
      "title": "推荐资料标题一"
    },
    {
      "id": 2,
      "title": "推荐资料标题二"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

### 3.63 杀半波

- 来源文件：`054sbanbo.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShaBanbo`
- 完整请求示例：`/api/kaijiang/getShaBanbo?web={web}&type={type}&num=1`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `1`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.64 杀半单双

- 来源文件：`055sbands.js`
- 方法：`GET`
- 路径：`/api/kaijiang/getShaBds`
- 完整请求示例：`/api/kaijiang/getShaBds?web={web}&type={type}&num=1`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- `type`：彩种/资料类型；本页面默认 `3`。
- `num`：模块数量/玩法参数；固定值 `1`。
- 成功响应示例：
```json
{
  "data": [
    {
      "content": "[\"鼠|05,17,29,41\",\"牛|04,16,28,40\"]",
      "res_code": "01,13,22,34,45,49",
      "res_sx": "龙,鸡,马,羊,狗,鼠",
      "term": "269"
    }
  ]
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```
- 特别说明：`content` 字段会被前端 `JSON.parse(...)`，必须返回合法 JSON 字符串。

### 3.65 公告弹窗

- 来源文件：`index.html`
- 方法：`GET`
- 路径：`/api/index/notice`
- 完整请求示例：`/api/index/notice?web={web}`
- 请求参数：
- `web`：站点 ID；本页面默认 `6`，Tab 切换后仍传当前全局 `web`。
- 成功响应示例：
```json
{
  "code": 600,
  "data": {
    "content": "<div>公告内容 HTML</div>"
  }
}
```
- 错误响应示例：
```json
{
  "code": 500,
  "message": "internal server error",
  "data": []
}
```

## 4. 非 Ajax 但前端会请求的资源

这些不是 JSON API，但后端/静态服务器也需要保证可访问：

- `/uploads/image/20250322/1742580086567063.png`
- `/uploads/image/20250322/1742580119746508.jpg`
- `/uploads/image/20250322/1742580130762983.jpg`
- `/uploads/image/...`：部分资料接口返回的 `image_url` 若不是 `http` 开头，前端会拼成 `httpApi + image_url`。
- `https://admin.shengshi8800.com/xgkj3.html`、`amkj2.html`、`xgkj2.html`：`kj.js` 会用 iframe 加载开奖页面。

## 5. 后端实现建议

### 5.1 数据处理链路

前端请求到达后端的路径有两种：

**路径 A — Next.js 显式映射（主要路径）：**

```
twsaimahui 前端请求
  → /api/kaijiang/getXiaoma2?web=6&type=3&num=6
  → Nginx 转发到 Next.js (端口 3000)
  → frontend/app/api/kaijiang/[...path]/route.ts
  → 根据 case 分支确定 modes_id（如 getXiaoma → modes_id=44）
  → Python /api/legacy/module-rows?modes_id=44&web=6&type=3
  → 查询 created.mode_payload_44 (优先) → public.mode_payload_44 (回退)
  → 返回 { modes_id, title, table_name, rows: [...] }
  → Next.js 数据映射函数格式化
  → 返回 { data: [{ term, content, res_code, res_sx, ... }] }
```

**路径 B — Python 兜底（fallback）：**

```
  → Next.js default 分支
  → 代理到 Python /api/kaijiang/getUnknownEndpoint?num=X
  → legacy/frontend_compat.py _handle_standard_kaijiang()
  → 使用 num 参数作为 modes_id 查询 mode_payload 表
  → 返回 { data: [...] }
```

### 5.2 实现方式选择

后端可按以下任一方式实现：

**方式 1（推荐）— Next.js 兼容层 + Python `/api/legacy/module-rows`**：

1. 在 Next.js 兼容层 `app/api/kaijiang/[...path]/route.ts` 中添加 case 分支
2. 确定每个 endpoint 对应的 `modes_id`
3. 实现数据映射函数（如需特殊字段）
4. Python 后端提供 `/api/legacy/module-rows` 端点（已实现）

**方式 2 — Python 原生 `/api/kaijiang/*` 路由**：

1. 直接使用 Python `legacy/frontend_compat.py` 中的 `handle_frontend_kaijiang_api`
2. 路由已注册在 `backend/src/routes/legacy_routes.py`（`add_prefix("GET", "/api/kaijiang/", ...)`）
3. 使用 `num` 参数作为 modes_id 查询对应的 `mode_payload_*` 表
4. 注意：此方式下 `num` 直接作为 modes_id 使用，需要确保 `num` 值与数据库中 modes_id 一致

### 5.3 modes_id 映射

已知的 modes_id 映射（从 Next.js 兼容层代码提取）：

| modes_id | 端点 | 业务名称 |
|---|---|---|
| 2 | getWei | 尾数 |
| 3 | getRccx | 吃肉草菜 |
| 8 | getHllx | 红蓝绿肖 |
| 12 | getTou | 两头/三头中特 |
| 20 | getShaWei | 杀三尾 |
| 26 | qqsh | 琴棋书画 |
| 28 | danshuang | 单双 |
| 31 | getDsnx | 特邀单双四肖 |
| 34 | getCode | 10码/16码/20码 |
| 38 | sbzt | 双波 |
| 42 | getShaXiao | 杀一肖/杀两肖/绝杀三肖 |
| 43 | getPingte (num=2) | 平特(2项) |
| 44 | getXiaoma/getXiaoma2 | 精品六肖/四肖八码/跑马图 |
| 45 | getHbnx/getHbx | 黑白 |
| 50 | getYjzy | 一句真言 |
| 52 | getSzxj | 四字玄机 |
| 53 | getXingte | 三行 |
| 56 | getPingte (num≠2) | 平特(其他) |
| 57 | getDxzt | 大小中特 |
| 58 | getShaBanbo | 杀半波 |
| 61 | getSjsx | 四季肖 |
| 63 | getJyzt | 家野 |
| 197 | getSanqiXiao4new | 三期必中 |

**未确定 modes_id 的端点**（约 28 个）目前走 Python 兜底路径，使用 `num` 参数值作为 modes_id。需要后续查询 `fetched_modes` 表确认真实映射。

### 5.4 通用实现原则

1. 保留公开 GET 接口，不强制鉴权。
2. 对所有 `/api/kaijiang/*` 接口，失败或无数据返回 `{ "data": [] }`，避免前端空指针。
3. 所有资料记录建议统一带 `term/res_code/res_sx`，即使某个模块暂时不用。
4. `web` 必须作为站点隔离参数使用，本页面默认传 `6`。
5. `type` 必须作为彩种隔离参数使用，根据前端传入的 type 值（1/2/3）返回对应彩种的数据。
6. 对 `content` 需 JSON 字符串的接口，后端应按字符串保存/输出，避免前端 `JSON.parse` 报错。
7. `/api/index/notice` 成功时必须返回 `code: 600`，否则前端会直接忽略公告内容。
8. `res_code` 和 `res_sx` 未开奖时返回空字符串 `""`，禁止返回 `null`。
9. 同一套 API 路径结构需要在不同域名下都可用（或通过网关/Nginx 统一转发）。
10. 号码统一使用两位字符串格式（`"01"`、`"09"`、`"49"`）。
11. 生肖统一使用简体中文。

### 5.5 新增端点检查清单

为每个 `/api/kaijiang/*` 端点实现后端接口时，请逐项确认：

- [ ] 确定正确的 `modes_id`（查 `fetched_modes` 表）
- [ ] 确认 `mode_payload_{modes_id}` 表存在且有数据
- [ ] 确认 `web`/`type` 过滤正确
- [ ] 确认 `res_code`/`res_sx` 不会返回 `null`
- [ ] 确认 content 是 JSON 字符串还是普通文本（见接口总览表）
- [ ] 确认特殊字段（`xiao`, `dan`, `shuang`, `nan`, `nv`, `title` 等）存在且非空
- [ ] 添加 CORS 头（如果 API 与前端不同域）
- [ ] 对 `/api/index/notice` 确认 `code=600`
- [ ] 对 `/api/post/getList` 确认 `pc=72` 数据存在
- [ ] XSS 过滤：`notice.content` 和 `post.title` 是 HTML 注入风险点
12. `data` 数组按 `term` 倒序排列，最新期在前。
13. GET 接口建议配置合理的 CORS 响应头。
14. `notice.content` 和 `post.title` 输出前必须过滤 XSS 危险内容。