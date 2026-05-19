"use client"

import { getSiteConfig } from "@/lib/sites"

export default function TwsaimahuiPage() {
  const site = getSiteConfig("twsaimahui")
  return (
    <iframe
      src={site?.vendorIndexPath || "/vendor/twsaimahui/index.html"}
      title={site?.siteKey || "twsaimahui"}
      style={{
        display: "block",
        width: "100%",
        minHeight: "100dvh",
        height: "100dvh",
        border: 0,
        background: "#fff",
      }}
    />
  )
}
