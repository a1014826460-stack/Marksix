import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twjsz666/site-data-adapter.js", "utf8")
const config = fs.readFileSync("frontend/public/vendor/twjsz666/site-config.js", "utf8")
const html = fs.readFileSync("frontend/public/vendor/twjsz666/index.html", "utf8")

for (const token of [
  'siteKey: "twjsz666"',
  'siteName: "台湾金手指"',
  'siteDomain: "www.twjsz666.com"',
  'lotteryType: 3',
  'lotteryType: 2',
  'lotteryType: 1',
]) if (!config.includes(token)) throw new Error(`missing site config token ${token}`)

for (const token of [
  "renderSanTouSiWeiHistory",
  "renderYixiaoYimaHistory",
  "renderShuangBoHistory",
  "renderPingTeXiaoHistory",
  "renderDaXiaoHistory",
  "SECTION_CONTRACTS",
  "Unknown visible twjsz666 section",
  "loadDraw({ lotteryType: selected })",
  "loadPredictions({ lotteryType: selected, historyLimit: HISTORY_LIMIT })",
  "event.source !== drawFrame.contentWindow",
  "event.origin !== window.location.origin",
  "暂无后端资料",
]) if (!adapter.includes(token)) throw new Error(`missing adapter contract token ${token}`)

if (adapter.includes("function renderUnavailableSection")) throw new Error("generic unavailable section fallback remains")

for (const prohibited of ["document.createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "rowDisplay"]) {
  if (adapter.includes(prohibited)) throw new Error(`forbidden DOM operation ${prohibited}`)
}

if (!html.includes("site-data-adapter.js")) throw new Error("adapter is not loaded by vendor entry")
console.log("twjsz666 adapter contract passed")
