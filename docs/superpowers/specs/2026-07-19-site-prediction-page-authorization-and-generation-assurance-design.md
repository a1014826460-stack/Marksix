# Site Prediction Page Authorization and Generation Assurance Design

## Context

`public.site_prediction_modules(status=1)` is the runtime authorization source
for generated prediction data. The current production audit for sites 5-8 has
no rows outside their stored blueprints, but that result is insufficient: some
blueprints were assembled from broad historical lists rather than an auditable
inventory of every prediction page that the current frontend can still reach.

The frontend has four distinct dependency forms:

1. The Shengshi8800 legacy shell for site 4 loads named static JS files from
   `frontend/public/vendor/shengshi8800/index.html`. Each live file has a
   fixed legacy endpoint/parameter mapping and executes with `web=4`.
2. Legacy vendor pages such as `twsaimahui/index.html` load named static JS
   files. Each live script calls a legacy endpoint with a fixed parameter set.
3. React homepage providers such as `twjinniu-homepage.ts` load explicit
   `mode_id` values, sometimes combining several source rows into one card.
4. `twcf888` article definitions map a live article to one mode or a declared
   composite. Snapshot-only and blocked articles are not generation modules.

These sources must be distinguished from commented-out HTML, orphan files,
and backend mechanisms that no frontend page reads.

## Goals

- Authorize every prediction module required by an accessible prediction page
  for sites 4-8, and no unrelated module.
- Make page, endpoint/parameter, mode ID, source kind, and generation
  assurance status reviewable from one internal manifest.
- Preserve every current API success payload, key order, legacy wrapper, and
  disabled-module empty response shape.
- Continue to enforce controlled future-generation guarantees only for modes
  with verified candidate and hit rules: rolling accuracy, cross-site prefix
  diversity, and same-site adjacent-period signature diversity.
- Make modules without a verified future rule explicit as `history_only` or
  `blocked`, rather than describing their future output as accuracy-controlled.

## Non-Goals

- Do not remove an accessible frontend page, alter vendor HTML, or redesign
  any page.
- Do not delete `created` or `public` prediction history.
- Do not expose generation assurance metadata, control records, future truth,
  or new fields through public, legacy, vendor, or admin success payloads.
- Do not infer a mode from an endpoint when the frontend adapter has no exact
  mapping; record it as blocked until an exact mapping exists.

## Source Manifest

Create an internal manifest owned by
`domains.prediction.site_page_dependencies`. Each immutable item contains:

- `site_key`, `page_path`, and `source_path`
- `endpoint` and normalized `params` for legacy pages, or a React provider ID
- one or more exact `mode_ids`
- `kind`: `page_module` or `composite_source`
- `generation_assurance`: `controlled_future`, `history_only`, or `blocked`
- a short rationale for a blocked item

Only live script tags in an accessible HTML document count. Scripts in HTML
comments do not. Existing static JS files that are not referenced by an
accessible page do not. A composite provider may depend on several source
mode IDs, but it does not broaden authorization beyond those exact source IDs.

For site 4, `static/js/kj.js`, `djck.js`, utility scripts, and the local draw
frame are not prediction-module dependencies. The following non-commented
prediction scripts have exact route mappings and form the site-4 target set:

```text
2, 3, 8, 12, 15, 20, 26, 28, 31, 34, 38, 43, 45, 46, 48, 49, 50, 51,
52, 53, 54, 56, 57, 58, 59, 61, 63, 65, 68, 88, 108, 116, 151, 197,
244, 246, 331
```

The site-4 manifest deliberately excludes old enabled rows such as `5`, `9`,
`10`, `22`, `24`, `27`, `30`, `39`, `41`, `42`, `44`, `47`, `60`, `62`,
`64`, `66`, `67`, `69`, `123`, `132`, `141`, `143`, `144`, `145`, `147`,
`149`, `152`, `155`, `157`, `158`, `159`, `251`, `295`, `333`, `336`,
`470`-`478`: no current non-commented Shengshi8800 prediction page reads
them. The list also excludes `tp5.js` because its endpoint maps to image
mode `331`, which remains a page dependency, and therefore is included above.

The manifest is internal tooling data. Existing HTTP serializers continue to
read `site_prediction_modules`; they neither return nor rely on the new
metadata in their response shapes.

## Blueprint and Database Flow

```text
reachable frontend page
  -> internal dependency manifest
  -> required page/composite source mode set for site
  -> site blueprint profile
  -> site_prediction_modules(status=1)
  -> public / legacy / vendor data readers
```

The reconciliation command first runs a no-write audit and reports four
separate sets: manifest modes, blueprint modes, active database modes, and
blocked page items. With `--apply`, it enables missing manifest-backed rows
and disables active rows outside the manifest-backed set. It only updates the
`status` column and timestamps; history remains intact.

The command must not use runtime API traffic as evidence: a page remains
authorized while it is accessible even when it has no recent requests.

## Generation Assurance

`generation_rules` remains the authoritative definition of a verified future
hit rule. The manifest maps a mode to an assurance status as follows:

- `controlled_future`: the mode has a verified generation rule and candidate
  controller. Future Taiwan generation uses the accuracy plan, stores only
  internal signature hashes, enforces its rule-specific cross-site prefix
  width, and rejects a complete same-site adjacent signature.
- `history_only`: the page requires the mode and existing/opened history can
  be shown, but its future payload has no verified candidate/hit semantics.
  The future controller must skip it instead of claiming a target rate.
- `blocked`: the frontend page has no exact supported data source. Its
  existing empty/history response shape remains; no fake mapping or generator
  is introduced.

The rule document is generated from the same assurance resolver and continues
to contain no future draw values. A manifest entry cannot mark a mode
`controlled_future` when `generation_rules` reports it unsupported.

## Error Handling and Compatibility

- A missing exact endpoint mapping fails the audit with its source file and
  is classified as `blocked`; it cannot silently enable a guessed mode.
- A database row for a disabled/blocked module remains query-compatible with
  current empty `data`, `rows`, or `history` wrappers.
- A `--apply` run is idempotent. It reports counts and changed IDs internally
  but does not alter any route response.
- The manifest audit runs in tests and the operator command. A frontend change
  that introduces an undeclared live dependency fails before deployment.

## Testing

- Parse `twsaimahui/index.html` and prove that only non-commented script tags
  contribute legacy page dependencies; explicitly confirm the commented
  `020nn4x.js` is excluded.
- Verify every live twsaimahui endpoint/`num` tuple maps to exact mode IDs in
  the frontend compatibility route; the unresolved six-not-in source remains
  `blocked`.
- Verify all `twjinniu-homepage.ts` `loadLegacyModeRows` IDs and twcf888
  live-backed article IDs are present in their site manifest.
- Verify blueprint mode sets equal the manifest's page and composite source
  set, and reconciliation disables only non-manifest active rows.
- Verify a supported mode such as 470 is `controlled_future`, while a text or
  image mode such as 50 or 476 is `history_only`; blocked sources cannot enter
  the authorized set.
- Run existing API contract suites to demonstrate unchanged successful API
  payloads and disabled-module empty wrappers.

## Documentation

Update `backend/docs/prediction-module-rules.md` with the three assurance
states and their guarantees. Update `backend/README_CN.md`,
`backend/docs/API.md`, and `backend/CLAUDE.md` to name the manifest as the
source for all accessible frontend prediction pages and to document the audit
and reconciliation commands.
