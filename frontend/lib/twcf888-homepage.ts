import "server-only"

import { getPublicSitePageData } from "@/lib/backend-api"
import {
  getTwcf888ArticleCatalog,
  type Twcf888ArticleGroup,
  type Twcf888ModuleStatus,
} from "@/lib/twcf888-articles"
import { getSiteConfig } from "@/lib/sites"

const SITE = getSiteConfig("twcf888")

export type Twcf888LotteryType = 1 | 2 | 3

export type Twcf888HomepageCard = {
  article_id: string
  title: string
  group: Twcf888ArticleGroup
  route: string
  mode_id: number | null
  module_status: Twcf888ModuleStatus
  data_status: "live_ready" | "missing_live_data" | "snapshot" | "blocked"
  latest_issue: string | null
  notes: string[]
}

export type Twcf888HomepageSection = {
  key: Twcf888ArticleGroup
  title: string
  cards: Twcf888HomepageCard[]
}

export type Twcf888HomepageModulesResponse = {
  ok: true
  site: {
    site_key: string
    web_id: number
    lottery_type: number
    current_issue: string
  }
  legend: readonly Twcf888ModuleStatus[]
  sections: Twcf888HomepageSection[]
  live_mode_summary: Array<{
    mode_id: number
    title: string
    available: boolean
    history_count: number
  }>
}

const SECTION_TITLES: Record<Twcf888ArticleGroup, string> = {
  amgst: "高手榜单",
  jsb: "绝杀榜单",
  jhq: "精华区",
  gs: "独家公式",
}

function buildCardNotes(
  moduleStatus: Twcf888ModuleStatus,
  modeId: number | null,
  available: boolean
) {
  if (moduleStatus === "snapshot_only") {
    return ["当前栏目为 snapshot_only。"]
  }
  if (moduleStatus === "blocked_requires_backend_work") {
    return ["当前栏目为 blocked_requires_backend_work。"]
  }
  if (!available && modeId !== null) {
    return [`live_backed 栏目未返回 mode_id=${modeId} 的实时记录。`]
  }
  return []
}

export async function getTwcf888HomepageModules(
  lotteryType: Twcf888LotteryType
): Promise<Twcf888HomepageModulesResponse> {
  const sitePage = await getPublicSitePageData({
    siteId: SITE?.defaultWebId ?? 8,
    lotteryType,
    historyLimit: 8,
  })

  const liveModules = new Map(
    sitePage.modules.map((module) => [Number(module.default_modes_id), module])
  )

  const sections = (["amgst", "jsb", "jhq", "gs"] as const).map((group) => {
    const cards = getTwcf888ArticleCatalog()
      .filter((item) => item.group === group)
      .map<Twcf888HomepageCard>((item) => {
        const liveModule = item.modeId !== null ? liveModules.get(item.modeId) : null
        const available = Boolean(liveModule?.history?.length)
        const dataStatus =
          item.moduleStatus === "snapshot_only"
            ? "snapshot"
            : item.moduleStatus === "blocked_requires_backend_work"
              ? "blocked"
              : available
                ? "live_ready"
                : "missing_live_data"

        return {
          article_id: item.id,
          title: item.title,
          group,
          route: `/twcf888/${group}/${item.id}?lottery_type=${lotteryType}`,
          mode_id: item.modeId,
          module_status: item.moduleStatus,
          data_status: dataStatus,
          latest_issue: liveModule?.history?.[0]?.issue ?? null,
          notes: buildCardNotes(item.moduleStatus, item.modeId, available),
        }
      })

    return {
      key: group,
      title: SECTION_TITLES[group],
      cards,
    }
  })

  const live_mode_summary = Array.from(liveModules.values()).map((module) => ({
    mode_id: Number(module.default_modes_id),
    title: module.title,
    available: module.history.length > 0,
    history_count: module.history.length,
  }))

  return {
    ok: true,
    site: {
      site_key: SITE?.siteKey || "twcf888",
      web_id: SITE?.defaultWebId ?? 8,
      lottery_type: lotteryType,
      current_issue: sitePage.draw.current_issue,
    },
    legend: [
      "live_backed",
      "snapshot_only",
      "blocked_requires_backend_work",
    ] as const,
    sections,
    live_mode_summary,
  }
}
