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

for (const file of files) {
  const source = fs.readFileSync(file, "utf8")
  if (/https?:\/\//i.test(source)) throw new Error(`external origin remains in ${file}`)
  if (/eval\s*\(|atob\s*\(/i.test(source)) throw new Error(`dynamic supplier script remains in ${file}`)
  for (const sentinel of ["Zz_hdx.cp567.cc", "xg16888.com", "xg8388.com", "014902.com", "黄大仙"]) {
    if (source.includes(sentinel)) throw new Error(`legacy sentinel ${sentinel} remains in ${file}`)
  }
}

if (!index.includes("class=\"nav clearfix\"")) throw new Error("vendor navigation sentinel missing")
if (!index.includes("src=\"kai.html\"")) throw new Error("draw iframe sentinel missing")
if (!index.includes("class=\"foot-img\"")) throw new Error("vendor footer sentinel missing")
console.log(`twjsz666 static contract passed (${files.length} files)`)
