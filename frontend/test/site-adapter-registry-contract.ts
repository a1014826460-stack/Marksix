import { getSiteAdapter } from "@/lib/site-platform/site-adapter-registry"

for (const siteKey of ["shengshi8800", "twsaimahui", "twcaibawang", "twjinniu", "twcf888", "twssz", "twbst528", "twjsz666", "twwanli", "twsyw"]) {
  const adapter = getSiteAdapter(siteKey)
  if (!adapter || adapter.mode !== "existing-dom-only") {
    throw new Error(`missing safe adapter: ${siteKey}`)
  }
  if (!adapter.draw || !adapter.predictions || !adapter.navigation || !adapter.footer) {
    throw new Error(`incomplete adapter: ${siteKey}`)
  }
  if (adapter.predictions.selectors.length === 0) {
    throw new Error(`missing existing prediction target: ${siteKey}`)
  }
}
