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
2. Register the site in `lib/sites.ts`.
3. Add a site adapter that maps canonical modules to the target page model.
4. Request `/api/prediction-modules` or the site-specific compatibility payload.
5. Validate that pending/opened/hit/miss states render correctly.

## Recommended Checks

- `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
- site-specific snapshot or manual browser checks
- API response checks for canonical fields

