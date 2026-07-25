import fs from "node:fs"
import ts from "typescript"

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const manifestModule = toDataModule(compileModule("frontend/lib/site-platform/site-manifest.ts"))
function manifestModuleFor(siteKey) {
  return toDataModule(
    compileModule(`frontend/sites/${siteKey}/site.manifest.ts`)
      .replace('"@/lib/site-platform/site-manifest"', JSON.stringify(manifestModule))
  )
}

const manifests = Object.fromEntries(
  ["shengshi8800", "twsaimahui", "twcaibawang", "twjinniu", "twcf888", "twssz"].map(
    (siteKey) => [siteKey, manifestModuleFor(siteKey)]
  )
)
const sitesModule = toDataModule(
  compileModule("frontend/lib/sites.ts")
    .replace(/[@]\/lib\/site-platform\/site-manifest/g, manifestModule)
    .replace(/[@]\/sites\/shengshi8800\/site\.manifest/g, manifests.shengshi8800)
    .replace(/[@]\/sites\/twsaimahui\/site\.manifest/g, manifests.twsaimahui)
    .replace(/[@]\/sites\/twcaibawang\/site\.manifest/g, manifests.twcaibawang)
    .replace(/[@]\/sites\/twjinniu\/site\.manifest/g, manifests.twjinniu)
    .replace(/[@]\/sites\/twcf888\/site\.manifest/g, manifests.twcf888)
    .replace(/[@]\/sites\/twssz\/site\.manifest/g, manifests.twssz)
)
const registryModule = toDataModule(
  compileModule("frontend/lib/site-registry.ts").replace('"@/lib/sites"', JSON.stringify(sitesModule))
)
const { resolveSiteApiContext, resolvePredictionModulesCompatibilityContext } = await import(registryModule)
const context = resolveSiteApiContext(
  "twjinniu",
  new URLSearchParams("site_id=5&web=5&web_id=5")
)

if (context.siteId !== 7 || context.webId !== 7) {
  throw new Error(`cross-site override leaked: siteId=${context.siteId}, webId=${context.webId}`)
}

const compatibilityContext = resolvePredictionModulesCompatibilityContext(
  new URLSearchParams("site_id=5")
)

if (compatibilityContext.siteKey !== "twcaibawang" || compatibilityContext.siteId !== 5) {
  throw new Error(
    `site_id compatibility lookup resolved the wrong site: ${compatibilityContext.siteKey}/${compatibilityContext.siteId}`
  )
}

let conflictRejected = false
try {
  resolvePredictionModulesCompatibilityContext(
    new URLSearchParams("site_key=twjinniu&site_id=5")
  )
} catch {
  conflictRejected = true
}

if (!conflictRejected) {
  throw new Error("site_key and site_id conflict must be rejected")
}

let missingIdentityRejected = false
try {
  resolvePredictionModulesCompatibilityContext(new URLSearchParams())
} catch (error) {
  missingIdentityRejected = error instanceof Error && error.message === "site_id or a registered site_key is required"
}

if (!missingIdentityRejected) {
  throw new Error("missing compatibility identity must retain its validation error")
}
