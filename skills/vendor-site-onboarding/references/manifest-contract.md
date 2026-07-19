# Manifest Contract

Use `frontend/sites/<siteKey>/site.manifest.ts` as the source of site identity and bridge behavior.

## Mandatory values

- `identity.siteKey`: lowercase kebab-case; matches `public/vendor/<siteKey>`.
- `identity.domains`, `routePath`, `siteId`, `webId`, `defaultLotteryType`: actual operational identity, never guessed from UI text.
- `frontend.vendorIndexPath`: existing path under `/vendor/`.
- `frontend.legacyPublicBasePath`: vendor asset base.
- `bridge.api`: same-origin compatibility bases. Use `""` and `/api/kaijiang` unless an approved alternate is required.
- `bridge.predictionModuleKeys`: only modules explicitly selected by the user or verified from supplied JavaScript.
- `brand`: logo/footer/navigation/contact values for shared shells or future DOM-slot injection; does not overwrite vendor UI automatically.
- `security`: exact external executable/navigation origins approved for the supplied archive.

## Data usage

Call `window.LotterySiteBridge.getPredictionModules()` for canonical prediction modules and `getDraw()` for normalized draw data. Listen to bridge events if the supplied UI owns rendering. Add a dedicated adapter plus fixtures when the supplied JS requires a proprietary field shape.
