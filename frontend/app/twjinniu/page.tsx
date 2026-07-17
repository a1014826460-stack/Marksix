import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import { TwjinniuHomeClient } from "@/components/twjinniu/TwjinniuHomeClient"

export default function TwjinniuPage() {
  return (
    <>
      <SiteTrafficTracker siteKey="twjinniu" eventType="site_page_view" path="/twjinniu" />
      <TwjinniuHomeClient />
    </>
  )
}
