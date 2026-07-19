import fs from "node:fs"
import vm from "node:vm"

const source = fs.readFileSync("frontend/public/vendor/twsaimahui/site-bridge.js", "utf8")
const events = []
const listeners = new Map()
const window = {
  location: { origin: "https://twsaimahui.test" },
  document: { currentScript: { dataset: { siteKey: "twsaimahui" } } },
  LEGACY_TWSAIMAHUI_RUNTIME: {
    applyBridgeConfig(config) { this.applied = config },
  },
  dispatchEvent(event) { events.push(event); for (const listener of listeners.get(event.type) || []) listener(event); return true },
  addEventListener(type, listener) { listeners.set(type, [...(listeners.get(type) || []), listener]) },
  CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail } },
  setTimeout,
  clearTimeout,
}
const responses = [
  { ok: true, json: async () => ({ ok: true, data: { site: { site_key: "twsaimahui", web_id: 6, lottery_type: 3 }, api: { http_api_base: "", kaijiang_api_base: "/api/kaijiang" }, bridge: { auto_load: { draw: false, prediction: false }, prediction_module_keys: [] }, brand: {} } }) },
  { ok: true, json: async () => ({ ok: true, data: { canonical_modules: [{ moduleKey: "module-a" }] } }) },
  { ok: false, status: 503, json: async () => ({ error: "offline" }) },
]
const context = {
  window,
  document: window.document,
  CustomEvent: window.CustomEvent,
  URL,
  AbortController,
  fetch: async () => responses.shift(),
  setTimeout,
  clearTimeout,
  console,
}
vm.runInNewContext(source, context, { filename: "site-bridge.js" })
await window.LotterySiteBridge.ready
if (window.LEGACY_TWSAIMAHUI_RUNTIME.applied.site.web_id !== 6) throw new Error("bridge config must apply runtime identity")
await window.LotterySiteBridge.getPredictionModules()
if (!events.some((event) => event.type === "lottery:prediction-ready")) throw new Error("prediction request must dispatch ready event")
let failed = false
try { await window.LotterySiteBridge.getDraw() } catch { failed = true }
if (!failed || !events.some((event) => event.type === "lottery:error" && event.detail.error.retryable)) throw new Error("failed draw requests must dispatch retryable errors")
