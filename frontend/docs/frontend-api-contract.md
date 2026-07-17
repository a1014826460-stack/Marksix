# Frontend API Contract

## Active Foreground Path

The active display frontend is `public/vendor/shengshi8800/**`.
Legacy JS calls same-origin Next.js API routes, and those routes proxy or adapt requests for the Python backend.

## Core Routes To Keep

- `app/api/sites/[siteKey]/site-page/route.ts`
- `app/api/sites/[siteKey]/homepage-modules/route.ts`
- `app/api/sites/[siteKey]/article-detail/route.ts`
- `app/api/sites/[siteKey]/prediction-modules/route.ts`
- `app/api/sites/[siteKey]/traffic-events/route.ts`
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

Legacy site-specific API routes must be thin compatibility forwarders to
`lib/site-api-service.ts`. They should record `api_compat_hit` traffic events
without blocking the original response.

## Unified Site API Rule

All new frontend site integrations should prefer:

- `GET /api/sites/<siteKey>/site-page`
- `GET /api/sites/<siteKey>/homepage-modules`
- `GET /api/sites/<siteKey>/article-detail`
- `GET /api/sites/<siteKey>/prediction-modules`
- `POST /api/sites/<siteKey>/traffic-events`

Successful unified responses use a stable envelope:

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
  "data": {}
}
```

Errors use:

```json
{ "ok": false, "error": "message" }
```

## Traffic Event Contract

`POST /api/sites/<siteKey>/traffic-events` accepts:

- `event_type`: `site_page_view | article_view | vendor_page_view | api_compat_hit`
- `visitor_id`
- `path`
- `route`
- `article_id`
- `referrer`
- `occurred_at`
- optional `utm_*` fields

The frontend route forwards to backend `/api/public/traffic-events`. The backend
stores hashed IP only; raw IP addresses must not be persisted.
