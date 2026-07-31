# 台湾金手指第二阶段 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 依次完成 twjsz666 全区块预测映射、三种彩票稳定性和所有供应商子页面内容闭环。

**Architecture:** 保持 iframe-vendor 和 existing-DOM-only 边界，在站点自有适配器内建立显式 section contracts 与命名 renderers。复用统一 same-origin API、现有预测模块和站点 manifest，通过静态契约、后端授权测试和 Playwright 完整扫描证明每一层。

**Tech Stack:** Legacy HTML/CSS/JavaScript, Next.js/TypeScript, Python/SQLite prediction services, Node contract tests, Python Playwright.

---

### Task 1: 建立完整 section inventory 与语义映射门槛

**Files:**
- Create: `frontend/test/twjsz666-section-inventory-contract.mjs`
- Modify: `frontend/public/vendor/twjsz666/site-data-adapter.js`
- Modify: `frontend/test/twjsz666-adapter-contract.mjs`

- [ ] **Step 1: 写失败的 inventory 测试**

从 `index.html` 读取每个 `.list-title` 及其稳定父容器，要求预测、组合、静态、不可用四类总数等于可见区块数，并要求“买码之前先上”内部九个 `.qxtable` 子卡单独列出。

- [ ] **Step 2: 运行测试确认失败**

Run: `node frontend/test/twjsz666-section-inventory-contract.mjs`

Expected: FAIL，指出当前 adapter 没有完整 `SECTION_CONTRACTS`，且存在通用 `renderUnavailableSection` fallback。

- [ ] **Step 3: 实现显式 section contracts**

在 adapter 中定义不可变 `SECTION_CONTRACTS`，每项包含 `id`、`titlePattern`、`containerSelector`、`classification`、`moduleKeys`、`rendererName`、`issueGroups` 和 supplier sentinels。为静态区块指定 `static`，语义不匹配区块指定 `unavailable`。

- [ ] **Step 4: 删除隐式 fallback**

`renderSection` 必须按 contract 的 rendererName 调用命名 renderer；未知可见区块抛出测试错误，不能落入统一整行 renderer。

- [ ] **Step 5: 运行 inventory/adapter 合同**

Run: `node frontend/test/twjsz666-section-inventory-contract.mjs && node frontend/test/twjsz666-adapter-contract.mjs`

Expected: PASS，inventory 数量闭合且没有未声明可见预测区块。

### Task 2: 补齐精确预测 renderers 与后端授权

**Files:**
- Modify: `frontend/public/vendor/twjsz666/site-data-adapter.js`
- Modify: `frontend/sites/twjsz666/site.manifest.ts`
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `backend/src/database/schema/prediction.py` only if exported compatibility constants need refreshing
- Modify: `backend/src/database/versioned_migrations.py`
- Modify: `backend/src/tests/unit/test_twjsz666_site_profile.py`
- Modify: `frontend/test/twjsz666-live-mapping-contract.py`

- [ ] **Step 1: 扩展失败 fixture**

为 `daxiao`、`shuangbo`、`pt1xiao`、`pt3xiao`、`pt1wei`、`4xiao8ma`、`jueshabanbo`、`juesha1wei`、`juesha2xiao`、`9xzt`、`yijuzhenyan` 提供八个 distinct issues、重复 issue、opened/future/hit rows 和真实 structured extra。

- [ ] **Step 2: 运行浏览器测试确认缺失映射失败**

Run: `python -m pytest -q frontend/test/twjsz666-live-mapping-contract.py`

Expected: FAIL，列出当前仍显示供应商快照或 `暂无后端资料` 的精确能力区块。

- [ ] **Step 3: 实现独立格式化器与 renderer**

分别实现大小、双波、平特一肖、平特三肖、平特一尾、四肖八码、绝杀二肖、一波、一尾、发财九肖和一句话中特码 renderer。每个函数只更新 contract 声明的 text slots；四肖八码保留两行拓扑，结果仅使用特别号。

- [ ] **Step 4: 为无精确能力的区块实现命名空态 renderer**

单双各四肖、一头一码24码、三头四尾、四字解平特肖、家禽 VS 野兽、精选22码、稳杀七码等各自拥有命名 unavailable renderer，逐槽清除期号、预测、结果和命中，不使用通用整行 fallback。

- [ ] **Step 5: 扩展 manifest 与站点模式授权**

加入实际渲染的 `juesha2xiao`、`9xzt` 等 module keys，更新 site dependency mode IDs 和版本化授权同步；测试断言 site 11 的授权集合与 adapter 实际依赖完全一致。

- [ ] **Step 6: 运行后端与浏览器合同**

Run: `python -m pytest -q backend/src/tests/unit/test_twjsz666_site_profile.py frontend/test/twjsz666-live-mapping-contract.py`

Expected: PASS，精确能力区块有数据，不安全近似区块为独立空态。

### Task 3: 强化彩票切换、缓存与错误降级

**Files:**
- Modify: `frontend/public/vendor/twjsz666/site-data-adapter.js`
- Create: `frontend/test/twjsz666-cache-error-contract.mjs`
- Modify: `frontend/test/twjsz666-live-mapping-contract.py`

