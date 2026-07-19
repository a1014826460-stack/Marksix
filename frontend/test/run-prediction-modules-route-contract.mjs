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
const twsaimahuiManifestModule = toDataModule(
  compileModule("frontend/sites/twsaimahui/site.manifest.ts")
    .replace('"@/lib/site-platform/site-manifest"', JSON.stringify(manifestModule))
)
const sitesModule = toDataModule(
  compileModule("frontend/lib/sites.ts")
    .replace(/[@]\/lib\/site-platform\/site-manifest/g, manifestModule)
    .replace(/[@]\/sites\/twsaimahui\/site\.manifest/g, twsaimahuiManifestModule)
)
const registryModule = toDataModule(
  compileModule("frontend/lib/site-registry.ts").replace('"@/lib/sites"', JSON.stringify(sitesModule))
)
const corsModule = toDataModule(`
  export function jsonWithCors(payload, init) {
    return new Response(JSON.stringify(payload), {
      ...init,
      headers: { "content-type": "application/json" },
    })
  }
  export function buildOptionsResponse() { return new Response(null, { status: 204 }) }
`)
const serviceModule = toDataModule(`
  export const contexts = []
  export async function getSitePredictionModules(context) {
    contexts.push(context)
    return { data: { canonical_modules: [], compatibility: { site_page: {}, vendor_homepage_modules: null } } }
  }
  export async function recordSiteApiCompatHit() { return null }
`)
const routeModule = toDataModule(
  compileModule("frontend/app/api/prediction-modules/route.ts")
    .replace('"@/lib/api/cors"', JSON.stringify(corsModule))
    .replace('"@/lib/site-api-service"', JSON.stringify(serviceModule))
    .replace('"@/lib/site-registry"', JSON.stringify(registryModule))
)

const { GET } = await import(routeModule)
const service = await import(serviceModule)

const missingIdentity = await GET(new Request("http://localhost/api/prediction-modules"))
if (missingIdentity.status !== 400) {
  throw new Error(`missing identity returned ${missingIdentity.status}, expected 400`)
}
if ((await missingIdentity.json()).error !== "site_id or a registered site_key is required") {
  throw new Error("missing identity changed the error envelope")
}

const conflict = await GET(
  new Request("http://localhost/api/prediction-modules?site_key=twjinniu&site_id=5")
)
if (conflict.status !== 500) {
  throw new Error(`identity conflict returned ${conflict.status}, expected 500`)
}
if ((await conflict.json()).error !== "site_key and site_id must identify the same registered site") {
  throw new Error("identity conflict changed the error envelope")
}

const resolvedBySiteId = await GET(
  new Request("http://localhost/api/prediction-modules?site_id=5")
)
const payload = await resolvedBySiteId.json()
if (resolvedBySiteId.status !== 200 || payload.site.site_key !== "twcaibawang" || payload.site.site_id !== 5) {
  throw new Error("site_id did not resolve the compatibility route to twcaibawang")
}
if (service.contexts.at(-1)?.siteId !== 5 || service.contexts.at(-1)?.webId !== 5) {
  throw new Error("the compatibility route sent the wrong site context to the data service")
}
