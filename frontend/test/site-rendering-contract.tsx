import type { ReactNode } from "react"

import { renderSiteByMode } from "@/lib/site-rendering"
import { getRegisteredSite } from "@/lib/site-registry"

const rendered: ReactNode = renderSiteByMode(getRegisteredSite("twjinniu"), {
  legacyShell: null,
  iframeVendor: null,
  reactHome: null,
})

void rendered
