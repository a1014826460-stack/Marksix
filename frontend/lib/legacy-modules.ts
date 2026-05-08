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

/** 内容转换函数签名 — 将原始后端内容转为前端显示文本 */
type ContentTransformer = (content: string, row: LegacyRawRow) => string

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
  /** 数据来源 web_id（旧站 JS 中有些用 web=2，大部分用 web=4） */
  web?: number
  /** 额外的 URL 查询参数 */
  params?: Record<string, string>
  /** 渲染使用的 CSS 表格类名（默认 "duilianpt1"） */
  tableClass?: string
  /**
   * 内容转换器 — 将后端原始 content 转换为前端显示文本。
   * 部分模块（如三期中特、三头中特）的 content 是 JSON 数组，
   * 旧站 JS 会从中提取特定字段显示，需模拟此处理逻辑。
   */
  contentTransform?: ContentTransformer
  /**
   * 预测文本来源列名（默认 "content"）。
   * 部分表没有 content 列，需要从其他列读取：
   *   "xiao"  → 七肖七码 (246)
   *   "hei"   → 黑白无双 (45)
   *   "title" → 一句真言 (50)
   */
  contentColumn?: string
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
  { endpoint: "getSanqiXiao4new", modesId: 197, title: "三期中特", key: "legacy_3zxt", limit: 8,
    contentTransform: (content) => {
      try {
        const items = JSON.parse(content)
        return items.map((item: string) => item.split('|')[0]).join('')
      } catch { return content }
    },
  },
  { endpoint: "sbzt",         modesId: 38, title: "双波中特",   key: "legacy_hllx",    limit: 6 },

  // ---- 台湾资料网（七肖七码） ----
  { endpoint: "getXiaoma",   modesId: 44, title: "台湾资料网", key: "legacy_7x7m",    limit: 6,  params: { num: "7" }, contentColumn: "content",
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        if (Array.isArray(parsed)) {
          const xiaoList: string[] = []
          const codeList: string[] = []
          for (const item of parsed) {
            const [xiao = "", code = ""] = String(item).split("|")
            if (xiao) xiaoList.push(xiao)
            if (code) codeList.push(code)
          }
          const parts = []
          const sections: Array<[number, string]> = [[1, "一肖"], [2, "二肖"], [4, "四肖"], [xiaoList.length, "七肖"]]
          for (const [n, label] of sections) {
            if (xiaoList.length >= n) {
              parts.push(`${label}:${xiaoList.slice(0, n).join("")} ${n === 1 ? "一" : n === 2 ? "二" : n === 4 ? "四" : "七"}码:${codeList.slice(0, n).join(".")}`)
            }
          }
          return parts.join(" | ")
        }
        return content
      } catch { return content }
    },
  },

  // ---- 黑白无双 ----
  { endpoint: "getHbnx",     modesId: 45,  title: "特邀高手→【黑白无双】→全新上线", key: "legacy_hbnx", limit: 6,
    contentColumn: "hei",
    contentTransform: (content, row) => {
      const bai = String(row?.bai ?? "")
      return `黑:${content.replace(/,/g, "")} 白:${bai.replace(/,/g, "")}`
    },
  },

  // ---- 一句真言（诗句） ----
  { endpoint: "getYjzy",     modesId: 50,  title: "一句真言",   key: "legacy_yjzy",    limit: 8,    tableClass: "duilianpt1 legacy-module-text",
    contentColumn: "title",
    contentTransform: (content, row) => {
      const jiexi = String(row?.jiexi ?? "")
      return `${content}（${jiexi}）`
    },
  },

  // ---- 六肖中特 ----
  { endpoint: "lxzt",        modesId: 46,  title: "六肖中特",   key: "legacy_lxzt",    limit: 10 },

  // ---- 三色生肖 ----
  { endpoint: "getHllx",     modesId: 8,   title: "三色生肖",   key: "legacy_3ssx",    limit: 8,  params: { num: "2" } },

  // ---- 大小中特 ----
  { endpoint: "getDxzt",     modesId: 57,  title: "大小中特",   key: "legacy_dxzt",    limit: 10 },

  // ---- 家野中特 ----
  { endpoint: "getJyzt",     modesId: 63,  title: "家野中特",   key: "legacy_jyzt",    limit: 10 },

  // ---- 平特尾 ----
  // 平特尾 content 格式：JSON 数组 ["尾|num1,num2,...", ...]
  // 旧站显示：提取第一个元素的第一个字符，重复 5 次 → "55555"
  { endpoint: "ptyw",        modesId: 54,  title: "平特尾",     key: "legacy_ptyw",    limit: 8,
    contentTransform: (content) => {
      try {
        const items = JSON.parse(content)
        const firstChar = items[0]?.split('|')[0]?.split('')[0] || ''
        return firstChar.repeat(5)
      } catch { return content }
    },
  },

  // ---- 九肖一码 ----
  { endpoint: "getXmx1",     modesId: 151, title: "九肖一码",   key: "legacy_9x1m",    limit: 10, params: { num: "9" } },

  // ---- 三头中特 ----
  // content 格式：JSON 数组 ["0|01,13,25,37,49", "1|02,14,26,38", ...]
  // 旧站显示：提取每个元素的第一个字符 + "头" → "0头3头4头"
  { endpoint: "getTou",      modesId: 12,  title: "三头中特",   key: "legacy_3tou",    limit: 10, params: { num: "3" },
    contentTransform: (content) => {
      try {
        const items = JSON.parse(content)
        return items.map((item: string) => item.split('|')[0].split('')[0] + '头').join('')
      } catch { return content }
    },
  },

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
  { endpoint: "getJuzi",     modesId: 68,  title: "欲钱买特码", key: "legacy_yqmtm",   limit: 10, params: { num: "yqmtm" }, tableClass: "duilianpt1 legacy-module-text" },

  // ---- 杀三肖 ----
  { endpoint: "getShaXiao",  modesId: 42,  title: "杀三肖",     key: "legacy_shaxiao", limit: 10 },

  // ---- 特码 ----
  { endpoint: "getCode",     modesId: 34,  title: "特码",       key: "legacy_tema",    limit: 10 },

  // ---- 琴棋书画 ----
  { endpoint: "qqsh",        modesId: 26,  title: "琴棋书画",   key: "legacy_qqsh",    limit: 10, tableClass: "duilianpt1 legacy-module-text" },

  // ---- 绝杀半波 ----
  { endpoint: "getShaBanbo", modesId: 58,  title: "绝杀半波",   key: "legacy_shabanbo", limit: 10 },

  // ---- 绝杀一尾 ----
  { endpoint: "getShaWei",   modesId: 20,  title: "绝杀一尾",   key: "legacy_shawei",  limit: 10, params: { num: "1" } },

  // ---- 四字玄机 ----
  { endpoint: "getSzxj",     modesId: 52,  title: "四字玄机",   key: "legacy_szxj",    limit: 10, tableClass: "duilianpt1 legacy-module-text" },

  // ---- 幽默 ----
  { endpoint: "getDjym",     modesId: 59,  title: "幽默",       key: "legacy_djym",    limit: 10, tableClass: "duilianpt1 legacy-module-text",
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        return parsed.title || parsed.content || content
      } catch { return content }
    },
  },

  // ---- 四季三肖（春夏秋冬） ----
  { endpoint: "getSjsx",     modesId: 61,  title: "四季三肖",   key: "legacy_sjsx",    limit: 10 },

  // ---- 肉菜草肖 ----
  { endpoint: "getRccx",     modesId: 3,   title: "肉菜草肖",   key: "legacy_rccx",    limit: 10, params: { num: "2" } },

  // ---- 一句平特佳 ----
  { endpoint: "yyptj",       modesId: 244, title: "一句平特佳", key: "legacy_yyptj",   limit: 10, tableClass: "duilianpt1 legacy-module-text",
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        return parsed.content || content
      } catch { return content }
    },
  },

  // ---- 五肖中特 ----
  { endpoint: "wxzt",        modesId: 48,  title: "五肖中特",   key: "legacy_wxzt",    limit: 6 },

  // ---- 六尾中特 ----
  { endpoint: "getWei",      modesId: 2,   title: "六尾中特",   key: "legacy_6wei",    limit: 10, params: { num: "6" } },

  // ---- 九肖中特 ----
  { endpoint: "jxzt",        modesId: 49,  title: "九肖中特",   key: "legacy_jxzt",    limit: 10 },

  // ---- 平特一肖 ----
  { endpoint: "getPingte",   modesId: 56,  title: "平特一肖",   key: "legacy_ptyx",    limit: 8 },

  // ---- 大小中特（带头数） ----
  { endpoint: "getDxztt1",   modesId: 108, title: "大小中特",   key: "legacy_dxztt1",  limit: 10,
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        return parsed.content || content
      } catch { return content }
    },
  },

  // ---- 单双四肖（第二版） ----
  { endpoint: "getDsnx",     modesId: 31,  title: "单双四肖",   key: "legacy_dsnx",    limit: 10 },

  // ---- 跑马 ----
  { endpoint: "getPmxjcz",   modesId: 331, title: "跑马",       key: "legacy_pmxjcz",  limit: 6,
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        return parsed.content || content
      } catch { return content }
    },
  },

  // ---- 句子（普通） ----
  { endpoint: "getJuzi",     modesId: 62,  title: "句子",       key: "legacy_juzi",    limit: 10, tableClass: "duilianpt1 legacy-module-text" },

  // ---- 七肖七码（新版 qxbm） ----
  { endpoint: "qxbm",        modesId: 44, title: "七肖七码",   key: "legacy_qxbm",    limit: 10, contentColumn: "content",
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        if (Array.isArray(parsed)) {
          const xiaoList: string[] = []
          const codeList: string[] = []
          for (const item of parsed) {
            const [xiao = "", code = ""] = String(item).split("|")
            if (xiao) xiaoList.push(xiao)
            if (code) codeList.push(code)
          }
          const parts = []
          const sections: Array<[number, string]> = [[1, "一肖"], [2, "二肖"], [4, "四肖"], [xiaoList.length, "七肖"]]
          for (const [n, label] of sections) {
            if (xiaoList.length >= n) {
              parts.push(`${label}:${xiaoList.slice(0, n).join("")} ${n === 1 ? "一" : n === 2 ? "二" : n === 4 ? "四" : "七"}码:${codeList.slice(0, n).join(".")}`)
            }
          }
          return parts.join(" | ")
        }
        return content
      } catch { return content }
    },
  },

  // ---- 五行八码 ----
  { endpoint: "qxbm",        modesId: 44, title: "五行八码",   key: "legacy_wxbm",    limit: 10, contentColumn: "content",
    contentTransform: (content) => {
      try {
        const parsed = JSON.parse(content)
        if (Array.isArray(parsed)) {
          const pairs = parsed.map((item: string) => {
            const [xiao = "", code = ""] = String(item).split("|")
            return `${xiao}:${code}`
          })
          return pairs.join(" ")
        }
        return content
      } catch { return content }
    },
  },
]

