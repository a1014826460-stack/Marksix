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

const sitesModule = toDataModule(compileModule("frontend/lib/sites.ts"))
const registryModule = toDataModule(
  compileModule("frontend/lib/site-registry.ts").replace('"@/lib/sites"', JSON.stringify(sitesModule))
)
const { resolveSiteApiContext } = await import(registryModule)
const context = resolveSiteApiContext(
  "twjinniu",
  new URLSearchParams("site_id=5&web=5&web_id=5")
)

if (context.siteId !== 7 || context.webId !== 7) {
  throw new Error(`cross-site override leaked: siteId=${context.siteId}, webId=${context.webId}`)
}
