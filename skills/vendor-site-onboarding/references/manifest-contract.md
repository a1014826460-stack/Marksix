# Manifest Contract

Use `frontend/sites/<siteKey>/site.manifest.ts` as the source of site identity and bridge behavior.

## Mandatory values

- `identity.siteKey`: lowercase kebab-case; matches `public/vendor/<siteKey>`.
- `identity.domains`, `routePath`, `siteId`, `webId`, `defaultLotteryType`: actual operational identity, never guessed from UI text.
- `frontend.vendorIndexPath`: existing path under `/vendor/`.
- `frontend.legacyPublicBasePath`: vendor asset base.
- `bridge.api`: same-origin compatibility bases. Use `""` and `/api/kaijiang` unless an approved alternate is required.
- `bridge.predictionModuleKeys`: only modules explicitly selected by the user or verified from supplied JavaScript.
- `bridge.runtime`: selectors for `drawSelector`, `predictionSelector`, `footerSelector`, and `navigationSelector`, plus `legacyPredictionScripts`. Use `"disabled"` only after disabling all independent prediction fetch scripts.
- `brand`: logo/footer/navigation/contact values for shared DOM-slot injection. Set `brand.footer.imageUrls` for footer images; these do not overwrite the vendor's header or other UI automatically.
- `security`: exact external executable/navigation origins approved for the supplied archive.

## Data usage

Load `/vendor/_shared/lottery-site-bridge.js` with `data-site-key`, then `/vendor/_shared/lottery-site-runtime.js`. Call `window.LotterySiteRuntime.mount({ bridge: window.LotterySiteBridge })` once. The shared renderer uses the configured selector mounts and supports per-site visual CSS overrides.

Call `window.LotterySiteBridge.getPredictionModules()` for canonical prediction modules and `getDraw()` for normalized draw data. Listen to bridge events if the supplied UI owns rendering. Add a dedicated adapter plus fixtures when the supplied JS requires a proprietary field shape.
