# 旧 JS 隔离嵌入 + 新站外壳方案

## 1. 目标

这个方案的目标不是“把旧站逻辑重写进 React”，而是：

1. 新站继续负责外壳：
   - 顶部
   - 导航
   - 页脚
   - 彩种切换 UI
   - 后续新功能入口
2. 旧站继续负责最难复刻的预测模块显示：
   - 旧 CSS
   - 旧 JS
   - 旧 HTML 拼接逻辑
3. 在不破坏旧站显示一致性的前提下，逐步把旧模块迁移到 React。

## 2. 总体结论

如果要“前端显示完全按照旧站进行”，最佳方案不是“把旧 JS 直接塞进 React 页面执行”，而是：

- `新站外壳 + iframe 隔离旧页面/旧模块区`

原因：

1. 旧 JS 大量依赖 `document.write`
2. 旧 JS 依赖全局变量，如 `httpApi`、`type`、`web`
3. 旧 JS 假设自己运行在完整旧页面上下文里
4. React/Next.js 有 SSR 和 hydration，直接混跑风险很高

所以：

- `直接调用旧 JS` 不是最佳解
- `隔离运行旧 JS` 才是最佳解

## 3. 推荐架构

推荐分成 3 层：

### 3.1 外壳层

由 Next.js/React 负责：

- Header
- NavTabs
- 彩种切换按钮
- 页面容器宽度
- Footer
- 新功能按钮
- 后台埋点、鉴权、A/B 开关

### 3.2 旧站隔离层

由一个 iframe 页面负责：

- 加载旧站 CSS
- 加载旧站 JS
- 提供旧 JS 所需全局变量
- 提供旧 DOM 容器
- 按旧顺序插入模块

### 3.3 数据兼容层

后端同时提供两套输出：

1. 给旧 JS 的旧格式接口
2. 给 React 的新格式接口

注意：

- 不要求这两套接口“长得一样”
- 只要求它们来自同一份底层数据

## 4. 为什么不要直接在新站里执行旧 JS

不推荐下面这种方式：

```tsx
useEffect(() => {
  const script = document.createElement("script")
  script.src = "/vendor/shengshi8800/static/js/027ptw.js"
  document.body.appendChild(script)
}, [])
```

原因：

1. `document.write` 会破坏 React 已经渲染好的 DOM
2. 旧 JS 执行顺序很强，缺一个容器就可能错位
3. 多个旧 JS 会共享全局变量，容易串状态
4. CSS 会污染新站
5. 很难做精确销毁和重新挂载
6. 彩种切换时很难保证旧脚本正确重跑

所以正确姿势是：

- 让旧 JS 在独立文档里运行
- 新站只把它“当成一个黑盒显示区域”

## 5. iframe 方案的标准形态

推荐页面结构：

```text
Next.js Page
  ├─ Header
  ├─ NavTabs
  ├─ Game Tabs
  ├─ LegacyModulesFrame   <- iframe
  ├─ New React Blocks     <- 以后逐步替换
  └─ Footer
```

iframe 内部负责：

```text
legacy-embed.html
  ├─ 旧 CSS
  ├─ 旧环境变量初始化
  ├─ 旧模块容器 DOM
  ├─ 旧 JS 文件加载
  └─ 高度回传给父页面
```

## 6. 当前仓库里最适合的落地方向

结合当前项目结构，推荐这样落：

### 6.1 新增一个独立嵌入页

建议新增：

- `frontend/public/vendor/shengshi8800/embed.html`

或者：

- `frontend/app/legacy-embed/page.tsx`

但从兼容性角度看，优先推荐：

- `public` 下的纯静态 `embed.html`

原因：

1. 最接近旧站运行环境
2. 不受 React 生命周期影响
3. 最容易直接加载旧 CSS/JS
4. 最容易复制旧站 DOM 结构

### 6.2 新站新增一个 iframe 包装组件

建议新增组件：

- `frontend/components/LegacyModulesFrame.tsx`

职责：

1. 根据彩种生成 iframe URL
2. 监听 iframe 高度消息
3. 设置自适应高度
4. 控制显示哪个旧页面

### 6.3 新站首页保留外壳

由 [frontend/app/page.tsx](/abs/path placeholder) 继续输出新站框架；
实际模块区域先替换为 iframe。

更具体地说：

1. Header 继续保留
2. NavTabs 继续保留
3. Game Tabs 继续保留
4. `PredictionModules` 可暂时下线或 behind feature flag
5. 用 `LegacyModulesFrame` 取代旧模块区

## 7. 彩种切换怎么做

旧站脚本依赖 `type`：

- `taiwan = 3`
- `macau = 2`
- `hongkong = 1`

所以 iframe URL 应该带查询参数，例如：

```text
/vendor/shengshi8800/embed.html?type=3&web=4
/vendor/shengshi8800/embed.html?type=2&web=4
/vendor/shengshi8800/embed.html?type=1&web=4
```

然后 `embed.html` 在最开始读取 query string：

```js
const params = new URLSearchParams(location.search)
window.type = Number(params.get("type") || 3)
window.web = Number(params.get("web") || 4)
```

这样旧 JS 不需要改业务逻辑，只需要让它不要再把 `type=3` 写死。

## 8. 旧接口和新接口要不要统一

结论：

- `不要强行统一成一个格式`
- `要保证两套格式都稳定`

### 8.1 给旧 JS 的接口

必须保持旧格式。

也就是继续让旧 JS 拿到它期望的格式：

```json
{
  "data": [...]
}
```

