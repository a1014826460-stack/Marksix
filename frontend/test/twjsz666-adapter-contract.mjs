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
  "renderThreeHeadFourTailUnavailable",
  "renderOneHeadOneCodeUnavailable",
  "renderOneHeadOneCode",
  "renderBeforeBetCards",
  "renderPublicCards",
  '"wuxiao_wuma"',
  "renderShuangBoHistory",
  "renderPingTeXiaoHistory",
  "renderDaXiaoHistory",
  "SECTION_CONTRACTS",
  "Unknown visible twjsz666 section",
  "loadDraw({ lotteryType: selected })",
  "loadPredictions({ lotteryType: selected, historyLimit: historyLimitForPage() })",
  "event.source !== drawFrame.contentWindow",
  "event.origin !== window.location.origin",
]) if (!adapter.includes(token)) throw new Error(`missing adapter contract token ${token}`)

if (adapter.includes("资料同步中")) throw new Error("loading placeholder remains in adapter")

if (adapter.includes("function renderUnavailableSection")) throw new Error("generic unavailable section fallback remains")

// 白名单说明（2026-09-29）：`highlightToken()` 用 `document.createElement("span")` +
// `insertBefore/appendChild` 把「命中的那一个 token」包成 `data-prediction-hit` 高亮节点
// ——这是该站点命中高亮的既有实现（HEAD 起就在），不是新增的 DOM 破坏。
// 仍禁止：`replaceChildren`（整块替换）、`innerHTML`（写入未转义 HTML）、`document.write`。
for (const prohibited of ["replaceChildren", "innerHTML", "document.write", "rowDisplay"]) {
  if (adapter.includes(prohibited)) throw new Error(`forbidden DOM operation ${prohibited}`)
}

if (!html.includes("site-data-adapter.js")) throw new Error("adapter is not loaded by vendor entry")
console.log("twjsz666 adapter contract passed")
