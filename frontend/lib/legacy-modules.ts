/**
 * 旧站预测模块注册表 — legacy-modules.ts
 * ---------------------------------------------------------------
 * 职责：定义旧站 36+ 个独立 JS 文件对应的 API 端点映射，
 *       并提供统一的数据获取函数供 page.tsx 服务端组件调用。
 *
 * 背景：
 *   旧站（/vendor/shengshi8800/index.html）通过 36+ 个独立 JS 文件
 *   各自调用 /api/kaijiang/xxx 端点获取数据。每个端点对应一个 modes_id，
 *   从后端 /api/legacy/module-rows 获取原始数据。
 *
 *   而新架构的 /api/public/site-page 只返回 site_prediction_modules 表中
 *   配置的模块（目前仅 1 个）。为显示所有旧模块，我们需要在此注册全部端点，
 *   在 page.tsx 中额外获取并合并到页面数据中。
 *
 * 数据流：
 *   page.tsx
 *     ├── getPublicSitePageData()   → 站点信息 + 开奖 + 已配置模块
 *     └── fetchAllLegacyModules()   → 36+ 旧模块并行获取 → 合并到 rawModules
 *
 * 扩展方式：
 *   如需新增模块，只需在 LEGACY_MODULE_DEFS 数组中添加一条记录。
 *   如需自定义渲染，可在 PredictionModules.tsx 或 PreResultBlocks.tsx
 *   中根据 mechanism_key 做特殊处理。
 */

import { backendFetchJson } from "@/lib/backend-api"
import type { PublicModule, PublicHistoryRow } from "@/lib/site-page"

// ===================== 类型定义 =====================

/** 旧模块定义 — 描述一个旧站预测模块 */
type LegacyModuleDef = {
  /** 端点名称（对应 kaijiang/[[...path]]/route.ts 的 switch-case） */
  endpoint: string
  /** 后端 modes_id（对应 mode_payload_xxx 表） */
  modesId: number
  /** 模块显示标题（来自旧站 JS 文件的标题文本） */
  title: string
  /** 唯一标识键，用作 PublicModule.mechanism_key */
  key: string
  /** 最大获取行数 */
  limit: number
  /** 额外的 URL 查询参数 */
  params?: Record<string, string>
}

/** 后端 /api/legacy/module-rows 返回的原始行类型 */
type LegacyRawRow = Record<string, string | number | null>

/** 后端 /api/legacy/module-rows 响应类型 */
type BackendLegacyPayload = {
  modes_id: number
  title: string
  table_name: string
  rows: LegacyRawRow[]
}

// ===================== 模块注册表 =====================

/**
 * 旧站模块定义列表
 * ---------------------------------------------------------------
 * 每个条目对应旧站中一个 JS 文件及其 API 请求。
 * 数据来源：frontend/app/api/kaijiang/[[...path]]/route.ts 的 switch-case
 * 和 frontend/public/vendor/shengshi8800/static/js/*.js 中的标题文本。
 *
 * 字段说明：
 *   endpoint — 端点名，对应 /api/kaijiang/{endpoint}
 *   modesId  — 后端 modes_id，选择 mode_payload_* 表
 *   title    — 模块标题，与旧站视觉一致
 *   key      — 唯一键，用于去重和 mechanism_key
 *   limit    — 最多获取的行数
 *   params   — 额外查询参数（如 num=2）
 */
