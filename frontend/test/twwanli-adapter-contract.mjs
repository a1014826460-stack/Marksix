import fs from "node:fs"

const html = fs.readFileSync("frontend/public/vendor/twwanli/index.html", "utf8")
const draw = fs.readFileSync("frontend/public/vendor/twwanli/kai.html", "utf8")
const localDraw = fs.readFileSync("frontend/public/vendor/shengshi8800/kj/local.html", "utf8")
const config = fs.readFileSync("frontend/public/vendor/twwanli/site-config.js", "utf8")
const adapter = fs.readFileSync("frontend/public/vendor/twwanli/site-data-adapter.js", "utf8")
const featuredPostAdapter = fs.readFileSync("frontend/public/vendor/twwanli/featured-post-data-adapter.js", "utf8")

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

const FEATURED_POSTS_SECTION = "jhtz"

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

const featuredSection = predictionSection(FEATURED_POSTS_SECTION)
if (!featuredSection) throw new Error("missing featured posts prediction section: jhtz")
const featuredRows = [...featuredSection.matchAll(/<a\b[\s\S]*?<\/a>/g)]
if (featuredRows.length !== 6) throw new Error(`featured posts must retain six supplier rows, got ${featuredRows.length}`)
for (const [index, [row]] of featuredRows.entries()) {
  const slotCounts = {
    issue: (row.match(/data-prediction-issue/g) || []).length,
    content: (row.match(/data-prediction-content(?!-secondary)/g) || []).length,
    result: (row.match(/data-prediction-result/g) || []).length,
  }
  if (slotCounts.issue !== 1 || slotCounts.content !== 1 || slotCounts.result !== 1) {
    throw new Error(`jhtz row ${index + 1} slots must be exactly issue/content/result: ${JSON.stringify(slotCounts)}`)
  }
}
for (const sentinel of ["181期", "180期", "renderFeaturedPosts", "modules.pt1wei", "modules.sitouzhongte", "modules.title_14"]) {
  if (sentinel === "181期" || sentinel === "180期") {
    if (html.includes(sentinel)) throw new Error(`featured posts must not retain static issue sentinel ${sentinel}`)
  } else if (!adapter.includes(sentinel)) {
    throw new Error(`featured posts adapter is missing ${sentinel}`)
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
  "renderBuyWhatOpens",
  "domestic_wild_category",
  "renderSumBigSmall",
  "renderSumOddEven",
  "renderMusicChess",
  "qinqi_reference",
  "rawValue(source, \"xiao_1\")",
  "rawValue(source, \"xiao_2\")",
]) {
  if (!adapter.includes(token)) throw new Error(`adapter is missing ${token}`)
}

// 白名单说明（2026-09-29）：`writeRow()` 的 `contentHtml` 通道需要把「一行多个候选项、
// 只有一个命中」的内容写成带 `data-prediction-hit` 的内联标记，因此 `innerHTML` 是
// 该展示机制的既有实现（HEAD 起就在，见 `writeRow`），不是新增的 DOM 破坏。
// 其余 DOM 构造/替换操作仍禁止：适配器只写既有文本叶节点。
for (const forbidden of ["document.createElement", "appendChild", "replaceChildren", "document.write", "lottery-site-runtime.js"]) {
  if (adapter.includes(forbidden)) throw new Error(`existing-DOM adapter must not use ${forbidden}`)
}

if (!draw.includes("that.index(el, \"LI\")")) throw new Error("draw tab index must ignore whitespace text nodes")
if (!draw.includes('height:190px!important') || draw.includes('height:155px')) {
  throw new Error("draw frame must preserve the shared panel's full 190px height on mobile")
}

