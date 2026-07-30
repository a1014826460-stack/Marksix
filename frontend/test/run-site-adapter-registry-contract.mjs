import fs from "node:fs"
import ts from "typescript"

function compile(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}
function data(source) { return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}` }

const adapters = {}
for (const siteKey of ["shengshi8800", "twsaimahui", "twcaibawang", "twjinniu", "twcf888", "twssz", "twbst528", "twjsz666"]) {
  adapters[siteKey] = data(compile(`frontend/sites/${siteKey}/site-adapter.ts`))
}
const registry = data(
  compile("frontend/lib/site-platform/site-adapter-registry.ts")
    .replace('"@/sites/shengshi8800/site-adapter"', JSON.stringify(adapters.shengshi8800))
    .replace('"@/sites/twsaimahui/site-adapter"', JSON.stringify(adapters.twsaimahui))
    .replace('"@/sites/twcaibawang/site-adapter"', JSON.stringify(adapters.twcaibawang))
    .replace('"@/sites/twjinniu/site-adapter"', JSON.stringify(adapters.twjinniu))
    .replace('"@/sites/twcf888/site-adapter"', JSON.stringify(adapters.twcf888))
    .replace('"@/sites/twssz/site-adapter"', JSON.stringify(adapters.twssz))
    .replace('"@/sites/twbst528/site-adapter"', JSON.stringify(adapters.twbst528))
    .replace('"@/sites/twjsz666/site-adapter"', JSON.stringify(adapters.twjsz666))
)
await import(data(compile("frontend/test/site-adapter-registry-contract.ts").replace('"@/lib/site-platform/site-adapter-registry"', JSON.stringify(registry))))
