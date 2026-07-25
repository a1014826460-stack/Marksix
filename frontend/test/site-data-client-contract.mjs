import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const source = fs.readFileSync(
  "frontend/public/vendor/_shared/lottery-site-data-client.js",
  "utf8"
)
const storage = new Map()
const persistentStorage = new Map()
let now = 0
let fetchCalls = 0
let fetchMode = "online"
let lastUrl = ""

const context = {
  URLSearchParams,
  Date: { now: () => now },
  Promise,
  setTimeout,
  clearTimeout,
  fetch: async (url) => {
    fetchCalls += 1
    lastUrl = String(url)
    if (fetchMode === "offline") throw new Error("network unavailable")
    if (url.includes("/draw?")) {
      return { ok: true, json: async () => ({ current_issue: "2026170", balls: [] }) }
    }
    return { ok: true, json: async () => ({ modules: [{ key: "wuxiao_wuma" }] }) }
  },
  sessionStorage: {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: (key) => storage.delete(key),
  },
  localStorage: {
    getItem: (key) => persistentStorage.get(key) ?? null,
    setItem: (key, value) => persistentStorage.set(key, String(value)),
    removeItem: (key) => persistentStorage.delete(key),
  },
}
context.window = context
vm.runInNewContext(source, context, { filename: "lottery-site-data-client.js" })

const client = context.LotterySiteDataClient.create({ siteKey: "twsaimahui" })
const first = client.loadDraw({ lotteryType: 3 })
const second = client.loadDraw({ lotteryType: 3 })
const [firstResult, secondResult] = await Promise.all([first, second])

assert.equal(fetchCalls, 1, "same draw request must be de-duplicated")
assert.equal(firstResult.state, "ready")
assert.equal(secondResult.data.current_issue, "2026170")

now += 6000
fetchMode = "offline"
const staleDraw = await client.loadDraw({ lotteryType: 3 })
assert.equal(staleDraw.state, "stale", "expired cached draw must provide stale fallback")
assert.equal(staleDraw.data.current_issue, "2026170")
assert.equal(staleDraw.source, "session-storage")

const uncachedPrediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 8 })
assert.equal(uncachedPrediction.state, "error")
assert.equal(uncachedPrediction.error.retryable, true)

fetchMode = "online"
const prediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 8 })
assert.equal(prediction.state, "ready")
assert.equal(prediction.data.modules[0].key, "wuxiao_wuma")

await client.loadPredictions({ lotteryType: 3, historyLimit: 8, includeVendor: false })
assert.match(lastUrl, /\/prediction-modules\?/, "prediction requests must use the registered site route")
assert.match(lastUrl, /include_vendor=0/, "site adapters must be able to exclude unrelated vendor composites")

now += 61_000
fetchMode = "offline"
const stalePrediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 8 })
assert.equal(stalePrediction.state, "stale")
assert.equal(stalePrediction.source, "session-storage")

fetchMode = "online"
now += 1
const durablePrediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 1, includeVendor: false })
assert.equal(durablePrediction.state, "ready")
assert.ok(persistentStorage.size > 0, "prediction data must survive a browser-session reset")

storage.clear()
const requestsBeforePersistentHit = fetchCalls
const recoveredFromPersistentCache = await client.loadPredictions({ lotteryType: 3, historyLimit: 1, includeVendor: false })
assert.equal(recoveredFromPersistentCache.state, "ready", "fresh persistent prediction cache must avoid a second visit request")
assert.equal(recoveredFromPersistentCache.source, "local-storage")
assert.equal(fetchCalls, requestsBeforePersistentHit)

now += 15 * 60_000
fetchMode = "offline"
const stalePersistentPrediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 1, includeVendor: false })
assert.equal(stalePersistentPrediction.state, "stale", "persistent prediction cache must provide bounded offline fallback")
assert.equal(stalePersistentPrediction.source, "local-storage")
