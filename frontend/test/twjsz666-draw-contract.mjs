import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twjsz666/site-data-adapter.js", "utf8")
const drawPage = fs.readFileSync("frontend/public/vendor/twjsz666/kai.html", "utf8")
const historyPage = fs.readFileSync("frontend/public/vendor/twjsz666/wylhc.html", "utf8")

for (const token of ["renderDrawPanel", "loadDraw({ lotteryType: type })", "loadDraw({ lotteryType: 3 })", "current_issue", "is_special", "开奖"])
  if (!adapter.includes(token)) throw new Error(`draw adapter missing ${token}`)

if (!drawPage.includes('data-lottery-type="3"') || !drawPage.includes('data-lottery-type="2"') || !drawPage.includes('data-lottery-type="1"'))
  throw new Error("draw tabs are incomplete")
if (!historyPage.includes('data-history-lottery-type')) throw new Error("history page does not declare its lottery type")
console.log("twjsz666 draw contract passed")
