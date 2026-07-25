---
name: vendor-site-onboarding
description: Onboard a supplied legacy lottery site HTML and JavaScript bundle into this repository without redesigning its UI. Use when adding a vendor site, configuring site manifests, connecting prediction modules or draw data, validating vendor assets, or preparing a vendor site build and deployment.
---

# Vendor Site Onboarding

Preserve vendor HTML, CSS, DOM, visual identity and business rendering unless the user explicitly requests a redesign. New integrations use the DOM-free site-data client and a site-owned adapter; they do not mount a shared UI runtime.

## Required workflow

1. Run `pnpm site:scaffold --site-key <siteKey>`.
2. Put the supplied archive under `frontend/public/vendor/<siteKey>/`; keep its `index.html` at the manifest entry path.
3. Register the actual `siteId`, `webId`, domains, lottery type and entry path. Add `frontend/sites/<siteKey>/site-adapter.ts` with the existing draw, prediction, navigation and footer selector contract.
4. Run `pnpm site:sync-manifests`.
5. Run `pnpm site:validate --site-key <siteKey>`; use `--strict` only after every detected external origin has been deliberately allowlisted or removed.
6. Add the shared data scripts before supplied dynamic scripts, without changing existing markup or script order:
   ```html
   <script src="/vendor/_shared/lottery-site-data-client.js"></script>
   <script src="site-data-adapter.js"></script>
   ```
7. Implement `site-data-adapter.js` as an existing-DOM-only adapter. It may use `LotterySiteDataClient` and dispatch `site-data:ready`, but it must not create, replace, remove, move or style DOM nodes; it must not disable or rewrite supplied scripts.
8. Use `loadDraw({ lotteryType })` and `loadPredictions({ lotteryType, historyLimit })`. They call same-origin `/api/sites/<siteKey>/draw` and `/api/sites/<siteKey>/prediction-modules`, de-duplicate requests and use bounded `sessionStorage` stale fallback. Do not expose Python backend URLs to browser code.
9. For a proprietary renderer, document a site-specific mapping from the canonical response to its existing DOM. If no safe existing selector exists, leave the selector list empty; never introduce a shared mount node.
10. Verify `pnpm site:test-ui-baseline`, `pnpm site:test-data-client`, `pnpm site:test-adapter-registry`, `pnpm site:test-ui-browser`, `tsc`, site validation and production build before deployment.

## Non-negotiable UI boundary

- Shared browser code must not call `document.createElement`, `appendChild`, `replaceChildren`, `innerHTML` or `document.write`, and must not inject CSS.
- Do not use `lottery-site-runtime.js`, `LotterySiteRuntime.mount()`, shared UI mount selectors, or `legacyPredictionScripts: "disabled"` for an existing site.
- Do not replace supplied HTML/CSS/JS, navigation labels, footer images, layout, or script execution. A UI change needs explicit user approval in a separate task.
- Treat `frontend/lib/site-platform/site-ui-baseline.ts` and each `site-adapter.ts` as the regression contract. Browser verification must prove original draw, navigation and footer sentinels remain present.

## Data readiness

- `site-data:ready`: `{ siteKey, resource, state }`; non-visual readiness signal emitted after a site adapter loads data.
- `state` is `ready`, `stale`, or `error`. A stale result remains safe to render while a later request fails.

Read `references/manifest-contract.md` before registering or changing a site.
