import fs from "node:fs"

const html = fs.readFileSync("frontend/public/vendor/twsyw/index.html", "utf8")
const draw = fs.readFileSync("frontend/public/vendor/twsyw/kai.html", "utf8")
const config = fs.readFileSync("frontend/public/vendor/twsyw/site-config.js", "utf8")
const adapter = fs.readFileSync("frontend/public/vendor/twsyw/site-data-adapter.js", "utf8")

for (const token of [
  'siteKey: "twsyw"',
  'siteName: "台湾神预网"',
  'siteDomain: "www.twsyw.com"',
  'lotteryType: 3',
  'lotteryType: 2',
  'lotteryType: 1',
]) {
  if (!config.includes(token)) throw new Error(`missing site identity token: ${token}`)
}

const SECTION_RENDERERS = Object.freeze({
  msks: "renderThreeColumnHistory", wsxx: "renderThreeColumnHistory", yxym: "renderOneCodeOneXiaoTable",
  wl4x: "renderThreeColumnHistory", dxzt: "renderThreeColumnHistory", jxzt: "renderUnavailableHistory",
  jz5x: "renderUnavailableHistory", "5wzt": "renderThreeColumnHistory", jx24m: "renderThreeColumnHistory",
  dssx: "renderThreeColumnHistory", sdzt: "renderThreeColumnHistory", ybzt: "renderThreeColumnHistory",
  tdsx: "renderThreeColumnHistory", "3tzt": "renderThreeColumnHistory", hsdx: "renderThreeColumnHistory",
  pt1xiao: "renderThreeColumnHistory", hsds: "renderThreeColumnHistory", qqsh: "renderThreeColumnHistory",
})
const WRITE_ROW_SECTIONS = Object.keys(SECTION_RENDERERS).filter((sectionId) => sectionId !== "yxym")

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

for (const [sectionId, renderer] of Object.entries(SECTION_RENDERERS)) {
  if (renderer === "renderOneCodeOneXiaoTable") {
    if (!adapter.includes("renderOneCodeOneXiaoTable(modules)")) throw new Error(`${sectionId} is not explicitly associated with its renderer`)
  } else if (!adapter.includes(`${renderer}("${sectionId}"`)) {
    throw new Error(`${sectionId} is not explicitly associated with its renderer`)
  }
}

for (const token of [
  "lottery-site-data-client.js",
  "site-config.js",
  "site-data-adapter.js",
  'site-key="twsyw"',
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
  "updatePredictionTitles",
  "historyLimit: 7",
]) {
  if (!adapter.includes(token)) throw new Error(`adapter is missing ${token}`)
}

for (const forbidden of ["document.createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "lottery-site-runtime.js"]) {
  if (adapter.includes(forbidden)) throw new Error(`existing-DOM adapter must not use ${forbidden}`)
}

for (const token of ['data-lottery-type="3"', 'data-lottery-type="2"', 'data-lottery-type="1"', 'data-current-issue', "postMessage", 'siteKey: "twsyw"']) {
  if (!draw.includes(token)) throw new Error(`draw tab contract is missing ${token}`)
}

console.log("twsyw adapter contract passed")
