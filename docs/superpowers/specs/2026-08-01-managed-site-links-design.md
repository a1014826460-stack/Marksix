# 动态站点链接与三行预测展示设计

## 目标

为全部已注册前端站点建立统一的动态外部链接模块。链接只能来自后端 `managed_sites` 表中已启用且域名非空的站点，排除当前站点，并随数据库增删改自动更新。同时将“期号、正文、开奖结果”同处一行的预测展示统一为三个独立块级叶节点，并把两项要求写入 `vendor-site-onboarding` 规范。

## 数据边界

- 数据源为 `managed_sites.id/name/domain/blueprint_name/enabled`。
- 公共响应只暴露 `name`、规范化后的 `domain`、`url` 和可公开的 `site_key`；不暴露 token、notes、内部授权或预测配置。
- 只选择 `enabled = 1` 且 `TRIM(domain) <> ''` 的记录，排除 `blueprint_name` 或域名匹配当前站点的记录，按 `id ASC` 排序。
- 域名允许数据库保存纯主机名或 HTTP(S) URL。服务端解析后只保留主机名，拒绝用户名、密码、查询、片段、非 HTTP(S) 协议和非法主机名；输出 URL 统一为 `https://{host}/`。
- 同一主机名只返回一次。无合法链接时返回空数组，不回退到供应商硬编码外链。

## API

后端新增：

`GET /api/public/site-links?current_site_key={siteKey}`

响应：

```json
{
  "links": [
    {
      "site_key": "shengshi8800",
      "name": "盛世台湾六合彩",
      "domain": "www.tw8800.com",
      "url": "https://www.tw8800.com/"
    }
  ]
}
```

Next 新增同源代理：

`GET /api/site-links?site_key={siteKey}`

代理先通过 manifest registry 校验 `site_key`，再请求 Python 公共接口。失败时返回结构化错误；前端组件保留标题并清空链接槽，不显示旧供应商链接。

## 共享组件

共享实现位于 `frontend/public/vendor/_shared/managed-site-links.js`，注册自定义元素：

```html
<managed-site-links site-key="twjsz666"></managed-site-links>
```

- 组件请求同源 `/api/site-links?site_key=...`。
- 组件只拥有并更新自身内部链接子树；动态站点数量变化时允许在该边界内创建或删除重复 `<a>`。
- 每个链接显示数据库站点名称，使用 `target="_blank"` 和 `rel="noopener noreferrer"`。
- 采用安静的四列网格，窄屏两列；不使用卡片嵌套、营销说明或硬编码品牌列表。
- 请求失败或返回空数组时，标题保留，链接区为空，不恢复模板外链。
- 当前站点由 `site-key` 属性显式传入，禁止通过可见标题或当前 host 猜测。

## 全站挂载

- 7 个供应商/legacy DOM 入口页加载共享脚本，并在统一属性图片模块之前挂载自定义元素。
- `twjsz666` 用共享组件替换“最快开奖（旗下网站）”硬编码表格，保留该区域在页尾的位置，不保留旧链接文字与图片占位 URL。
- `twcaibawang` 通过 React 模板的共享页尾渲染路径挂载相同自定义元素，并在客户端确保共享脚本只加载一次。
- 所有 8 个 manifest 站点必须在静态契约中出现且只出现一个组件实例。后续新增站点的 onboarding 契约自动要求挂载。

## 三行预测展示

当一个历史预测重复单元同时含有期号、正文和开奖结果时，三个字段必须使用三个独立、既有或预先声明的最小叶节点，并采用块级展示：

```html
<font data-prediction-issue>180期 一句话</font>
<span data-prediction-content>「预测正文」</span>
<font data-prediction-result>开:04兔错</font>
```

- 禁止用整行 `textContent` 拼成一句。
- 不要求把本来就是三列的表格改成单列；该规则只针对三个语义字段原本挤在同一文本流的单元格。
- 三个字段使用 `display: block`，正文可自然换行，期号和结果不得与正文粘连。
- 当前 `twjsz666` 一句话模块作为基准；全站扫描命中的同类模块并按各自 DOM slot contract 修复。

## SKILL 规范

`skills/vendor-site-onboarding/SKILL.md` 新增：

1. 三字段同单元格时必须三行独立展示，并写浏览器计算样式契约。
2. 外部站点链接禁止硬编码；只能使用公共站点链接 API 和共享组件。
3. 组件必须排除当前站点、仅展示启用域名、使用 HTTPS 和安全新窗口属性。
4. 新增站点必须挂载唯一共享组件；数据库变化不应要求修改站点 HTML。

## 验收

1. 后端单测覆盖启用过滤、当前站点排除、去重、非法域名和 HTTPS 规范化。
2. Next 路由契约覆盖 site key 校验、参数透传、成功和后端失败。
3. 共享组件契约覆盖动态数量、安全属性、空数据和错误清理。
4. 8 个 manifest 站点各有唯一挂载，且入口文件不再包含已知供应商外部域名。
5. 浏览器验证数据库 fixture 增删后链接数量和顺序变化，当前站点不出现。
6. 浏览器验证所有命中的期号/正文/结果节点计算样式为块级。
7. 运行后端聚焦测试、共享站点测试、TypeScript、严格站点校验与生产构建。

## 自检

- 无占位符或未决产品决定。
- 公共响应不泄露管理字段。
- 动态 DOM 创建权限仅限共享组件自身拥有的重复链接子树。
- 不修改统一开奖模块，不执行远程或数据库迁移操作。
