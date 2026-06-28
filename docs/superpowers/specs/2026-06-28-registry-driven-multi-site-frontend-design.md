# Registry-Driven Multi-Site Frontend Design

## Context

The frontend currently serves five public sites:

- `shengshi8800`
- `twsaimahui`
- `twcaibawang`
- `twjinniu`
- `twcf888`

The project should not unify site UI. Each site keeps its own vendor assets, visual style, and page behavior. The unified work is about architecture, API consistency, site onboarding, prediction data flow, and first-party traffic metrics for the management system.

Existing backend prediction work in the current worktree is outside this design scope.

## Goals

- Make new sites easier to add through a registry-driven structure.
- Provide a unified API surface under `/api/sites/<siteKey>/...`.
- Keep old site-specific APIs as compatibility forwarders.
- Keep large site UI components in place during the first phase.
- Centralize site capabilities such as render mode, homepage modules, prediction adapters, and Article providers.
- Add first-party Traffic Events and Traffic Metrics for multi-site management reporting.

## Non-Goals

- Do not redesign site UI.
- Do not split large React home components in this phase.
- Do not remove existing legacy API routes.
- Do not replace the Python backend public API.
- Do not depend on third-party analytics for management reporting.

## Architecture

Introduce a registry-driven site model.

### Site Registry

The Site Registry is the single source for site identity and operational defaults:

- `siteKey`
- route path
- domains
- vendor asset paths
- default `web_id`
- default `site_id`
- default `Lottery Type`
- metadata
- `renderMode`
- optional capabilities

Initial render modes:

- `legacy-shell`: `shengshi8800`
- `iframe-vendor`: `twsaimahui`
- `react-home`: `twcaibawang`, `twjinniu`, `twcf888`

### Site Adapter

Site Adapters own site-specific translation from canonical data to the shape expected by existing UI or vendor JavaScript.

Adapter capabilities may include:

- prediction module compatibility payloads
- homepage module provider
- Article catalog/detail provider
- traffic defaults
- vendor module defaults

Route files should not hard-code site branching when a capability can be resolved through the registry.

### Page Entries

Keep existing public URLs. Each `app/<site>/page.tsx` should become a thin entry that resolves `siteKey` and delegates to a shared site page renderer or render-mode component.

Large UI components are preserved. They can receive data from shared site services without being split in this phase.

## Unified API

Add unified frontend API routes:

- `GET /api/sites/<siteKey>/site-page`
- `GET /api/sites/<siteKey>/homepage-modules`
- `GET /api/sites/<siteKey>/article-detail`
- `GET /api/sites/<siteKey>/prediction-modules`
- `POST /api/sites/<siteKey>/traffic-events`

Unified successful responses use:

```json
{
  "ok": true,
  "site": {
    "site_key": "twjinniu",
    "site_id": 7,
    "web_id": 7,
    "lottery_type": 3,
    "domain": "www.twjinniu.com"
  },
  "data": {},
  "compatibility": {}
}
```

Unified errors use:

```json
{ "ok": false, "error": "message" }
```

Error status rules:

- unknown `siteKey`: `404`
- missing or invalid required parameters: `400`
- backend, provider, or adapter failure: `500`

## Data Flow

```text
request siteKey
 -> Site Registry
 -> Site Service
 -> backend-api / local provider
 -> Canonical Prediction Schema
 -> Site Adapter
 -> unified response
```

Prediction data keeps the existing canonical rule:

```text
backend payload -> canonical prediction module -> site adapter payload -> legacy HTML/JS or React renderer
```

`raw` remains a compatibility fallback, not the preferred rendering source.

## Legacy Compatibility

Existing API routes remain and become thin forwarders to shared services:

- `/api/twjinniu/site-page`
- `/api/twjinniu/homepage-modules`
- `/api/twcf888/site-page`
- `/api/twcf888/homepage-modules`
- `/api/vendor/article-detail`
- `/api/prediction-modules`

`/api/vendor/article-detail` continues to resolve site context from host/referer, then delegates to the unified Article service.

Compatibility routes may keep old response shapes where vendor assets require them, but their internal data source should be shared.

## Traffic Events

Add first-party Traffic Events for management reporting.

Initial event types:

- `site_page_view`
- `article_view`
- `vendor_page_view`
- `api_compat_hit`

Event fields:

- `site_key`
- `site_id`
- `web_id`
- `lottery_type`
- `event_type`
- `path`
- `route`
- `article_id`
- `referrer`
- `utm_source`
- `utm_medium`
- `utm_campaign`
- `user_agent`
- `ip_hash`
- `visitor_id`
- `occurred_at`

Privacy rule: do not store raw IP addresses. Store an IP hash when needed for UV and abuse detection.

Reliability rule: tracker failures must not break public pages or API responses. Traffic write failures should be logged and otherwise ignored by the caller.

Deduplication rule: avoid counting repeated page views from the same `visitor_id + site_key + path` in a short window as separate PVs when caused by client retries or rapid remounts.

## Management Metrics

Add backend/admin aggregation endpoints:

- `GET /api/admin/traffic/overview`
- `GET /api/admin/traffic/sites`
- `GET /api/admin/traffic/timeseries`

Initial Traffic Metrics:

- today PV
- today UV
- PV/UV by site
- article view ranking
- referrer ranking
- 7-day and 30-day site trends
- compatibility API hit counts by route and site

The existing dashboard overview may later include a compact traffic summary, but traffic aggregation should be implemented as a separate backend domain so it does not tangle with crawler, prediction, or error log metrics.

## Testing

Frontend verification:

- `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
- Site Registry resolves all five `siteKey` values.
- Each unified API route returns a stable envelope.
- Unknown sites return `404`.
- Legacy API forwarders preserve required compatibility behavior.
- Article provider capability resolves for `twjinniu`, `twcf888`, and `twcaibawang`.
- Traffic tracker sends the expected payload and tolerates API failure.

Backend/admin verification:

- Traffic Event write validates event type and site identity.
- Traffic Event write hashes IP and does not persist raw IP.
- Traffic Metric aggregation returns PV/UV by site.
- `api_compat_hit` events are included in route usage metrics.
- Existing dashboard overview remains compatible.

Manual checks:

- Open all five public site routes.
- Confirm tracker requests appear in the browser Network panel.
- Confirm old vendor/static pages still render.
- Confirm old API routes still respond.
- Confirm admin traffic endpoints show per-site data after page visits.

## Rollout

1. Add registry types and migrate current site config into the registry shape.
2. Add site services and adapters while keeping old call sites working.
3. Add `/api/sites/<siteKey>/...` routes.
4. Convert old site-specific API routes into forwarders.
5. Add Traffic Event storage and frontend tracker.
6. Add backend/admin Traffic Metrics endpoints.
7. Update frontend README and API contract docs.
8. Run frontend type checks and focused backend/admin tests.
