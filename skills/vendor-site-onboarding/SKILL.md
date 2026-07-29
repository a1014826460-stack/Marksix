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
8. Use `loadDraw({ lotteryType })` and `loadPredictions({ lotteryType, historyLimit })` for each of the three configured lottery IDs. They call same-origin `/api/sites/<siteKey>/draw` and `/api/sites/<siteKey>/prediction-modules`, de-duplicate requests and use bounded `sessionStorage` stale fallback. Do not expose Python backend URLs to browser code. The public API accepts at most 20 distinct issues.
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
    Completion is based on the supplied page, not on the initial request list:
    enumerate every visible prediction heading/card in the entry HTML and
    reconcile that inventory against the mapping. The count of mapped,
    intentionally blocked, and explicitly static non-prediction sections must
    equal the count of visible sections. Never stop after the first named or
    easiest modules while other visible sections still contain supplier terms.
11. For composite vendor blocks, map all approved backend modules into the
    existing block using only existing text nodes. A renderer may combine API
    rows, but it must label each replacement and must not claim vendor static
    results are backend results.
12. Write a **DOM slot contract** for every prediction section before coding:
    `vendor selector -> retained labels -> dynamic term/value/result slots ->
    canonical module key(s) -> token formatter -> history-index alignment`.
    Register an explicit named renderer for every section. Never use a generic
    `rowDisplay`/whole-row renderer as a fallback.
13. Render only the dynamic slots, never an enclosing `tr`, `table`, `div`, or
    section container. Preserve the supplied labels, punctuation, colours and
    structure. Fixed grids must update their existing cells in order (for
    example, `tr.zt24mtr td` for 24码); paired history layouts must update their
    header and detail rows independently; composite layouts must name every
    backend key and align all module rows by term/history index. Format raw API
    tokens before writing them: do not expose implementation separators such as
    `生肖|号码`, raw arrays, or a generic `【tokens】 开 result` sentence unless
    that exact sentence is the vendor slot contract.
14. When data is absent, clear only the mapped dynamic slot and show
    `暂无后端资料` in that slot. Do not leave vendor terms, predictions, results,
    `对/错`, `?????`, or hit highlights visible anywhere in the mapped row.
15. Treat `historyLimit` as a limit of **distinct issues**, not source-record
    count. Canonical module rows must be de-duplicated by the normalized issue
    (`issue`, otherwise `year + term`) before a vendor adapter maps history
    indices. Retain the first/latest row deterministically; never fill extra
    vendor rows by repeating an earlier issue. Clear unused existing rows.
    Before selecting the request limit, count the supplied HTML's complete
    issue groups for every mapped section (a paired header/detail layout is
    one group, a multi-row card is one group). Set the site request to the
    largest required count, capped at 20: `min(max(sectionIssueGroups), 20)`.
    Never infer eight or ten from a generic default: a ten-group section must
    receive ten rows even when another section has only eight groups. Every
    renderer must still stop at its own existing group count.
16. Add a browser contract test that verifies representative formatted slots:
    retained labels remain present, values land in their exact selector/cell,
    multi-module sections use both responses, raw token separators are absent,
    vendor static sentinels are absent, and duplicate API records for one issue
    yield one visible issue row. A test that merely finds API text somewhere in
    a section is insufficient.
    For every complex/repeated card, the contract must enumerate its exact
    container selector, each dynamic child slot, and literal vendor sentinels
    (old domain, term, numbers, result text and marketing copy) that must be
    absent after render. Do not use sibling-count/offset selection for a
    semantic block when the vendor provides a stable class, heading or slot
    selector; write a dedicated renderer for that block instead.
    A complex multi-line module (for example, a header plus two number rows,
    cards with four sub-lines, or four composite kill categories) must always
    have a dedicated formatter and named renderer. It must write only the
    pre-existing child text slots for term, labels, values and result; never
    collapse the section into a generic summary sentence.
    In addition to representative slot assertions, scan every inventoried
    prediction section after render. Fail when any mapped section retains a
    supplier issue sentinel, `????` placeholder, old regional prefix, or result
    text from the supplied snapshot. Click all lottery tabs and repeat the
    inventory scan; a passing test for a subset of headings is not sufficient
    evidence that homepage onboarding is complete.

### Prediction HTML layout failure prevention

The main cause of incorrect prediction presentation is treating a vendor
heading or a nearby table as the module's structure. A heading identifies a
section; it does **not** prove its card count, column count, row grouping, or
which child nodes are data slots. Do not infer a renderer from the module name
or from a visually similar section.

### Prediction result normalization

Prediction history rows commonly retain all seven draw values in CSV fields
such as `res_code`, `res_sx`, and `res_color`. A prediction module's result
cell displays the **special ball only**, which is the last aligned value from
each field. Never concatenate the CSV fields into the result cell. For example,
`20,37,24,28,19,48,34` plus `猪,马,羊,兔,鼠,羊,鸡` must render as
`开:34鸡对/错`, not as a seven-number result.