// ===================== 工具函数 =====================

/**
 * 判断预测是否命中开奖结果
 * ---------------------------------------------------------------
 * 通过比对预测文本中的生肖/数字与开奖结果来判断正确性。
 * 支持解析 JSON 格式的预测内容（如六尾中特、九肖一码）。
 *
 * @param content - 预测文本
 * @param resSx   - 开奖生肖（逗号分隔）
 * @param resCode - 开奖号码（逗号分隔）
 * @returns true=命中, false=未命中, null=无开奖数据
 */
const ZODIAC_SET = new Set(["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"])

function isPredictionCorrect(
  content: string,
  resSx: string,
  resCode: string
): boolean | null {
  if (!resSx && !resCode) return null

  const sxList = resSx.split(",").filter(Boolean).map((s) => s.trim())
  const codeList = resCode.split(",").filter(Boolean).map((s) => s.trim())

  // 展开 JSON 数组内容（六尾中特、九肖一码等用 JSON 存储）
  let textToCheck = content
  try {
    const parsed = JSON.parse(content)
    if (Array.isArray(parsed)) textToCheck = parsed.join(",")
  } catch {
    // 不是 JSON，保持原始文本
  }

  // 检查预测中的生肖是否出现在开奖生肖中
  for (const char of textToCheck) {
    if (ZODIAC_SET.has(char) && sxList.includes(char)) {
      return true
    }
  }

  // 提取所有数字，检查是否出现在开奖号码中
  const allNumbers = textToCheck.match(/\d+/g) || []
  for (const num of allNumbers) {
    if (codeList.includes(num)) return true
  }

  // 有开奖数据但未匹配到 → 预测错误
  return false
}

