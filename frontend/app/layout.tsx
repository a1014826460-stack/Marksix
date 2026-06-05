import type { Metadata, Viewport } from "next"
import { headers } from "next/headers"
import { buildSiteMetadata, findSiteByHost, findSiteByPathname } from "@/lib/sites"
import "./globals.css"

const DEFAULT_METADATA: Metadata = {
  title: "全网最准尽在台湾六合彩论坛",
  description: "全网最准尽在台湾六合彩论坛",
  icons: {
    icon: "/favicon.ico",
  },
}

export async function generateMetadata(): Promise<Metadata> {
  const headerStore = await headers()
  const forwardedHost = headerStore.get("x-forwarded-host")
  const host = forwardedHost || headerStore.get("host")
  const pathname =
    headerStore.get("x-invoke-path") ||
    headerStore.get("x-matched-path") ||
    headerStore.get("next-url")
  const normalizedHost = String(host || "").trim().toLowerCase().replace(/:\d+$/, "")
  const matchedSite =
    (normalizedHost === "localhost" || normalizedHost === "127.0.0.1"
      ? findSiteByPathname(pathname)
      : null) || findSiteByHost(host)

  if (!matchedSite) {
    return DEFAULT_METADATA
  }

  return buildSiteMetadata(matchedSite.siteKey, DEFAULT_METADATA)
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  minimumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  )
}
