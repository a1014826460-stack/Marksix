import fs from "node:fs"
import path from "node:path"

const sitesDir = path.resolve("frontend/sites")
const outputPath = path.join(sitesDir, "site-manifests.generated.ts")
const siteKeys = fs.readdirSync(sitesDir, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(sitesDir, entry.name, "site.manifest.ts")))
  .map((entry) => entry.name)
  .sort()
const identifier = (siteKey) => siteKey.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())
const imports = siteKeys.map((siteKey) => `import ${identifier(siteKey)} from "@/sites/${siteKey}/site.manifest"`)
const names = siteKeys.map(identifier)
fs.writeFileSync(outputPath, `${imports.join("\n")}\n\nexport const VENDOR_SITE_MANIFESTS = [${names.join(", ")}] as const\n`, "utf8")
console.log(`Synced ${siteKeys.length} vendor site manifest(s).`)
