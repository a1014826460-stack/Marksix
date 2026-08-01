import fs from "node:fs"

const sites = fs.readFileSync("frontend/lib/sites.ts", "utf8")

for (const token of [
  'import twsywManifest from "@/sites/twsyw/site.manifest"',
  "toFrontendSiteConfig(twsywManifest)",
]) {
  if (!sites.includes(token)) throw new Error(`twsyw API registration is missing ${token}`)
}

console.log("twsyw site registration contract passed")
