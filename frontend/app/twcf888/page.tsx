import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import { Twcf888HomeClient } from "@/components/twcf888/Twcf888HomeClient"

export default function Twcf888Page() {
  return (
    <>
      <SiteTrafficTracker siteKey="twcf888" eventType="site_page_view" path="/twcf888" />
      <Twcf888HomeClient />
    </>
  )
}
