import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"
import { createRequire } from "node:module"
const require = createRequire(import.meta.url)
const ts = require("typescript")
const t = Date.parse("2026-10-08T22:32:00+08:00")
const balls = Array.from({ length: 7 }, (_, i) => ({ value: String(i + 1).padStart(2, "0"), color: "red", zodiac: "鼠", element: "金" }))

function route(file, elapsed, changes = {}) {
  const now = t + elapsed * 1000
  const data = { current_issue: "2026281", draw_time: "2026-10-08 22:32:00", reveal_start: "2026-10-08 22:32:00", result_balls: balls.slice(0, 6), special_ball: balls[6], server_now: Math.floor(now / 1000), server_now_ms: now, is_complete: true, revealed_count: 7, reveal_interval_seconds: 1, ...changes }
  const deadline = { current_issue: "2026281", current_draw_time: t / 1000, next_issue: "2026282", next_time: t + 86400000, server_now: Math.floor(now / 1000), server_now_ms: now }
  class FixedDate extends Date { static now() { return now } }
  class Response { constructor(body, options = {}) { this.body = body; this.options = options; this.headers = new Headers(options.headers) } static json(body, options) { return new Response(body, options) } }
  function evaluate(path) {
    const module = { exports: {} }
    const code = ts.transpileModule(fs.readFileSync(path, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } }).outputText
    const get = (url) => structuredClone(String(url).includes("deadline") ? deadline : data)
    vm.runInNewContext(code, {
      exports: module.exports, module, Date: FixedDate, URL, URLSearchParams, Headers,
      fetch: async (url) => ({ ok: true, json: async () => get(url) }),
      require(name) {
        if (name === "next/server") return { NextResponse: Response }
        if (name === "@/lib/backend-api") return { getBackendApiBaseUrl: () => "http://backend/api", backendFetchJson: async (url) => get(url) }
        if (name === "@/lib/sites") return { matchSiteRequest: () => ({ site: { defaultLotteryTypeId: 3 } }) }
        if (name === "@/lib/site-registry") return { resolveSiteApiContext: () => ({ lotteryType: 3, siteKey: "tw8800" }) }
        if (name === "@/lib/site-platform/site-data-cache") return { siteDataCacheHeaders: () => ({ "Cache-Control": "no-store" }) }
        if (name.startsWith("@/lib/")) return evaluate(`frontend/lib/${name.slice(6)}.ts`)
        if (name.startsWith("./")) return evaluate(`frontend/lib/${name.slice(2)}.ts`)
        return require(name)
      },
    }, { filename: path })
    return module.exports
  }
  return evaluate(file)
}

let cases = 0
for (const path of ["frontend/app/api/latest-draw/route.ts", "frontend/app/wy.json/route.ts", "frontend/app/api/sites/[siteKey]/draw/route.ts"]) {
  for (const [elapsed, expected] of [[-1, 0], [0, 1], [24.999, 1], [25, 2], [149.999, 6], [150, 7]]) {
    const response = await route(path, elapsed).GET({ url: "http://localhost/api/latest-draw?lottery_type=3" }, { params: Promise.resolve({ siteKey: "tw8800" }) })
    const actual = path.includes("wy.json") ? (response.body[0].openCode.split(",").filter(Boolean).length) : path.includes("[siteKey]") ? response.body.data.balls.length : response.body.result_balls.length + Number(Boolean(response.body.special_ball))
    assert.equal(actual, expected, `${path}: malformed full seven backend must respect +${elapsed}s`)
    assert.equal(response.options.headers["Cache-Control"], "no-store")
    cases += 1
  }
  for (const changes of [{ draw_time: "2026-10-07 22:32:00", reveal_start: "2026-10-07 22:32:00" }, { reveal_start: "bad" }, { current_issue: "2026280" }]) {
    const response = await route(path, 1, changes).GET({ url: "http://localhost/api/latest-draw?lottery_type=3" }, { params: Promise.resolve({ siteKey: "tw8800" }) })
    const actual = path.includes("wy.json") ? response.body[0].openCode.split(",").filter(Boolean).length : path.includes("[siteKey]") ? response.body.data.balls.length : response.body.result_balls.length + Number(Boolean(response.body.special_ball))
    assert.equal(actual, changes.reveal_start === "2026-10-07 22:32:00" ? 1 : 0, `${path}: authoritative current schedule must bound bad payload metadata`)
    cases += 1
  }
}
console.log(`Taiwan draw proxy gate passed (${cases} real route cases)`)
