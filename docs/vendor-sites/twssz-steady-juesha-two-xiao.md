# twssz「只是有点帅【稳杀二肖】」前端预测模块

## Section 合同

| 项目 | 定义 |
| --- | --- |
| TITLE | 只是有点帅【稳杀二肖】 |
| 稳定 DOM 锚点 | `p[data-prediction-section="juesha2xiao-steady"]`（首行锚点，后续同级 7 个 `p` 为历史组） |
| section ID / moduleKey | `juesha2xiao-steady` / `juesha2xiao` |
| 分类 | `mapped`，专用 renderer `renderSteadyJueshaTwoXiaoHistory` |
| 历史组数 | 8 |
| 槽位合同 | `data-prediction-issue`: 8；`data-prediction-content`: 8；`data-prediction-result`: 8；`content-secondary`: 0 |
| 业务语义 | 后端 `juesha2xiao` 生成的两生肖排除预测；每期取 `prediction.tokens[0..1]`。 |
| 命中规则 | 复用后端 `result.isCorrect`；已开奖只写特别号对/错，未来期只写“待开奖”。 |
| 空态 | 无对应行时清空三个叶节点，不显示模板期号、生肖或旧结果。 |

## 入口 HTML 原始展示片段（改造前）

```html
<p style="text-align: center; line-height: 33px;">绝杀二肖:
  <font color="#ff0000">【鸡羊】</font>开:</p>
<p style="text-align: center; line-height: 33px;">绝杀二肖:
  <font color="#ff0000">【鸡龙】</font>开:<font color="#FF0000">38蛇对</font></p>
```

接入后仍保留 8 个原有段落、样式与顺序，仅声明三个最小叶节点：
`issue` 写 `207期`，`content` 写 `绝杀二肖: 【鸡羊】开:`，`result` 写
`38蛇对` 或 `待开奖`。

## API 与数据流

请求：

```text
GET /api/sites/twssz/prediction-modules
  ?lottery_type={1|2|3}&history_limit=16&include_vendor=false
```

适配器读取响应外层的 `canonical_modules[]`，定位
`moduleKey === "juesha2xiao"`，再读取 `rows[]`。每行字段为：

- `issue` 或 `term`：期号；
- `prediction.tokens`：两生肖预测值；
- `result.isOpened`、`result.text`、`result.isCorrect`：开奖状态、特别号文本和命中状态。

请求、缓存和渲染按 `lottery_type` 隔离；切换彩种只渲染当前彩种的 8 个既有段落。
适配器不创建或替换 DOM 节点，不使用 `innerHTML`、`createElement`、`appendChild`、
`replaceChildren` 或 `document.write`。
