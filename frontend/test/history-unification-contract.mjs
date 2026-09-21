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
if (!legacyDrawApi.includes("ball.element") || !sharedDrawPanel.includes('buildAppUrl("/api/latest-draw?')) {
  throw new Error("live draw rendering contract changed unexpectedly")
}

// 历史开奖展示闸门必须与后端 system_config 的可配置延迟一致（默认 8 分钟），
// 不允许再出现写死的 4 分钟快照兜底。
if (!historyApi.includes("HISTORY_UNLOCK_DELAY_MINUTES")) {
  throw new Error("frontend history fallback must use the configurable unlock delay")
}
if (historyApi.includes("4 * 60 * 1000")) {
  throw new Error("frontend history fallback must not hardcode a four minute window")
}
if (!historyApi.includes(": 8")) {
  throw new Error("frontend history fallback default must be eight minutes")
}

// 香港彩轮序发布：共享开奖面板必须按已公布前缀逐号展示。
for (const token of [
  "PROGRESSIVE_REVEAL_LOTTERY_TYPES = { 1: true }",
  "function _progressiveBallCount(",
  "latest-draw:branch-progressive-render",
]) {
  if (!sharedDrawPanel.includes(token)) {
    throw new Error(`shared draw panel must keep HK progressive (rolling) publication: ${token}`)
  }
}

// twsaimahui 不再维护独立开奖面板：runtime 垫片抽到 /vendor/_shared/kj-runtime.js，
// 由共享 local.html 统一引用。
if (fs.existsSync("frontend/public/vendor/twsaimahui/kj/local.html")) {
  throw new Error("twsaimahui must reuse the shared draw panel instead of forking it")
}
const kjRuntimeShim = source("frontend/public/vendor/_shared/kj-runtime.js")
for (const token of [
  "window.LEGACY_TWSAIMAHUI_RUNTIME",
  "LegacyKjRuntime",
  "buildAppUrl",
  "buildHistoryUrl",
  "buildVendorPath",
  "sharedPanelPath",
]) {
  if (!kjRuntimeShim.includes(token)) {
    throw new Error(`shared kj runtime shim missing contract token: ${token}`)
  }
}
if (!sharedDrawPanel.includes('<script src="/vendor/_shared/kj-runtime.js"></script>')) {
  throw new Error("shared draw panel must load the shared kj runtime shim")
}
if (sharedDrawPanel.includes("LEGACY_TWSAIMAHUI_RUNTIME")) {
  throw new Error("shared draw panel must not re-implement the site runtime shim inline")
}
const twsaimahuiKj = source("frontend/public/vendor/twsaimahui/static/js/kj.js")
if (!twsaimahuiKj.includes('window.LegacyKjRuntime.buildVendorPath("kj/local.html")')) {
  throw new Error("twsaimahui kj tabs must resolve the shared draw panel through the shim")
}
if (twsaimahuiKj.includes('? __legacyTwsRuntime.buildVendorPath("kj/local.html")')) {
  throw new Error("twsaimahui kj tabs must not fall back to its own removed draw panel")
}
const twsaimahuiIndex = source("frontend/public/vendor/twsaimahui/index.html")
if (twsaimahuiIndex.indexOf("/vendor/_shared/kj-runtime.js") > twsaimahuiIndex.indexOf("static/js/kj.js")) {
  throw new Error("twsaimahui must load the kj runtime shim before its kj tabs script")
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
