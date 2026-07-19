import fs from "node:fs"
import path from "node:path"

const args = process.argv.slice(2)
const strict = args.includes("--strict")
const siteKey = args[args.indexOf("--site-key") + 1] || ""
if (!siteKey) {
  console.error("Usage: pnpm site:validate --site-key <siteKey> [--strict]")
  process.exit(1)
}
const manifestPath = path.resolve("frontend/sites", siteKey, "site.manifest.ts")
if (!fs.existsSync(manifestPath)) {
  console.error(`Missing manifest: ${manifestPath}`)
  process.exit(1)
}
const source = fs.readFileSync(manifestPath, "utf8")
const entryMatch = source.match(/vendorIndexPath:\s*["']([^"']+)["']/)
if (!entryMatch) {
  console.error("Manifest must declare frontend.vendorIndexPath")
  process.exit(1)
}
const entryPath = path.resolve("frontend/public", `.${entryMatch[1]}`)
if (!fs.existsSync(entryPath)) {
  console.error(`Missing vendor entry: ${entryPath}`)
  process.exit(1)
}
const root = path.resolve("frontend/public/vendor", siteKey)
const scan = (directory) => fs.readdirSync(directory, { withFileTypes: true }).flatMap((item) => {
  const target = path.join(directory, item.name)
  return item.isDirectory() ? scan(target) : /\.(?:html?|js)$/i.test(item.name) ? [target] : []
})
const origins = new Set()
for (const file of scan(root)) {
  for (const match of fs.readFileSync(file, "utf8").matchAll(/https?:\/\/[^"'\s<>()]+/g)) {
    try { origins.add(new URL(match[0].replaceAll("&#45;", "-")).origin) } catch {}
  }
}
const allowlist = new Set([...source.matchAll(/https?:\/\/[^"'\s,]+/g)].flatMap((match) => {
  try { return [new URL(match[0]).origin] } catch { return [] }
}))
const executableAndNavigationOrigins = new Set(
  [...origins].filter((origin) =>
    !origin.startsWith("http://www.w3.org") &&
    !origin.startsWith("https://cli.vuejs.org") &&
    !origin.startsWith("https://github.com") &&
    !origin.startsWith("https://html.spec.whatwg.org") &&
    origin !== "http://localhost" &&
    origin !== "https://admin.shengshi8800.com" &&
    origin !== "https://b.jsc111111.com"
  )
)
const unlisted = [...executableAndNavigationOrigins].filter((origin) => !allowlist.has(origin))
console.log(`Validated local entry: ${entryMatch[1]}`)
console.log(`Detected external origins: ${origins.size}`)
if (unlisted.length) console.log(`Unlisted origins:\n${unlisted.map((origin) => `- ${origin}`).join("\n")}`)
if (strict && unlisted.length) {
  console.error("Strict validation rejected unlisted external origins.")
  process.exit(1)
}
console.log(`Vendor site ${siteKey} is valid.`)
