import fs from "node:fs"
import vm from "node:vm"

const source = fs.readFileSync("frontend/public/vendor/_shared/lottery-site-bridge.js", "utf8")
const vendorHtml = fs.readFileSync("frontend/public/vendor/twsaimahui/index.html", "utf8")
const sharedRuntime = fs.readFileSync("frontend/public/vendor/_shared/lottery-site-runtime.js", "utf8")
if (!vendorHtml.includes('/vendor/_shared/lottery-site-bridge.js') || !vendorHtml.includes('/vendor/_shared/lottery-site-runtime.js') || !vendorHtml.includes('id="vendor-site-footer"')) throw new Error("vendor page must load the shared bridge, runtime, and footer mount")
if (/<script[^>]+src=['"]static\/js\/\d{3}/.test(vendorHtml)) throw new Error("vendor page must not execute independent legacy prediction scripts")
if (!sharedRuntime.includes("vendor-shared-nav-fixed") || !sharedRuntime.includes("canonical_modules")) throw new Error("shared runtime must own sticky navigation and canonical prediction rendering")
const events = []
const listeners = new Map()
const storage = new Map()
let now = 1_700_000_000_000
let fetchCalls = 0
let resolveDraw
const window = {
  location: { origin: "https://twsaimahui.test" },
  document: { currentScript: { dataset: { siteKey: "twsaimahui" } } },
  LEGACY_TWSAIMAHUI_RUNTIME: { applyBridgeConfig(config) { this.applied = config } },
  dispatchEvent(event) { events.push(event); for (const listener of listeners.get(event.type) || []) listener(event); return true },
  addEventListener(type, listener) { listeners.set(type, [...(listeners.get(type) || []), listener]) },
  CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail } },
  sessionStorage: {
    getItem(key) { return storage.get(key) || null },
    setItem(key, value) { storage.set(key, value) },
    removeItem(key) { storage.delete(key) },
  },
  setTimeout,
  clearTimeout,
}
const config = { site: { site_key: "twsaimahui", web_id: 6, lottery_type: 3 }, api: { http_api_base: "", kaijiang_api_base: "/api/kaijiang" }, bridge: { auto_load: { draw: true, prediction: true }, prediction_module_keys: ["module-a"], runtime: {} }, brand: {} }
const context = {
  window,
  document: window.document,
  CustomEvent: window.CustomEvent,
  URL,
  AbortController,
  fetch: async (path) => {
    fetchCalls++
    if (path.endsWith("bridge-config")) return { ok: true, json: async () => ({ ok: true, data: config }) }
    if (path.includes("prediction-modules")) return { ok: true, json: async () => ({ ok: true, data: { canonical_modules: [{ moduleKey: "module-a" }] } }) }
    if (path.includes("draw")) return new Promise((resolve) => { resolveDraw = () => resolve({ ok: true, json: async () => ({ ok: true, data: { current_issue: "2026170" } }) }) })
    return { ok: false, status: 503, json: async () => ({ error: "offline" }) }
  },
  Date: class extends Date { static now() { return now } },
  setTimeout,
  clearTimeout,
  console,
}
vm.runInNewContext(source, context, { filename: "site-bridge.js" })
await window.LotterySiteBridge.ready
if (window.LEGACY_TWSAIMAHUI_RUNTIME.applied.site.web_id !== 6) throw new Error("bridge config must apply runtime identity")

const firstDraw = window.LotterySiteBridge.getDraw()
const secondDraw = window.LotterySiteBridge.getDraw()
if (fetchCalls !== 2) throw new Error("concurrent draw calls must share one in-flight request")
resolveDraw()
await Promise.all([firstDraw, secondDraw])
if (!events.some((event) => event.type === "lottery:draw-ready")) throw new Error("draw request must dispatch ready event")

const callsAfterDraw = fetchCalls
await window.LotterySiteBridge.getDraw()
if (fetchCalls !== callsAfterDraw) throw new Error("fresh draw cache must avoid a network request")

now += 30_000
await window.LotterySiteBridge.getDraw()
await Promise.resolve()
if (fetchCalls !== callsAfterDraw + 1 || !events.some((event) => event.type === "lottery:draw-stale")) throw new Error("stale draw cache must render then refresh")

await window.LotterySiteBridge.getPredictionModules()
if (!events.some((event) => event.type === "lottery:prediction-ready")) throw new Error("prediction request must dispatch ready event")
