import fs from "node:fs"
import path from "node:path"

const args = process.argv.slice(2)
const valueFor = (name) => args[args.indexOf(name) + 1] || ""
const siteKey = valueFor("--site-key")
if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(siteKey)) {
  console.error("Usage: pnpm site:scaffold --site-key <lowercase-kebab-case>")
  process.exit(1)
}
const manifestPath = path.resolve("frontend/sites", siteKey, "site.manifest.ts")
const vendorPath = path.resolve("frontend/public/vendor", siteKey)
if (fs.existsSync(manifestPath)) {
  console.error(`Manifest already exists: ${manifestPath}`)
  process.exit(1)
}
fs.mkdirSync(path.dirname(manifestPath), { recursive: true })
fs.mkdirSync(vendorPath, { recursive: true })
fs.writeFileSync(manifestPath, `import { defineVendorSiteManifest } from "@/lib/site-platform/site-manifest"\n\nexport default defineVendorSiteManifest({\n  identity: { siteKey: "${siteKey}", domains: ["example.com"], routePath: "/${siteKey}", siteId: 1, webId: 1, defaultLotteryType: 3 },\n  frontend: { renderMode: "iframe-vendor", vendorIndexPath: "/vendor/${siteKey}/index.html", legacyPublicBasePath: "/vendor/${siteKey}", defaultGame: "taiwan", forumTitle: "New Vendor Site" },\n  bridge: { api: { httpApiBase: "", kaijiangApiBase: "/api/kaijiang" }, autoLoad: { draw: false, prediction: false }, predictionModuleKeys: [] },\n  brand: { siteName: "New Vendor Site", navigation: [], footer: { copyright: "" } },\n  security: { externalScriptOrigins: [], externalNavigationOrigins: [] },\n})\n`, "utf8")
console.log(`Created ${manifestPath}`)
console.log(`Place supplied files under ${vendorPath}`)
