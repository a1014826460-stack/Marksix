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
6. Use `/api/sites/<siteKey>/prediction-modules` and `/api/sites/<siteKey>/draw` through `window.LotterySiteBridge`. Do not expose Python backend URLs to browser code.
7. For dynamic predictions, require either explicit DOM selectors plus a documented adapter or a listener for `lottery:prediction-ready`. Do not guess proprietary payload semantics.
8. Verify `tsc`, existing contract tests, site validation and production build before deployment.

## Bridge events

- `lottery:bridge-ready`: bridge configuration loaded.
- `lottery:prediction-loading` / `lottery:prediction-ready`: canonical prediction data state.
- `lottery:draw-loading` / `lottery:draw-ready`: normalized draw data state.
- `lottery:error`: `{ phase, error: { code, message, retryable } }`.
- `lottery:runtime-config-applied`: a legacy runtime accepted the manifest configuration.

Read `references/manifest-contract.md` before creating or changing a manifest.
