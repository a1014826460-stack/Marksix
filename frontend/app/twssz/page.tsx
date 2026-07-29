import { notFound } from "next/navigation"

import { VendorSitePage } from "@/components/site-platform/VendorSitePage"
import { getVendorSiteManifest } from "@/lib/site-platform/site-manifests"

export default function TwsszPage() {
  const manifest = getVendorSiteManifest("twssz")
  if (!manifest) notFound()
  return <VendorSitePage manifest={manifest} />
}
