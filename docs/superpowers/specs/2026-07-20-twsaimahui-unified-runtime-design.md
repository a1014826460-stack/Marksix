# twsaimahui Unified Runtime Design

## Goal

Make `twsaimahui` the first vendor site that uses a shared runtime for draw data,
prediction data, sticky navigation, and configurable footer content while retaining
its supplied HTML, CSS, images, and presentation style.

## Scope

- Keep the page at `/twsaimahui` as an iframe-hosted vendor bundle.
- Use one browser bridge contract for all future vendor sites.
- Make the twsaimahui vendor HTML consume the bridge rather than independently
  requesting draw and prediction APIs.
- Keep site-specific rendering behind DOM selector adapters.
- Make the runtime cache canonical data in memory and `sessionStorage`, then
  refresh it in the background when an entry is stale.
- Add visible runtime state through events and test contracts.

## Non-goals

- Rebuild the supplied vendor UI in React.
- Require other existing vendor sites to migrate in this change.
- Infer the meaning of opaque legacy prediction payloads.
- Replace the existing backend scheduler or database connection configuration.

## Shared Runtime

`frontend/public/vendor/twsaimahui/site-bridge.js` becomes the reference
implementation for future vendor bundles. The bridge owns:

1. Fetching `/api/sites/<siteKey>/bridge-config`, `/draw`, and
   `/prediction-modules`.
2. Request de-duplication for callers requesting the same resource and query.
3. In-memory caching plus namespaced `sessionStorage` cache entries.
4. Stale-while-revalidate behavior: render a cached value immediately, then emit
   an updated ready event after the background request finishes.
5. A consistent event contract:
   `lottery:<resource>-loading`, `lottery:<resource>-ready`,
   `lottery:<resource>-stale`, and `lottery:error`.

The bridge response is the only data source used by the vendor's shared draw and
prediction adapters. Legacy module scripts remain static visual assets only and
must not issue prediction API requests after the adapter is installed.

## Data Contracts

Draw data remains `NormalizedSiteDraw` from
`frontend/lib/site-platform/site-draw.ts`. It contains a current issue, next
issue/deadline, and normalized balls with the special-ball flag.

Prediction data remains the `canonical_modules` list from
`frontend/lib/prediction-contract.ts`. The response may include compatibility
payloads for older sites, but new adapter code renders only the canonical list.

The manifest declares a `dom` adapter section with selectors for draw and
prediction targets, and declares footer image/contact data. The manifest remains
the sole site-specific configuration source; the shared runtime must not contain
site names, image paths, module labels, or selectors.

## twsaimahui Adapter

The twsaimahui HTML receives a small adapter script after `site-bridge.js`.
It listens to bridge events and:

- Renders normalized draw data into the existing draw panel and uses the site's
  existing color classes/markup.
- Renders canonical prediction modules into a dedicated existing content target
  without changing the surrounding legacy page design.
- Displays loading and recoverable error state in the same target instead of
  blocking page rendering.
- Injects manifest-configured footer images, copyright text, and contact links
  into a dedicated footer mount point.

The adapter supplies a fixed top navigation behavior: the existing navigation
is fixed from initial render, reserves its height in document flow, and uses
`scrollIntoView` with a header offset for same-page links.

## Cache Policy

- Draw: 20-second fresh TTL and 120-second stale TTL.
- Prediction: 5-minute fresh TTL and 30-minute stale TTL.
- Cache keys include site key, resource, lottery type, and normalized query.
- An expired stale entry is discarded; a network failure falls back to a still
  stale entry and emits a retryable error event.
- Caches never include credentials or backend internal endpoints.

## Backend and Health Preconditions

The frontend's site APIs keep using the current normalized route handlers. The
existing `/api/health` worker/draw status must be healthy before manual browser
acceptance testing. A database connection error is an environment failure, not
a vendor adapter fallback condition.

## Tests

- Extend the bridge VM contract to prove concurrent requests coalesce, fresh
  cache avoids a request, stale cache emits data then refreshes, and errors are
  retryable.
- Add static adapter/manifest tests for the configured DOM selectors, fixed nav,
  shared footer mount, and absence of legacy prediction API loading.
- Run TypeScript checks, bridge/manifest tests, and a production frontend build.
- Perform a local API smoke test for the site draw and prediction endpoints once
  PostgreSQL connectivity is available.
