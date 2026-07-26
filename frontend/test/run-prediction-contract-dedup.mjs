import fs from "node:fs"
import ts from "typescript"

function compile(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}
function data(source) { return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}` }

const contract = compile("frontend/test/prediction-contract-dedup-contract.ts")
  .replace('"@/lib/prediction-contract"', JSON.stringify(data(compile("frontend/lib/prediction-contract.ts"))))
await import(data(contract))
