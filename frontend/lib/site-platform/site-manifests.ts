import { VENDOR_SITE_MANIFESTS } from "@/sites/site-manifests.generated"

export { VENDOR_SITE_MANIFESTS }

export function getVendorSiteManifest(siteKey: string) {
  return VENDOR_SITE_MANIFESTS.find((manifest) => manifest.identity.siteKey === siteKey) || null
}
