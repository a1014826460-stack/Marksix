# 台湾百事通静态资料页动态化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将台湾百事通首页高手榜 16 个资料页及其余相同拓扑资料页接入独立后端预测资料。

**Architecture:** 页面专属 existing-DOM adapter 以页面编号选择显式模块合同，读取 canonical prediction rows 并只更新供应商 `p` 内的叶节点。后端站点 10 profile 授权对应机制，接口维持 `web_id=10` 隔离。

**Tech Stack:** Next.js 同源 API、原生浏览器 JavaScript、Python Playwright、Python pytest、PostgreSQL/SQLite 迁移。

---

### Task 1: 固化页面合同与失败测试

**Files:**
- Create: `frontend/test/twbst528-static-article-contract.mjs`
- Create: `frontend/test/twbst528-static-article-contract.py`

- [ ] **Step 1: Write the failing static contract**

```js
for (const page of ["141", "142", "143", "144", "145", "146", "147", "148", "149", "150", "151", "152", "153", "154", "155", "156"]) {
  assert(indexFor(page).includes('static-article-data-adapter.js'))
}
```

- [ ] **Step 2: Run the contract and verify it fails**

Run: `node frontend/test/twbst528-static-article-contract.mjs`

Expected: failure because the pages do not load the adapter.

- [ ] **Step 3: Write a browser contract**

```python
assert article.locator(".article-content > p").count() == 8
assert "第510期" in article.locator("p").first.inner_text()
assert "供应商旧期号" not in article.inner_text()
```

- [ ] **Step 4: Run the browser contract and verify it fails**

Run: `D:\python\python.exe frontend/test/twbst528-static-article-contract.py`

Expected: failure because API data is not rendered.

### Task 2: 建立资料页 existing-DOM adapter

**Files:**
- Create: `frontend/public/vendor/twbst528/static-article-data-adapter.js`
- Modify: `frontend/public/vendor/twbst528/141.html`
- Modify: `frontend/public/vendor/twbst528/142.html`
- Modify: `frontend/public/vendor/twbst528/143.html`
- Modify: `frontend/public/vendor/twbst528/144.html`
- Modify: `frontend/public/vendor/twbst528/145.html`
- Modify: `frontend/public/vendor/twbst528/146.html`
- Modify: `frontend/public/vendor/twbst528/147.html`
- Modify: `frontend/public/vendor/twbst528/148.html`
- Modify: `frontend/public/vendor/twbst528/149.html`
- Modify: `frontend/public/vendor/twbst528/150.html`
- Modify: `frontend/public/vendor/twbst528/151.html`
- Modify: `frontend/public/vendor/twbst528/152.html`
- Modify: `frontend/public/vendor/twbst528/153.html`
- Modify: `frontend/public/vendor/twbst528/154.html`
- Modify: `frontend/public/vendor/twbst528/155.html`
- Modify: `frontend/public/vendor/twbst528/156.html`

- [ ] **Step 1: Add shared client and adapter before supplied scripts**

```html
<script src="site-config.js"></script>
<script src="/vendor/_shared/lottery-site-data-client.js"></script>
<script src="static-article-data-adapter.js"></script>
```

- [ ] **Step 2: Implement page number contracts**

```js
var PAGE_CONTRACTS = {
  "141": { moduleKey: "title_198", label: "逢买必中" },
  "142": { moduleKey: "juesha1wei", label: "绝杀①尾" },
  "156": { moduleKey: "yijuzhenyan", label: "一句中特" }
};
```

- [ ] **Step 3: Implement smallest-leaf renderers**

```js
function renderArticleRows(rows, contract) {
  articleRows().forEach(function (node, index) {
    writeExistingTextLeaves(node, formatArticleRow(rows[index], contract));
  });
}
```

- [ ] **Step 4: Run first-stage contracts**

Run: `node frontend/test/twbst528-static-article-contract.mjs; D:\python\python.exe frontend/test/twbst528-static-article-contract.py`

Expected: both commands pass.

### Task 3: 授权站点 10 的页面机制并验证隔离

**Files:**
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `backend/src/database/versioned_migrations.py`
- Modify: `backend/src/tests/unit/test_twbst528_page_dependencies.py`

- [ ] **Step 1: Add a failing authorization assertion**

```python
assert required_mode_ids_for_site_key("twbst528") == (
    198, 20, 483, 14, 5, 47, 279, 66, 53, 132, 26, 470, 12, 50,
)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `D:\python\python.exe -m pytest backend/src/tests/unit/test_twbst528_page_dependencies.py -q`

Expected: failure because page-only mechanisms are absent.

- [ ] **Step 3: Add the distinct page dependencies and migration synchronization**

```python
("title_198", 198), ("juesha1wei", 20), ("sitouzhongte", 483),
("title_14", 14), ("title_5", 5), ("title_47", 47),
```

- [ ] **Step 4: Re-run focused backend tests**

Run: `D:\python\python.exe -m pytest backend/src/tests/unit/test_twbst528_page_dependencies.py backend/src/tests/unit/test_public_module_history.py -q`

Expected: PASS and site 10 remains the only history source.

### Task 4: Register, verify, and audit remaining pages

**Files:**
- Modify: `frontend/sites/twbst528/site-adapter.ts`
- Modify: `frontend/test/twbst528-live-mapping-contract.mjs`
- Modify: `docs/superpowers/specs/2026-07-29-twbst528-static-article-dynamic-design.md`

- [ ] **Step 1: Register static article selectors**

```ts
predictions: { resource: "predictions", selectors: ["#zhenyan_ping_xiao", ".article-content > p"] }
```

- [ ] **Step 2: Write the remaining-page audit table**

Record each remaining page’s title, issue-group topology, mechanism candidate, authorization status, and exact empty state before implementation.

- [ ] **Step 3: Run full verification**

Run: `pnpm site:validate --site-key twbst528; pnpm site:test-adapter-registry; pnpm site:test-ui-baseline; pnpm site:test-ui-browser; pnpm --filter @liuhecai/frontend exec tsc --noEmit; git diff --check`

Expected: every command exits 0.
