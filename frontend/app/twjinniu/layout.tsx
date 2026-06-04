import { buildSiteMetadata } from "@/lib/sites"

export const metadata = buildSiteMetadata("twjinniu")

export default function TwjinniuLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
