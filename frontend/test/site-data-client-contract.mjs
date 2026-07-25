import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const source = fs.readFileSync(
  "frontend/public/vendor/_shared/lottery-site-data-client.js",
  "utf8"
)
const storage = new Map()
let now = 0
let fetchCalls = 0
let fetchMode = "online"

const context = {
  URLSearchParams,
  Date: { now: () => now },
  Promise,
  setTimeout,
  clearTimeout,
  fetch: async (url) => {
    fetchCalls += 1
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

now += 61_000
fetchMode = "offline"
const stalePrediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 8 })
assert.equal(stalePrediction.state, "stale")
assert.equal(stalePrediction.source, "session-storage")

now += 15 * 60_000
const expiredPrediction = await client.loadPredictions({ lotteryType: 3, historyLimit: 8 })
assert.equal(expiredPrediction.state, "error", "prediction stale cache must be bounded")
