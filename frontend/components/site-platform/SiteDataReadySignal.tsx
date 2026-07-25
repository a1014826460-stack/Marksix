"use client"

import { useEffect } from "react"

export function SiteDataReadySignal({ siteKey }: { siteKey: string }) {
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("site-data:ready", {
      detail: { siteKey, resource: "page-data", state: "ready" },
    }))
  }, [siteKey])

  return null
}
