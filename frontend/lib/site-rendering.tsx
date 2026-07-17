import type { ReactNode } from "react"

import type { FrontendSiteConfig } from "@/lib/sites"

type RenderModeSlots = {
  legacyShell: ReactNode
  iframeVendor: ReactNode
  reactHome: ReactNode
}

export function renderSiteByMode(site: FrontendSiteConfig, slots: RenderModeSlots): ReactNode {
  if (site.renderMode === "legacy-shell") return slots.legacyShell
  if (site.renderMode === "iframe-vendor") return slots.iframeVendor
  return slots.reactHome
}
