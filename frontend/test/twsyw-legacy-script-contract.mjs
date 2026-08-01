import fs from "node:fs"
const root = "frontend/public/vendor/twsyw"
for (const file of ["index.html", "kai.html"]) {
  const html = fs.readFileSync(`${root}/${file}`, "utf8")
  if (/\bintegrity=/.test(html) || html.includes("data-cf-beacon")) throw new Error(`${file} retains unavailable SRI/beacon code`)
}
const draw = fs.readFileSync(`${root}/kai.html`, "utf8")
if (!draw.includes("/vendor/shengshi8800/kj/local.html?lottery_type=3") || draw.includes('data[" url"]')) throw new Error("draw must use the local panel with valid option keys")
console.log("twsyw legacy script contract passed")
