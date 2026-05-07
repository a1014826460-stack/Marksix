/**
 * 首页入口 — page.tsx（服务端组件）
 * ---------------------------------------------------------------
 * 从 Python 后端获取实时数据，渲染为完整的六合彩论坛页面。
 *
 * 数据流：
 *   1. 服务端调用 getPublicSitePageData() → Python 后端 /api/public/site-page
 *   2. 使用 transformSitePageData() 将后端数据转为前端组件格式
 *   3. 将转换后的数据传给 HomePageClient（客户端组件）
 *   4. HomePageClient 分发数据给 Header / NavTabs / PreResultBlocks /
 *      PredictionModules / LotteryResult / Footer 等子组件
 *
 * 与旧站的关系：
 *   - 旧站静态页面仍可通过 /vendor/shengshi8800/index.html 访问
 *   - 新 React 版本逐步取代旧站，使用相同的 CSS 类名保持视觉一致
 *   - 数据统一从 /api/public/site-page 获取，不再需要 43 个独立 JS 请求
 *
 * @see HomePageClient — 客户端交互组件（时钟、游戏切换等）
 * @see transformSitePageData — 后端数据 → 前端组件数据转换
 */

import { getPublicSitePageData, getConfiguredSiteId } from "@/lib/backend-api"
import { transformSitePageData } from "@/lib/lotteryData"
import type { PublicModule } from "@/lib/site-page"
import { fetchAllLegacyModulesByGame } from "@/lib/legacy-modules"
import { HomePageClient } from "./HomePageClient"

export default async function HomePage() {
  // ========== 从后端获取站点页面数据（站点信息 + 开奖 + 已配置模块） ==========
  // /api/public/site-page 只返回 site_prediction_modules 表中配置的模块，
  // 目前仅 "四字词语(澳欲钱料)" 一条记录
  const apiData = await getPublicSitePageData({
    siteId: getConfiguredSiteId(),
    historyLimit: 8,
  })

  // ========== 并行获取旧站 36+ 个预测模块数据（三种彩种） ==========
  // 一次性获取台湾彩(type=3)、澳门彩(type=2)、香港彩(type=1) 的旧模块数据，
  // 每种内部按 6 并发分批获取，三种彩种之间并行请求。
  const legacyByGame = await fetchAllLegacyModulesByGame()

  // ========== 构建按游戏类型分组的完整模块列表 ==========
  // 每个彩种 = site-page 模块（四字词语）+ 对应类型的旧模块
  // 避免模块重复（按 mechanism_key 去重）
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

  // ========== 转换为前端组件所需的数据格式 ==========
  // 传入 modulesByGame 让 transformSitePageData 将其注入到 LotteryPageData
  const pageData = transformSitePageData(apiData, modulesByGame)

  // ========== 渲染客户端交互页面 ==========
  return <HomePageClient data={pageData} />
}
