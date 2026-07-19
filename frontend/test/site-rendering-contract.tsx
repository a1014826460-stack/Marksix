import { createElement, type ReactNode } from "react"

import { VendorSitePage } from "@/components/site-platform/VendorSitePage"
import { renderSiteByMode } from "@/lib/site-rendering"
import { getRegisteredSite } from "@/lib/site-registry"
import twsaimahuiManifest from "@/sites/twsaimahui/site.manifest"

const rendered: ReactNode = renderSiteByMode(getRegisteredSite("twjinniu"), {
  legacyShell: null,
  iframeVendor: null,
  reactHome: null,
})
void rendered

const manifestPage = createElement(VendorSitePage, { manifest: twsaimahuiManifest })
if (manifestPage.props.manifest.frontend.vendorIndexPath !== "/vendor/twsaimahui/index.html") {
  throw new Error("manifest-backed vendor pages must preserve the configured vendor entry")
}
