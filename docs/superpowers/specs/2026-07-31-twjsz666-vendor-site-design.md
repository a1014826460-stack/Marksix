# 台湾金手指（twjsz666）供应商站点设计

## 目标与边界

新增站点 `twjsz666`，站点名为“台湾金手指”，域名为 `www.twjsz666.com`。以 `frontend/public/vendor/Zz_hdx.cp567.cc/` 为模板，保留其 HTML、CSS、DOM 拓扑、导航、页脚、内部页面和现有脚本行为；仅为数据接入、同源安全和站点标识做必要修改。

现有工作区未提交改动必须保留。本次不执行远程操作，不新增专用预测算法，不重构为 React 页面。

## 架构与数据流

- `siteKey` 使用 `twjsz666`，入口为 `/vendor/twjsz666/index.html`，站点路由为 `/twjsz666`。
- 注册且仅注册三种彩票：台湾彩 `lotteryType=3`、澳门彩 `lotteryType=2`、香港彩 `lotteryType=1`，默认台湾彩。
- 使用现有 `iframe-vendor` 模式，保留 `kai.html`、`sx.html`、`wylhc.html` 等模板内部页面。
- `siteConfig` 是站点适配器中唯一的站点常量来源；可见站点名、域名和区域标题均从它派生。
- 父页面只接受已知 `kai.html` iframe 发出的同源 `postMessage({ type: "lottery-change", siteKey, lotteryType })`，校验 `event.origin` 和 `event.source` 后切换状态。
- 通过同源 `LotterySiteDataClient` 调用 `/api/sites/twjsz666/draw` 和 `/api/sites/twjsz666/prediction-modules`。缓存、请求和渲染状态按 `lotteryType` 隔离，迟到响应不能覆盖当前彩票。
- 模板页面在原有供应商动态脚本之前加载共享数据客户端和站点自有 `site-data-adapter.js`；适配器只更新既有文本、属性和样式槽，不创建、移动、替换或注入 DOM/CSS。
- 外部脚本、外链导航、外部图片和旧域名引用按 onboarding 规范移除或改为同源安全链接，同时保留对应节点和布局。

## 预测映射与 DOM 槽位

实现前盘点入口 HTML 的全部可见预测区块，重点包括稳定容器 `yxym`、`pttj`、`duilianpt`、`zl`、`jzlx`、`bizhong1`、`ptyx`、`sqbz`、`qxtable`、`xjct`、`pnzl`、`gongshi`。每个可见区块必须且只能归入以下一种状态：

1. 精确复用：后端模块维度、容量、行拓扑和命中规则一致。
2. 批准的组合复用：多个现有后端模块分别供给模板保留的命名子行。
3. 暂无后端资料：没有语义安全的现有模块时清空动态槽并显示 `暂无后端资料`。

每个区块建立独立 slot contract：

`容器选择器 -> 保留标签/标点 -> 期号、预测值、结果槽 -> canonical module key -> 命名 formatter/renderer -> 历史索引`

渲染要求：

- 统计每个区块的完整期号组，`historyLimit = min(max(区块期号组数), 20)`。
- 按归一化期号（优先 `issue`，否则 `year + term`）去重，按模板现有组数消费，不重复旧期号。
- 解析 `prediction.extra` 的 CSV、JSON、`生肖|号码` 等传输格式后写入独立槽位，不能暴露分隔符、原始数组或通用整行摘要。
- 结果只写特别号对应的 `开:号码生肖对/错` 或 `开:待开奖`；命中只使用模板既有黄色标记，并在切换/重绘前清除旧命中。
- 标题使用活动彩票区域前缀；供应商静态期号、号码、`????`、`对/错`、旧区域名和营销结果文本不得残留。

## 后端复用与授权

- 为 `twjsz666` 分配数据库中下一个可用 `siteId/webId`，注册站点 manifest、站点页面依赖、模式授权和版本化迁移。
- 优先使用已有成熟预测模块；每个复用模块记录维度、容量、字段、结果规则和目标槽位。没有安全近似时保持明确不可用状态，不把替代模块冒充供应商原机制。
- 生成并验证目标 `webId`、三种彩票类型的实际数据行；空的首选模块不能遮蔽有数据的批准回退模块。

## 测试与验收

- 静态契约：三种彩票、站点名/域名、入口路径、无外部 origin、无旧站哨兵，且原始导航、页脚和布局节点保留。
- 适配器契约：唯一 `siteConfig`、iframe 来源校验、`lotteryType` 请求透传、按彩票隔离缓存和每个区块的命名 renderer。
- 浏览器契约：依次点击台湾/澳门/香港标签；拦截请求验证 `lottery_type`；使用至少 8 个不同期号的真实形状 fixture，断言期号顺序、精确槽位、组合模块双来源、结果文本/命中状态、无分隔符和无供应商哨兵；验证缓存回程不会串台。
- 后端闭环：站点授权/迁移、目标站点数据行、同源 API payload、浏览器 DOM 槽位渲染四层均通过。
- 最终执行：`pnpm site:test-ui-baseline`、`pnpm site:test-data-client`、`pnpm site:test-adapter-registry`、站点浏览器契约、`tsc`、`pnpm site:validate --site-key twjsz666`、严格验证（外部 origin 已清理后）和生产构建。

## 方案自检

- 无未决 TODO/TBD；所有不可用预测均有明确空态。
- 架构保持供应商 DOM 边界，未引入共享 UI runtime 或新 UI。
- 站点名、域名和区域前缀只从 `siteConfig` 派生。
- 每个可见预测区块必须在实现阶段完成盘点、映射或明确不可用分类，不能只覆盖容易处理的区块。
