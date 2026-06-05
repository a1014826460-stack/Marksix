import { buildSiteMetadata } from "@/lib/sites"

export const metadata = buildSiteMetadata("twcf888")

export default function Twcf888Layout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
