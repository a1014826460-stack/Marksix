import fs from "node:fs"

const html = fs.readFileSync("frontend/public/vendor/twwanli/index.html", "utf8")
const draw = fs.readFileSync("frontend/public/vendor/twwanli/kai.html", "utf8")
const config = fs.readFileSync("frontend/public/vendor/twwanli/site-config.js", "utf8")
const adapter = fs.readFileSync("frontend/public/vendor/twwanli/site-data-adapter.js", "utf8")

if (!html.includes('<iframe width="100%" height="270" frameborder="0" scrolling="no" src="kai.html">')) {
  throw new Error("outer draw frame must fit the complete draw tab page")
}

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

const WRITE_ROW_SECTIONS = [
  "msks", "wsxx", "wl4x", "dxzt", "jxzt", "jz5x", "5wzt", "jx24m", "sdzt",
  "ybzt", "tdsx", "3tzt", "hsdx", "pt1xiao", "hsds", "qqsh", "dssx",
]

function predictionSection(sectionId) {
  return html.match(new RegExp(`<div[^>]*id="${sectionId}"[^>]*data-prediction-section[^>]*>[\\s\\S]*?(?=<div[^>]*data-prediction-section|$)`))?.[0] || ""
}

for (const sectionId of WRITE_ROW_SECTIONS) {
  const section = predictionSection(sectionId)
  if (!section) throw new Error(`missing writeRow prediction section: ${sectionId}`)
  const dynamicRows = [...section.matchAll(/<tr\b[\s\S]*?<\/tr>/g)].filter(([row]) => row.includes("data-prediction-"))
  if (!dynamicRows.length) throw new Error(`${sectionId} writeRow section must enumerate dynamic rows`)
  for (const [index, [row]] of dynamicRows.entries()) {
    const slotCounts = {
      issue: (row.match(/data-prediction-issue/g) || []).length,
      content: (row.match(/data-prediction-content(?!-secondary)/g) || []).length,
      result: (row.match(/data-prediction-result/g) || []).length,
    }
    if (slotCounts.issue !== 1 || slotCounts.content !== 1 || slotCounts.result !== 1) {
      throw new Error(`${sectionId} row ${index + 1} writeRow slots must be exactly issue/content/result: ${JSON.stringify(slotCounts)}`)
    }
  }
}

for (const sectionId of WRITE_ROW_SECTIONS) {
  if (!adapter.includes(`renderThreeColumnHistory("${sectionId}"`) && !adapter.includes(`renderOddEvenFourXiao(modules)`)) {
    throw new Error(`${sectionId} is not explicitly associated with a writeRow renderer`)
  }
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
  "loadPredictions({ lotteryType: lotteryType, historyLimit: 8 })",
  "selectLottery",
  "renderOneCodeOneXiaoTable",
  "renderThreeColumnHistory",
  "renderUnavailableHistory",
  "historyLimit: 8",
  "modules[\"3hang\"]",
  "modules[\"6xzt\"]",
  "renderFiveElements",
  "renderLuckyOminousSixXiao",
  "rawValue(source, \"xiao_1\")",
  "rawValue(source, \"xiao_2\")",
]) {
  if (!adapter.includes(token)) throw new Error(`adapter is missing ${token}`)
}

for (const forbidden of ["document.createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "lottery-site-runtime.js"]) {
  if (adapter.includes(forbidden)) throw new Error(`existing-DOM adapter must not use ${forbidden}`)
}

if (!draw.includes("that.index(el, \"LI\")")) throw new Error("draw tab index must ignore whitespace text nodes")
if (!draw.includes('height:190px!important') || draw.includes('height:155px')) {
  throw new Error("draw frame must preserve the shared panel's full 190px height on mobile")
}

for (const sectionId of ["jz5x", "dssx", "sdzt", "qqsh"]) {
  if (!html.includes(`id="${sectionId}"`)) throw new Error(`missing ${sectionId} contract anchor`)
}
if (!html.includes("#sdzt [data-prediction-issue]") || !html.includes("#sdzt [data-prediction-content]") || !html.includes("#sdzt [data-prediction-result]")) {
  throw new Error("four-segment prediction leaves must retain centered alignment")
}

for (const token of ['data-lottery-type="3"', 'data-lottery-type="2"', 'data-lottery-type="1"', 'data-current-issue', "postMessage", 'siteKey: "twwanli"']) {
  if (!draw.includes(token)) throw new Error(`draw tab contract is missing ${token}`)
}

console.log("twwanli adapter contract passed")
