import fs from "node:fs"

const root = "frontend/public/vendor/twsyw"
const html = fs.readFileSync(`${root}/index.html`, "utf8")
const draw = fs.readFileSync(`${root}/kai.html`, "utf8")
const config = fs.readFileSync(`${root}/site-config.js`, "utf8")
const adapter = fs.readFileSync(`${root}/site-data-adapter.js`, "utf8")
const manifest = fs.readFileSync("frontend/sites/twsyw/site.manifest.ts", "utf8")
const dependencies = fs.readFileSync("backend/src/domains/prediction/site_page_dependencies.py", "utf8")

// 开奖标签页与面板已从 kai.html 内联进 index.html：少一层同源 iframe。
// 契约改为断言"内联后的结构存在"且"不再有指向 kai.html 的活动 iframe"。
if (html.includes('src="kai.html"')) {
  throw new Error("index.html must not keep the kai.html iframe after inlining the draw tabs")
}
for (const token of [
  'class="KJ-TabBox"',
  '<p data-current-issue aria-live="polite"></p>',
  'KJTB.init(".KJ-TabBox")',
  'class="KJ-IFRAME"',
  "TwsywSiteDataAdapter.selectLottery",
]) {
  if (!html.includes(token)) throw new Error(`inlined draw tabs missing token: ${token}`)
}
for (const lotteryType of ["3", "2", "1"]) {
  if (!html.includes(`data-lottery-type="${lotteryType}"`)) {
    throw new Error(`inlined draw tabs missing lottery type ${lotteryType}`)
  }
}
if (!html.includes("/vendor/shengshi8800/kj/local.html?lottery_type=3")) {
  throw new Error("inlined draw tabs must keep using the unified local draw panel")
}
// 适配器不能再依赖被移除的中间 iframe 文档；期号写回同文档的 [data-current-issue]。
// 只看代码、忽略行注释，避免注释里提到旧选择器就误判。
const adapterCode = adapter.replace(/^\s*\/\/.*$/gm, "")
if (adapterCode.includes("knownDrawFrame") || adapterCode.includes("iframe[src='kai.html']")) {
  throw new Error("adapter must not depend on the removed kai.html frame")
}
if (!adapterCode.includes("drawPanelFrame") || !adapter.includes('document.querySelector("[data-current-issue]")')) {
  throw new Error("adapter must look up the inlined panel target lazily in the same document")
}

for (const token of ['siteKey: "twsyw"', 'siteName: "台湾神预网"', 'siteDomain: "www.twsyw.com"', 'lotteryType: 3', 'lotteryType: 2', 'lotteryType: 1']) {
  if (!config.includes(token)) throw new Error(`missing site identity token: ${token}`)
}