const LEGACY_MODULE_DEFS: LegacyModuleDef[] = [
  // ---- 核心模块（已由 PreResultBlocks 专用渲染） ----
  // 注意：如果 /api/public/site-page 已返回这些模块的 mechanism_key
  // （pt2xiao / 3zxt / hllx），则此处会被 excludeKeys 过滤去重
  { endpoint: "getPingte", modesId: 43, title: "两肖平特王",  key: "legacy_pt2xiao",   limit: 6,  params: { num: "2" } },
  { endpoint: "getSanqiXiao4new", modesId: 197, title: "三期中特", key: "legacy_3zxt", limit: 8 },
  { endpoint: "sbzt",         modesId: 38, title: "双波中特",   key: "legacy_hllx",    limit: 6 },

  // ---- 七肖七码 / 台湾资料网 ----
  { endpoint: "getXiaoma",   modesId: 246, title: "台湾资料网", key: "legacy_7x7m",    limit: 6,  params: { num: "7" } },

  // ---- 黑白无双 ----
  { endpoint: "getHbnx",     modesId: 45,  title: "特邀高手→【黑白无双】", key: "legacy_hbnx", limit: 6 },

  // ---- 一句真言（诗句） ----
  { endpoint: "getYjzy",     modesId: 50,  title: "一句真言",   key: "legacy_yjzy",    limit: 8 },

  // ---- 六肖中特 ----
  { endpoint: "lxzt",        modesId: 46,  title: "六肖中特",   key: "legacy_lxzt",    limit: 10 },

  // ---- 三色生肖 ----
  { endpoint: "getHllx",     modesId: 8,   title: "三色生肖",   key: "legacy_3ssx",    limit: 8,  params: { num: "2" } },

  // ---- 大小中特 ----
  { endpoint: "getDxzt",     modesId: 57,  title: "大小中特",   key: "legacy_dxzt",    limit: 10 },

  // ---- 家野中特 ----
  { endpoint: "getJyzt",     modesId: 63,  title: "家野中特",   key: "legacy_jyzt",    limit: 10 },

  // ---- 平特尾 ----
  { endpoint: "ptyw",        modesId: 54,  title: "平特尾",     key: "legacy_ptyw",    limit: 8 },

  // ---- 九肖一码 ----
  { endpoint: "getXmx1",     modesId: 151, title: "九肖一码",   key: "legacy_9x1m",    limit: 10, params: { num: "9" } },

  // ---- 三头中特 ----
  { endpoint: "getTou",      modesId: 12,  title: "三头中特",   key: "legacy_3tou",    limit: 10, params: { num: "3" } },

  // ---- 心特 ----
  { endpoint: "getXingte",   modesId: 53,  title: "心特",       key: "legacy_xingte",  limit: 10 },

  // ---- 四肖八码 ----
  { endpoint: "sxbm",        modesId: 51,  title: "四肖八码",   key: "legacy_4x8m",    limit: 10 },

  // ---- 单双 ----
  { endpoint: "danshuang",   modesId: 28,  title: "单双",       key: "legacy_danshuang", limit: 10 },

  // ---- 单双四肖 ----
  { endpoint: "dssx",        modesId: 31,  title: "单双四肖",   key: "legacy_dssx",    limit: 10 },

  // ---- 特段 ----
  { endpoint: "getCodeDuan", modesId: 65,  title: "特段",       key: "legacy_teduan",  limit: 10 },

  // ---- 欲钱买特码 ----
  { endpoint: "getJuzi",     modesId: 68,  title: "欲钱买特码", key: "legacy_yqmtm",   limit: 10, params: { num: "yqmtm" } },

  // ---- 杀三肖 ----
  { endpoint: "getShaXiao",  modesId: 42,  title: "杀三肖",     key: "legacy_shaxiao", limit: 10 },

  // ---- 特码 ----
  { endpoint: "getCode",     modesId: 34,  title: "特码",       key: "legacy_tema",    limit: 10 },

  // ---- 琴棋书画 ----
  { endpoint: "qqsh",        modesId: 26,  title: "琴棋书画",   key: "legacy_qqsh",    limit: 10 },

  // ---- 绝杀半波 ----
  { endpoint: "getShaBanbo", modesId: 58,  title: "绝杀半波",   key: "legacy_shabanbo", limit: 10 },

  // ---- 绝杀一尾 ----
  { endpoint: "getShaWei",   modesId: 20,  title: "绝杀一尾",   key: "legacy_shawei",  limit: 10, params: { num: "1" } },

  // ---- 四字玄机 ----
  { endpoint: "getSzxj",     modesId: 52,  title: "四字玄机",   key: "legacy_szxj",    limit: 10 },

  // ---- 幽默 ----
  { endpoint: "getDjym",     modesId: 59,  title: "幽默",       key: "legacy_djym",    limit: 10 },

  // ---- 四季三肖（春夏秋冬） ----
  { endpoint: "getSjsx",     modesId: 61,  title: "四季三肖",   key: "legacy_sjsx",    limit: 10 },

  // ---- 肉菜草肖 ----
  { endpoint: "getRccx",     modesId: 3,   title: "肉菜草肖",   key: "legacy_rccx",    limit: 10, params: { num: "2" } },

  // ---- 一句平特佳 ----
  { endpoint: "yyptj",       modesId: 244, title: "一句平特佳", key: "legacy_yyptj",   limit: 10 },

  // ---- 五肖中特 ----
  { endpoint: "wxzt",        modesId: 48,  title: "五肖中特",   key: "legacy_wxzt",    limit: 6 },

  // ---- 六尾中特 ----
  { endpoint: "getWei",      modesId: 2,   title: "六尾中特",   key: "legacy_6wei",    limit: 10, params: { num: "6" } },

  // ---- 九肖中特 ----
  { endpoint: "jxzt",        modesId: 49,  title: "九肖中特",   key: "legacy_jxzt",    limit: 10 },

  // ---- 平特一肖 ----
  { endpoint: "getPingte",   modesId: 56,  title: "平特一肖",   key: "legacy_ptyx",    limit: 8 },

  // ---- 大小中特（带头数） ----
  { endpoint: "getDxztt1",   modesId: 108, title: "大小中特",   key: "legacy_dxztt1",  limit: 10 },

  // ---- 单双四肖（第二版） ----
  { endpoint: "getDsnx",     modesId: 31,  title: "单双四肖",   key: "legacy_dsnx",    limit: 10 },

  // ---- 跑马 ----
  { endpoint: "getPmxjcz",   modesId: 331, title: "跑马",       key: "legacy_pmxjcz",  limit: 6 },

  // ---- 句子（普通） ----
  { endpoint: "getJuzi",     modesId: 62,  title: "句子",       key: "legacy_juzi",    limit: 10 },

  // ---- 七肖七码（新版 qxbm） ----
  { endpoint: "qxbm",        modesId: 246, title: "七肖七码",   key: "legacy_qxbm",    limit: 10 },
]