/**
 * 格式化开奖结果文本
 * ---------------------------------------------------------------
 * 格式：最后一个生肖 + 最后一个号码
 * 如 "蛇14"、"马01"
 */
function formatResultLabel(resCode: string, resSx: string): string {
  const codeSplit = resCode.split(",").filter(Boolean)
  const sxSplit = resSx.split(",").filter(Boolean)
  if (codeSplit.length === 0 && sxSplit.length === 0) return "待开奖"
  const lastCode = codeSplit.length > 0 ? codeSplit[codeSplit.length - 1] : ""
  const lastSx = sxSplit.length > 0 ? sxSplit[sxSplit.length - 1] : ""
  return `${lastSx}${lastCode}`
}

/**
 * 将后端原始行数据转换为 PublicHistoryRow 格式
 * ---------------------------------------------------------------
 * 每个旧模块的行数据字段类似：
 *   { term: "269", year: "2026", res_code: "01,02", res_sx: "鼠,牛", content: "虎羊" }
 *
 * 转换为：
 *   { issue: "269期", prediction_text: "虎羊", result_text: "牛02", ... }
 *
 * 支持字段：
 *   - term / start+end：单期使用 term；三期中特等使用 start-end 范围
 *   - content：应用 contentTransform 转换（JSON 数组→精简显示）
 *
 * @param row    - 后端返回的原始行数据
 * @param options - 可选配置 { contentTransform, key }
 * @returns 标准化后的历史行
 */
