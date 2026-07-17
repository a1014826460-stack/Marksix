"use client"

import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import { getSiteConfig } from "@/lib/sites"

export default function TwsaimahuiPage() {
  const site = getSiteConfig("twsaimahui")
  return (
    <>
      <SiteTrafficTracker siteKey="twsaimahui" eventType="vendor_page_view" path="/twsaimahui" />
      <iframe
        src={site?.vendorIndexPath || "/vendor/twsaimahui/index.html"}
        title={site?.metadataTitle || site?.forumTitle || site?.siteKey || "twsaimahui"}
        style={{
          display: "block",
          width: "100%",
          minHeight: "100dvh",
          height: "100dvh",
          border: 0,
          background: "#fff",
        }}
      />
    </>
  )
}
