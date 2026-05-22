# twcaibawang API / Backend Checklist

## Current Conclusion

`twcaibawang` 第一阶段接入，当前**不需要新增后端 API**。

现有前端兼容层已经可以复用现有后端公开接口完成：

- 站点配置：`web_id = 5`
- 默认开奖彩种：`lottery_type = 1`
- 统一开奖模块：复用 `frontend/public/vendor/shengshi8800/kj/local.html`

## Already Wired Frontend Compatibility Routes

当前已接入的兼容路由：

- `GET /wy.json`
- `GET /index/ajax/ttklsjl`
- `GET /index/index/history.html`
- `GET /index_files/pub.js`
- `GET /index_files/gg.js`

这些路由都只为 `twcaibawang` 提供兼容，不改变其他站点的既有行为。

## Existing Backend APIs That Are Enough Now

当前阶段实际使用、并且已经足够的后端接口：

1. `GET /api/public/latest-draw`
   - 用途：生成 `wy.json` 的当期开奖号码。
   - 前端适配：`frontend/app/wy.json/route.ts`

2. `GET /api/public/next-draw-deadline`
   - 用途：生成 `wy.json` 的 `nextexpect` 和 `nextTime`。
   - 前端适配：`frontend/app/wy.json/route.ts`

3. `GET /api/public/draw-history`
   - 用途：生成 `historyAO`，兼容 `wylhc.html` 历史开奖页。
   - 前端适配：`frontend/app/index/ajax/ttklsjl/route.ts`

## Existing Optional APIs You Can Reuse Later

这些接口当前不是 `twcaibawang` 首页运行必需，但后续做动态资料模块时可以直接复用：

1. `GET /api/public/site-page`
   - 聚合站点、开奖、模块历史数据。
   - 前端已有转发：`GET /api/lottery-data`

2. `GET /api/public/notice`
   - 站点公告弹窗。
   - 前端已有兼容：`GET /api/index/notice`

3. `GET /api/legacy/post-list`
   - 旧站图片/帖子列表。
   - 前端已有兼容：`GET /api/post/getList`

4. `GET/POST /api/predict/[mechanism]`
   - 预测机制统一入口。
   - 适合后续把静态资料块改成动态生成模块时复用。

## Backend Configuration Checklist

后端这阶段主要是核对配置，不是新增接口：

1. `managed_sites` 中确认 `web_id = 5` 的站点记录已启用。
2. 确认该站点绑定的 `lottery_type_id` 为你希望的默认彩种。
3. 确认 `lottery_draws` 中 `lottery_type = 1/2/3` 都已有正常开奖数据。
4. 确认 `/api/public/latest-draw`、`/api/public/next-draw-deadline`、`/api/public/draw-history` 在 PostgreSQL 当前数据上返回正常。

你前面已经明确：

- `web_id = 5` 已存在
- `lottery_type = 1/2/3` 已存在于 PostgreSQL

所以当前真正需要后端确认的重点，只剩：

- `managed_sites.web_id = 5` 对应站点的默认 `lottery_type_id`
- 三个 public draw API 的返回值是否与你实际业务数据一致

## APIs Not Needed Right Now

当前阶段**不需要**专门为 `twcaibawang` 新增这些后端能力：

- 专属 `twcaibawang` 开奖接口
- 专属 `twcaibawang` 历史接口
- 专属 `pub.js` / `gg.js` 后端接口
- 专属 Next.js API route 到 Python backend 的新桥接路径

原因是本阶段只是让旧站样式稳定跑起来，数据来源已经可以通过现有 public draw APIs 转换完成。

## What Will Need New Backend Work Later

如果你下一阶段要把首页大量静态“预测资料”改成真实动态内容，就需要继续补后端数据来源。那时建议分成两类：

1. 可以直接复用现有能力的模块
   - 已进入 `site_prediction_modules` 的标准预测模块
   - 可通过 `/api/public/site-page` 或 `/api/lottery-data` 读取的模块
   - 可通过 `/api/predict/[mechanism]` 单独生成/调试的机制

2. 需要新开发或扩展的模块
   - 目前仍是纯静态 HTML 文案、但数据库中没有对应 `mechanism_key / mode_id` 的资料块
   - 需要按 `web_id = 5` 单独排序、单独展示、单独命中的模块
   - 需要图片化、模板化输出的资料模块
   - 需要文章详情、栏目列表、分类页的数据接口

## Recommended Next Backend Additions For Dynamic Modules

如果你准备开始第二阶段动态化，建议优先补这几类：

1. `site_prediction_modules` 中补齐 `twcaibawang` 的模块配置
2. 为缺失的资料块确认 `mechanism_key`、`mode_id`、来源表
3. 若存在文章型资料页，再补：
   - 栏目列表接口
   - 文章详情接口
   - 站点栏目与静态 slug 的映射
4. 若存在图片资料页，再补：
   - 图片资源与期号绑定规则
   - 图片类模块的 API 输出字段

## Practical Recommendation

当前阶段可以先不动后端路由。

下一步如果你要继续推进，我建议按这个顺序：

1. 先验证 `twcaibawang` 首页、开奖 iframe、历史页在本地完整跑通。
2. 再梳理首页每一块预测资料，区分：
   - 可以直接映射到现有 `/api/lottery-data`
   - 需要新增 `site_prediction_modules`
   - 需要新增文章/图片类 API
3. 最后再决定是否把部分静态页改造成 Next 页面。
