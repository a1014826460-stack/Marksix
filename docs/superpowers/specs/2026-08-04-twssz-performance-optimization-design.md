# twssz 前端性能优化设计

## 背景与证据

`twssz` 供应商入口 HTML 约 1.16 MB，包含 71 个表格、335 行、629 个单元格、
2095 个 `font`、1260 个 `span` 和 187 张图片。页面首次加载还会分别请求
`history_limit=1` 与 `history_limit=16` 的预测接口。后一响应约 1.31 MB，包含
45 个模块和约 624 条历史记录；每条 canonical row 重复携带完整 `raw` 数据。

本次优化不改变供应商 HTML 拓扑、模块数量、历史组数、文字格式、彩种切换语义、
缓存隔离规则和既有同源 API 身份。

## 方案比较

### 方案 A：仅删除首次 `history_limit=1` 请求

改动最小，可立即减少一次约 98 KB 请求和一次局部渲染，但 1.31 MB 历史响应、
同步 JSON 解析和全量 DOM 写入仍然存在。

### 方案 B：合并请求、精简响应并分批渲染（采用）

首次只请求一次 `history_limit=16`。为站点数据客户端增加显式 compact 查询，
由 Next.js compatibility 层裁剪 canonical row，仅返回 renderer 使用的字段。
首屏模块先渲染，剩余映射在浏览器空闲批次处理。该方案兼顾传输、解析和主线程
开销，且不改变后端公共完整响应及其他站点。

### 方案 C：重写模板为虚拟列表或 React 页面

潜在性能最好，但会破坏供应商唯一 UI 基线、稳定 DOM 槽位及已有 adapter 合同，
不符合本次范围。

## 数据流设计

1. `twssz/site-data-adapter.js` 初始化时只调用历史预测加载，参数保持
   `lottery_type`、`history_limit=16`、`include_vendor=0`，新增 `compact=1`。
2. `lottery-site-data-client.js` 将 compact 作为预测请求与缓存 key 的一部分，避免
   完整响应和精简响应互相污染。
3. `/api/sites/{siteKey}/prediction-modules` 仅在明确收到 `compact=1` 时裁剪响应。
   完整接口默认行为保持不变。
4. compact row 保留：`issue`、`year`、`term`、`prediction`、`result`、`status`、
   顶层 `image_url`，以及显式的结构化扩展字段。不得返回完整数据库 `raw`。
5. 天地模块不再读取 `row.raw.xiao`，而从 canonical `prediction.tokens/groups/extra`
   获取同义结构化值。图片模块优先读取 `prediction.imageUrl` 或顶层 `image_url`。
6. 首屏 A级、AAA级和明确位于首屏的模块同步渲染；其余映射按固定批次经
   `requestIdleCallback`（降级到 `setTimeout`）执行。每次彩种切换带 generation
   token，旧批次不得覆盖新彩种。

## 缓存与切换

- `lottery_type`、`historyLimit`、`includeVendor`、`compact` 共同组成缓存 key。
- 每种彩票只允许一个 16 期历史请求；返回缓存彩种时复用已解析 module map。
- 快速切换时，迟到响应和旧渲染批次必须检查当前彩票与 generation token。
- 切换到尚无缓存的彩票时，只清理已有动态叶节点，不改 DOM 结构。

## 错误处理

- 精简请求失败时继续使用数据客户端现有 stale/durable cache。
- 无可用历史数据时保持当前命名空态，不恢复供应商静态预测内容。
- compact 字段缺失不得回退读取完整 `raw`；对应叶节点显示既有空态。

## 测试与验收

1. 静态合同断言初始化不再调用 `historyLimit: 1`，只调用一次 16 期加载。
2. 数据客户端合同断言 compact 进入 URL 与缓存 key，并按三种彩票隔离。
3. API 路由测试断言默认响应仍含完整兼容数据，`compact=1` 不含 row `raw`，但
   天地和图片 renderer 所需字段仍存在。
4. 浏览器合同覆盖三种彩票切换、缓存回切、16 期历史、期号/正文/结果/命中、
   天地模块和 `sxztu` 图片。
5. 性能门槛：本地 `history_limit=16&compact=1` 响应体相对现状显著下降；首屏
   预测网络请求由两次降为一次；不得增加 console/page error。
6. 执行 `pnpm site:validate --site-key twssz`、相关前后端测试、TypeScript 检查和
   `git diff --check`。

## 非目标

- 不压缩或重写供应商 HTML。
- 不删除 16 期历史记录或预测模块。
- 不改变数据库数据、预测生成规则或站点授权。
- 不部署服务器；部署需要当次消息另行明确授权。
