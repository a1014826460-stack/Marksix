/**
 * 前端数据类型定义与静态 mock 数据 — lotteryData.ts
 * ---------------------------------------------------------------
 * 本文件包含：
 *   1. LotteryPageData 及其子类型的定义 — 前端组件所使用的数据结构
 *   2. lotteryData 静态 mock 数据对象 — 供前端开发/测试使用
 *
 * ⚠️ 重要说明：
 *   - lotteryData 中的 mock 数据仅用于前端独立开发和样式预览
 *   - 生产环境数据通过 backend-api.ts 中的 getPublicSitePageData() 从后端获取
 *   - 后端返回的类型是 PublicSitePageData（见 site-page.ts），
 *     前端需要将 modules[] 转换为 LotteryPageData 格式供组件使用
 *
 * 新旧架构的数据格式差异：
 *   新架构（LotteryPageData）  旧站（独立 JS 文件 + AJAX）
 *   一个完整对象包含所有数据    每个 JS 文件只取自己需要的字段
 *   类型安全（TypeScript）      无类型约束（纯 JavaScript）
 */

import type { PublicSitePageData, PublicModule, PublicHistoryRow } from "@/lib/site-page"

// ===================== 基础类型 =====================

/** 彩票游戏类型：台湾彩、澳门彩、香港彩 */
export type LotteryGame = "taiwan" | "macau" | "hongkong"

/** 号码球波色 */
export type BallColor = "red" | "blue" | "green"

/** 单个开奖号码球 */
export type ResultBall = {
  value: string   // 号码（如 "01"）
  color: BallColor // 波色
  zodiac: string  // 生肖
}

/**
 * 预测数据行 — 前端组件的通用行格式
 * ---------------------------------------------------------------
 * 这是前端渲染预测表格的最小数据单元，用于 PreResultBlocks 的 SourceTable 组件。
 * 后端返回的 PublicHistoryRow 需要转换为此格式。
 *
 * @property issue   - 期号（如 "122期" 或 "120-122期"）
 * @property label   - 标签（如 "平特王"、"三期中特"）
 * @property content - 预测内容（如 "虎羊"、"红波+绿波"）
 * @property result  - 开奖结果文本
 */
export type PlainRow = {
  issue: string
  label: string
  content: string
  result: string
}

/** 信息区块 — 用于展示"一肖中特"等带锚点的预测信息卡片 */
export type InfoSection = {
  id: string       // 区块唯一标识
  title: string    // 区块标题
  anchor?: string  // 锚点 ID（用于导航跳转，对应 NavTabs 中的链接）
  rows: PlainRow[] // 区块内的数据行
}

/**
 * 前端页面数据的完整结构
 * ---------------------------------------------------------------
 * 这是前端组件（PreResultBlocks、LotteryResult、InfoCard 等）需要的完整数据格式。
 * 数据来源可以是：
 *   1. Mock 数据（开发阶段）：lotteryData 对象
 *   2. 后端 API（生产阶段）：通过转换函数将 PublicSitePageData 映射为此格式
 *
 * 与 PublicSitePageData 的对应关系：
 *   后端字段                    前端字段
 *   ────────────────────────────────────────────────
 *   draw.current_issue        → currentIssue
 *   draw.result_balls         → resultBalls
 *   draw.special_ball         → specialBall
 *   modules[0].history        → flatKingRows（需转换格式）
 *   modules[1].history        → threeIssueRows（需转换格式）
 *   modules[2].history        → doubleWaveRows（需转换格式）
 */
export type LotteryPageData = {
  game: LotteryGame       // 游戏类型
  tabLabel: string        // 标签显示文字（如 "台湾彩"）
  currentIssue: string    // 当前期号
  resultBalls: ResultBall[] // 普通开奖号码球（通常 6 个）
  specialBall: ResultBall   // 特码球

  // ---- 三个核心预测模块的数据 ----
  flatKingRows: PlainRow[]    // 模块一：两肖平特王的数据行
  threeIssueRows: PlainRow[]  // 模块二：三期中特的数据行
  doubleWaveRows: PlainRow[]  // 模块三：双波中特的数据行

  // ---- 扩展数据 ----
  historyRows: PlainRow[]     // 开奖历史记录行
  infoSections: InfoSection[] // 其他信息区块（如"一肖中特"）

  // ---- 原始后端模块数据（供通用渲染器使用） ----
  /** 后端返回的完整模块列表，由 PredictionModules 组件消费 */
  rawModules: PublicModule[]

  // ---- 按游戏类型分组的预测模块数据 ----
  /** 三种彩种各自的完整模块列表，由 HomePageClient 根据 activeGame 切换 */
  modulesByGame: Record<LotteryGame, PublicModule[]>
}

