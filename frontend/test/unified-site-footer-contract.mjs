import fs from "node:fs"

const images = [
  "/uploads/image/20250322/1742580086567063.png",
  "/uploads/image/20250322/1742580119746508.jpg",
  "/uploads/image/20250322/1742580130762983.jpg",
]

const staticSites = [
  ["shengshi8800", "frontend/public/vendor/shengshi8800/index.html", "盛世台湾六合彩", "tw8800.com", 720],
  ["twcf888", "frontend/public/vendor/twcf888.com/index.html", "台湾创富网", "twcf888.com", 800],
  ["twjinniu", "frontend/public/vendor/twjinniu/index.html", "台湾通天网", "twtongtian.com", 800],
  ["twsaimahui", "frontend/public/vendor/twsaimahui/index.html", "台湾赛马会", "twsaimahui.com", 720],
  ["twssz", "frontend/public/vendor/twssz/index.html", "台湾神算子", "twssz.com", 800],
  ["twbst528", "frontend/public/vendor/twbst528/index.html", "台湾百事通", "www.twbst528.com", 768],
]

function assertUnifiedFooter(siteKey, source, siteName, siteDomain, maxWidth) {
  const wrapperMarkup = `<div class="legacy-site-footer" style="width:100%;max-width:${maxWidth}px;margin:0 auto;box-sizing:border-box;">`
  if ((source.match(/class=["']legacy-site-footer["']/g) || []).length !== 1 || !source.includes(wrapperMarkup)) {
    throw new Error(`${siteKey} footer must be constrained to the ${maxWidth}px site width`)
  }
  if ((source.match(/id=["']legacy-attribute-anchor["']/g) || []).length !== 1) {
    throw new Error(`${siteKey} must contain exactly one attribute footer`)
  }
  const footerStart = source.indexOf('id="legacy-attribute-anchor"')
  const footer = source.slice(footerStart)
  let previousImageIndex = -1
  for (const image of images) {
    const imageMarkup = `<img src="${image}" width="100%" loading="lazy" decoding="async">`
    const imageIndex = footer.indexOf(imageMarkup)
    if (imageIndex < 0) {
      throw new Error(`${siteKey} missing compliant footer image ${image}`)
    }
    if (imageIndex <= previousImageIndex) throw new Error(`${siteKey} footer images are out of order`)
    previousImageIndex = imageIndex
  }
  for (const text of ["属性知识", "说明：本论坛所提供的内容", "论坛免责声明", "返回顶部", `【${siteName}】域名：${siteDomain}`, `盡在${siteName}`]) {
    if (!footer.includes(text)) throw new Error(`${siteKey} footer missing ${text}`)
  }
  for (const prohibited of ["galleryEl.innerHTML", "galleryHtml ="] ) {
    if (footer.includes(prohibited)) throw new Error(`${siteKey} footer must not use ${prohibited}`)
  }
  for (const image of images) {
    if (footer.includes(`httpApi + '${image}`) || footer.includes(`httpApi +'${image}`)) {
      throw new Error(`${siteKey} footer image must not depend on httpApi: ${image}`)
    }
  }
}

for (const [siteKey, file, siteName, siteDomain, maxWidth] of staticSites) {
  assertUnifiedFooter(siteKey, fs.readFileSync(file, "utf8"), siteName, siteDomain, maxWidth)
}

const caibawang = fs.readFileSync("frontend/components/twcaibawang/TwcaibawangHomeClient.tsx", "utf8")
for (const token of [
  "function renderUnifiedSiteFooter",
  '<div class="legacy-site-footer" style="width:100%;max-width:800px;margin:0 auto;box-sizing:border-box;">',
  "siteName",
  "siteDomain",
  ...images,
  'loading="lazy"',
  'decoding="async"',
  "论坛免责声明",
  "返回顶部",
]) {
  if (!caibawang.includes(token)) throw new Error(`twcaibawang footer missing ${token}`)
}
