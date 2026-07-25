import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import { TwjinniuHomeClient } from "@/components/twjinniu/TwjinniuHomeClient"
import { SiteDataReadySignal } from "@/components/site-platform/SiteDataReadySignal"

export default function TwjinniuPage() {
  return (
    <>
      <SiteTrafficTracker siteKey="twjinniu" eventType="site_page_view" path="/twjinniu" />
      <SiteDataReadySignal siteKey="twjinniu" />
      <TwjinniuHomeClient />
    </>
  )
}
