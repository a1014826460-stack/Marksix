# Twssz Complete Prediction Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every Twssz prediction result and historical row that appears in the supplied vendor page with the selected backend prediction modules and the backend-provided draw result.

**Architecture:** The vendor HTML remains the visual template and contains only structural display cells. `site-data-adapter.js` selects the existing rows and writes the selected canonical module's term, prediction, draw result and status into them. A new canonical `wuzhong5ma` mechanism provides the exact five-number exclusion data for the “内幕⑤不中” table. Every data request carries the active Taiwan/Macau/Hong Kong lottery type.

**Tech Stack:** Python backend prediction registry and generator; static vendor HTML/ES5 browser adapter; Playwright contract tests; Node static-contract test.

---

### Task 1: Define and authorize the exact five-no-hit module

**Files:**
- Modify: `backend/src/predict/mechanisms.py`
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Test: `backend/src/tests/unit/test_twssz_wuzhong5ma.py`

- [ ] Write a failing test that expects `get_prediction_config("wuzhong5ma")` to expose mode 485, five number labels, and exclusion hit logic.
- [ ] Run `D:\python\python.exe -m pytest backend/src/tests/unit/test_twssz_wuzhong5ma.py -q` and confirm it fails because the mechanism is absent.
- [ ] Add `wuzhong5ma` with `mode_payload_485`, `label_count=5`, number parsing/formatting, and `excludes_hit`; replace Twssz dependency “内幕五不中” with mode 485.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: Make the Twssz page dependency manifest match confirmed mappings

**Files:**
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `frontend/sites/twssz/site.manifest.ts`
- Test: `backend/src/tests/unit/test_twssz_page_dependencies.py`

- [ ] Write a failing test asserting that Twssz authorizes `wuzhong5ma`, `sanxiao_siwei_xiao`, `sanxiao_siwei_wei`, `juesha1wei`, `juesha1xiao`, `juesha2xiao`, `jueshabanbo`, `pt2xiao`, `title_48`, `shuangbo`, and `3hang`.
- [ ] Run the focused test and confirm failure.
- [ ] Update the dependency and frontend manifests to request exactly those canonical module keys, preserving existing supported keys.
- [ ] Re-run the focused test and confirm it passes.

### Task 3: Add a failing end-to-end mapping test

**Files:**
- Modify: `frontend/test/twssz-live-mapping-contract.py`

- [ ] Extend the mocked prediction envelope with eight distinctive rows for every mapped module and explicit API `result` values.
- [ ] Add assertions after selecting Hong Kong that each prediction section shows the Hong Kong marker, API term, API result text and API status; assert no old vendor terms `204期`, `46鸡对`, `13马对`, or `?????` remain in mapped sections.
- [ ] Run `D:\python\python.exe frontend/test/twssz-live-mapping-contract.py` and confirm it fails against the current partial adapter.

### Task 4: Replace static prediction payload text with structural targets

**Files:**
- Modify: `frontend/public/vendor/twssz/index.html`
- Modify: `frontend/public/vendor/twssz/site-data-adapter.js`

- [ ] Preserve each supplied section's table, typography, colors, borders and number of visible historical rows; remove only static term/prediction/result/status values.
- [ ] Add stable `data-prediction-section` and `data-prediction-row` attributes to existing structural rows without adding a new layout or stylesheet.
- [ ] Add renderer definitions for every table: A-level, 连肖连尾, 24码, 大小, 家野二肖, 三头, 特料公开清单, 平特尾/肖, 八肖, 五不中, 天地二肖, 绝杀、综合资料、三肖六码、双波和单/波表。
- [ ] Render API rows in chunks after the first paint; each renderer writes only existing text nodes and derives result display exclusively from `row.result` and `row.status`.
- [ ] Ensure a section without available API rows uses the existing layout with “暂无后端资料”, never falls back to vendor prediction/history text.

### Task 5: Verify data source, three-lottery switching and UI contract

**Files:**
- Modify: `frontend/test/twssz-adapter-contract.mjs`
- Modify: `frontend/test/twssz-live-mapping-contract.py`

- [ ] Update static contract assertions for the new module, data attributes and the removed static prediction sentinels.
- [ ] Run `node frontend/test/twssz-adapter-contract.mjs`.
- [ ] Run `D:\python\python.exe frontend/test/twssz-live-mapping-contract.py`.
- [ ] Run `pnpm site:validate --site-key twssz --strict`, `pnpm site:test-data-client`, `pnpm site:test-adapter-registry`, `pnpm site:test-ui-baseline`, and `pnpm exec tsc --noEmit -p frontend/tsconfig.json` from `frontend`.
- [ ] Run focused backend tests for the new mechanism and dependencies.
- [ ] Run `git diff --check` and review only touched files.
