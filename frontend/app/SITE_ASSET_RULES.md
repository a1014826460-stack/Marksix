# Site Asset Rules

`frontend/app` 下的多站点文件请遵循下面的约定，避免标题、favicon、静态资源路径分散在多个文件里难以维护。

## 单一配置源

所有站点级基础信息统一放在 [frontend/lib/sites.ts](/d:/pythonProject/outsource/Liuhecai/frontend/lib/sites.ts)：

- `routePath`
- `vendorIndexPath`
- `legacyPublicBasePath`
- `defaultWebId`
- `defaultLotteryTypeId`
- `forumTitle`
- `metadataTitle`
- `metadataDescription`
- `faviconPath`
- `headerImagePath`
- `shellCssPaths`
- `pageCssPaths`

## 页面层规则

- `app/<site>/layout.tsx` 只负责读取站点配置并导出 metadata。
- `app/<site>/page.tsx` 只负责读取站点配置并渲染页面。
- 不要在页面和 layout 中重复硬编码：
  - 标题
  - description
  - favicon 路径
  - vendor CSS 路径
  - 站点入口 URL

## 静态资源规则

- favicon 一律通过 `faviconPath` 配置。
- vendor CSS 一律通过 `pageCssPaths` 或 `shellCssPaths` 配置。
- 站点头图一律通过 `headerImagePath` 配置。
- 兼容老站资源时，优先使用站内路径或同源路径，避免直接依赖外域地址。

## 新增站点时

1. 先在 `frontend/lib/sites.ts` 新增完整配置。
2. 再添加对应的 `app/<site>/layout.tsx` 和 `app/<site>/page.tsx`。
3. 页面内部优先读取配置，不要再次写死 vendor 路径。
4. 如果站点有额外 CSS/图标/头图，也优先补到配置字段中。
