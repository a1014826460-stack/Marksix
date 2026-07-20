import fs from "node:fs"
import ts from "typescript"

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}
function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const manifestModule = toDataModule(compileModule("frontend/lib/site-platform/site-manifest.ts"))
const pilotModule = toDataModule(compileModule("frontend/sites/twsaimahui/site.manifest.ts").replace('"@/lib/site-platform/site-manifest"', JSON.stringify(manifestModule)))
const projectionModule = toDataModule(
  compileModule("frontend/lib/site-platform/site-bridge-config.ts")
    .replace('"@/lib/site-platform/site-manifest"', JSON.stringify(manifestModule))
)
const drawModule = toDataModule(compileModule("frontend/lib/site-platform/site-draw.ts"))
const { defineVendorSiteManifest } = await import(manifestModule)
const { default: twsaimahui } = await import(pilotModule)
const { projectPublicBridgeConfig } = await import(projectionModule)
const { normalizeSiteDraw } = await import(drawModule)

if (twsaimahui.identity.siteKey !== "twsaimahui") throw new Error("twsaimahui manifest must retain its stable site key")
if (twsaimahui.identity.webId !== 6 || twsaimahui.identity.defaultLotteryType !== 3) throw new Error("twsaimahui manifest must expose web 6 and Taiwan type 3")
if (twsaimahui.frontend.vendorIndexPath !== "/vendor/twsaimahui/index.html") throw new Error("twsaimahui manifest must own the vendor entry path")
const config = projectPublicBridgeConfig(twsaimahui)
if (config.api.kaijiang_api_base !== "/api/kaijiang" || config.site.web_id !== 6) throw new Error("bridge config projection must expose configured API and web identity")
if (config.bridge.runtime.draw_selector !== ".vendor-shared-draw-mount" || config.brand.footer.imageUrls.length !== 4) throw new Error("bridge config must project shared runtime selectors and footer images")

const draw = normalizeSiteDraw({ current_issue: "2026125", result_balls: [{ value: "1", color: "red", zodiac: "馬" }], special_ball: { value: "49", color: "green", zodiac: "雞" } }, { next_issue: "2026126", next_time: "2026-05-21 21:30:00" })
if (draw.balls.length !== 2 || draw.balls[0].value !== "01" || !draw.balls[1].is_special || draw.balls[0].zodiac !== "马") throw new Error("draw normalization must pad values, normalize zodiac, and mark special balls")

const invalidRouteInput = { identity: { siteKey: "route-site", domains: ["example.test"], routePath: "/custom-route", siteId: 1, webId: 1, defaultLotteryType: 3 }, frontend: { renderMode: "iframe-vendor", vendorIndexPath: "/vendor/route-site/index.html", legacyPublicBasePath: "/vendor/route-site", defaultGame: "taiwan", forumTitle: "Route" }, bridge: { api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" }, autoLoad: { draw: false, prediction: false }, predictionModuleKeys: [] }, brand: { siteName: "Route", navigation: [], footer: { copyright: "" } }, security: { externalScriptOrigins: [], externalNavigationOrigins: [] } }
let invalidRouteRejected = false
try { defineVendorSiteManifest(invalidRouteInput) } catch (error) { invalidRouteRejected = error instanceof Error && error.message.includes("routePath") }
if (!invalidRouteRejected) throw new Error("manifest routes must use the site key path")

for (const input of [
  { identity: { siteKey: "Invalid_Key", domains: ["example.test"], routePath: "/invalid", siteId: 1, webId: 1, defaultLotteryType: 3 }, frontend: { renderMode: "iframe-vendor", vendorIndexPath: "/vendor/invalid/index.html", legacyPublicBasePath: "/vendor/invalid", defaultGame: "taiwan", forumTitle: "Invalid" }, bridge: { api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" }, autoLoad: { draw: false, prediction: false }, predictionModuleKeys: [] }, brand: { siteName: "Invalid", navigation: [], footer: { copyright: "" } }, security: { externalScriptOrigins: [], externalNavigationOrigins: [] } },
  { identity: { siteKey: "valid-site", domains: ["example.test"], routePath: "/valid", siteId: 1, webId: 1, defaultLotteryType: 3 }, frontend: { renderMode: "iframe-vendor", vendorIndexPath: "/vendor/valid/index.html", legacyPublicBasePath: "/vendor/valid", defaultGame: "taiwan", forumTitle: "Valid" }, bridge: { api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" }, autoLoad: { draw: false, prediction: false }, predictionModuleKeys: ["module-a", "module-a"] }, brand: { siteName: "Valid", navigation: [], footer: { copyright: "" } }, security: { externalScriptOrigins: [], externalNavigationOrigins: [] } },
]) {
  let rejected = false
  try { defineVendorSiteManifest(input) } catch { rejected = true }
  if (!rejected) throw new Error("invalid manifests must be rejected")
}