for (const sectionId of ["jz5x", "dssx", "sdzt", "qqsh"]) {
  if (!html.includes(`id="${sectionId}"`)) throw new Error(`missing ${sectionId} contract anchor`)
}
// 居中规则 2026-09-29 起从「逐模块列举（#sdzt/#tdsx/#pt1xiao/#qqsh）」升级为共享样式块里的
// 全局 `[data-prediction-*] { text-align:center }`（覆盖面更大：所有模块的三段槽位）。
// 断言随之改为校验「槽位存在 + 全局居中规则」，语义不变。
for (const slot of ["data-prediction-issue", "data-prediction-content", "data-prediction-result"]) {
  if (!html.includes(`[${slot}]`)) throw new Error(`prediction leaves lost their ${slot} slot`)
}
if (!/\[data-prediction-issue\][^}]*text-align:\s*center/.test(html)) {
  throw new Error("prediction leaves must be centered by the shared style block")
}

for (const token of ['data-lottery-type="3"', 'data-lottery-type="2"', 'data-lottery-type="1"', "postMessage", 'siteKey: "twwanli"']) {
  if (!draw.includes(token)) throw new Error(`draw tab contract is missing ${token}`)
}
if (!localDraw.includes('id="currentIssue"')) throw new Error("shared local draw panel is missing its current issue slot")

const FEATURED_POST_PAGES = {
  "21.html": { moduleKey: "pt1wei", rows: 6 },
  "22.html": { moduleKey: "pt1xiao", rows: 6 },
  "25.html": { moduleKey: "pt1wei", rows: 7 },
  "26.html": { moduleKey: "pt1xiao", rows: 7 },
  "27.html": { moduleKey: "title_14", rows: 7 },
  "28.html": { moduleKey: "sitouzhongte", rows: 7 },
}
const FEATURED_SCRIPT_SRI = "sha512-JRtS+0PLnTvcdvspgnTlqoQmRKYc1BDmytkGpy3gzejYB2m0D8Q9PVAi0rAR+mkfxIgceSlvZ5dLyLY9ATFqqw=="

for (const [filename, contract] of Object.entries(FEATURED_POST_PAGES)) {
  const article = fs.readFileSync(`frontend/public/vendor/twwanli/${filename}`, "utf8")
  for (const token of [
    'data-prediction-article="true"',
    `data-prediction-module="${contract.moduleKey}"`,
    "/vendor/_shared/lottery-site-data-client.js",
    "site-config.js",
    "featured-post-data-adapter.js",
    `integrity="${FEATURED_SCRIPT_SRI}"`,
    "/vendor/twwanli/static/picture/18d310a363f7a6a0d82a09afd2953d21.jpg",
    "台湾万利网",
  ]) {
    if (!article.includes(token)) throw new Error(`${filename} is missing ${token}`)
  }
  const articleRows = [...article.matchAll(/<p\b[^>]*data-prediction-row[^>]*>[\s\S]*?<\/p>/g)]
  if (articleRows.length !== contract.rows) throw new Error(`${filename} must retain ${contract.rows} dynamic article rows`)
  for (const [index, [row]] of articleRows.entries()) {
    for (const slot of ["issue", "content", "result"]) {
      const count = (row.match(new RegExp(`data-prediction-${slot}`, "g")) || []).length
      if (count !== 1) throw new Error(`${filename} row ${index + 1} must have one ${slot} slot`)
    }
  }
  if (/2025\d+期|\?{4,}/.test(article)) throw new Error(`${filename} retains a supplier prediction snapshot`)
  if (article.includes("新港六合彩") || article.includes("www.hy-inserve.com")) throw new Error(`${filename} retains legacy site identity`)
}

for (const token of ["lotteryTypeFromUrl", "historyLimit: 8", "renderArticle", "resultText", "data-prediction-module"]) {
  if (!featuredPostAdapter.includes(token)) throw new Error(`featured post adapter is missing ${token}`)
}
for (const forbidden of ["document.createElement", "appendChild", "replaceChildren", "innerHTML", "document.write"]) {
  if (featuredPostAdapter.includes(forbidden)) throw new Error(`featured post adapter must not use ${forbidden}`)
}

console.log("twwanli adapter contract passed")
