"use client"

import { useEffect } from "react"

import type { SiteTrafficEventType } from "@/lib/site-api-service"

type SiteTrafficTrackerProps = {
  siteKey: string
  eventType: SiteTrafficEventType
  articleId?: string
  path?: string
}

const VISITOR_KEY = "liuhecai_site_visitor_id"

function getVisitorId() {
  try {
    const existing = window.localStorage.getItem(VISITOR_KEY)
    if (existing) return existing
    const generated =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    window.localStorage.setItem(VISITOR_KEY, generated)
    return generated
  } catch {
    return ""
  }
}

export function SiteTrafficTracker({
  siteKey,
  eventType,
  articleId,
  path,
}: SiteTrafficTrackerProps) {
  useEffect(() => {
    const payload = {
      event_type: eventType,
      visitor_id: getVisitorId(),
      path: path || window.location.pathname,
      route: window.location.pathname,
      article_id: articleId,
      referrer: document.referrer,
      occurred_at: new Date().toISOString(),
      utm_source: new URLSearchParams(window.location.search).get("utm_source") || undefined,
      utm_medium: new URLSearchParams(window.location.search).get("utm_medium") || undefined,
      utm_campaign: new URLSearchParams(window.location.search).get("utm_campaign") || undefined,
    }
    const endpoint = `/api/sites/${encodeURIComponent(siteKey)}/traffic-events`
    const body = JSON.stringify(payload)

    if (navigator.sendBeacon) {
      const sent = navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }))
      if (sent) return
    }

    void fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => undefined)
  }, [articleId, eventType, path, siteKey])

  return null
}