// ===================== 游戏切换标签配置 =====================

/** 游戏切换标签配置，用于 LotteryResult 组件的游戏切换栏 */
export const games: { key: LotteryGame; label: string }[] = [
  { key: "taiwan", label: "台湾彩" },
  { key: "macau", label: "澳门彩" },
  { key: "hongkong", label: "香港彩" },
]

// ===================== 静态 Mock 数据 =====================

/** 台湾彩的基准 mock 数据 */
const baseData: LotteryPageData = {
  game: "taiwan",
  tabLabel: "台湾彩",
  currentIssue: "122",

  // 开奖号码：6 个普通球 + 1 个特码球
  resultBalls: [
    { value: "01", color: "red", zodiac: "鸡" },
    { value: "15", color: "blue", zodiac: "兔" },
    { value: "23", color: "red", zodiac: "羊" },
    { value: "32", color: "green", zodiac: "狗" },
    { value: "38", color: "green", zodiac: "龙" },
    { value: "44", color: "green", zodiac: "蛇" },
  ],
  specialBall: { value: "07", color: "red", zodiac: "鼠" },

  // 模块一：两肖平特王 — 每期预测两个生肖
  flatKingRows: [
    { issue: "122期", label: "平特王", content: "虎羊", result: "猫猫准" },
    { issue: "121期", label: "平特王", content: "龙马", result: "龙马准" },
  ],

  // 模块二：三期中特 — 跨期综合预测
  threeIssueRows: [
    { issue: "120-122期", label: "三期中特", content: "鸡狗猪", result: "开:中几期" },
    { issue: "117-119期", label: "三期中特", content: "龙马羊", result: "开:中1期" },
  ],

  // 模块三：双波中特 — 预测红波/蓝波/绿波组合
  doubleWaveRows: [
    { issue: "122期", label: "双波中特", content: "红波+绿波", result: "开:？00准" },
    { issue: "121期", label: "双波中特", content: "蓝波+绿波", result: "开:蛇14准" },
  ],

  // 开奖历史记录
  historyRows: [
    { issue: "122期", label: "开奖记录", content: "01 15 23 32 38 44 + 07", result: "待更新" },
    { issue: "121期", label: "开奖记录", content: "02 14 21 33 38 41 + 47", result: "蛇14开" },
  ],

  // 其他信息区块（如"一肖中特"）
  infoSections: [
    {
      id: "seven",
      title: "台湾资料网",
      anchor: "7x1m",
      rows: [
        { issue: "122期", label: "一肖中特", content: "马", result: "待更新" },
        { issue: "121期", label: "一肖中特", content: "蛇", result: "蛇14开" },
      ],
    },
  ],

  // 原始后端模块数据（mock 数据中没有后端模块，保持空数组）
  rawModules: [],

  // 按游戏类型分组的模块（mock 数据均为空）
  modulesByGame: {
    taiwan: [],
    macau: [],
    hongkong: [],
  },
}

// ===================== 各游戏类型的 Mock 数据 =====================

/**
 * 三种彩票游戏类型的 mock 数据
 * 澳门彩和香港彩共用台湾彩的数据结构，仅替换游戏相关字段
 */
export const lotteryData: Record<LotteryGame, LotteryPageData> = {
  taiwan: baseData,
  macau: {
    ...baseData,
    game: "macau",
    tabLabel: "澳门彩",
    currentIssue: "088",
    specialBall: { value: "18", color: "red", zodiac: "猴" },
  },
  hongkong: {
    ...baseData,
    game: "hongkong",
    tabLabel: "香港彩",
    currentIssue: "046",
    specialBall: { value: "16", color: "green", zodiac: "鼠" },
  },
}

/**
 * 根据游戏类型获取对应的 mock 数据
 * @param game - 游戏类型字符串（"taiwan" / "macau" / "hongkong"）
 * @returns 对应的 LotteryPageData 对象
 *
 * 注意：此函数仅用于开发阶段，生产环境应使用 getPublicSitePageData()
 */
export function getLotteryData(game: string | null): LotteryPageData {
  if (game === "macau" || game === "hongkong" || game === "taiwan") {
    return lotteryData[game]
  }

  return lotteryData.taiwan
}

// ===================== 数据转换辅助函数 =====================

