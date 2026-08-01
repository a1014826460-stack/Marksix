import fs from "node:fs"

const sites = fs.readFileSync("frontend/lib/sites.ts", "utf8")

for (const token of [
  'import twwanliManifest from "@/sites/twwanli/site.manifest"',
  "toFrontendSiteConfig(twwanliManifest)",
]) {
  if (!sites.includes(token)) throw new Error(`twwanli API registration is missing ${token}`)
}

console.log("twwanli site registration contract passed")
