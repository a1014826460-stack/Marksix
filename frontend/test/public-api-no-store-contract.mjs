import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"
import ts from "typescript"

const module = { exports: {} }
class NextResponse extends Response { static json(data, init) { return Response.json(data, init) } }
vm.runInNewContext(ts.transpileModule(fs.readFileSync("frontend/lib/api/cors.ts", "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, {
  exports: module.exports, module, require: () => ({ NextResponse }),
})
for (const status of [200, 400, 500]) {
  const response = module.exports.jsonWithCors({ data: [] }, { status })
  assert.equal(response.headers.get("Cache-Control"), "no-store", `shared public JSON response ${status} must forbid caching`)
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*")
}
for (const [path, method] of [["frontend/app/api/lottery-data/route.ts", "GET"], ["frontend/app/api/predict/[mechanism]/route.ts", "GET"], ["frontend/app/api/predict/[mechanism]/route.ts", "POST"]]) {
  for (const fail of [false, true]) {
    const loaded = { exports: {} }
    const data = async () => { if (fail) throw new Error("offline"); return { data: [] } }
    const code = ts.transpileModule(fs.readFileSync(path, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
    vm.runInNewContext(code, { exports: loaded.exports, module: loaded, URL, URLSearchParams,
      require(name) {
        if (name === "next/server") return { NextResponse }
        if (name === "@/lib/backend-api") return { getConfiguredSiteId: () => 1, getPublicSitePageData: data }
        if (name === "@/lib/api/predictionRunner") return { parsePredictionSearchParams: () => ({}), runPrediction: data }
        throw new Error(`unexpected import ${name}`)
      },
    })
    const response = await loaded.exports[method]({ url: "http://frontend/api/test", headers: { get: () => null }, json: async () => ({}) }, { params: Promise.resolve({ mechanism: "test" }) })
    assert.equal(response.headers.get("Cache-Control"), "no-store", `${path} ${method} ${fail ? "error" : "success"} must forbid caching`)
  }
}
console.log("Public JSON and result proxies no-store contract passed (9 response paths)")
