import fs from "node:fs"
import path from "node:path"

const root = "frontend/public/vendor/twjsz666"
const files = []
function visit(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name)
    if (entry.isDirectory()) visit(file)
    else if (/\.(html|css|js)$/.test(entry.name)) files.push(file)
  }
}
visit(root)

const index = fs.readFileSync(path.join(root, "index.html"), "utf8")
if (!index.includes('data-site-key="twjsz666"')) throw new Error("missing twjsz666 marker")
const faviconPath = "/vendor/twjsz666/static/picture/favicon.ico"
if (!fs.existsSync(path.join(root, "static", "picture", "favicon.ico"))) {
  throw new Error("missing site favicon asset")
}
for (const file of fs.readdirSync(root).filter((entry) => entry.endsWith(".html"))) {
  const source = fs.readFileSync(path.join(root, file), "utf8")
  if (!new RegExp(`<link\\s+rel=["']icon["']\\s+type=["']image/x-icon["']\\s+href=["']${faviconPath}["']`, "i").test(source)) {
    throw new Error(`missing twjsz666 favicon link in ${file}`)
  }
}
for (const script of [
  'src="site-config.js"',
  'src="/vendor/_shared/lottery-site-data-client.js"',
  'src="site-data-adapter.js"',
]) if (!index.includes(script)) throw new Error(`missing required script ${script}`)

for (const token of [
  "three-head-four-tail-table",
  "one-sentence-table",
  ".three-head-four-tail-table th:nth-child(2) .zl",
  "font-size: 22px",
  "white-space: nowrap",
  ".one-sentence-table td > font",
  "display: block",
]) {
  if (!index.includes(token)) throw new Error(`missing prediction layout rule ${token}`)
}
if (!/【三头４尾】[\s\S]{0,300}<table[^>]*class="[^"]*three-head-four-tail-table/.test(index)) {
  throw new Error("three-head-four-tail layout class is not attached to its own table")
}
if (!/「一句话中特码」[\s\S]{0,300}<table[^>]*class="[^"]*one-sentence-table/.test(index)) {
  throw new Error("one-sentence layout class is not attached to its own table")
}

for (const file of files) {
  const source = fs.readFileSync(file, "utf8")
  if (source.includes("资料同步中")) throw new Error(`loading placeholder remains in ${file}`)
  if (/https?:\/\//i.test(source)) throw new Error(`external origin remains in ${file}`)
  if (/eval\s*\(|atob\s*\(/i.test(source)) throw new Error(`dynamic supplier script remains in ${file}`)
  for (const sentinel of ["Zz_hdx.cp567.cc", "xg16888.com", "xg8388.com", "014902.com", "黄大仙"]) {
    if (source.includes(sentinel)) throw new Error(`legacy sentinel ${sentinel} remains in ${file}`)
  }
}

if (!index.includes("class=\"nav clearfix\"")) throw new Error("vendor navigation sentinel missing")
if (!index.includes("src=\"kai.html\"")) throw new Error("draw iframe sentinel missing")
if (!index.includes("class=\"foot-img\"")) throw new Error("vendor footer sentinel missing")

const footerImages = [
  "/uploads/image/20250322/1742580086567063.png",
  "/uploads/image/20250322/1742580119746508.jpg",
  "/uploads/image/20250322/1742580130762983.jpg",
]
if ((index.match(/id=["']legacy-attribute-anchor["']/g) || []).length !== 1) {
  throw new Error("twjsz666 must contain exactly one unified attribute image module")
}
if ((index.match(/id=["']legacy-attribute-gallery["']/g) || []).length !== 1) {
  throw new Error("twjsz666 must contain exactly one unified attribute image gallery")
}
const footerStart = index.indexOf('id="legacy-attribute-anchor"')
const textFooterStart = index.indexOf('class="foot-img"')
if (footerStart < index.indexOf("最快开奖（旗下网站）") || footerStart > textFooterStart) {
  throw new Error("unified attribute image module must be in the terminal area before the text footer")
}
let previousImageIndex = -1
for (const image of footerImages) {
  const imageMarkup = `<img src="${image}" width="100%" loading="lazy" decoding="async">`
  const imageIndex = index.indexOf(imageMarkup, footerStart)
  if (imageIndex < 0) throw new Error(`missing compliant footer image ${image}`)
  if (imageIndex <= previousImageIndex) throw new Error("unified footer images are out of order")
  previousImageIndex = imageIndex
}
console.log(`twjsz666 static contract passed (${files.length} files)`)