Apply this at both boundaries:

- The canonical prediction contract must normalize `code`, `zodiac`, and
  `color` to their last aligned token before a site adapter receives them.
- A vendor adapter that owns a result formatter must defensively select the
  last token again, because compatibility endpoints or cached payloads may
  bypass the canonical normalizer.

Result regression fixtures must mirror production payload shape. At least one
opened row must provide seven-value CSV `res_code/res_sx/res_color` fields and
assert a single result such as `开:34鸡错`. A fixture containing only
`code: "34", zodiac: "鸡"` is insufficient: it cannot detect full-draw leakage.
Before completion, probe the running same-origin prediction endpoint and assert
that no opened canonical row has a comma in `result.code` or `result.zodiac`,
then inspect the rendered browser DOM using that real response.

Before implementing a renderer, inspect the supplied reference HTML and record
the following for that exact module in its DOM slot contract:

| Inspect | Record and preserve |
| --- | --- |
| Repetition unit | One issue's exact wrapper and its number of rows; e.g. a four-row 24码 group or a two-row header/detail card. |
| Card topology | Single-column cards, paired columns, fixed grid, or one composite cell. Do not reuse a sibling module's topology. |
| Dynamic slots | Separate selectors for issue, title, prediction tokens, draw text, `对/错`, and hit markers. |
| Static slots | Decorative divider rows, legends, labels, punctuation, font/color nodes, and `br` line breaks that must not receive API data. |
| History capacity | Count complete issue groups in this section, not `<tr>` elements or cards in another section. |
| Empty and hit state | Exact existing nodes to clear for missing data and the existing background/highlight node used for a hit. |

Apply these rules without exception:

- **Never use a generic whole-row or whole-card text writer.** Calling
  `textContent`/`replaceExistingText` on a container that owns nested
  `font`, `span`, `br`, or multiple data fields destroys supplier formatting,
  merges lines, and removes yellow hit markers. Update the smallest existing
  leaf node for each field instead.
- **Use one dedicated named renderer per non-identical topology.** Similar
  labels do not imply compatible DOM. For example, a single-column AAA history
  card must never share the two-column A-grade renderer; a paired 8肖16码 card
  must write header and two-line detail rows separately; and a multi-category
  综合绝杀 cell needs four independently formatted blocks.
- **Bind fixed groups explicitly.** A 24码 module is `title row + three number
  rows`, not four interchangeable rows. Bind the first row only to the issue
  title and the following rows only to their fixed cells. For paired cards,
  bind header/detail pairs; for one-row histories, bind one card per issue.
  Never fill an empty sibling column, a decorative row, or the next group's
  header merely because it is adjacent in the DOM.
- **Preserve supplier segmentation.** When the reference displays separate
  fields such as `期号`, `＜嫩＞`, `生肖`, `数字`, `波色`, `大小`, and `尾数`, write
  each field to its retained slot. Do not assemble a new prose sentence or
  flatten it into an API summary. Preserve vendor punctuation, colors,
  whitespace, and line breaks.
- **Treat term headers as required data, not decoration.** If every issue
  group has a title/header, render its normalized issue there. Never derive it
  from a fragile text search after writing number cells, and never omit it
  because the API prediction values exist.
- **Keep the full requested history shape.** Request the maximum distinct
  issue count required by any visible section, then render each module only to
  its own number of complete groups. De-duplicate by issue before indexing;
  do not repeat a record to fill a card, skip intermediate issues, or let a
  three-row response silently produce a discontinuous eight-card history.
- **Map composite mechanisms by field, not by a convenient replacement.** If
  one vendor block has multiple categories, explicitly name the backend module
  and field feeding every category. A missing category must show the approved
  empty state in that category only; it must not cause the entire block to be
  replaced with an unrelated one-line module.
- **Highlight only through existing markup.** When a prediction hits, set the
  supplied yellow-background node or its existing style/class on the matching
  leaf token. Do not replace it with yellow text, an added wrapper, or a
  container-level style. Clear obsolete hit state before rendering the next
  row.
- **Use semantic anchors before positional traversal.** Start from a unique
  vendor heading, stable class, or approved section ID, then query its
  contained slots. Do not select `following-sibling`/`nth-child` across
  unrelated modules unless the DOM contract records that exact stable
  relationship and a browser test covers it.

For every complex or repeated module, the browser contract must assert all of
the following after rendering: exact issue-group count; exact row/cell count;
issue header presence and order; retained labels and `br` line breaks; values
in their specific child slots; hit background markup; no blank secondary
column; no vendor static term/result/placeholder; and no raw API separators.
The test must inspect the module's own container, not merely search for the
expected text anywhere on the page.

17. Verify `pnpm site:test-ui-baseline`, `pnpm site:test-data-client`, `pnpm site:test-adapter-registry`, `pnpm site:test-ui-browser`, `tsc`, site validation and production build before deployment.

18. Add a browser contract test that clicks all three draw tabs and, for each
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
