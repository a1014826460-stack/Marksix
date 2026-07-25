---
name: vendor-site-onboarding
description: Onboard a supplied legacy lottery site HTML and JavaScript bundle into this repository without redesigning its UI. Use when adding a vendor site, configuring site manifests, connecting prediction modules or draw data, validating vendor assets, or preparing a vendor site build and deployment.
---

# Vendor Site Onboarding

Preserve vendor HTML, CSS, DOM, visual identity and business rendering unless the user explicitly requests a redesign. New integrations use the DOM-free site-data client and a site-owned adapter; they do not mount a shared UI runtime.

## Required site constants

Every vendor site defines one immutable `siteConfig` object in its site-owned
adapter. Do not duplicate literal domains, site names or regional labels in
HTML/JS; read them from this object when a supplied text node is allowed to be
updated. It must include:

```js
var siteConfig = {
  siteKey: "example",
  siteName: "站点名称",
  siteDomain: "example.com",
  lotteries: [
    { key: "taiwan", lotteryType: 3, label: "台湾彩", titlePrefix: "台湾精选", titleRegionPrefix: "台湾" },
    { key: "macau", lotteryType: 2, label: "澳门彩", titlePrefix: "澳门精选", titleRegionPrefix: "澳门" },
    { key: "hong-kong", lotteryType: 1, label: "香港彩", titlePrefix: "香港精选", titleRegionPrefix: "香港" }
  ]
};
```

- A site must expose **exactly** these three lotteries: 台湾彩、澳门彩、香港彩.
  Do not add a fourth game and do not omit any of the three, even when the
  supplied vendor page initially shows only one.
- Every prediction title must use the selected lottery's regional prefix.
  Titles already containing `xx精选` use `titlePrefix`; generic titles must be
  prefixed with `titleRegionPrefix` and one ASCII space. For example,
  `澳洲精选『精选24码』` becomes `台湾精选『精选24码』`, and `A级猛料大公开` becomes
  `台湾 A级猛料大公开`. The prefix is derived from the active lottery in
  `siteConfig.lotteries`, never hardcoded per title.
- Switching a draw tab is a mandatory cross-frame state change: the parent
  vendor page must receive the selected `lotteryType`, request predictions
  using that same ID, re-render only the existing mapped nodes, and update all
  prediction title prefixes. A default lottery may be used only until the
  first explicit selection. Cached and in-flight prediction results must be
  keyed by `lotteryType`; a response for a previously selected lottery must not
  overwrite the active lottery's table.
- Every visible site name/domain in vendor text must be derived from
  `siteConfig.siteName` / `siteConfig.siteDomain`; for example,
  `执笔先生（gat566.cc）15码中特` becomes
  `执笔先生（twssz.com）15码中特` when `siteDomain` is `twssz.com`.
  Keep the supplied node, layout and styling; update text only where the user
  has approved vendor-text replacement.
- All internal links must be generated from the configured frontend base URL
  and route path. External vendor URLs remain blocked. Do not put a domain,
  site name, regional prefix or frontend URL directly in page JS/HTML when it
  can be read from `siteConfig`.

## Required workflow

1. Run `pnpm site:scaffold --site-key <siteKey>`.
2. Put the supplied archive under `frontend/public/vendor/<siteKey>/`; keep its `index.html` at the manifest entry path.
3. Register the actual `siteId`, `webId`, domains and entry path. Configure the
   exact 台湾彩、澳门彩、香港彩 trio in the manifest and add
   `frontend/sites/<siteKey>/site-adapter.ts` with the existing draw,
   prediction, navigation and footer selector contract.
4. Run `pnpm site:sync-manifests`.
5. Run `pnpm site:validate --site-key <siteKey>`; use `--strict` only after every detected external origin has been deliberately allowlisted or removed.
6. Add the shared data scripts before supplied dynamic scripts, without changing existing markup or script order:
   ```html
   <script src="/vendor/_shared/lottery-site-data-client.js"></script>
   <script src="site-data-adapter.js"></script>
   ```
7. Implement `site-data-adapter.js` as an existing-DOM-only adapter. It may use `LotterySiteDataClient` and dispatch `site-data:ready`, but it must not create, replace, remove, move or style DOM nodes; it must not disable or rewrite supplied scripts.
8. Use `loadDraw({ lotteryType })` and `loadPredictions({ lotteryType, historyLimit })` for each of the three configured lottery IDs. They call same-origin `/api/sites/<siteKey>/draw` and `/api/sites/<siteKey>/prediction-modules`, de-duplicate requests and use bounded `sessionStorage` stale fallback. Do not expose Python backend URLs to browser code.
9. If the draw UI is in an iframe, make its tab handler send a same-origin
   `postMessage({ type: "lottery-change", siteKey, lotteryType })`; parent
   code must verify both `event.origin` and `event.source` against the known
   draw iframe before calling `selectLottery(lotteryType)`. Do not infer the
   selected lottery from visual tab text.
10. For a proprietary renderer, document a site-specific mapping from the canonical response to its existing DOM. If no safe existing selector exists, leave the selector list empty; never introduce a shared mount node.
11. Verify `pnpm site:test-ui-baseline`, `pnpm site:test-data-client`, `pnpm site:test-adapter-registry`, `pnpm site:test-ui-browser`, `tsc`, site validation and production build before deployment.

12. Add a browser contract test that clicks all three draw tabs and, for each
    tab, proves: (a) prediction request `lottery_type` equals the selected
    draw value; (b) mapped prediction data is from that response; and (c) a
    generic title such as `A级猛料大公开` displays the configured regional
    prefix. Also prove `siteConfig` contains only 台湾彩、澳门彩、香港彩 and no
    legacy domain, site name, regional prefix or external navigation URL
    remains in active vendor scripts.

## Non-negotiable UI boundary

- Shared browser code must not call `document.createElement`, `appendChild`, `replaceChildren`, `innerHTML` or `document.write`, and must not inject CSS.
- Do not use `lottery-site-runtime.js`, `LotterySiteRuntime.mount()`, shared UI mount selectors, or `legacyPredictionScripts: "disabled"` for an existing site.
- Do not replace supplied HTML/CSS/JS, navigation labels, footer images, layout, or script execution. A UI change needs explicit user approval in a separate task.
- Treat `frontend/lib/site-platform/site-ui-baseline.ts` and each `site-adapter.ts` as the regression contract. Browser verification must prove original draw, navigation and footer sentinels remain present.

## Data readiness

- `site-data:ready`: `{ siteKey, resource, state }`; non-visual readiness signal emitted after a site adapter loads data.
- `state` is `ready`, `stale`, or `error`. A stale result remains safe to render while a later request fails.

Read `references/manifest-contract.md` before registering or changing a site.
