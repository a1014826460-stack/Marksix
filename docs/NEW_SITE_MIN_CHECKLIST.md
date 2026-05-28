# 新站点最小落地清单

这份清单只关注“把一个新站点最小可用地跑起来”。

## 0. 先确认当前架构

当前链路是：

```text
旧站 HTML/JS
  -> frontend /api/*
  -> Python backend /api
  -> 数据库
```

因此新站点是否可用，不只是复制一个静态目录，还至少要同时满足：

- 后端存在站点记录
- 后端存在该站点的预测模块记录
- 兼容 API 能接住旧站请求
- 旧站前端配置指向正确的 `web/type/apiBase`

## 1. 站点真实目录

新站点真实目录统一放在：

```text
frontend/public/vendor/<site_key>/
```

最少通常包含：

```text
index.html
embed.html
static/js/lottery_config.js
```

## 2. 后端站点记录

至少确认：

- `managed_sites` 有该站点记录
- `enabled=1`
- `web_id` 正确
- `lottery_type_id` 正确

重点注意：

- 前端旧站里的 `web` 对应的是 `managed_sites.web_id`
- 不是 `managed_sites.id`

## 3. 预测模块记录

至少确认：

- `public.site_prediction_modules` 有该站点记录
- 模块状态正常
- 默认表名能对应到真实数据表

推荐接口顺序：

1. `POST /api/admin/sites/{site_id}/prediction-modules/sync`
2. `GET /api/admin/sites/{site_id}/prediction-modules`
3. 如缺模块，再手动补模块配置
4. `POST /api/admin/sites/{site_id}/prediction-modules/generate-all`

## 4. 不再走的旧链路

当前不要再依赖：

- `utils.data_fetch`
- `POST /api/admin/sites/{site_id}/fetch`

当前原则是：

- 抓取链路已废弃
- 站点资料由后台管理员手动维护
- 模块生成由后台管理流程显式触发

## 5. 前端旧站配置

关键文件通常是：

[frontend/public/vendor/twsaimahui/static/js/lottery_config.js](/d:/pythonProject/outsource/Liuhecai/frontend/public/vendor/twsaimahui/static/js/lottery_config.js)

至少确认：

- `apiBase`
- `web`
- `type`

示例：

```js
window.LOTTERY_CONFIGS = {
  taiwan: {
    apiBase: "http://127.0.0.1:3000",
    web: 6,
    type: 3,
  },
}
```

### 5.1 强制检查 `web/type` 一致性

这里必须区分两层含义：

- `lib/sites.ts` 里的 `defaultWebId/defaultLotteryTypeId` 只是站点入口默认值
- 旧站 HTML/JS 运行时真正发出去的 `/api/*` 请求参数，才是最终生效值

至少同时检查下面几层：

1. `frontend/lib/sites.ts`
   - `defaultWebId`
   - `defaultLotteryTypeId`
   - `vendorIndexPath` / `embedPath`
2. 旧站入口页
   - `index.html`
   - `embed.html`
   - 是否在运行时重写 `window.web` / `window.type`
3. 彩种配置脚本
   - `static/js/lottery_config.js`
   - 是否存在“按 `type` 改写 `web`”的映射
4. 旧 JS 全局兼容逻辑
   - 是否直接读取 `window.web`
   - 是否把写入 `window.web` 反向解释成切换 `type`
5. 嵌套 iframe / 复用资源
   - 是否直接引用其他站点的 `local.html`、`index.html`、`static/js/*`
   - 是否隐式继承了其他站点的 `web/type` 规则

必须避免的错误：

- 只改 `lib/sites.ts` 的 `defaultWebId`，却没有检查旧站运行时脚本
- 默认入口是 `web=A`，但页面切换彩种后偷偷请求 `web=B`
- 一个站点复用另一个站点的开奖页或脚本，却没有记录这层耦合
- 以为后端严格按显式 `web` 隔离之后，前端发错 `web` 也会“自动正常”

## 6. 兼容 API 层

优先检查：

- `frontend/app/api/kaijiang/[[...path]]/route.ts`
- `frontend/app/api/post/getList/route.ts`
- `frontend/app/api/index/notice/route.ts`

如果新站旧 JS 请求了新的历史路径或特殊端点，需要在兼容层补映射。

## 7. 最小联调顺序

推荐按下面顺序排查，效率最高：

1. 图片列表
   - `/api/post/getList?web={web_id}&type={type}&pc=72`
2. 公告
   - `/api/index/notice?web={web_id}`
3. 一个通用预测模块
4. 一个特殊旧路径模块
5. 切换所有彩种 Tab，检查浏览器 Network 中实际发出的 `/api/kaijiang/*`、`/api/post/*`、`/api/index/*` 的 `web/type`
6. 页面整体打开后检查控制台是否存在 404、500、JSON 解析错误

## 8. 最常见问题

### `data=[]`

通常说明：

- 后端没有该 `web/type` 的数据
- 或模块生成未落到正确站点

### 200 但页面不显示

通常说明：

- 字段名与旧 JS 预期不一致
- 返回类型不一致
- 某些字段为空串而旧 JS 没做保护

### 404 / 500

通常说明：

- 兼容 API 没接住
- 兼容层内部映射缺失
- 后端模块数据未生成

## 9. 验收标准

一个“最小可用新站点”至少满足：

1. 有后端站点记录
2. 有站点预测模块记录
3. 模块生成流程可执行
4. `mode_payload_*` 里有对应 `web/type` 数据
5. `lottery_config.js` 的 `apiBase/web/type` 正确
6. 浏览器 Network 里实际请求出去的 `web/type` 与站点预期一致
7. 页面能看到图片、公告和至少几个预测模块

## 10. 参考文档

- [readme.md](/d:/pythonProject/outsource/Liuhecai/readme.md)
- [frontend/README.md](/d:/pythonProject/outsource/Liuhecai/frontend/README.md)
- [docs/FRONTEND_MULTI_SITE_GUIDE.md](/d:/pythonProject/outsource/Liuhecai/docs/FRONTEND_MULTI_SITE_GUIDE.md)
