import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"
import { createRequire } from "node:module"

const require = createRequire(import.meta.url)
const ts = require("typescript")
const anchor = Date.parse("2026-10-08T22:32:00+08:00")
const balls = Array.from({ length: 6 }, (_, i) => ({ value: String(i + 1).padStart(2, "0"), color: "red", zodiac: "鼠", element: "金" }))

function fullHistory(seconds, changes = {}) {
  return {
    lottery_type: 3, lottery_name: "台湾彩", year: 2026, sort: "l", years: [2026],
    page: 1, page_size: 20, total: 1, total_pages: 1, server_now: anchor / 1000 + seconds,
    items: [{ issue: "2026281", date: "2026年10月08日", title: "台湾彩", draw_time: "2026-10-08 22:32:00", reveal_start: "2026-10-08 22:32:00", balls, specialBall: { ...balls[0], value: "07" }, ...changes }],
  }
}

function loadRoute(file, data, nowMs) {
  class FixedDate extends Date { static now() { return nowMs } }
  const response = class {
    constructor(body, options = {}) { this.body = body; this.options = options }
    static json(body, options) { return new response(body, options) }
  }
  const moduleCache = new Map()
  function evaluate(path) {
    if (moduleCache.has(path)) return moduleCache.get(path)
    const result = { exports: {} }
    moduleCache.set(path, result.exports)
    const javascript = ts.transpileModule(fs.readFileSync(path, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } }).outputText
    const context = {
      exports: result.exports, module: result, Date: FixedDate, URL, URLSearchParams, process: { env: {} },
      fetch: async () => ({ ok: true, json: async () => structuredClone(data) }),
      require(name) {
        if (name === "next/server") return { NextResponse: response }
        if (name === "@/lib/backend-api") return { getBackendApiBaseUrl: () => "http://backend/api", backendFetchJson: async () => structuredClone(data) }
        if (name === "@/lib/sites") return { matchSiteRequest: () => ({ site: { defaultLotteryTypeId: 3 } }) }
        if (name.startsWith("@/lib/")) return evaluate(`frontend/lib/${name.slice(6)}.ts`)
        return require(name)
      },
    }
    vm.runInNewContext(javascript, context, { filename: path })
    return result.exports
  }
  return evaluate(file)
}

const routes = ["frontend/app/api/draw-history/route.ts", "frontend/app/index/ajax/ttklsjl/route.ts"]
let cases = 0
for (const path of routes) {
  for (const seconds of [-1, 0, 1, 25, 149]) {
    const route = loadRoute(path, fullHistory(seconds), anchor + seconds * 1000)
    const result = await route.GET({ url: "http://127.0.0.1/api/draw-history?lottery_type=3&year=2026" })
    const rows = path.includes("ttklsjl") ? JSON.parse(result.body.slice("var historyAO = ".length, -1)).data : result.body.items
    assert.equal(rows.length, 0, `${path}: backend full seven must remain hidden at +${seconds}s`)
    cases += 1
  }
  for (const changes of [{ reveal_start: "bad" }, { draw_time: "2026-02-30 22:32:00" }, { draw_time: "", reveal_start: "" }]) {
    const route = loadRoute(path, fullHistory(1000, changes), anchor + 1000 * 1000)
    const result = await route.GET({ url: "http://127.0.0.1/api/draw-history?lottery_type=3" })
    const rows = path.includes("ttklsjl") ? JSON.parse(result.body.slice("var historyAO = ".length, -1)).data : result.body.items
    assert.equal(rows.length, 0, `${path}: bad anchors must close the history gate`)
    cases += 1
  }
  const legal = loadRoute(path, fullHistory(480), anchor + 480 * 1000)
  const legalResult = await legal.GET({ url: "http://127.0.0.1/api/draw-history?lottery_type=3" })
  const legalRows = path.includes("ttklsjl") ? JSON.parse(legalResult.body.slice("var historyAO = ".length, -1)).data : legalResult.body.items
  assert.equal(legalRows.length, 1, `${path}: completed history must remain visible`)
  const futureClock = loadRoute(path, fullHistory(7200), anchor + 1000)
  const futureResult = await futureClock.GET({ url: "http://127.0.0.1/api/draw-history?lottery_type=3" })
  const futureRows = path.includes("ttklsjl") ? JSON.parse(futureResult.body.slice("var historyAO = ".length, -1)).data : futureResult.body.items
  assert.equal(futureRows.length, 0, `${path}: future backend clock must not override frontend server time`)
  cases += 2
}
console.log(`Draw history independent gate contract passed (${cases} route cases)`)
