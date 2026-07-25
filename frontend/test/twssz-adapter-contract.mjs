import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twssz/site-data-adapter.js", "utf8")

for (const token of ["createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "<style"]) {
  if (adapter.includes(token)) throw new Error(`adapter must not mutate UI: ${token}`)
}

for (const token of ["LotterySiteDataClient", "loadDraw", "loadPredictions", "site-data:ready", "textContent", ".dz_content08ab2d table", "DOMContentLoaded", "firstContentSibling", "IntersectionObserver", "requestIdleCallback", "historyLimit: 1", "historyLimit: 8", "message", "lottery-change", "activeLottery", "titleRegionPrefix"]) {
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

const html = fs.readFileSync("frontend/public/vendor/twssz/index.html", "utf8")
if (/https?:\/\//i.test(html)) {
  throw new Error("twssz vendor HTML must not retain external origins")
}
const imageTags = html.match(/<img\b[^>]*>/gi) || []
if (imageTags.length !== 192) throw new Error(`expected 192 vendor images, got ${imageTags.length}`)
if (imageTags.some((tag) => !/\bloading="lazy"/i.test(tag) || !/\bdecoding="async"/i.test(tag))) {
  throw new Error("every supplied vendor image must use native lazy loading without changing its source")
}

const drawHtml = fs.readFileSync("frontend/public/vendor/twssz/kai.html", "utf8")
if (/data-cf-beacon|v4513226cdae34746b4dedf0b4dfa099e1781791509496\.js/i.test(drawHtml)) {
  throw new Error("draw page must not retain the unavailable Cloudflare beacon script")
}
for (const label of ["台湾彩", "澳门彩", "香港彩"]) {
  if (!drawHtml.includes(label)) throw new Error(`draw tab missing ${label}`)
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
