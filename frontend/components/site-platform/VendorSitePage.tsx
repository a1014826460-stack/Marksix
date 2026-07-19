"use client"

import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import type { VendorSiteManifest } from "@/lib/site-platform/site-manifest"

export function VendorSitePage({ manifest }: { manifest: VendorSiteManifest }) {
  const { identity, frontend } = manifest
  return (
    <>
      <SiteTrafficTracker
        siteKey={identity.siteKey}
        eventType="vendor_page_view"
        path={identity.routePath}
      />
      <iframe
        src={frontend.vendorIndexPath}
        title={frontend.metadataTitle || frontend.forumTitle || identity.siteKey}
        style={{
          display: "block",
          width: "100%",
          minHeight: "100dvh",
          height: "100dvh",
          border: 0,
          background: manifest.brand.theme?.background || "#fff",
        }}
      />
    </>
  )
}
