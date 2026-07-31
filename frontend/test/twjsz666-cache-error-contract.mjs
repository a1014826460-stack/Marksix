import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twjsz666/site-data-adapter.js", "utf8")
const client = fs.readFileSync("frontend/public/vendor/_shared/lottery-site-data-client.js", "utf8")

for (const token of [
  "historyByLottery[selected]",
  "historyRequests[selected]",
  "activeLottery.lotteryType === selected",
  "distinctRows(module)",
  "Math.min(Math.max(maximum, 1), 20)",
  "event.source !== drawFrame.contentWindow",
  "event.origin !== window.location.origin",
  "message.siteKey !== siteConfig.siteKey",
]) {
  if (!adapter.includes(token)) throw new Error(`missing cache/error contract token: ${token}`)
}

for (const token of [
  "inFlight[requestKey]",
  "state: \"stale\"",
  "state: \"error\"",
  "delete inFlight[requestKey]",
  "JSON.stringify(normalizedQuery)",
]) {
  if (!client.includes(token)) throw new Error(`shared client lacks cache/error behavior: ${token}`)
}

if (/modules\["9xiao12ma"\]\s*\|\|\s*modules\.pt1xiao/.test(adapter)) {
  throw new Error("unsafe one-head/one-code approximate fallback remains")
}
if (/modules\.pt3xiao\s*\|\|\s*modules\.title_47/.test(adapter)) {
  throw new Error("unsafe three-head/four-tail approximate fallback remains")
}

console.log("twjsz666 cache/error contract passed")
