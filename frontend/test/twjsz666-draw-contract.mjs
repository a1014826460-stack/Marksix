import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twjsz666/site-data-adapter.js", "utf8")
const drawPage = fs.readFileSync("frontend/public/vendor/twjsz666/kai.html", "utf8")
const indexPage = fs.readFileSync("frontend/public/vendor/twjsz666/index.html", "utf8")
const siteLayout = fs.readFileSync("frontend/app/twjsz666/layout.tsx", "utf8")

for (const token of ["renderDrawPanel", "loadDraw({ lotteryType: type })", "loadDraw({ lotteryType: 3 })", "current_issue", "is_special", "开奖"])
  if (!adapter.includes(token)) throw new Error(`draw adapter missing ${token}`)

if (!drawPage.includes('data-lottery-type="3"') || !drawPage.includes('data-lottery-type="2"') || !drawPage.includes('data-lottery-type="1"'))
  throw new Error("draw tabs are incomplete")
for (const lotteryType of ["3", "2", "1"]) {
  if (!drawPage.includes(`/vendor/shengshi8800/kj/local.html?lottery_type=${lotteryType}`)) {
    throw new Error(`draw tab ${lotteryType} does not use the unified draw module`)
  }
}
if (!drawPage.includes('class="KJ-IFRAME"')) throw new Error("draw tabs do not retain the unified draw iframe slot")
if (!drawPage.includes('that.index(el,"LI")') || !drawPage.includes('that.getEl(dom,ind,"DIV")')) {
  throw new Error("draw tabs must select the matching unified draw panel")
}
if (!siteLayout.includes('buildSiteMetadata("twjsz666")')) throw new Error("twjsz666 top-level metadata is not site-owned")
if (!indexPage.includes('href="/history?type=3"')) throw new Error("history entry does not use the standard page")
console.log("twjsz666 draw contract passed")