// ===================== 工具函数 =====================

/**
 * 将后端原始行数据转换为 PublicHistoryRow 格式
 * ---------------------------------------------------------------
 * 每个旧模块的行数据字段类似：
 *   { term: "269", year: "2026", res_code: "01,02", res_sx: "鼠,牛", content: "虎羊" }
 *
 * 转换为：
 *   { issue: "269期", prediction_text: "虎羊", result_text: "牛02准", is_opened: true, ... }
 *
 * @param row - 后端返回的原始行数据
 * @returns 标准化后的历史行
 */
function rowToHistoryRow(row: LegacyRawRow): PublicHistoryRow {
  const term = String(row.term || "")
  const issue = term ? `${term}期` : ""

  // 获取预测文本（content 字段）
  const predictionText = String(row.content ?? row.value ?? "")

  // 解析开奖结果：res_code 和 res_sx 是逗号分隔的字符串
  const resCodeRaw = String(row.res_code || "")
  const resSxRaw = String(row.res_sx || "")
  const codeSplit = resCodeRaw.split(",").filter(Boolean)
  const sxSplit = resSxRaw.split(",").filter(Boolean)

  const hasResult = codeSplit.length > 0 || sxSplit.length > 0
  const lastCode = codeSplit.length > 0 ? codeSplit[codeSplit.length - 1] : "00"
  const lastSx = sxSplit.length > 0 ? sxSplit[sxSplit.length - 1] : "？"

  // 格式化结果文本：如 "蛇14准"、"待开奖"
  const resultText = hasResult ? `${lastSx}${lastCode}准` : "待开奖"

  return {
    issue,
    year: String(row.year || ""),
    term,
    prediction_text: predictionText,
    result_text: resultText,
    is_opened: hasResult,
    source_web_id: null,
    raw: { ...row },
  }
}

/**
 * 为特定模块定义获取数据
 * ---------------------------------------------------------------
 * 调用后端 /api/legacy/module-rows 获取原始行数据，
 * 转换为 PublicModule 格式。
 *
 * @param def - 模块定义
 * @returns PublicModule 格式的模块数据（行数据为空时返回 null）
 */
async function fetchLegacyModule(def: LegacyModuleDef): Promise<PublicModule | null> {
  try {
    const payload = await backendFetchJson<BackendLegacyPayload>("/legacy/module-rows", {
      query: {
        modes_id: def.modesId,
        limit: def.limit,
        web: 4,
        type: 3,
        ...def.params,
      },
    })

    const rows = payload.rows || []
    if (rows.length === 0) return null

    return {
      id: def.modesId,
      mechanism_key: def.key,
      title: def.title,
      default_modes_id: def.modesId,
      default_table: payload.table_name || `mode_payload_${def.modesId}`,
      sort_order: 0,
      status: true,
      history: rows.map(rowToHistoryRow),
    }
  } catch (err) {
    // 单个模块失败不应影响整体页面渲染
    console.warn(`[legacy-modules] 获取模块失败: ${def.title}`, err)
    return null
  }
}

// ===================== 主导出函数 =====================

/**
 * 并行获取所有旧站预测模块数据
 * ---------------------------------------------------------------
 * 一次性获取 36+ 个旧模块，过滤掉空结果。
 * 在 page.tsx 中与 getPublicSitePageData() 的结果合并。
 *
 * @param excludeKeys - 需要排除的 key 列表（避免与已有模块重复）
 * @returns PublicModule 数组
 *
 * 用法示例：
 *   const legacyModules = await fetchAllLegacyModules(["pt2xiao", "3zxt", "hllx"])
 *   // 合并到 apiData.modules
 *   apiData.modules = [...apiData.modules, ...legacyModules]
 */
export async function fetchAllLegacyModules(excludeKeys: string[] = []): Promise<PublicModule[]> {
  // 过滤掉已由其他组件（如 PreResultBlocks）处理的模块
  const activeDefs = LEGACY_MODULE_DEFS.filter(
    (def) => !excludeKeys.includes(def.key.replace("legacy_", "")) &&
             !excludeKeys.includes(def.key)
  )

  // 并行获取所有模块
  const results = await Promise.all(activeDefs.map(fetchLegacyModule))

  // 过滤掉 null（获取失败或空数据）
  return results.filter((m): m is PublicModule => m !== null)
}

/**
 * 获取完整的模块定义列表（用于调试和配置）
 */
export function getLegacyModuleDefs(): LegacyModuleDef[] {
  return LEGACY_MODULE_DEFS
}