function rowToHistoryRow(
  row: LegacyRawRow,
  options?: { contentTransform?: ContentTransformer; key?: string; contentColumn?: string }
): PublicHistoryRow {
  // 期号：三期中特使用 start-end 范围，其他使用 term
  let issue: string
  const start = row.start
  const end = row.end
  if (start && end && String(start) !== String(row.term)) {
    issue = `${start}-${end}期`
  } else {
    const term = String(row.term || "")
    issue = term ? `${term}期` : ""
  }

  // 获取预测文本：支持自定义列名（contentColumn），默认 content/value
  const sourceCol = options?.contentColumn
  const rawContent = sourceCol
    ? String(row[sourceCol] ?? "")
    : String(row.content ?? row.value ?? "")
  const predictionText = options?.contentTransform
    ? options.contentTransform(rawContent, row)
    : rawContent

  // 解析开奖结果：res_code 和 res_sx 是逗号分隔的字符串
  const resCodeRaw = String(row.res_code || "")
  const resSxRaw = String(row.res_sx || "")

  const hasResult = resCodeRaw.split(",").filter(Boolean).length > 0 ||
                    resSxRaw.split(",").filter(Boolean).length > 0

  // 判断正确性：使用原始 content（未经转换）进行判断
  const isCorrect = isPredictionCorrect(rawContent, resSxRaw, resCodeRaw)

  // 特定模块的结果文本特殊处理
  let resultText: string
  if (options?.key === "legacy_3zxt") {
    // 三期中特：旧站显示"中1期"/"中几期"（文本计数）
    resultText = hasResult ? "中1期" : "中几期"
  } else {
    resultText = hasResult ? formatResultLabel(resCodeRaw, resSxRaw) : "待开奖"
  }

  return {
    issue,
    year: String(row.year || ""),
    term: String(row.term || ""),
    prediction_text: predictionText,
    result_text: resultText,
    is_opened: hasResult,
    is_correct: isCorrect,
    source_web_id: null,
    raw: { ...row },
  }
}

// 自增计数器，为每个旧模块生成唯一负整数 ID（避免与 site-page API 的正数 ID 冲突）
let _legacyIdCounter = 0

/**
 * 为特定模块定义获取数据
 * ---------------------------------------------------------------
 * 调用后端 /api/legacy/module-rows 获取原始行数据，
 * 转换为 PublicModule 格式。
 *
 * @param def - 模块定义
 * @returns PublicModule 格式的模块数据（行数据为空时返回 null）
 */
async function fetchLegacyModule(def: LegacyModuleDef, type: number = 3): Promise<PublicModule | null> {
  const maxRetries = 2
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const payload = await backendFetchJson<BackendLegacyPayload>("/legacy/module-rows", {
        query: {
          modes_id: def.modesId,
          limit: def.limit,
          web: def.web ?? 4,
          type,
          ...def.params,
        },
      })

      const rows = payload.rows || []
      if (rows.length === 0) {
        console.warn(`[legacy-modules] 模块 "${def.title}" (modes_id=${def.modesId}, type=${type}) 无数据`)
        return null
      }

      _legacyIdCounter--
      const uniqueId = _legacyIdCounter

      return {
        id: uniqueId,
        mechanism_key: def.key,
        title: def.title,
        default_modes_id: def.modesId,
        default_table: payload.table_name || `mode_payload_${def.modesId}`,
        sort_order: 0,
        status: true,
        cssClass: def.tableClass,
        history: rows.map((row) => rowToHistoryRow(row, {
          contentTransform: def.contentTransform,
          contentColumn: def.contentColumn,
          key: def.key,
        })),
      }
    } catch (err) {
      const msg = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
      if (attempt < maxRetries) {
        // 重试前等待一段时间（指数退避）
        await new Promise(r => setTimeout(r, 200 * (attempt + 1)))
        continue
      }
      console.warn(`[legacy-modules] 获取模块失败: ${def.title} (modes_id=${def.modesId}) — ${msg}`)
      return null
    }
  }
  return null
}