/**
 * 后端数据转前端组件格式 — transformSitePageData()
 * ---------------------------------------------------------------
 * 将 Python 后端 /api/public/site-page 返回的 PublicSitePageData
 * 转换为前端组件所需的 LotteryPageData 格式。
 *
 * 转换映射：
 *   后端字段                     前端字段
 *   ───────────────────────────────────────────────────────
 *   draw.current_issue         → currentIssue
 *   draw.result_balls          → resultBalls
 *   draw.special_ball          → specialBall
 *   modules[0~N]               → modules（原始模块数组，供通用渲染器使用）
 *   modules[].history          → 根据 mechanism_key 分别映射到
 *                                flatKingRows / threeIssueRows / doubleWaveRows
 *
 * @param apiData - 后端返回的完整页面数据
 * @param siteGame - 可选的游戏类型覆盖（从 site.lottery_type_id 映射）
 * @returns 前端组件使用的 LotteryPageData
 */

/**
 * 根据站点信息确定游戏类型
 * lottery_type_id: 1=香港彩, 2=澳门彩, 3=台湾彩（依据数据库配置）
 */
function resolveGameType(lotteryTypeId: number, lotteryName?: string): LotteryGame {
  const name = (lotteryName || "").toLowerCase()
  if (name.includes("台湾") || lotteryTypeId === 3) return "taiwan"
  if (name.includes("澳门") || lotteryTypeId === 2) return "macau"
  return "hongkong" // 默认香港彩
}

/**
 * 从模块列表中提取指定 mechanism_key 的数据行，转换为 PlainRow 格式
 *
 * @param modules  - 后端返回的模块列表
 * @param key      - 要匹配的 mechanism_key（如 "pt2xiao"、"3zxt"）
 * @returns 转换后的 PlainRow 数组（找不到匹配模块时返回空数组）
 */
function extractModuleRows(modules: PublicModule[], key: string): PlainRow[] {
  const mod = modules.find(m => m.mechanism_key === key)
  if (!mod) return []
  return mod.history.map((row: PublicHistoryRow) => ({
    issue: row.issue,
    label: mod.title,
    content: row.prediction_text,
    result: row.result_text,
  }))
}

/**
 * 将后端 PublicSitePageData 转换为前端 LotteryPageData
 *
 * @param apiData - 从 getPublicSitePageData() 获取的 API 数据
 * @returns 可用于 PreResultBlocks / LotteryResult 等组件的页面数据
 *
 * 用法示例：
 *   const apiData = await getPublicSitePageData({ siteId: 1 })
 *   const pageData = transformSitePageData(apiData)
 */
export function transformSitePageData(
  apiData: PublicSitePageData,
  modulesByGame?: Record<LotteryGame, PublicModule[]>
): LotteryPageData {
  const defaultModulesByGame: Record<LotteryGame, PublicModule[]> = {
    taiwan: apiData.modules,
    macau: [],
    hongkong: [],
  }

  return {
    /* ---- 游戏信息 ---- */
    game: resolveGameType(apiData.site.lottery_type_id, apiData.site.lottery_name),
    tabLabel: apiData.site.lottery_name || apiData.site.name,

    /* ---- 开奖信息 ---- */
    currentIssue: apiData.draw.current_issue,
    resultBalls: apiData.draw.result_balls,
    specialBall: apiData.draw.special_ball ?? { value: "", color: "red", zodiac: "" },

    /* ---- 三个核心预测模块（根据 mechanism_key 匹配） ---- */
    // 注意：这些字段仅在数据库中存在对应 mechanism_key 的模块时才有数据
    flatKingRows: extractModuleRows(apiData.modules, "pt2xiao"),     // 两肖平特王（平特2肖）
    threeIssueRows: extractModuleRows(apiData.modules, "3zxt"),      // 三期中特（3肖中特）
    doubleWaveRows: extractModuleRows(apiData.modules, "hllx"),      // 双波中特（红蓝绿肖）

    /* ---- 扩展数据 ---- */
    historyRows: [],        // 开奖历史（目前 API 未单独提供）
    infoSections: [],       // 其他信息区块（后续从 modules 中提取）

    /* ---- 原始模块数据（供通用渲染器使用） ---- */
    /** 保留后端返回的完整模块列表，供 PredictionModules 组件消费 */
    rawModules: apiData.modules,

    /* ---- 按游戏类型分组的预测模块数据 ---- */
    modulesByGame: modulesByGame ?? defaultModulesByGame,
  }
}

/**
 * 将模块历史行转换为通用表格行格式
 * 用于 PredictionModules 组件中的通用渲染
 *
 * @param module - 后端返回的单个模块
 * @returns PlainRow 数组
 */
export function moduleToRows(module: PublicModule): PlainRow[] {
  return module.history.map((row: PublicHistoryRow) => ({
    issue: row.issue,
    label: row.is_opened ? "开奖" : "预测",
    content: row.prediction_text,
    result: row.result_text,
  }))
}

