# 台湾金手指第二阶段完善设计

## 目标

在已完成的 `twjsz666` 供应商站点骨架上，按 A → B → C 完成预测资料闭环、生产稳定性与内容页面完整性。继续保留供应商 HTML、CSS、DOM 拓扑和视觉结构，不引入共享 UI runtime，不新增重复预测算法，不执行远程操作。

## 阶段 A：完整预测资料闭环

### 可见区块清单

入口页全部 `.list-title` 区块必须进入机器可读 inventory。每个区块只能归入：精确实时映射、批准的组合映射、明确不可用、静态非预测内容。

实时候选包括单双各四肖、一头一码24码、发财九肖、三头四尾、平特一肖、四字解平特肖、公开资料、双波中特、家禽 VS 野兽、平特三肖、四肖八码、大小中特、七尾中特、平特一尾公式、精选22码、绝杀二肖、绝杀一波、绝杀一尾、稳杀七码、一句话中特码。属性知识、图片展示、普通开奖导航和页脚属于静态非预测内容。

### 语义映射

- 绑定前记录预测维度、数量、包含/排除含义、组合字段、行数和命中规则。
- 优先精确模块：`daxiao`、`shuangbo`、`pt1xiao`、`4xiao8ma`、`jueshabanbo`、`juesha1wei`、`juesha2xiao`、`yijuzhenyan` 等只能绑定语义一致的区块。
- 删除现有不安全近似映射，例如不能将 `9xiao12ma` 当作一头一码24码，也不能将生肖模块当作头尾模块。
- 组合区块逐子行声明 module key、字段、formatter 和命中规则；缺失子字段只清理该槽并显示 `暂无后端资料`。
- 每个 inventory 条目注册显式命名 renderer，禁止未匹配区块落入统一整行 renderer。

### DOM 槽位与历史

- 每个区块记录：容器选择器、保留标签、期号槽、预测槽、结果槽、module key、formatter、历史索引。
- `historyLimit = min(max(完整期号组数), 20)`；按规范化 issue 去重后再映射历史索引。
- 写入前解析 CSV、JSON、数组和 `标签|号码`；不得暴露传输分隔符或通用摘要句。
- 只显示特别号结果；未来期显示 `开:待开奖`。命中只使用模板既有黄色节点，并在切换前清除。
- 浏览器契约逐区块断言行/单元格/期号顺序/标签/换行/命中和供应商哨兵清理。

## 阶段 B：生产稳定性

### API 与缓存

- 浏览器仅请求同源 `/api/sites/twjsz666/*`。
- draw/prediction 请求、缓存和 in-flight promise 按 `lotteryType` 隔离并去重。
- 明确处理 `ready`、`stale`、`error`；stale 可以保留已知数据，error 不能恢复供应商快照。
- 模块选择以 distinct row 数为准；空的首选模块不能遮蔽已批准且有数据的回退。
- 客户端和服务端共同保证最多 20 个 distinct issues。

### 跨 iframe 状态

- `kai.html` tab 只发送 `{ type, siteKey, lotteryType }`，不从标签文本推断。
- 父页面每次消息重新定位 draw iframe，校验 `origin`、`source`、`siteKey` 和 lotteryType 取值。
- 快速切换、iframe 重载、迟到响应和缓存回程不能覆盖当前彩票。

### 资源与错误边界

- 全量扫描所有 HTML/CSS/JS 的 external origin、动态执行、旧域名和供应商脚本。
- 停用不必要追踪脚本、修复 iframe URL/integrity/404；图片只接受同源 URL。
- 增加 API 超时、空数据、重复期号、错误、stale、迟到响应和缓存回程测试。

## 阶段 C：内容与页面完整性

### 子页面与导航

- 页面清单覆盖首页、`kai.html`、`sx.html`、`wylhc.html` 和 154–167 内容页。
- 所有内部链接使用配置的站点 base path/route 生成；无供应商端口、域名和追踪参数。
- 记录页区分开奖历史和预测快照：开奖历史接入现有同源数据来源；预测快照必须映射或清空。

### 品牌与 metadata

- 页面 title、站点名、域名、区域前缀、metadata、favicon 和 footer copyright 从站点配置派生。
- 清理旧年份、旧供应商广告语、旧域名和静态“已验证/必中”结果；保留通用栏目标签和结构。

### 图片与页脚

- 保留模板图片节点、尺寸、顺序和布局，路径只允许 `/vendor/twjsz666/...` 或 `/uploads/...`。
- 本阶段不把属性知识替换为统一图库；只清理失效/外部路径并验证可加载。
- 为每个子页面增加标题、导航、页脚、同源图片和固定内容 baseline。

## 验收门槛

1. inventory 中 mapped、approved composite、unavailable、static 的总数等于全部可见区块数。
2. 三种彩票和缓存回程均通过完整 inventory 浏览器扫描。
3. 站点授权/迁移、目标 web ID 数据行、同源 API payload、DOM slot 渲染四层独立验证。
4. 所有子页面无外部 origin、旧站身份和预测快照哨兵。
5. `site:test-ui-baseline`、`site:test-data-client`、`site:test-adapter-registry`、`site:test-ui-browser`、TypeScript、严格站点验证、后端聚焦测试和生产构建全部通过。

## 自检

- 无占位符或未决产品决定。
- 范围按 A → B → C 顺序执行，A 的 DOM contracts 是 B/C 的基础。
- 未引入重设计、共享 DOM mount 或重复预测算法。
- 无远程部署、数据库迁移执行或服务器操作。
