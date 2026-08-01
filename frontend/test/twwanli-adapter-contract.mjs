import fs from "node:fs"

const html = fs.readFileSync("frontend/public/vendor/twwanli/index.html", "utf8")
const draw = fs.readFileSync("frontend/public/vendor/twwanli/kai.html", "utf8")
const config = fs.readFileSync("frontend/public/vendor/twwanli/site-config.js", "utf8")
const adapter = fs.readFileSync("frontend/public/vendor/twwanli/site-data-adapter.js", "utf8")

for (const token of [
  'siteKey: "twwanli"',
  'siteName: "台湾万利网"',
  'siteDomain: "www.twwanli.com"',
  'lotteryType: 3',
  'lotteryType: 2',
  'lotteryType: 1',
]) {
  if (!config.includes(token)) throw new Error(`missing site identity token: ${token}`)
}

for (const token of [
  "lottery-site-data-client.js",
  "site-config.js",
  "site-data-adapter.js",
  'site-key="twwanli"',
  'id="legacy-attribute-anchor"',
  'id="legacy-attribute-gallery"',
]) {
  if (!html.includes(token)) throw new Error(`vendor entry is missing ${token}`)
}

for (const token of [
  "loadDraw({ lotteryType: lotteryType })",
  "loadPredictions({ lotteryType: lotteryType, historyLimit: 7 })",
  "selectLottery",
  "renderOneCodeOneXiaoTable",
  "renderThreeColumnHistory",
  "renderUnavailableHistory",
  "historyLimit: 7",
]) {
  if (!adapter.includes(token)) throw new Error(`adapter is missing ${token}`)
}

for (const forbidden of ["document.createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "lottery-site-runtime.js"]) {
  if (adapter.includes(forbidden)) throw new Error(`existing-DOM adapter must not use ${forbidden}`)
}

for (const token of ['data-lottery-type="3"', 'data-lottery-type="2"', 'data-lottery-type="1"', 'data-current-issue', "postMessage", 'siteKey: "twwanli"']) {
  if (!draw.includes(token)) throw new Error(`draw tab contract is missing ${token}`)
}

console.log("twwanli adapter contract passed")
