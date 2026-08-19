import fs from "node:fs"

function source(path) {
  return fs.readFileSync(path, "utf8")
}

const proxy = source("frontend/proxy.ts")
const historyApi = source("frontend/app/api/draw-history/route.ts")
const legacyHistoryJsonp = source("frontend/app/index/ajax/ttklsjl/route.ts")
const legacyDrawApi = source("frontend/app/wy.json/route.ts")
const sharedDrawPanel = source("frontend/public/vendor/shengshi8800/kj/local.html")

for (const path of ["/index/index/history.html", "/baomaqg/am/kaijiangjilu.html"]) {
  if (!proxy.includes(path)) throw new Error(`legacy history mapping missing: ${path}`)
}
for (const suffix of ["/history.html", "/wylhc.html"]) {
  if (!proxy.includes(`pathname.endsWith(\"${suffix}\")`)) {
    throw new Error(`legacy history suffix mapping missing: ${suffix}`)
  }
}
if (!proxy.includes("NextResponse.rewrite(url)")) {
  throw new Error("legacy history URLs must render the standard history component by rewrite")
}
if (fs.existsSync("frontend/app/index/index/history.html/route.ts")) {
  throw new Error("independent legacy history route must be removed")
}
if ((historyApi.match(/Cache-Control/g) || []).length < 2 || !historyApi.includes('"no-store"')) {
  throw new Error("all frontend draw-history responses must disable caching")
}
if (!historyApi.includes('code !== "ENOENT"')) {
  throw new Error("missing fallback snapshots must not fail the history API")
}
if (!historyApi.includes("items: []") || !historyApi.includes("total: 0")) {
  throw new Error("missing fallback snapshots must return an empty paginated history response")
}
if (!legacyHistoryJsonp.includes('backendFetchJson<DrawHistoryResponse>("/public/draw-history"')) {
  throw new Error("legacy JSONP history output must reuse the gated backend history API")
}
if (!legacyHistoryJsonp.includes('"Cache-Control": "no-store"')) {
  throw new Error("legacy JSONP history output must disable caching")
}
if (legacyDrawApi.includes('backendFetchJson<DrawHistoryResponse>("/public/draw-history"')) {
  throw new Error("live draw compatibility API must not depend on delayed history")
}
if (!legacyDrawApi.includes("ball.element") || !sharedDrawPanel.includes('fetch("/api/latest-draw?')) {
  throw new Error("live draw rendering contract changed unexpectedly")
}

for (const path of [
  "frontend/public/vendor/twbst528/history.html",
  "frontend/public/vendor/twcaibawang.com/wylhc.html",
  "frontend/public/vendor/twcf888.com/wylhc.html",
  "frontend/public/vendor/twjsz666/wylhc.html",
  "frontend/public/vendor/twsyw/history.html",
  "frontend/public/vendor/twwanli/wylhc.html",
]) {
  if (fs.existsSync(path)) throw new Error(`independent history template remains: ${path}`)
}

console.log("History unification and live draw isolation contract passed")
