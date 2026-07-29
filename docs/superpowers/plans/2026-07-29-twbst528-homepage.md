# 台湾百事通首页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将供应商静态包注册为 `twbst528` 站点，并在首页以既有 DOM 槽位接入统一开奖和预测 API。

**Architecture:** 新站保留完整静态包并通过 iframe vendor 页面加载；配置和 DOM 适配器分别承担身份与数据渲染。前端 manifest 将站点纳入公共 API、域名匹配和流量统计上下文，后端须随后为同一 key 建立独立 profile。

**Tech Stack:** Next.js、TypeScript、原生 JavaScript、现有 LotterySiteDataClient、Playwright/Python、Node.js 契约测试。

---

### Task 1: 复制供应商包并建立身份配置

**Files:**
- Create: `frontend/public/vendor/twbst528/**`
- Create: `frontend/public/vendor/twbst528/site-config.js`
- Modify: `frontend/public/vendor/twbst528/index.html`

- [ ] 复制 `Zz_amxxc.cp567.cc` 的全部静态文件到 `twbst528`，保持相对资源路径。
- [ ] 为首页添加 `site-config.js` 和共享 `lottery-site-data-client.js`，位置在供应商动态脚本之前。
- [ ] 将首页 title、站点名、域名文本和无效外部数据入口替换为可由 `siteConfig` 更新的既有文本槽位；保留供应商 DOM/CSS。
- [ ] 验证：`Test-Path frontend/public/vendor/twbst528/index.html` 返回 `True`。

### Task 2: 建立首页 DOM 槽位映射并先写失败测试

**Files:**
- Create: `frontend/test/twbst528-live-mapping-contract.py`
- Modify: `frontend/public/vendor/twbst528/index.html`

- [ ] 列出首页所有稳定 `tbody` ID、三列历史表和固定资料卡的期组数。
- [ ] 测试供应商首页存在三彩标签、主导航、首期预测 `tbody` 和页脚；测试 API 结果只能进入该模块的 `td` 叶节点。
- [ ] 运行：`D:\python\python.exe frontend/test/twbst528-live-mapping-contract.py`。
- [ ] 预期：因 `site-data-adapter.js` 尚不存在而失败。

### Task 3: 实现既有 DOM 数据适配器

**Files:**
- Create: `frontend/public/vendor/twbst528/site-data-adapter.js`
- Modify: `frontend/public/vendor/twbst528/index.html`

- [ ] 定义模块标题到后端 mechanism key 的显式映射，未批准模块只清空自身动态槽位并显示“暂无后端资料”。
- [ ] 按每个表的现有 `tr` 一行一期开写入期号、预测和开奖结果；命中仅复用已有黄色背景叶节点。
- [ ] 绑定三个玩法标签，验证 `postMessage` 来源/iframe 后调用 `selectLottery(lotteryType)`；按当前玩法缓存结果。
- [ ] 运行 Task 2 测试，预期通过。

### Task 4: 注册前端站点

**Files:**
- Create: `frontend/sites/twbst528/site.manifest.ts`
- Create: `frontend/sites/twbst528/site-adapter.ts`
- Create: `frontend/app/twbst528/page.tsx`
- Create: `frontend/app/twbst528/layout.tsx`
- Modify: `frontend/sites/site-manifests.generated.ts`
- Modify: `frontend/lib/sites.ts`
- Modify: `frontend/lib/site-platform/site-adapter-registry.ts`
- Modify: `frontend/lib/site-platform/site-ui-baseline.ts`
- Modify: `frontend/test/run-site-adapter-registry-contract.mjs`

- [ ] 使用 `siteKey=twbst528`、域名 `www.twbst528.com`/`twbst528.com`、路由 `/twbst528` 和独立预留 `siteId/webId=10` 注册 manifest。
- [ ] 增加 iframe 路由和元数据，注册 adapter、UI baseline 与测试读取路径。
- [ ] 运行：`pnpm site:sync-manifests`，然后 `pnpm site:test-adapter-registry`。
- [ ] 预期：新站被注册且 adapter 完整。

### Task 5: 验证与交接

**Files:**
- Modify: `skills/vendor-site-onboarding/SKILL.md`（仅在发现新的通用规则时）

- [ ] 运行：`pnpm site:validate --site-key twbst528`。
- [ ] 运行：`pnpm site:test-ui-baseline`、`pnpm site:test-ui-browser`、`pnpm --filter @liuhecai/frontend exec tsc --noEmit`、`pnpm build:frontend`。
- [ ] 运行：`git diff --check`。
- [ ] 记录后端启用前置条件：创建 managed site 的 web_id 10、blueprint `twbst528` 及经审计的模块授权；不得复用现有站点资料。

