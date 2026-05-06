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
import { fetchAllLegacyModules } from "@/lib/legacy-modules"
import { HomePageClient } from "./HomePageClient"

export default async function HomePage() {
  // ========== 从后端获取站点页面数据（站点信息 + 开奖 + 已配置模块） ==========
  // /api/public/site-page 只返回 site_prediction_modules 表中配置的模块，
  // 目前仅 "四字词语(澳欲钱料)" 一条记录
  const apiData = await getPublicSitePageData({
    siteId: getConfiguredSiteId(),
    historyLimit: 8,
  })

  // ========== 并行获取旧站 36+ 个预测模块数据 ==========
  // 旧站通过独立 JS 文件调用 /api/kaijiang/xxx 端点获取数据，
  // 此处直接调用后端 /api/legacy/module-rows 并行获取所有模块。
  //
  // 排除已在 site_prediction_modules 中配置且由专用组件渲染的 key：
  // pt2xiao（两肖平特王）、3zxt（三期中特）、hllx（双波中特）
  const excludeLegacyKeys = ["pt2xiao", "3zxt", "hllx"]
  const legacyModules = await fetchAllLegacyModules(excludeLegacyKeys)

  // ========== 合并新旧模块数据 ==========
  // 将旧模块追加到 apiData.modules 中，
  // 保证 site_prediction_modules 配置的模块优先（靠前）
  // 旧模块使用 legacy_xxx 作为 mechanism_key
  const mergedModules = [...apiData.modules]

  for (const legacyMod of legacyModules) {
    // 避免模块重复（按 key 去重）
    const isDuplicate = mergedModules.some(
      (m) => m.mechanism_key === legacyMod.mechanism_key
    )
    if (!isDuplicate) {
      mergedModules.push(legacyMod)
    }
  }

  // ========== 将合并后的数据注入回 apiData ==========
  apiData.modules = mergedModules

  // ========== 转换为前端组件所需的数据格式 ==========
  const pageData = transformSitePageData(apiData)

  // ========== 渲染客户端交互页面 ==========
  return <HomePageClient data={pageData} />
}