// ===================== 主导出函数 =====================

/**
 * 带并发限制的批量获取函数
 * ---------------------------------------------------------------
 * 为避免 Python 后端（ThreadingHTTPServer）无法处理过多并发连接，
 * 将请求分批执行，每批最多 concurrent 个并行请求。
 */
async function batchFetch<T>(
  items: T[],
  fetcher: (item: T) => Promise<PublicModule | null>,
  concurrent = 3
): Promise<(PublicModule | null)[]> {
  const results: (PublicModule | null)[] = []
  for (let i = 0; i < items.length; i += concurrent) {
    const batch = items.slice(i, i + concurrent)
    const batchResults = await Promise.all(batch.map(fetcher))
    results.push(...batchResults)
  }
  return results
}

/**
 * 并行获取所有旧站预测模块数据
 * ---------------------------------------------------------------
 * 分批获取 36+ 个旧模块（每批 6 个并发），过滤掉空结果。
 * 在 page.tsx 中与 getPublicSitePageData() 的结果合并。
 *
 * @param excludeKeys - 需要排除的 key 列表（避免与已有模块重复）
 * @param type         - 彩种类型：1=香港彩, 2=澳门彩, 3=台湾彩（默认 3）
 * @returns PublicModule 数组
 *
 * 用法示例：
 *   const legacyModules = await fetchAllLegacyModules([], 1)  // 香港彩
 *   // 合并到 apiData.modules
 *   apiData.modules = [...apiData.modules, ...legacyModules]
 */
export async function fetchAllLegacyModules(
  excludeKeys: string[] = [],
  type: number = 3
): Promise<PublicModule[]> {
  // 过滤掉已由其他组件（如 PreResultBlocks）处理的模块
  const activeDefs = LEGACY_MODULE_DEFS.filter(
    (def) => !excludeKeys.includes(def.key.replace("legacy_", "")) &&
             !excludeKeys.includes(def.key)
  )

  // 分批获取所有模块（每批 6 个并发，避免后端过载）
  const results = await batchFetch(activeDefs, (def) => fetchLegacyModule(def, type), 6)

  // 过滤掉 null（获取失败或空数据）
  return results.filter((m): m is PublicModule => m !== null)
}

/**
 * 游戏类型 → 后端 type 参数映射
 * ---------------------------------------------------------------
 * 前端 LotteryGame 枚举值 => 后端 /api/legacy/module-rows 的 type 参数
 */
export const GAME_TYPE_MAP: Record<string, number> = {
  taiwan: 3,
  macau: 2,
  hongkong: 1,
}

/**
 * 并行获取所有 3 种彩种的旧站模块数据
 * ---------------------------------------------------------------
 * 一次性获取台湾彩(type=3)、澳门彩(type=2)、香港彩(type=1) 的旧模块数据，
 * 返回按游戏类型分组的 Record。
 * 三种彩种并行获取，每种内部按 6 并发分批。
 */
export async function fetchAllLegacyModulesByGame(): Promise<Record<string, PublicModule[]>> {
  // 顺序获取三种彩种（避免并发过多导致 Python ThreadingHTTPServer 拒绝连接）
  const taiwanMods = await fetchAllLegacyModules([], GAME_TYPE_MAP.taiwan)
  const macauMods = await fetchAllLegacyModules([], GAME_TYPE_MAP.macau)
  const hongkongMods = await fetchAllLegacyModules([], GAME_TYPE_MAP.hongkong)

  return {
    taiwan: taiwanMods,
    macau: macauMods,
    hongkong: hongkongMods,
  }
}

/**
 * 获取完整的模块定义列表（用于调试和配置）
 */
export function getLegacyModuleDefs(): LegacyModuleDef[] {
  return LEGACY_MODULE_DEFS
}