- [ ] **Step 1: 写缓存/错误失败测试**

覆盖同一彩票请求去重、三种彩票独立缓存、stale 回程、首选空模块回退、重复 issue、快速 3→2→1 切换和 type 3 迟到响应。

- [ ] **Step 2: 运行测试确认竞态失败**

Run: `node frontend/test/twjsz666-cache-error-contract.mjs && python -m pytest -q frontend/test/twjsz666-live-mapping-contract.py`

Expected: FAIL，指出 error/stale 状态、空模块选择或缓存回程尚未满足合同。

- [ ] **Step 3: 实现按 lotteryType 隔离的资源状态**

分别维护 draw/prediction cache 与 in-flight map；响应携带发起时的 lotteryType，只有仍为 active 的响应调用 render。`distinctRows(module).length` 决定首选/回退，不使用 truthy object 判断。

- [ ] **Step 4: 实现错误和 stale 降级**

stale 保持已渲染数据并发 readiness；error 清理当前 contract 动态槽并显示其命名空态，绝不恢复静态 supplier snapshot。

- [ ] **Step 5: 强化 iframe 消息校验**

校验 origin/source/siteKey/type，拒绝不在 `{1,2,3}` 的 lotteryType；iframe 重载后重新绑定 tab，仍由父页面每次定位已知 iframe。

- [ ] **Step 6: 运行缓存和浏览器合同**

Run: `node frontend/test/twjsz666-cache-error-contract.mjs && python -m pytest -q frontend/test/twjsz666-live-mapping-contract.py`

Expected: PASS，所有竞态、缓存和错误场景不串台。

### Task 4: 完善子页面、导航、品牌与同源资源

**Files:**
- Modify: `frontend/public/vendor/twjsz666/index.html`
- Modify: `frontend/public/vendor/twjsz666/kai.html`
- Modify: `frontend/public/vendor/twjsz666/sx.html`
- Modify: `frontend/public/vendor/twjsz666/wylhc.html`
- Modify: `frontend/public/vendor/twjsz666/154.html` through `167.html`
- Create: `frontend/public/vendor/twjsz666/subpage-data-adapter.js`
- Create: `frontend/test/twjsz666-subpage-contract.mjs`
- Modify: `frontend/test/twjsz666-static-contract.mjs`

- [ ] **Step 1: 写全页面失败合同**

枚举 18 个 HTML 页面，断言站点 title/导航/页脚、无 external origin/旧品牌/旧域名/追踪脚本、图片 URL 同源、内部链接可解析到 `/vendor/twjsz666/` 或 `/twjsz666`。

- [ ] **Step 2: 运行合同确认失败**

Run: `node frontend/test/twjsz666-subpage-contract.mjs`

Expected: FAIL，列出缺少配置脚本、残留静态标题或不可达链接的子页面。

- [ ] **Step 3: 接入站点自有 subpage adapter**

子页面在供应商动态脚本前加载 `site-config.js` 和 `subpage-data-adapter.js`。adapter 只更新既有 title、站点名/域名文本和内部链接，不创建/移动/替换 DOM。

- [ ] **Step 4: 规范开奖记录与图片路径**

`wylhc.html` 只保留合法开奖记录槽和同源资源，清除预测快照；`sx.html`、内容页和页脚图片保持节点顺序/尺寸且全部同源。属性知识区块保持现状，不替换统一图库。

- [ ] **Step 5: 运行子页面/静态合同**

Run: `node frontend/test/twjsz666-subpage-contract.mjs && node frontend/test/twjsz666-static-contract.mjs`

Expected: PASS，所有页面清单闭合且资源/导航可达。

### Task 5: 执行四层数据与完整回归验收

**Files:**
- Modify: `frontend/test/site-ui-browser-contract.py`
- Modify: `frontend/test/twjsz666-live-mapping-contract.py`
- Test: all files changed above

- [ ] **Step 1: 扩展完整 inventory 浏览器扫描**

在台湾、澳门、香港及缓存回程后，逐 contract 断言 issue count/order、slot values、结果、命中、 retained labels、`br` 拓扑、无 supplier sentinel 和无跨彩票 marker。

- [ ] **Step 2: 验证四层数据链路**

运行站点 profile/授权测试、同源 API fixture、浏览器 DOM slot contract；对无本地生产数据的模块保留显式 unavailable 证据，不借用其他 web ID 数据。

- [ ] **Step 3: 执行站点回归门槛**

Run: `pnpm site:test-ui-baseline && pnpm site:test-data-client && pnpm site:test-adapter-registry && pnpm site:test-ui-browser`

Expected: PASS。

- [ ] **Step 4: 执行类型、严格验证与构建**

Run: `pnpm exec tsc -p frontend/tsconfig.json --noEmit && pnpm site:validate --site-key twjsz666 --strict && pnpm build:frontend`

Expected: PASS，external origins 为 0，生产构建成功。

- [ ] **Step 5: 执行最终差异检查**

Run: `git diff --check && git status --short`

Expected: 仅包含第二阶段文档、twjsz666 站点、相关授权和测试文件；没有远程操作或生成缓存噪音。
