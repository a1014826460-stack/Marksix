import fs from "node:fs"
import path from "node:path"

const root = "frontend/public/vendor/twjsz666"
const contentPages = Array.from({ length: 14 }, (_, index) => `${index + 154}.html`)
const pageNames = ["index.html", "kai.html", "sx.html", "wylhc.html", ...contentPages]
const actualPages = fs.readdirSync(root).filter((name) => name.endsWith(".html")).sort()

function fail(message) {
  throw new Error(message)
}

function source(name) {
  return fs.readFileSync(path.join(root, name), "utf8")
}

if (actualPages.length !== pageNames.length || pageNames.some((name) => !actualPages.includes(name))) {
  fail(`expected the complete 18-page inventory, got: ${actualPages.join(", ")}`)
}

for (const name of pageNames) {
  const html = source(name)
  const configPosition = html.indexOf('src="site-config.js"')
  const adapterPosition = html.indexOf('src="subpage-data-adapter.js"')
  const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1].replace(/\s+/g, " ").trim() || ""

  if (!/<body\b[^>]*\bdata-site-key="twjsz666"/i.test(html)) fail(`${name}: missing site marker`)
  if (!/<body\b[^>]*\bdata-page-title="[^"]*"/i.test(html)) fail(`${name}: missing page title contract`)
  if (!title.startsWith("台湾金手指")) fail(`${name}: title is not branded: ${title}`)
  if (!/<meta\s+name="keywords"\s+content="台湾金手指,www\.twjsz666\.com/i.test(html)) fail(`${name}: keywords are not site-owned`)
  if (!/<meta\s+name="description"\s+content="台湾金手指[^\"]*www\.twjsz666\.com"/i.test(html)) fail(`${name}: description is not site-owned`)
  if (configPosition < 0 || adapterPosition < configPosition) fail(`${name}: site config/subpage adapter order is invalid`)
  if (/data-cf-beacon|crossorigin="anonymous"|integrity="sha512-/i.test(html)) fail(`${name}: supplier tracking attributes remain`)
  if (/v4513226cdae34746b4dedf0b4dfa099e1781791509496\.js/i.test(html)) fail(`${name}: supplier tracking script remains`)
  if (/无标题文档|澳彩六合彩|2023台湾正版资料|\/baomaqg\//i.test(html)) fail(`${name}: legacy metadata or route remains`)

  for (const match of html.matchAll(/\b(?:href|src)=(['"])(.*?)\1/gi)) {
    const url = match[2].trim()
    if (!url || url.includes("${") || url.startsWith("#")) continue
    if (/^(?:https?:)?\/\//i.test(url) || /^(?:javascript|data):/i.test(url)) fail(`${name}: unsafe URL ${url}`)
    if (url.startsWith("/")) {
      const allowed = ["/favicon.ico", "/twjsz666", "/vendor/twjsz666/", "/vendor/_shared/", "/uploads/"]
      if (!allowed.some((prefix) => url === prefix || url.startsWith(prefix))) fail(`${name}: route escapes the site boundary: ${url}`)
      continue
    }
    const target = url.split(/[?#]/, 1)[0]
    if (target && !fs.existsSync(path.resolve(root, target))) fail(`${name}: local URL does not resolve: ${url}`)
  }
}

const index = source("index.html")
if (!index.includes('class="nav clearfix"') || !index.includes('href="wylhc.html"')) fail("index: navigation contract missing")
if (!index.includes('class="foot-img"') || !index.includes('src="kai.html"')) fail("index: footer/draw iframe contract missing")

const kai = source("kai.html")
for (const lotteryType of ["3", "2", "1"]) {
  if (!kai.includes(`data-lottery-type="${lotteryType}"`)) fail(`kai: missing lottery type ${lotteryType}`)
}
if ((kai.match(/\/vendor\/twjsz666\/wylhc\.html/g) || []).length !== 3) fail("kai: draw tabs must use site-owned record URLs")

const sx = source("sx.html")
for (const image of ["long", "tu", "hu", "niu", "shu", "zhu", "gou", "ji", "hou", "yang", "ma", "she"]) {
  if (!sx.includes(`src="static/picture/${image}.gif"`)) fail(`sx: missing ${image}.gif`)
}

const records = source("wylhc.html")
if (!records.includes('id="saveAoMenRecordcontainer"')) fail("wylhc: record container missing")
if (!records.includes('href="index.html"')) fail("wylhc: return-home navigation missing")

for (const name of contentPages) {
  const html = source(name)
  if (!html.includes('href="index.html"')) fail(`${name}: return-home navigation missing`)
  if (!html.includes('class="post-list"')) fail(`${name}: content container missing`)
  if (!html.includes('src="sx.html"')) fail(`${name}: zodiac iframe missing`)
  if (!html.includes('class="foot-img"')) fail(`${name}: footer missing`)
}

const adapterPath = path.join(root, "subpage-data-adapter.js")
if (!fs.existsSync(adapterPath)) fail("missing subpage-data-adapter.js")
const adapter = fs.readFileSync(adapterPath, "utf8")
for (const required of ["Twjsz666SiteConfig", "data-page-title", "siteName", "siteDomain", "DOMContentLoaded", "LotterySiteDataClient", "loadPredictions", "ARTICLE_MODULE_KEYS", "renderArticleRows"]) {
  if (!adapter.includes(required)) fail(`subpage adapter missing ${required}`)
}
if (/createElement|appendChild|insertBefore|replaceChild|\.innerHTML\s*=/i.test(adapter)) {
  fail("subpage adapter must not create, move, or replace DOM nodes")
}

for (const name of contentPages) {
  const html = source(name)
  if (!html.includes('data-prediction-article="true"')) fail(`${name}: prediction article is not marked for API rendering`)
  if (!html.includes('data-prediction-module="')) fail(`${name}: prediction module is not declared`)
  if (/20(?:24|25)\d{3}期/.test(html)) fail(`${name}: supplier prediction snapshot remains`)
}

console.log(`twjsz666 subpage contract passed (${pageNames.length} pages)`)
