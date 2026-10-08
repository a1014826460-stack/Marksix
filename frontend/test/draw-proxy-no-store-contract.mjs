/** Public draw proxies must not freeze clock samples in browsers or intermediate caches. */
import assert from "node:assert/strict"
import fs from "node:fs"
import ts from "typescript"

const dataModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
const backendModule = dataModule('export function getBackendApiBaseUrl() { return "http://backend.invalid/api" }')
const serverModule = dataModule('export const NextResponse = { json(data, init) { return Response.json(data, init) } }')
const transpile = (path) => ts.transpileModule(fs.readFileSync(path, "utf8"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
const historyGateModule = dataModule(transpile("frontend/lib/draw-history-gate.ts"))
const liveGateModule = dataModule(transpile("frontend/lib/taiwan-draw-gate.ts").replace('"./draw-history-gate"', JSON.stringify(historyGateModule)))
const originalFetch = globalThis.fetch
let checked = 0
try {
  for (const resource of ["latest-draw", "next-draw-deadline"]) {
    const routePath = `frontend/app/api/${resource}/route.ts`
    const source = ts.transpileModule(fs.readFileSync(routePath, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
    }).outputText.replace('"next/server"', JSON.stringify(serverModule))
      .replace('"@/lib/backend-api"', JSON.stringify(backendModule))
      .replace('"@/lib/taiwan-draw-gate"', JSON.stringify(liveGateModule))
    const { GET } = await import(dataModule(source))
    for (const scenario of ["success", "upstream-error", "network-error"]) {
      globalThis.fetch = async (url, options) => {
        assert.ok([`http://backend.invalid/api/public/${resource}?lottery_type=3`, "http://backend.invalid/api/public/next-draw-deadline?lottery_type=3"].includes(String(url)))
        assert.equal(options.cache, "no-store")
        if (scenario === "network-error") throw new Error("offline")
        if (scenario === "upstream-error") return new Response("unavailable", { status: 503 })
        return Response.json({ current_issue: "2026280", server_now: 1791383521 })
      }
      const response = await GET(new Request(`http://frontend.invalid/api/${resource}?lottery_type=3`))
      assert.equal(response.status, scenario === "success" ? 200 : scenario === "upstream-error" ? 503 : 502)
      assert.equal(response.headers.get("Cache-Control"), "no-store", `${resource} ${scenario} must prohibit response caching`)
      if (scenario === "success") assert.equal((await response.json()).server_now, 1791383521)
      checked++
    }
  }
} finally {
  globalThis.fetch = originalFetch
}
console.log(`draw proxy no-store contract passed (${checked} response paths)`)
