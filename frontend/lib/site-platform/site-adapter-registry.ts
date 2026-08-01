import type { ExistingDomAdapter } from "@/lib/site-platform/site-adapter"
import shengshi8800 from "@/sites/shengshi8800/site-adapter"
import twsaimahui from "@/sites/twsaimahui/site-adapter"
import twcaibawang from "@/sites/twcaibawang/site-adapter"
import twjinniu from "@/sites/twjinniu/site-adapter"
import twcf888 from "@/sites/twcf888/site-adapter"
import twssz from "@/sites/twssz/site-adapter"
import twbst528 from "@/sites/twbst528/site-adapter"
import twjsz666 from "@/sites/twjsz666/site-adapter"
import twwanli from "@/sites/twwanli/site-adapter"

const SITE_ADAPTERS: Readonly<Record<string, ExistingDomAdapter>> = Object.freeze({
  shengshi8800,
  twsaimahui,
  twcaibawang,
  twjinniu,
  twcf888,
  twssz,
  twbst528,
  twjsz666,
  twwanli,
})

export function getSiteAdapter(siteKey: string): ExistingDomAdapter | null {
  return SITE_ADAPTERS[siteKey] || null
}

export function getAllSiteAdapters(): readonly ExistingDomAdapter[] {
  return Object.values(SITE_ADAPTERS)
}
