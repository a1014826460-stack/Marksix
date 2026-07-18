# Prediction Contract Guide

This document defines the frontend-side prediction data contract for multi-site support.

## Goal

- Do not unify site UI.
- Do unify how prediction module data is normalized.
- Let each site keep its own HTML/CSS/JS, while reading from the same canonical module model.

## Canonical Schema

### `CanonicalPredictionModule`

- `moduleKey`: stable module identifier
- `title`: display title
- `displayKind`: `text | tokens | groups | image | composite | unknown`
- `rows`: normalized history rows
- `source`: origin metadata

### `CanonicalPredictionRow`

- `issue`
- `year`
- `term`
- `prediction`
- `result`
- `status`
- `raw`

### `CanonicalPredictionValue`

- `text`
- `tokens`
- `groups`
- `imageUrl`
- `extra`

### `CanonicalPredictionResult`

- `isOpened`
- `isCorrect`
- `code`
- `zodiac`
- `color`
- `text`

## Adapter Flow

### Backend -> Canonical

Input sources:

- `/api/public/site-page`
- `/api/vendor/homepage-modules`
- legacy `mode_payload_*`

Normalization rules:

- Keep stable module identity in `moduleKey`.
- Preserve backend-specific leftovers in `raw`.
- Never depend on `raw` for primary rendering if a canonical field exists.

### Canonical -> Site Payload

Each site may adapt canonical rows into:

- old HTML/JS payloads
- React props
- table-like render models

This layer may change field names, grouping style, and display strings, but must not alter the canonical truth.

## New Site Flow

1. Place target HTML/CSS/JS under `public/vendor/<site_key>/`.
2. Register the site in `lib/sites.ts` with `renderMode` and `capabilities`.
3. Use `lib/site-registry.ts` to resolve defaults and request parameters.
4. Add a site adapter or provider only when the shared `lib/site-api-service.ts`
   defaults are not enough.
5. Request `/api/sites/<siteKey>/prediction-modules` for the preferred unified
   contract, or keep `/api/prediction-modules` only as a compatibility path.
6. Validate that pending/opened/hit/miss states render correctly.

## Unified Prediction API

Preferred route:

```text
GET /api/sites/<siteKey>/prediction-modules
```

The response keeps canonical modules in `data.canonical_modules` and legacy
adapter payloads in `data.compatibility`.

Compatibility route:

```text
GET /api/prediction-modules?site_key=<siteKey>
```

The compatibility route preserves its older response shape while sourcing data
from the shared site service. It accepts either a registered `site_key` or a
registered `site_id`. When both are supplied they must identify the same
registered site; a conflict returns the existing error envelope instead of
silently selecting another site. Path-owned site routes continue to ignore
query-string `site_id`, `web`, and `web_id` overrides. Missing identity keeps
the route's existing `400` error envelope; identity conflicts retain the
existing `500` error envelope.

## Recommended Checks

- `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
- site-specific snapshot or manual browser checks
- API response checks for canonical fields
