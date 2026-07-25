import { getSiteAdapter } from "@/lib/site-platform/site-adapter-registry"

for (const siteKey of ["shengshi8800", "twsaimahui", "twcaibawang", "twjinniu", "twcf888"]) {
  const adapter = getSiteAdapter(siteKey)
  if (!adapter || adapter.mode !== "existing-dom-only") {
    throw new Error(`missing safe adapter: ${siteKey}`)
  }
  if (!adapter.draw || !adapter.predictions || !adapter.navigation || !adapter.footer) {
    throw new Error(`incomplete adapter: ${siteKey}`)
  }
}
