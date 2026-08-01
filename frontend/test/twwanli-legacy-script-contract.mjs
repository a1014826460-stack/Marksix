import fs from "node:fs"

const root = "frontend/public/vendor/twwanli"
const index = fs.readFileSync(`${root}/index.html`, "utf8")
const draw = fs.readFileSync(`${root}/kai.html`, "utf8")

if (/<img\b[^>]+\bsrc=["']https?:\/\//i.test(index)) {
  throw new Error("vendor entry must not request unavailable remote image assets")
}

if (/<\/span>|<\/b>/.test(index.slice(index.indexOf("function CalConv"), index.indexOf("function www_helpor_net")))) {
  throw new Error("calendar script contains injected markup that prevents CalConv from loading")
}
if (draw.includes('data[" url"]')) throw new Error("draw frame must use the configured iframe URL key")
if (!draw.includes("'url':'/vendor/shengshi8800/kj/local.html?lottery_type=3")) throw new Error("draw frame must use the local draw panel")

for (const file of ["index.html", "kai.html", "sx.html"]) {
  const html = fs.readFileSync(`${root}/${file}`, "utf8")
  if (/\bintegrity=/.test(html)) throw new Error(`${file} retains a mismatched local script integrity value`)
  if (html.includes("data-cf-beacon")) throw new Error(`${file} retains the unavailable Cloudflare beacon script`)
}

console.log("twwanli legacy script contract passed")
