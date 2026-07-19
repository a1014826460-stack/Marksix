# Vendor Site Bridge Pilot Design

## Objective

Create a reusable, configuration-driven onboarding layer for supplied legacy HTML and JavaScript bundles without redesigning their UI. Pilot the layer on `twsaimahui`, retaining its existing HTML, Vue/jQuery runtime, CSS, DOM and legacy API compatibility.

## Scope

- Add a typed site manifest that records operational identity, vendor entry, render mode, bridge settings, visual configuration, selected prediction modules and allowed external origins.
- Derive the `twsaimahui` registry entry from its manifest, while retaining existing registry APIs for the other sites.
- Add a generic `/[siteKey]` iframe entry for future manifest-backed vendor sites and convert `twsaimahui` to use its shared page component.
- Add `/api/sites/[siteKey]/bridge-config` and `/api/sites/[siteKey]/draw` endpoints.
- Add a vendor browser bridge which receives manifest configuration, provides normalized API calls, emits stateful browser events and leaves vendor rendering ownership unchanged.
- Update `twsaimahui` runtime to apply bridge-provided `site_key`, API bases, `web` and default lottery type after the existing static fallback initializes.
- Add repository onboarding skill, manifest scaffolding/synchronization/validation commands and focused contract tests.

## Non-goals

- Do not rewrite any vendor UI into shared React components.
- Do not remove `/api/kaijiang/*`, `/api/index/notice`, or other existing compatibility routes.
- Do not automatically infer prediction module semantics from arbitrary supplied JavaScript.
- Do not migrate the other four sites during the pilot.
- Do not remove or rewrite unapproved vendor external links in this phase; validation reports them for review.

## Manifest Contract

Each site owns `frontend/sites/<siteKey>/site.manifest.ts`. A manifest provides:

- `identity`: `siteKey`, domains, route, `siteId`, `webId`, default lottery type.
- `frontend`: render mode, vendor index, legacy asset base, game/metadata/capabilities used by the existing registry.
- `bridge`: compatibility API bases, bridge auto-load flags and selected prediction module keys.
- `brand`: site name, logo/favicon, theme, navigation, footer and contacts. These values are exposed as data; the pilot does not force them into the original twsaimahui DOM.
- `security`: external script/navigation origin allowlists.

The manifest is validated in TypeScript before it can be exposed. A generated manifest index imports every manifest so Next.js can bundle it. `scripts/sync-site-manifests.mjs` recreates this index from manifest files. New sites add a manifest and run the sync command rather than hand-editing routing code.

## Runtime and Data Flow

```text
vendor index.html
  -> site-bridge.js (site key is supplied as a data attribute)
  -> GET /api/sites/:siteKey/bridge-config
  -> apply config to LEGACY_TWSAIMAHUI_RUNTIME and LOTTERY_CONFIGS
  -> existing vendor JavaScript continues to call legacy compatibility endpoints

optional new vendor integration
  -> LotterySiteBridge.getPredictionModules()
  -> GET /api/sites/:siteKey/prediction-modules
  -> lottery:prediction-ready / lottery:error events

optional new vendor integration
  -> LotterySiteBridge.getDraw()
  -> GET /api/sites/:siteKey/draw
  -> lottery:draw-ready / lottery:error events
```

`LotterySiteBridge` owns generic request state only. It dispatches `lottery:bridge-ready`, `lottery:prediction-loading`, `lottery:prediction-ready`, `lottery:draw-loading`, `lottery:draw-ready`, and `lottery:error`. A legacy page may listen to these events or continue using its existing JavaScript unchanged.

## API Contracts

`GET /api/sites/:siteKey/bridge-config`

```json
{
  "ok": true,
  "site": { "site_key": "twsaimahui", "site_id": 6, "web_id": 6, "lottery_type": 3 },
  "data": {
    "api": { "http_api_base": "", "kaijiang_api_base": "/api/kaijiang" },
    "bridge": { "auto_load": { "draw": false, "prediction": false }, "prediction_module_keys": [] },
    "brand": {}
  }
}
```

`GET /api/sites/:siteKey/draw?lottery_type=1|2|3`

```json
{
  "ok": true,
  "site": { "site_key": "twsaimahui", "lottery_type": 3 },
  "data": {
    "current_issue": "2026125",
    "opened_at": null,
    "next_issue": "2026126",
    "next_draw_at": "2026-05-21 21:30:00",
    "balls": [{ "value": "01", "color": "red", "zodiac": "马", "element": null, "is_special": false }]
  }
}
```

Backend failures return `{ "ok": false, "error": { "code", "message", "retryable" } }`. The browser bridge turns timeout, failed HTTP response and malformed envelopes into this same error representation.

## twsaimahui Pilot Behaviour

1. Add `site-bridge.js` before `legacy_runtime.js` in the existing page head.
2. Preserve runtime defaults so a bridge configuration outage does not prevent page rendering.
3. When bridge configuration arrives, `legacy_runtime.js` updates API bases, `site_key`, `web` and default lottery type, then dispatches `lottery:runtime-config-applied`.
4. `lottery_config.js` updates all three legacy lottery entries to use the manifest `web` and API base, while retaining lottery-specific `type` values 3/2/1.
5. Existing `ajax_interceptor.js` and `api_client.js` continue to use `LEGACY_TWSAIMAHUI_RUNTIME` and therefore receive the configured values without changing their call sites.

## Validation and Safety

- A manifest must have a lowercase kebab-case key, unique non-empty identity values, an existing `/vendor/...` entry and no duplicate module keys.
- The validation script verifies manifest paths, reports external script/navigation origins found in vendor HTML/JS and rejects any origin absent from the manifest allowlist when `--strict` is supplied.
- Contract tests cover manifest validation, generated registry lookup, bridge configuration projection and normalized draw mapping.
- A browser-independent test exercises `site-bridge.js` in a minimal DOM/event/fetch harness.
- Existing frontend type and registry/compatibility contract checks remain required.

## Known Pilot Limitation

The bridge exposes configuration and normalized data without changing the original `twsaimahui` module rendering. A new supplied page must either declare DOM slots for a generic renderer or listen to `LotterySiteBridge` events. An opaque legacy module that only understands a proprietary payload still needs an explicit adapter profile and fixture before it can be dynamically populated. This is intentional: guessing module semantics would risk incorrect lottery content.
