# Dynamic Managed Site Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one database-driven external-site links module for every registered frontend site and enforce three-line issue/content/result rendering.

**Architecture:** A public Python service projects safe enabled-site link records from `managed_sites`; a Next route proxies that data under the browser origin. One shared custom element owns the dynamic repeated links DOM and is mounted by all vendor and React-template sites.

**Tech Stack:** Python route/service/repository tests, Next.js TypeScript route, vanilla Custom Elements, legacy HTML, React template integration, Node contracts, Playwright.

---

### Task 1: Public managed-site links service

**Files:**
- Modify: `backend/src/domains/sites/repository.py`
- Modify: `backend/src/domains/sites/service.py`
- Modify: `backend/src/routes/public_routes.py`
- Create: `backend/src/tests/unit/test_public_site_links.py`
- Modify: `backend/src/tests/unit/test_api_contract_public_routes.py`

- [ ] Write failing tests for enabled/domain filtering, current-site exclusion, ID ordering, host deduplication, pure-host and HTTPS input, and rejection of credentials/query/fragment/non-HTTP protocols.
- [ ] Run `python -m pytest -q backend/src/tests/unit/test_public_site_links.py backend/src/tests/unit/test_api_contract_public_routes.py` and confirm the missing service/route failures.
- [ ] Add a repository query selecting only public candidate columns and a service projector returning `{site_key,name,domain,url}` with `https://` normalization.
- [ ] Register `GET /api/public/site-links` and map `current_site_key` without requiring admin authentication.
- [ ] Re-run both test files and confirm all pass.

### Task 2: Same-origin Next proxy

**Files:**
- Create: `frontend/app/api/site-links/route.ts`
- Create: `frontend/test/site-links-route-contract.mjs`

- [ ] Write a failing source/runtime contract requiring `site_key`, manifest registry validation, backend path `/public/site-links`, parameter mapping, CORS JSON response and structured 404/502 errors.
- [ ] Run `node frontend/test/site-links-route-contract.mjs` and confirm the route is missing.
- [ ] Implement `GET /api/site-links` with `resolveSiteApiContext`, `backendFetchJson`, `jsonWithCors` and `OPTIONS`.
- [ ] Re-run the route contract and TypeScript.

### Task 3: Shared Custom Element

**Files:**
- Create: `frontend/public/vendor/_shared/managed-site-links.js`
- Create: `frontend/test/managed-site-links-contract.mjs`

- [ ] Write a failing VM/DOM contract for endpoint selection, site-key requirement, ordered rendering, empty/error cleanup, HTTPS URLs, `target=_blank`, `rel=noopener noreferrer`, and one fetch for repeated connection.
- [ ] Run `node frontend/test/managed-site-links-contract.mjs` and confirm the shared script is missing.
- [ ] Implement `managed-site-links` with an owned shadow/root subtree, four/two-column responsive grid, loading-neutral state and no supplier fallback.
- [ ] Re-run the component contract.

### Task 4: Mount all manifest sites

**Files:**
- Modify: `frontend/public/vendor/shengshi8800/index.html`
- Modify: `frontend/public/vendor/twbst528/index.html`
- Modify: `frontend/public/vendor/twcf888.com/index.html`
- Modify: `frontend/public/vendor/twjinniu/index.html`
- Modify: `frontend/public/vendor/twjsz666/index.html`
- Modify: `frontend/public/vendor/twsaimahui/index.html`
- Modify: `frontend/public/vendor/twssz/index.html`
- Modify: `frontend/components/twcaibawang/TwcaibawangHomeClient.tsx`
- Create: `frontend/test/managed-site-links-mount-contract.mjs`

- [ ] Write a failing manifest-driven contract requiring exactly one component mount and one shared script integration per registered site.
- [ ] Run the contract and record all eight missing mounts.
- [ ] Mount the component before each unified attribute image module; replace the `twjsz666` hardcoded “旗下网站” table; add a once-only loader for the React template.
- [ ] Assert no known supplier external origin or hardcoded managed-site list remains in the replaced module.
- [ ] Re-run mount, unified footer and site adapter registry contracts.

### Task 5: Three-line prediction standard and SKILL rules

**Files:**
- Modify: `skills/vendor-site-onboarding/SKILL.md`
- Modify: `frontend/test/twjsz666-prediction-design-contract.mjs`
- Create: `frontend/test/prediction-three-line-contract.mjs`
- Modify matching site HTML/CSS only where the inventory identifies issue/content/result in one text flow.

- [ ] Write failing contracts requiring the reusable SKILL language and block-level issue/content/result leaves.
- [ ] Scan all registered entry HTML/React renderers and list actual matches; do not rewrite three-column tables.
- [ ] Fix each match using existing/predeclared leaves and `display:block`; never replace a whole table row with a summary.
- [ ] Add the public-links and three-line rules to SKILL, including database-source and browser test requirements.
- [ ] Re-run design, three-line and affected site browser contracts.

### Task 6: Full verification

**Files:**
- Modify: `frontend/test/site-ui-browser-contract.py` if shared-link browser coverage needs a central fixture.

- [ ] Run backend focused tests and `node` contracts from Tasks 1-5.
- [ ] Run `pnpm site:test-ui-baseline`, `pnpm site:test-data-client`, `pnpm site:test-adapter-registry`, and `pnpm site:test-ui-browser`.
- [ ] Run `pnpm exec tsc -p frontend/tsconfig.json --noEmit` and strict validation for all registered site keys.
- [ ] Run `pnpm build:frontend`; restore only build-generated `frontend/next-env.d.ts` if changed and preserve existing `frontend/tsconfig.tsbuildinfo` changes.
- [ ] Run `git diff --check` and confirm no unrelated files, remote operations or generated preview artifacts were introduced.
