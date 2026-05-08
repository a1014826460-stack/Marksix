/**
 * 归档中的旧首页实现（暂停作为公开入口使用）
 * ---------------------------------------------------------------
 * 2026-05-08 起，前端公开入口改为 /legacy-shell?t=3。
 * 原先挂在 "/" 的 React 首页逻辑保留在此文件，仅作封存参考，避免继续作为主入口维护。
 */

import { getPublicSitePageData, getConfiguredSiteId } from "@/lib/backend-api"
import { transformSitePageData } from "@/lib/lotteryData"
import type { PublicModule } from "@/lib/site-page"
import { fetchAllLegacyModulesByGame } from "@/lib/legacy-modules"
import { HomePageClient } from "../HomePageClient"

export async function ArchivedRootHomePage() {
  const apiData = await getPublicSitePageData({
    siteId: getConfiguredSiteId(),
    historyLimit: 8,
  })

  const legacyByGame = await fetchAllLegacyModulesByGame()

  function mergeSiteAndLegacy(
    siteModules: PublicModule[],
    legacyModules: PublicModule[]
  ): PublicModule[] {
    const merged = [...siteModules]
    for (const legacyMod of legacyModules) {
      const isDuplicate = merged.some(
        (m) => m.mechanism_key === legacyMod.mechanism_key
      )
      if (!isDuplicate) {
        merged.push(legacyMod)
      }
    }
    return merged
  }

  const modulesByGame = {
    taiwan: mergeSiteAndLegacy(apiData.modules, legacyByGame.taiwan),
    macau: mergeSiteAndLegacy(apiData.modules, legacyByGame.macau),
    hongkong: mergeSiteAndLegacy(apiData.modules, legacyByGame.hongkong),
  }

  const pageData = transformSitePageData(apiData, modulesByGame)

  return <HomePageClient data={pageData} />
}
