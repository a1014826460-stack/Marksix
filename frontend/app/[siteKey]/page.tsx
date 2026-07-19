import { notFound } from "next/navigation"

import { VendorSitePage } from "@/components/site-platform/VendorSitePage"
import { getVendorSiteManifest } from "@/lib/site-platform/site-manifests"

export default async function ManifestVendorSitePage({
  params,
}: {
  params: Promise<{ siteKey: string }>
}) {
  const { siteKey } = await params
  const manifest = getVendorSiteManifest(siteKey)
  if (!manifest || manifest.identity.routePath !== `/${siteKey}`) notFound()
  return <VendorSitePage manifest={manifest} />
}
