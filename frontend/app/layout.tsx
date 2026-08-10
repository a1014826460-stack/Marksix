import type { Metadata, Viewport } from "next"
import { headers } from "next/headers"
import Script from "next/script"
import { buildSiteMetadata, findSiteByHost, findSiteByPathname } from "@/lib/sites"
import "./globals.css"

const DEFAULT_METADATA: Metadata = {
  title: "全网最准尽在台湾六合彩论坛",
  description: "全网最准尽在台湾六合彩论坛",
}

export async function generateMetadata(): Promise<Metadata> {
  const headerStore = await headers()
  const forwardedHost = headerStore.get("x-forwarded-host")
  const host = forwardedHost || headerStore.get("host")
  const rawPathname =
    headerStore.get("x-pathname") ||
    headerStore.get("x-invoke-path") ||
    headerStore.get("x-matched-path") ||
    headerStore.get("next-url")

  // Normalise the pathname: Next.js headers may carry a full URL (e.g.
  // "http://127.0.0.1:3000/twjinniu") in some environments.  Extract the
  // path portion so findSiteByPathname can match it.
  let pathname = rawPathname
  if (pathname && pathname.startsWith("http")) {
    try {
      pathname = new URL(pathname).pathname
    } catch {
      // If parsing fails, keep the original value – findSiteByPathname
      // gracefully returns null for non-path strings.
    }
  }

  // Pathname-based matching takes precedence in all environments so that
  // child routes like /twjinniu are correctly identified even in dev mode.
  // Host-based matching is the fallback for production domains that hit "/"
  // with a site-specific Host header (e.g. www.twtongtian.com).
  const matchedSite = findSiteByPathname(pathname) || findSiteByHost(host)

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
      <body>
        <Script
          src="/vendor/_shared/forced-announcement.js"
          strategy="beforeInteractive"
        />
        {children}
      </body>
    </html>
  )
}
