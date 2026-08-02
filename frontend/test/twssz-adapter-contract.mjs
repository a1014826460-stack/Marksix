import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twssz/site-data-adapter.js", "utf8")
const dependencies = fs.readFileSync("backend/src/domains/prediction/site_page_dependencies.py", "utf8")

for (const token of ["createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "<style"]) {
  if (adapter.includes(token)) throw new Error(`adapter must not mutate UI: ${token}`)
}

for (const token of ["LotterySiteDataClient", "loadDraw", "loadPredictions", "site-data:ready", "textContent", ".dz_content08ab2d table", "DOMContentLoaded", "requestIdleCallback", "historyLimit: 1", "TWSSZ_HISTORY_LIMIT = 16", "historyLimit: TWSSZ_HISTORY_LIMIT", "message", "lottery-change", "activeLottery", "titleRegionPrefix", "function resultCode", "setAttribute(\"bgcolor\", \"#FFFF00\")"]) {
  if (!adapter.includes(token)) throw new Error(`twssz adapter missing ${token}`)
}

if (!adapter.includes("event.source !== drawFrame.contentWindow")) {
  throw new Error("twssz must accept lottery changes only from its draw iframe")
}
if (!adapter.includes("lotteryType: lottery.lotteryType")) {
  throw new Error("twssz prediction requests must use the selected draw lottery")
}

if (!adapter.includes('tailLabel.textContent = "⑤码"')) {
  throw new Error("twssz adapter must preserve the original five-number label")
}

for (const token of ["renderGradeHistory", "renderLinkedGroups", "renderMa24Grid", "renderFifteenCodeHistory", "renderAiForumHistory", "renderJiaYeErXiaoHistory", "renderTeLiaoHistory", "renderDanShuangHistory", "renderCompositeKillHistory", "renderDaxiaoHistory", "renderEightXiaoHistory", "renderFiveNotHistory", "renderThreeXiaoHistory", "renderDoubleWaveHistory", "renderOneHeadHistory", "renderAaaGradeHistory", "data-site-slot", "tr.zt24mtr", ".bbzhong122", "title_66"]) {
  if (!adapter.includes(token)) throw new Error(`twssz adapter missing DOM-slot renderer contract: ${token}`)
}
if (adapter.includes('sixiao_sima", title: "精准四肖", target: function () { return targetAfter("top_13"')) {
  throw new Error("15码中特 card must not use a fragile top_13 sibling-offset mapping")
}
for (const prohibited of ["rotateNumbers", "style.backgroundColor"]) {
  if (adapter.includes(prohibited)) throw new Error(`twssz complex prediction modules must not use fabricated or generic rendering: ${prohibited}`)
}
for (const required of [
  '{ key: "pt2xiao", title: "家野二肖", renderer: renderJiaYeErXiaoHistory }',
  '{ key: "juesha1wei", title: "精选特料专区", renderer: renderTeLiaoHistory }',
  '{ key: "danshuangtema", title: "单双中特", renderer: renderDanShuangHistory }'
]) {
  if (!adapter.includes(required)) throw new Error(`twssz module must use its dedicated renderer: ${required}`)
}
for (const required of [
  "renderSxztuImage",
  'renderSxztuImage(modules.sxztu)',
  "data-prediction-image='sxztu'",
  "loadHistoricalPredictions(lottery)",
  "fourZodiacHistoryTarget",
  'waveSlots.length !== 2',
  'label + ":" + values.slice(0, 10).join(".")',
]) {
  if (!adapter.includes(required)) throw new Error(`twssz missing regression contract: ${required}`)
}
if (adapter.includes('target: function () { return targetAfter("top_8", 2, 2); }')) {
  throw new Error("精准四肖 must not rely on the ambiguous duplicate #top_8 sibling offset")
}
for (const prohibited of ["rowDisplay", "replaceRowText", "replaceLeafText", "renderStandardSection"]) {
  if (adapter.includes(prohibited)) throw new Error(`twssz must not use whole-row renderer: ${prohibited}`)
}
if (/COMPLETE_SECTION_MAPPINGS[\s\S]*?(?:\{[^}]*\})/.test(adapter) && !adapter.includes("renderer:")) {
  throw new Error("every twssz mapping requires an explicit renderer")
}

