import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { VendorSitePage } from "@/components/site-platform/VendorSitePage"
import { getVendorSiteManifest } from "@/lib/site-platform/site-manifests"
import { buildSiteMetadata } from "@/lib/sites"

export async function generateMetadata({
  params,
}: {
  params: Promise<{ siteKey: string }>
}): Promise<Metadata> {
  const { siteKey } = await params
  return buildSiteMetadata(siteKey)
}

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
