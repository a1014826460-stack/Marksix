import assert from "node:assert/strict"
import fs from "node:fs"
import ts from "typescript"

const dataModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
const nextModule = dataModule('export class NextResponse extends Response { static json(data, init) { return Response.json(data, init) } }')
const source = ts.transpileModule(fs.readFileSync("app/api/python/[...path]/route.ts", "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText.replace('"next/server"', JSON.stringify(nextModule))
const routes = await import(dataModule(source))
const originalFetch = globalThis.fetch
let checked = 0
try {
  for (const method of ["GET", "POST", "PUT", "PATCH", "DELETE"]) {
    for (const scenario of ["success", "upstream-error", "network-error", "timeout"]) {
      globalThis.fetch = async (_url, options) => {
        assert.equal(options.cache, "no-store")
        if (scenario === "network-error") throw new Error("offline")
        if (scenario === "timeout") throw Object.assign(new Error("aborted"), { name: "AbortError" })
        return new Response('{"ok":true}', { status: scenario === "upstream-error" ? 503 : 200,
          headers: { "Content-Type": "application/json" } })
      }
      const request = new Request("http://admin.invalid/api/python/admin/draws", { method,
        ...(method === "GET" ? {} : { body: "{}" }) })
      request.nextUrl = new URL(request.url)
      const response = await routes[method](request, { params: Promise.resolve({ path: ["admin", "draws"] }) })
      assert.equal(response.headers.get("Cache-Control"), "no-store", `${method} ${scenario} must prohibit response caching`)
      assert.equal(response.status, { success: 200, "upstream-error": 503, "network-error": 502, timeout: 504 }[scenario])
      checked++
    }
  }
} finally { globalThis.fetch = originalFetch }
console.log(`admin proxy no-store contract passed (${checked} method/result paths)`)
