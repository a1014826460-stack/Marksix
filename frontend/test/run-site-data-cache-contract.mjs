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

const cacheModule = toDataModule(compileModule("frontend/lib/site-platform/site-data-cache.ts"))
const contractModule = toDataModule(
  compileModule("frontend/test/site-data-cache-contract.ts").replace(
    '"@/lib/site-platform/site-data-cache"',
    JSON.stringify(cacheModule)
  )
)

await import(contractModule)
