# Manifest Contract

Use the site registry and `frontend/sites/<siteKey>/site-adapter.ts` as the source of identity and existing-DOM integration behavior.

## Mandatory values

- `identity.siteKey`: lowercase kebab-case; matches `public/vendor/<siteKey>`.
- `identity.domains`, `routePath`, `siteId`, `webId`, `defaultLotteryType`: actual operational identity, never guessed from UI text.
- `frontend.vendorIndexPath`: existing path under `/vendor/`.
- `frontend.legacyPublicBasePath`: vendor asset base.
- API calls: use same-origin `/api/sites/<siteKey>/draw` and `/api/sites/<siteKey>/prediction-modules`; preserve all existing backend compatibility endpoints for vendor scripts.
- `site-adapter.ts`: set `mode: "existing-dom-only"`; selectors identify existing draw, prediction, navigation and footer nodes only. Empty prediction selector arrays are valid when no safe existing target exists.
- Footer, logo and navigation configuration describes existing assets and markup. It is not permission for shared DOM-slot injection.
- `security`: exact external executable/navigation origins approved for the supplied archive.

## Data usage

Load `/vendor/_shared/lottery-site-data-client.js`, then the site-owned `site-data-adapter.js`. Do not call a shared UI runtime or add a shared visual container.

Call `window.LotterySiteDataClient.create({ siteKey })`, then `loadPredictions()` or `loadDraw()`. The client returns `{ state, data?, error?, source }` and manages request de-duplication plus bounded session cache fallback. A dedicated adapter may map data to approved existing nodes only when that mapping has been reviewed.