const html = fs.readFileSync("frontend/public/vendor/twssz/index.html", "utf8")
if (!html.includes("<title>台湾神算子，算无遗漏</title>")) {
  throw new Error("twssz vendor page must expose the configured browser title")
}
if (!html.includes('rel="icon" href="static/file/favicon.ico"')) {
  throw new Error("twssz vendor page must use its supplied favicon")
}
if (!html.includes('<link rel="shortcut icon" href="static/file/favicon.ico" type="image/x-icon">')) {
  throw new Error("twssz vendor page must expose the supplied favicon to legacy browsers")
}
for (const staticIssue of ["204期", "203期", "202期", "201期", "200期", "199期", "198期", "197期"]) {
  if (html.includes(staticIssue)) throw new Error(`twssz source must not retain static prediction text: ${staticIssue}`)
}
for (const staticPlaceholder of ["待加载期", "暂无后端资料", "精选24码;准确率绝对100%;大胆下注!"]) {
  if (html.includes(staticPlaceholder)) {
    throw new Error(`twssz source must not retain static prediction placeholder: ${staticPlaceholder}`)
  }
}
if ((html.match(/class="bbzhong122"/g) || []).length !== 8) {
  throw new Error("15码中特 must retain its eight supplied card containers")
}
if ((html.match(/class="zt24mtr"/g) || []).length !== 16) {
  throw new Error("精选24码 must retain eight fixed two-row number grids")
}
for (const staticPrediction of [
  "执笔先生（gat566.cc）15码中特",
  "204期必中三尾",
  "204期必中五尾",
  "14</font>.<font>24",
  "单车变宝马",
]) {
  if (html.includes(staticPrediction)) {
    throw new Error(`twssz source must not retain static 15码 prediction data: ${staticPrediction}`)
  }
}
if (/https?:\/\//i.test(html)) {
  throw new Error("twssz vendor HTML must not retain external origins")
}
const imageTags = html.match(/<img\b[^>]*>/gi) || []
if (imageTags.length !== 194) throw new Error(`expected 194 vendor images including the shared attribute module, got ${imageTags.length}`)
if (imageTags.some((tag) => !/\bloading="lazy"/i.test(tag) || !/\bdecoding="async"/i.test(tag))) {
  throw new Error("every supplied vendor image must use native lazy loading without changing its source")
}
if (!html.includes('<managed-site-links site-key="twssz" style="display:block;width:100%;max-width:800px;margin:0 auto;box-sizing:border-box;"></managed-site-links>')) {
  throw new Error("twssz links must be constrained to the supplied 800px page shell")
}
if (!html.includes('data-prediction-image="sxztu"')) {
  throw new Error("狗头传密 must expose its existing image as the sxztu prediction slot")
}

const drawHtml = fs.readFileSync("frontend/public/vendor/twssz/kai.html", "utf8")
if (/data-cf-beacon|v4513226cdae34746b4dedf0b4dfa099e1781791509496\.js/i.test(drawHtml)) {
  throw new Error("draw page must not retain the unavailable Cloudflare beacon script")
}
for (const label of ["台湾彩", "澳门彩", "香港彩"]) {
  if (!drawHtml.includes(label)) throw new Error(`draw tab missing ${label}`)
}
const attributeImages = [
  "/uploads/image/20250322/1742580086567063.png",
  "/uploads/image/20250322/1742580119746508.jpg",
  "/uploads/image/20250322/1742580130762983.jpg",
]
if (!html.includes('id="legacy-attribute-anchor"')) throw new Error("twssz must use the shared attribute image module")
for (const src of attributeImages) {
  if (!html.includes(`src="${src}"`)) throw new Error(`shared attribute image is missing: ${src}`)
}

for (const prohibitedLabel of ["澳洲六合彩", "新香港六合彩"]) {
  if (drawHtml.includes(prohibitedLabel)) throw new Error(`draw tab must not retain ${prohibitedLabel}`)
}
if ((drawHtml.match(/data-opt=/g) || []).length !== 3) {
  throw new Error("draw module must expose exactly three lottery tabs")
}
for (const [label, type] of [["台湾彩", "3"], ["澳门彩", "2"], ["香港彩", "1"]]) {
  const tabPattern = new RegExp(`lottery_type=${type}[^>]*>[\\s\\S]{0,80}${label}`)
  if (!tabPattern.test(drawHtml)) throw new Error(`${label} must use lottery_type=${type}`)
}

for (const token of [
  "title_5",
  "juesha1wei",
  "juesha1xiao",
  "juesha2xiao",
  "jueshabanbo",
  "tableAfterHeading",
  "compositeTable",
  "compositeLines",
]) {
  if (!adapter.includes(token)) throw new Error(`twssz adapter missing complete mapping contract: ${token}`)
}
if (!dependencies.includes('("狗头传密四不像中特图", 474)')) {
  throw new Error("twssz must authorize the exact sxztu image mode 474")
}

for (const token of [
  "siteConfig",
  "top_14",
  "top_9",
  "top_13",
  "top_11",
  "top_10",
  "top_6",
  "top_8",
  "top_4",
  "top_1",
  "top_2",
  "top_12",
  "titlePrefix",
  "siteDomain",
]) {
  if (!adapter.includes(token)) throw new Error(`twssz adapter missing mapped table contract: ${token}`)
}
