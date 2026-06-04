# Frontend API Contract

## Active Foreground Path

The active display frontend is `public/vendor/shengshi8800/**`.
Legacy JS calls same-origin Next.js API routes, and those routes proxy or adapt requests for the Python backend.

## Core Routes To Keep

- `app/api/kaijiang/[[...path]]/route.ts`
- `app/api/post/getList/route.ts`
- `app/api/latest-draw/route.ts`
- `app/api/next-draw-deadline/route.ts`
- `app/api/draw-history/route.ts`
- `app/api/lottery-data/route.ts`
- `app/api/predict/[mechanism]/route.ts`
- `app/api/prediction-modules/route.ts`
- `app/uploads/image/[bucket]/[filename]/route.ts`

## Prediction Contract Rule

Prediction data must flow through the canonical schema in `lib/prediction-contract.ts`.

Pipeline:

1. backend payload -> canonical prediction module
2. canonical prediction module -> site adapter payload
3. site adapter payload -> legacy HTML/JS or React renderer

Canonical fields:

- `CanonicalPredictionModule`
- `CanonicalPredictionRow`
- `CanonicalPredictionValue`
- `CanonicalPredictionResult`

The canonical layer is the only place where new sites should normalize mixed backend shapes from:

- `/api/public/site-page`
- `/api/vendor/homepage-modules`
- legacy `mode_payload_*` rows

## Compatibility Rule

Do not change legacy response formats unless needed to fix a clear bug.