const SECTION_RENDERERS = Object.freeze({
  top_xiao_code: { renderer: "renderTopXiaoCode", rows: 56 }, fslx: { renderer: "renderFslx", rows: 20 }, m24: { renderer: "renderM24", rows: 20 }, daxiao: { renderer: "renderDaxiao", rows: 20 }, jiaye: { renderer: "renderJiaye", rows: 20 }, qixiao: { renderer: "renderQixiao", rows: 20 }, jiaye4xiao: { renderer: "renderJiaye4xiao", rows: 20 }, gold6xiao: { renderer: "renderGold6xiao", rows: 21 }, pt1wei: { renderer: "renderPt1wei", rows: 21 }, winner12: { renderer: "renderWinner12", rows: 20 }, jiuxiao: { renderer: "renderJiuxiao", rows: 20 }, lianma: { renderer: "renderLianma", rows: 20 }, nannv: { renderer: "renderNannv", rows: 20 }, danshuang: { renderer: "renderDanshuang", rows: 20 }, dssx: { renderer: "renderDssx", rows: 20 }, hblvxiao: { renderer: "renderHblvxiao", rows: 21 }, santou: { renderer: "renderSantou", rows: 20 }, qiw: { renderer: "renderQiw", rows: 20 }, kill4xiao: { renderer: "renderKill4xiao", rows: 20 }, kill3wei: { renderer: "renderKill3wei", rows: 20 }, chengyu: { renderer: "renderChengyu", rows: 20 }, shuangbo: { renderer: "renderShuangbo", rows: 20 }, kill1tou: { renderer: "renderKill1tou", rows: 20 }, five_no_hit: { renderer: "renderFiveNoHit", rows: 20 }, composite_kill: { renderer: "renderCompositeKill", rows: 20 },
})
function section(id) { return html.match(new RegExp(`<div[^>]*id="${id}"[^>]*data-prediction-section[^>]*>[\\s\\S]*?(?=<div[^>]*class="white-box"|<div[^>]*class="foot-yuming"|$)`))?.[0] || "" }
for (const [id, contract] of Object.entries(SECTION_RENDERERS)) {
  const { renderer, rows: expectedRows } = contract
  const source = section(id)
  if (!source) throw new Error(`missing prediction section: ${id}`)
  const rows = [...source.matchAll(/<tr\b[\s\S]*?<\/tr>/g)].filter(([row]) => row.includes("data-prediction-content"))
  if (!rows.length) throw new Error(`${id} must enumerate prediction groups`)
  if (rows.length !== expectedRows) throw new Error(`${id} static contract expected ${expectedRows} dynamic rows, found ${rows.length}`)
  for (const [index, [row]] of rows.entries()) {
    const counts = { issue: (row.match(/data-prediction-issue/g) || []).length, content: (row.match(/data-prediction-content/g) || []).length, result: (row.match(/data-prediction-result/g) || []).length }
    if (counts.issue !== 1 || counts.content !== 1 || counts.result !== 1) throw new Error(`${id} row ${index + 1} must have exactly issue/content/result slots: ${JSON.stringify(counts)}`)
  }
  if (renderer === "renderTopXiaoCode") {
    const headerIssues = (source.match(/data-prediction-draw-issue/g) || []).length
    const headerResults = (source.match(/data-prediction-draw-result/g) || []).length
    if (expectedRows !== 56 || headerIssues !== 8 || headerResults !== 8) throw new Error(`${id} must retain 8 draw headers and 56 dynamic detail rows`)
    if (!adapter.includes("renderTopXiaoCode(modules)")) throw new Error(`${id} renderer missing`)
  } else if (!adapter.includes(`function ${renderer}(`)) throw new Error(`${id} renderer missing`)
}
for (const token of ["lottery-site-data-client.js", "site-config.js", "site-data-adapter.js", 'site-key="twsyw"', "managed-site-links.js", "loadDraw({lotteryType:type})", "loadPredictions({lotteryType:type,historyLimit:20})", "selectLottery"]) {
  if (!html.includes(token) && !adapter.includes(token)) throw new Error(`missing integration token: ${token}`)
}
if (!html.includes("data-site-domain") || !adapter.includes("data-site-domain")) {
  throw new Error("visible supplier domains must be bound to the immutable site config")
}
if (!html.includes("data-prediction-draw-issue") || !adapter.includes("renderTopXiaoCode")) {
  throw new Error("top composite draw headers must be mapped to same-origin prediction rows")
}
for (const forbidden of ["document.createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "lottery-site-runtime.js"]) {
  if (adapter.includes(forbidden)) throw new Error(`existing-DOM adapter must not use ${forbidden}`)
}
const attributeImages = [
  "/uploads/image/20250322/1742580086567063.png",
  "/uploads/image/20250322/1742580119746508.jpg",
  "/uploads/image/20250322/1742580130762983.jpg",
]
if ((html.match(/id="legacy-attribute-anchor"/g) || []).length !== 1 || (html.match(/id="legacy-attribute-gallery"/g) || []).length !== 1) {
  throw new Error("twsyw must contain exactly one unified attribute image module")
}
const gallery = html.match(/<div id="legacy-attribute-gallery">([\s\S]*?)<\/div>/)?.[1] || ""
for (const image of attributeImages) {
  if (!gallery.includes(`src="${image}"`) || !gallery.includes('loading="lazy"') || !gallery.includes('decoding="async"')) throw new Error(`missing managed attribute image ${image}`)
}
if (html.indexOf('id="legacy-attribute-anchor"') < html.indexOf('id="composite_kill"') || html.indexOf('id="legacy-attribute-anchor"') > html.indexOf('class="foot-yuming"')) {
  throw new Error("attribute image module must follow the final prediction section and precede the vendor footer")
}
for (const [moduleKey, modeId, legacyImage] of [["pmtj_image", 476, "Winer911_1003_213_1623.jpg"], ["brainteaser", 475, "Winer911_1007_213_1249.jpg"]]) {
  if (!html.includes(`data-prediction-image="${moduleKey}"`)) throw new Error(`${moduleKey} image slot is missing`)
  if (html.includes(legacyImage)) throw new Error(`${moduleKey} must not retain the supplier image`)
  if (!adapter.includes(`renderPredictionImage("${moduleKey}"`)) throw new Error(`${moduleKey} image renderer is missing`)
  if (!manifest.includes(`"${moduleKey}"`)) throw new Error(`${moduleKey} manifest mapping is missing`)
  if (!dependencies.includes(`("${moduleKey}", ${modeId})`)) throw new Error(`${moduleKey} mode mapping is missing`)
}
if (!html.includes('id="legacy-attribute-anchor" style="max-width:800px')) {
  throw new Error("attribute module must retain the vendor page maximum width")
}
if (!html.includes('<div class="white-box" style="max-width:800px;margin-left:auto;margin-right:auto;box-sizing:border-box;"><managed-site-links site-key="twsyw"></managed-site-links></div>')) {
  throw new Error("managed site links must retain the vendor page maximum width")
}
for (const token of ['data-lottery-type="3"', 'data-lottery-type="2"', 'data-lottery-type="1"', 'data-current-issue', "postMessage", 'siteKey: "twsyw"']) {
  if (!draw.includes(token)) throw new Error(`draw tab contract is missing ${token}`)
}
// kai.html 保留为兼容直链/旧页面的独立副本，其面板高度必须与共享面板一致（移动端不被裁切）。
if (!draw.includes("height:200px!important") || draw.includes("height:155px")) {
  throw new Error("draw frame must preserve the shared panel's full 200px height on mobile")
}
if (!html.includes("height:200px!important")) {
  throw new Error("inlined draw tabs must keep the shared panel's 200px mobile height")
}
console.log("twsyw adapter contract passed")
