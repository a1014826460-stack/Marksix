---
name: vendor-site-onboarding
description: Onboard a supplied legacy lottery site HTML and JavaScript bundle into this repository without redesigning its UI. Use when adding a vendor site, configuring site manifests, connecting prediction modules or draw data, validating vendor assets, or preparing a vendor site build and deployment.
---

# Vendor Site Onboarding

Preserve vendor HTML, CSS, DOM, visual identity and business rendering unless the user explicitly requests a redesign. Use the manifest and browser bridge for configuration and data integration.

## Required workflow

1. Run `pnpm site:scaffold --site-key <siteKey>`.
2. Put the supplied archive under `frontend/public/vendor/<siteKey>/`; keep its `index.html` at the manifest entry path.
3. Complete `frontend/sites/<siteKey>/site.manifest.ts` with actual `siteId`, `webId`, domains, lottery type, entry path, visual configuration, external-origin allowlists, and selected prediction module keys.
4. Run `pnpm site:sync-manifests`.
5. Run `pnpm site:validate --site-key <siteKey>`; use `--strict` only after every detected external origin has been deliberately allowlisted or removed.
6. Add the shared scripts in this order before the supplied dynamic scripts:
   ```html
   <script src="/vendor/_shared/lottery-site-bridge.js" data-site-key="<siteKey>"></script>
   <script src="/vendor/_shared/lottery-site-runtime.js"></script>
   <script>window.LotterySiteRuntime.mount({ bridge: window.LotterySiteBridge });</script>
   ```
7. Set `bridge.runtime` selectors for the supplied draw, prediction, footer and navigation mounts. For a migrated site, set `legacyPredictionScripts: "disabled"`, convert legacy prediction `<script>` elements into non-executing `<template data-legacy-prediction-src="...">` markers, and retain the surrounding DOM/CSS only when it remains part of the visual layout.
8. Use `/api/sites/<siteKey>/prediction-modules` and `/api/sites/<siteKey>/draw` through `window.LotterySiteBridge`. Do not expose Python backend URLs to browser code. The bridge performs in-flight de-duplication and `sessionStorage` stale-while-revalidate caching; renderers receive canonical `canonical_modules` and normalized draw balls.
9. For dynamic predictions, require either explicit DOM selectors plus a documented adapter or a listener for `lottery:prediction-ready`. Do not guess proprietary payload semantics.
10. Verify `tsc`, existing contract tests, site validation and production build before deployment.

## Bridge events

- `lottery:bridge-ready`: bridge configuration loaded.
- `lottery:prediction-loading` / `lottery:prediction-ready` / `lottery:prediction-stale`: canonical prediction data state.
- `lottery:draw-loading` / `lottery:draw-ready` / `lottery:draw-stale`: normalized draw data state.
- `lottery:error`: `{ phase, error: { code, message, retryable } }`. A stale cache remains renderable while this error is emitted.
- `lottery:runtime-config-applied`: a legacy runtime accepted the manifest configuration.

Read `references/manifest-contract.md` before creating or changing a manifest.
