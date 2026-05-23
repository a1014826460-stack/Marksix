import { buildSiteMetadata } from "@/lib/sites"

export const metadata = buildSiteMetadata("twcaibawang")

export default function TwcaibawangLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
