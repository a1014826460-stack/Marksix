import { buildSiteMetadata } from "@/lib/sites"

export const metadata = buildSiteMetadata("twssz")

export default function TwsszLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