里面字段还是它熟悉的：

- `content`
- `title`
- `jiexi`
- `hei`
- `bai`
- `xiao`
- `code`
- `xiao_1`
- `xiao_2`
- `tou`

### 8.2 给 React 的接口

继续保持新格式：

- `PublicModule`
- `PublicHistoryRow`
- `LotteryPageData`

### 8.3 真正该统一的地方

应该统一的是：

- 底层数据源
- 字段语义
- 兼容转换逻辑

不应该统一的是：

- 最终返回给旧 JS 和新 React 的 JSON 外观

## 9. 正确的数据策略

建议采用：

```text
数据库 / 底层数据表
  ├─ Legacy DTO Adapter  -> 给旧 JS
  └─ Modern DTO Adapter  -> 给新 React
```

也就是说：

1. 底层数据只维护一份
2. 旧接口做旧格式映射
3. 新接口做新格式映射

这样可以避免两个问题：

1. 为了旧 JS 把新站类型系统拖乱
2. 为了新站重构把旧 JS 直接搞坏

## 10. 如何确保“完全按旧站显示”

要做到这一点，关键不是“接口统一”，而是下面 6 件事。

### 10.1 运行环境一致

要保证 iframe 页面内：

- 旧 CSS 全部加载
- 旧 JS 全部按原顺序加载
- 旧 DOM 容器结构保持一致
- 全局变量保持一致

### 10.2 请求参数一致

旧 JS 发出的请求参数必须和旧站一致：

- `type`
- `web`
- `num`
- endpoint 名

### 10.3 返回格式一致

给旧 JS 的接口返回必须和旧站兼容格式一致。

不是“差不多”，而是：

- 字段名一致
- 字段位置一致
- JSON/字符串形态一致

例如：

- 有的模块要 `content: string`
- 有的模块要 `content: "[\"鼠|01\",...]"` 这种 JSON 字符串
- 有的模块要 `hei/bai`
- 有的模块要 `xiao_1/xiao_2`

### 10.4 资源顺序一致

旧站很多内容依赖脚本加载顺序。

要保证：

1. CSS 先加载
2. 公共基础脚本先加载
3. 模块脚本后加载
4. 需要的容器先在 DOM 里出现

### 10.5 布局容器一致

不要只引 JS 不引旧 HTML 容器。

很多旧脚本会默认某个 id/class 已存在，例如：

- `#sqbzBox`
- `#sbztBox`
- `#wxztBox`
- `.ds4xbox`

如果容器结构不一致，就算数据一样，显示也会错。

### 10.6 验收方式一致

必须做视觉验收，而不是只看接口通不通。

建议验收方式：

1. 同一彩种打开旧站原页
2. 打开新站 iframe 方案页
3. 按模块截图对比
4. 比较：
   - 标题
   - 括号
   - 颜色
   - 行数
   - 顺序
   - 高亮
   - 条件显示逻辑

## 11. 建议的实施阶段

### 阶段 1：先跑通完整旧内容

目标：

- 新站外壳 + iframe 成功显示旧模块区

做法：

1. 做 `embed.html`
2. 把旧站需要的 DOM 结构搬进去
3. 支持 `type/web` query
4. 保持旧 JS 原样加载
5. 父页面接收 iframe 高度

### 阶段 2：冻结兼容接口

目标：

- 旧 JS 在新环境下可稳定运行

做法：

1. 逐个 endpoint 核对旧返回格式
2. 给兼容接口做快照测试
3. 明确哪些字段是“不能改”的

### 阶段 3：逐模块 React 化

目标：

- 不是一次性重写全部，而是一块块替换

替换策略：

1. 先从结构简单的模块开始
2. React 版和 iframe 版并存
3. 单模块验收通过后再切换

### 阶段 4：最终收口

目标：

- 当 React 版足够完整时，再移除 iframe 中对应旧模块

## 12. 推荐的目录调整

建议新增：

```text
frontend/
  app/
    legacy-shell/
      page.tsx
  components/
    LegacyModulesFrame.tsx
  public/
    vendor/
      shengshi8800/
        embed.html
        static/
```

建议保留：

- `frontend/app/api/kaijiang/[[...path]]/route.ts`
- `frontend/lib/legacy-modules.ts`

因为这两个文件分别代表：

- 旧接口兼容层
- 新接口统一层

## 13. 这个方案的优点

1. 最容易先做到“显示完全像旧站”
2. 风险最小
3. 不会把 React 页面污染得很严重
4. 可以平滑迁移，不用一次重写 40+ 模块
5. 出问题时容易回退

## 14. 这个方案的缺点

1. 初期会同时维护两套前端逻辑
2. iframe 与父页面通信会增加复杂度
3. SEO 和首屏控制不如纯 React
4. 样式和高度同步需要额外处理
5. 最终仍然要做 React 替换，否则技术债会一直在

## 15. 最终建议

如果现在项目的第一优先级是：

- `显示必须和旧站一模一样`

那就应该选：

- `旧 JS 隔离嵌入 + 新站外壳`

并且具体实现上优先选：

- `iframe`
- `兼容旧接口`
- `双 DTO 输出`
- `逐模块 React 替换`

不要选：

- 在 React 组件里直接跑旧 JS
- 强迫旧接口和新接口完全共用同一个 JSON 外观

## 16. 一句话版本

最稳的做法是：

- `让新站管壳`
- `让 iframe 管旧模块`
- `让后端同时说两种“语言”`

这样既能保住旧站显示一致性，也能给新站后续替换留出空间。
