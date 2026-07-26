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
10. Before rendering, create a complete **visible prediction table mapping**:
    `vendor heading/row -> canonical module key (or approved nearest replacement) -> existing DOM target -> API term/prediction/result/status fields`.
    Every visible historical row in a mapped table must receive the active
    lottery response. Never leave a vendor term, prediction, draw, `对/错`,
    `?????`, or other historical hit text as a fallback. If a module has no
    exact backend capability, document the approved replacement in the mapping
    and render `暂无后端资料` until that replacement responds; ask the user when
    no safe replacement has been approved.
11. For composite vendor blocks, map all approved backend modules into the
    existing block using only existing text nodes. A renderer may combine API
    rows, but it must label each replacement and must not claim vendor static
    results are backend results.
12. Verify `pnpm site:test-ui-baseline`, `pnpm site:test-data-client`, `pnpm site:test-adapter-registry`, `pnpm site:test-ui-browser`, `tsc`, site validation and production build before deployment.

13. Add a browser contract test that clicks all three draw tabs and, for each
    tab, proves: (a) prediction request `lottery_type` equals the selected
    draw value; (b) mapped prediction data is from that response; and (c) a
    generic title such as `A级猛料大公开` displays the configured regional
    prefix. The test must request at least eight distinctive historical API
    rows, assert each mapped table contains its selected-lottery marker,
    `result.text` and `result.isCorrect` label, and assert representative
    vendor static sentinels are absent. Also prove `siteConfig` contains only
    台湾彩、澳门彩、香港彩 and no legacy domain, site name, regional prefix or
    external navigation URL remains in active vendor scripts.

## Non-negotiable UI boundary

- Shared browser code must not call `document.createElement`, `appendChild`, `replaceChildren`, `innerHTML` or `document.write`, and must not inject CSS.
- Do not use `lottery-site-runtime.js`, `LotterySiteRuntime.mount()`, shared UI mount selectors, or `legacyPredictionScripts: "disabled"` for an existing site.
- Do not replace supplied HTML/CSS/JS, navigation labels, footer images, layout, or script execution. A UI change needs explicit user approval in a separate task.
- Treat `frontend/lib/site-platform/site-ui-baseline.ts` and each `site-adapter.ts` as the regression contract. Browser verification must prove original draw, navigation and footer sentinels remain present.

## Unified Attribute Image Module

When the product requirement explicitly replaces a vendor page's trailing static
table or gallery, use this single **属性知识** module. It contains exactly the
three managed, same-origin images in this order. Keep the wrapper classes and
IDs unchanged so every site has one stable module contract:

```html
<div class="box pad" id="legacy-attribute-anchor">
  <div class="list-title">属性知识</div>
  <div id="legacy-attribute-gallery">
    <img src="/uploads/image/20250322/1742580086567063.png" width="100%" loading="lazy" decoding="async">
    <img src="/uploads/image/20250322/1742580119746508.jpg" width="100%" loading="lazy" decoding="async">
    <img src="/uploads/image/20250322/1742580130762983.jpg" width="100%" loading="lazy" decoding="async">
  </div>
</div>
```

- Do not use the legacy `httpApi` variable, runtime `innerHTML`, or a script to
  construct this module. The fixed same-origin URLs work in iframe-vendor and
  direct vendor entry pages, avoid an undeclared global, and do not add a
  synchronous DOM write.
- Do not add, remove, reorder, or substitute its three images per site.
- `loading="lazy"` and `decoding="async"` are required; they preserve the
  supplied visual width while deferring image decode/load until needed.
- Replace only the explicitly approved terminal static table/galleries. Do not
  remove ordinary prediction tables, navigation, draw markup, or a vendor
  footer as part of this replacement.
- Add the module selector to the site adapter/footer contract and write a
  browser test that asserts the three ordered `src` values and no external
  image origin.

## Data readiness

- `site-data:ready`: `{ siteKey, resource, state }`; non-visual readiness signal emitted after a site adapter loads data.
- `state` is `ready`, `stale`, or `error`. A stale result remains safe to render while a later request fails.

Read `references/manifest-contract.md` before registering or changing a site.
