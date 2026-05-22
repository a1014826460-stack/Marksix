"use client"

import { getSiteConfig } from "@/lib/sites"

export default function TwcaibawangPage() {
  const site = getSiteConfig("twcaibawang")

  return (
    <iframe
      src={site?.vendorIndexPath || "/vendor/twcaibawang.com/index.html"}
      title={site?.siteKey || "twcaibawang"}
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
