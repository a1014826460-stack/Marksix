/**
 * 后端 API 响应类型定义 — site-page.ts
 * ---------------------------------------------------------------
 * 本文件定义了 Python 后端 /api/public/site-page 接口返回数据的 TypeScript 类型。
 *
 * 数据结构层级：
 *   PublicSitePageData
 *     ├── site        站点信息（PublicSite）
 *     ├── draw        当前开奖快照（PublicDrawSnapshot）
 *     │     ├── current_issue  当期期号
 *     │     ├── result_balls   开奖号码球数组（6 个普通球）
 *     │     └── special_ball   特码球（第 7 个球）
 *     └── modules[]   预测模块列表（每个站点有多个预测模块）
 *           ├── mechanism_key  预测机制唯一标识（如 "flat_king"）
 *           ├── title          模块显示标题
 *           └── history[]      历史预测行数据
 *
 * 数据来源：Python 后端从数据库中查询并组装此结构，
 *           前端通过 backendFetchJson() 请求获取，然后传递给组件渲染。
 *
 * 旧站对比：旧站每个 JS 文件请求各自的 API 端点获取对应模块数据，
 *           新架构通过一次请求获取所有模块数据，减少网络开销。
 */

// ===================== 基础类型 =====================

/** 开奖号码球的颜色，对应六合彩的波色分类：红波、蓝波、绿波 */
export type BallColor = "red" | "blue" | "green"

/** 单个开奖号码球 */
export type ResultBall = {
  value: string   // 号码值（如 "01", "15", "49"）
  zodiac: string  // 对应的生肖（如 "鼠", "牛", "虎"）
  color: BallColor // 波色（红/蓝/绿）
}

// ===================== 预测模块相关类型 =====================

/** 单个预测历史行 — 对应一个预测记录及其开奖结果 */
export type PublicHistoryRow = {
  issue: string               // 期号（如 "122期"）
  year: string                // 年份
  term: string                // 期数序号
  prediction_text: string     // 预测文本（如 "虎羊"、"红波+绿波"）
  result_text: string         // 开奖结果文本（如 "蛇14准"）
  is_opened: boolean          // 是否已开奖（false 表示该期尚未开奖）
  is_correct: boolean | null  // 预测是否正确：true=准, false=不准, null=待开奖
  source_web_id: number | null // 数据来源站点 web_id
  raw: Record<string, unknown> // 原始数据（扩展字段，供未来兼容）
}

/** 单个预测模块 — 对应页面上一个预测区块 */
export type PublicModule = {
  id: number              // 模块 ID（数据库主键）
  mechanism_key: string   // 预测机制标识键（如 "flat_king"、"three_issue"）
  title: string           // 模块显示标题（如 "两肖平特王"）
  default_modes_id: number // 关联的 modes 表 ID
  default_table: string   // 默认数据表名（如 "mode_payload_flat_king"）
  sort_order: number      // 排序号（值越小越靠前）
  status: boolean         // 启用状态（true=启用，false=禁用）
  history: PublicHistoryRow[] // 该模块的历史预测行数据列表
  /** 渲染该模块使用的 CSS 类名，对应旧站 style.css 中的表格类 */
  cssClass?: string
}

// ===================== 站点相关类型 =====================

/** 站点基本信息 — 对应数据库中的 sites 表 */
export type PublicSite = {
  id: number           // 站点 ID
  name: string         // 站点名称（如 "盛世8800"）
  domain: string       // 站点域名
  lottery_type_id: number // 关联的彩票类型 ID（台湾彩/澳门彩/香港彩）
  lottery_name?: string   // 彩票类型名称（可选）
  enabled: boolean     // 站点是否启用
  start_web_id: number // 数据抓取的起始 web_id
  end_web_id: number   // 数据抓取的结束 web_id
  announcement?: string // 站点公告（可选）
  notes?: string        // 备注信息（可选）
}

// ===================== 开奖结果相关类型 =====================

/** 当前开奖快照 — 最新一期的开奖结果 */
export type PublicDrawSnapshot = {
  current_issue: string       // 当前期号（如 "122期"）
  result_balls: ResultBall[]  // 开奖号码球（通常 6 个）
  special_ball: ResultBall | null // 特码球（第 7 个球，可能为空）
}

// ===================== 顶层响应类型 =====================

/** 后端 /api/public/site-page 接口的完整响应结构 */
export type PublicSitePageData = {
  site: PublicSite              // 站点信息
  draw: PublicDrawSnapshot      // 当前开奖快照
  modules: PublicModule[]       // 所有启用的预测模块（含历史数据）
  /** 注意：modules 数组中的每个模块的 history 字段包含该模块的历史预测行，
   *        history_limit 参数控制返回的最大行数（默认 8 行）。
   *        PreResultBlocks 组件需要将此数据转换为 LotteryPageData 中的
   *        flatKingRows / threeIssueRows / doubleWaveRows 格式。 */
}
