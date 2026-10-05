import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"



import { backendFetchJson } from "@/lib/backend-api"

import { loadLegacySqliteRow, loadLegacyTextMapping } from "@/lib/legacy-sqlite-fallback"



export const runtime = "nodejs"



type LegacyScalar = string | number | null

type LegacyItem = Record<string, LegacyScalar>

type LegacyRow = Record<string, unknown>



type BackendLegacyRowsPayload = {

  modes_id: number

  title: string

  table_name: string

  rows: LegacyRow[]

}



const LEGACY_WEB_FALLBACK_BY_TYPE: Record<number, Partial<Record<number, number>>> = {

  2: { 1: 4, 2: 4, 3: 2 },

  3: { 1: 4, 2: 4, 3: 4 },

  44: { 1: 2, 2: 2, 3: 2 },

  48: { 1: 2, 2: 2, 3: 2 },

  57: { 1: 2, 2: 2, 3: 2 },

  108: { 1: 2, 2: 2, 3: 2 },

  244: { 1: 2, 2: 2, 3: 2 },

  246: { 1: 2, 2: 2, 3: 2 },

  331: { 1: 2, 2: 2, 3: 2 },

}



function asString(value: unknown) {

  return value === null || value === undefined ? "" : String(value)

}



function splitCsv(value: unknown) {

  return asString(value)

    .split(",")

    .map((item) => item.trim())

    .filter(Boolean)

}



function parseJsonObject(value: unknown) {

  const raw = asString(value).trim()

  if (!raw || !raw.startsWith("{")) {

    return null as Record<string, unknown> | null

  }



  try {

    const parsed = JSON.parse(raw)

    return parsed && typeof parsed === "object" && !Array.isArray(parsed)

      ? (parsed as Record<string, unknown>)

      : null

  } catch {

    return null

  }

}



function parseJsonArray(value: unknown) {

  const raw = asString(value).trim()

  if (!raw) return [] as string[]



  try {

    const parsed = JSON.parse(raw)

    return Array.isArray(parsed) ? parsed.map((item) => String(item)) : []

  } catch {

    return []

  }

}



function baseItem(row: LegacyRow, extra: Record<string, LegacyScalar> = {}): LegacyItem {

  return {

    ...extra,

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    term: asString(row.term),

  }

}

function parseJsonKeyObject(value: unknown) {
  const raw = asString(value).trim()
  if (!raw || !raw.startsWith("{")) {
    return null as Record<string, unknown> | null
  }

  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null
  } catch {
    return null
  }
}



function lastCsvValue(value: unknown) {

  const items = splitCsv(value)

  return items[items.length - 1] || ""

}



function looksLikeNumberList(value: unknown, minimumCount = 1) {

  const items = splitCsv(value)

  return items.length >= minimumCount && items.every((item) => /^\d{1,2}$/.test(item))

}



function looksLikeShortZodiac(value: unknown) {

  const raw = asString(value).trim()

  return Boolean(raw) && !raw.includes(",") && !raw.includes("{") && raw.length <= 2

}



function loadExactLegacyRow(row: LegacyRow, modesId: number) {

  return loadLegacySqliteRow(modesId, {

    term: asString(row.term),

    year: asString(row.year),

    type: asString(row.type || 3),

    web: asString(row.web || row.web_id || 4),

  })

}



function parsePayloadJson(value: unknown) {

  const raw = asString(value).trim()

  if (!raw) {

    return null as Record<string, unknown> | null

  }



  try {

    const parsed = JSON.parse(raw)

    return parsed && typeof parsed === "object" && !Array.isArray(parsed)

      ? (parsed as Record<string, unknown>)

      : null

  } catch {

    return null

  }

}



function findTextMappingPayload(row: LegacyRow, modesId: number, zodiacCandidates: unknown[]) {

  const specialZodiac =

    zodiacCandidates.map((value) => asString(value).trim()).find((value) => looksLikeShortZodiac(value)) ||

    lastCsvValue(row.res_sx)

  const specialCode = lastCsvValue(row.res_code)

  const mapping = loadLegacyTextMapping(modesId, {

    specialZodiac: specialZodiac || undefined,

    specialCode: specialCode || undefined,

  })



  if (!mapping) {

    return null

  }



  const payload = parsePayloadJson(mapping.payload_json)

  return payload || {

    title: asString(mapping.title || mapping.text_content),

    content: asString(mapping.content),

    jiexi: asString(mapping.jiexi),

  }

}



async function fetchLegacyRows(url: URL, modesId: number, limit = 10) {

  const web = url.searchParams.get("web")

  const type = url.searchParams.get("type")

  const hasExplicitWeb = web !== null && web.trim() !== ""

  const requestedWeb = Number(web || "0") || undefined

  const typeNumber = Number(type || "0")



  async function fetchWithWeb(webValue: number | undefined) {

    return backendFetchJson<BackendLegacyRowsPayload>("/legacy/module-rows", {

      query: {

        modes_id: modesId,

        limit,

        web: webValue,

        type: type || undefined,

      },

    })

  }



  const primary = await fetchWithWeb(requestedWeb)

  const fallbackWeb = LEGACY_WEB_FALLBACK_BY_TYPE[modesId]?.[typeNumber]



  if (primary.rows.length > 0) {

    return primary

  }

  // Keep explicit web requests site-isolated. If a caller pins `web`,
  // returning empty data is safer than mixing rows from other sites.
  if (hasExplicitWeb) {

    return primary

  }



  if (fallbackWeb !== undefined && fallbackWeb !== requestedWeb) {

    const fallback = await fetchWithWeb(fallbackWeb)

    if (fallback.rows.length > 0) {

      return fallback

    }

  }



  // 最后兜底：不带 web 过滤查询，捕获所有 web 值下的数据

  if (requestedWeb !== undefined || fallbackWeb !== undefined) {

    const unfiltered = await fetchWithWeb(undefined)

    if (unfiltered.rows.length > 0) {

      return unfiltered

    }

  }



  return primary

}



async function fetchLegacyCurrentTerm() {

  return backendFetchJson<{ term: string; next_term: string; issue: string }>("/legacy/current-term")

}



function mapSimpleContent(rows: LegacyRow[]) {

  return rows.map((row) => baseItem(row, { content: asString(row.content) }))

}



function ensureJsonArray(value: unknown): string {

  const raw = asString(value).trim()

  if (!raw) return "[]"

  try {

    const parsed = JSON.parse(raw)

    return JSON.stringify(Array.isArray(parsed) ? parsed : [])

  } catch {

    return "[]"

  }

}



function mapStructuredTitleRows(rows: LegacyRow[]) {

  return rows.map((row) => ({

    year: asString(row.year),

    title: asString(row.title),

    content: asString(row.content),

    jiexi: asString(row.jiexi),

    image_url: asString(row.image_url),

    x7m14: ensureJsonArray(row.x7m14),

    code: asString(row.code),

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    term: asString(row.term),

  }))

}



function mapPingte2(rows: LegacyRow[]) {

  return rows.map((row) => baseItem(row, { content: asString(row.content) }))

}



function mapSanqi(rows: LegacyRow[]) {

  return rows.map((row) =>

    baseItem(row, {

      start: asString(row.start || row.term),

      end: asString(row.end || row.term),

      content: asString(row.content),

      // 窗口内已开奖各期的特肖（按期中升序，逗号分隔）；前台据此显示「中N期」
      period_zodiacs: asString(row.period_zodiacs),

    }),

  )

}



function sanqiWindowZodiacs(rows: LegacyRow[]) {

  const ordered = rows.slice().sort((left, right) => {

    const leftTerm = Number(asString(left.term).trim() || "0")

    const rightTerm = Number(asString(right.term).trim() || "0")

    return leftTerm - rightTerm

  })

  const zodiacs: string[] = []

  for (const row of ordered) {

    const list = asString(row.res_sx)

      .split(",")

      .map((value) => value.trim())

      .filter(Boolean)

    if (list.length > 0) {

      zodiacs.push(list[list.length - 1])

    }

  }

  return zodiacs.join(",")

}



// 窗口内逐期开奖（按期号升序）。供应商把三期窗口拆成「每期一行」存储
// （最新窗口只有 1 行，历史窗口 3 行），每行自带该期真实开奖；这里把整个窗口的
// 逐期结果一并带出，供 twsaimahui `023sanqibizhong.js` 逐期渲染。
// 只新增字段，不改既有 res_code/res_sx（仍是窗口内最新已开奖那一期）的语义。
function sanqiWindowPeriods(rows: LegacyRow[]) {

  const ordered = rows.slice().sort((left, right) => {

    const leftTerm = Number(asString(left.term).trim() || "0")

    const rightTerm = Number(asString(right.term).trim() || "0")

    return leftTerm - rightTerm

  })

  return ordered.map((row) => ({

    term: asString(row.term),

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

  }))

}



function filterSanqiDisplayRows(rows: LegacyRow[]) {

  const grouped = new Map<string, LegacyRow[]>()



  for (const row of rows) {

    const start = asString(row.start || row.term).trim()

    const end = asString(row.end || row.term).trim()

    const key = `${start}-${end}`

    const bucket = grouped.get(key)

    if (bucket) {

      bucket.push(row)

    } else {

      grouped.set(key, [row])

    }

  }



  const picked: LegacyRow[] = []

  for (const bucket of grouped.values()) {

    let latest: LegacyRow | null = null

    let latestDrawn: LegacyRow | null = null

    for (const row of bucket) {

      const rowTerm = Number(asString(row.term).trim() || "0")

      if (!latest || rowTerm > Number(asString(latest.term).trim() || "0")) {

        latest = row

      }

      const drawn = asString(row.res_sx)

        .split(",")

        .map((value) => value.trim())

        .filter(Boolean)

        .length > 0

      if (drawn && (!latestDrawn || rowTerm > Number(asString(latestDrawn.term).trim() || "0"))) {

        latestDrawn = row

      }

    }

    // 优先展示窗口内**已开奖**的最新一期（未开奖期没有开奖号可显示）；
    // 全部未开奖时才回退到期号最大的一行。
    const survivor = latestDrawn || latest

    if (!survivor) continue

    // 同一个三期窗口内的每一期共用同一组候选（库内已按窗口同步 content），
    // 因此这里把窗口内已开奖每一期的特肖一并带出，供前台计算「中N期」；
    // periods 是该窗口的逐期开奖明细（新增字段，只增不改）。
    picked.push({ ...survivor, period_zodiacs: sanqiWindowZodiacs(bucket), periods: sanqiWindowPeriods(bucket) })

  }



  return picked.sort((left, right) => {

    const leftTerm = Number(asString(left.term).trim() || "0")

    const rightTerm = Number(asString(right.term).trim() || "0")

    return rightTerm - leftTerm

  })

}



function mapSevenXiaoQiMa(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsedObject = parseJsonObject(row.xiao) || parseJsonObject(row.content)

    const parsedArray = parseJsonArray(row.content)

    let items: string[] = []



    if (parsedArray.length > 0) {

      items = parsedArray

    } else {

      const xiaos = splitCsv(parsedObject?.xiao || row.xiao).slice(0, 7)

      const codes = splitCsv(parsedObject?.code || row.code).slice(0, xiaos.length)

      items = xiaos.map((xiao, index) => `${xiao}|${codes[index] || ""}`)

    }



    const content = JSON.stringify(items)

    return {

      content,

      image_url: asString(row.image_url),

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

    }

  })

}

function buildTwsaimahuiXiaomaContentItems(row: LegacyRow[]) {

  return row.flatMap((item) => {

    const parsedArray = parseJsonArray(item.content)

    if (parsedArray.length > 0) {

      return parsedArray
        .map((entry) => {

          const [name, codes = ""] = String(entry).split("|")

          const normalizedCodes = codes.replace(/\./g, ",").trim()

          return name && normalizedCodes ? `${name}|${normalizedCodes}` : ""

        })
        .filter(Boolean)

    }



    const parsedObject = parseJsonObject(item.xiao) || parseJsonObject(item.content)
    const xiaos = splitCsv(parsedObject?.xiao || item.xiao)
    const codes = splitCsv(parsedObject?.code || item.code)

    if (xiaos.length > 0) {

      return xiaos.map((xiao, index) => `${xiao}|${codes[index] || ""}`).filter(Boolean)

    }



    return []

  })

}



function mapTwsaimahuiXiaomaRows(rows: LegacyRow[]) {

  return rows.map((row) => ({

    content: JSON.stringify(buildTwsaimahuiXiaomaContentItems([row])),

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    term: asString(row.term),

  }))

}



function mapHeiBai(rows: LegacyRow[]) {

  return rows.map((row) =>

    baseItem(row, {

      hei: asString(row.hei),

      bai: asString(row.bai),

    }),

  )

}



function mapHeiBaiContent(rows: LegacyRow[]) {

  return rows.map((row) => {

    const heiVal = asString(row.hei)

    const baiVal = asString(row.bai)

    return {

      content: JSON.stringify([`黑|${heiVal}`, `白|${baiVal}`]),

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

    }

  })

}



// mode 251（家野两肖 / getJyxiao2）的后端列：
//   title = `家禽|牛,马,羊,鸡,狗,猪`（**组名|组成员**）—— 这张表没有 content 列，
//   title 就是它的正文列（见 backend/src/predict/mechanisms.py 的 content_column 兼容）；
//   xiao  = 两肖（供应商原始 mode_payload_251 的 xiao 宽度恒为 2，例如 `蛇,龙`）。
// 历史实现丢掉了 title、并用 xiao 合成 `["马|","虎|",…]`（竖线后为空码），
// 于是组名丢失、同一批 6 肖被渲染两遍。这里按后端字段组装：
//   content ← `["组名|组成员"]`，xiao ← 两肖。
// 生成侧历史上曾把 title 的成员列表误当成候选标签（宽度 6），已落库的行因此带 6 肖；
// 按字段语义取前 2 项，既不修改已落库正文，也不再把 6 肖冒充两肖。
const JYXIAO2_XIAO_WIDTH = 2

function jyxiao2GroupItems(row: LegacyRow) {

  const title = asString(row.title).trim()

  if (!title.includes("|")) return [] as string[]

  const [label, values = ""] = title.split("|")

  const name = label.trim()

  if (!name) return [] as string[]

  return [`${name}|${values.trim()}`]

}

function mapJyxiao2(rows: LegacyRow[]) {

  return rows.map((row) => {

    const groupItems = jyxiao2GroupItems(row)

    const parsedArray = groupItems.length > 0 ? groupItems : parseJsonArray(row.content)

    let items: string[] = []

    if (parsedArray.length > 0) {

      items = parsedArray

    } else {

      const parsedObject = parseJsonObject(row.xiao) || parseJsonObject(row.content)

      const xiaos = splitCsv(parsedObject?.xiao || row.xiao)

      const codes = splitCsv(parsedObject?.code || row.code)

      items = xiaos.map((x, i) => `${x}|${codes[i] || ""}`)

    }

    return {

      content: JSON.stringify(items.slice(0, JYXIAO2_XIAO_WIDTH)),

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

      xiao: splitCsv(row.xiao).slice(0, JYXIAO2_XIAO_WIDTH).join(",") || asString(row.xiao),

    }

  })

}



function mapSanqiTwsaimahui(rows: LegacyRow[]) {

  return rows.map((row) => {

    const start = asString(row.start || row.term)

    const end = asString(row.end || row.term)

    return {

      content: asString(row.content),

      name: `${start}-${end}`,

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      // 新增字段（既有字段全部保留、语义不变）：窗口内逐期开奖明细，按期中升序。
      // 渲染器按它逐期显示「开:<特肖><特码> 准/错」，未开奖期 res_code/res_sx 为空串。
      periods: Array.isArray(row.periods) ? row.periods : [],

    }

  })

}



function mapX2jiam8(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsedObject = parseJsonObject(row.xiao) || parseJsonObject(row.content)

    const parsedArray = parseJsonArray(row.content)

    let xiaoVal: string

    let codeVal: string

    if (parsedArray.length > 0) {

      const xiaos: string[] = []

      const codes: string[] = []

      for (const item of parsedArray) {

        const [x = "", c = ""] = String(item).split("|")

        if (x) xiaos.push(x)

        if (c) codes.push(c)

      }

      xiaoVal = xiaos.join(",")

      codeVal = codes.join(",")

    } else {

      xiaoVal = splitCsv(parsedObject?.xiao || row.xiao).join(",")

      codeVal = splitCsv(parsedObject?.code || row.code).join(",")

    }

    return {

      code: codeVal,

      content: xiaoVal,

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

    }

  })

}



function mapYzxj(rows: LegacyRow[]) {

  return rows.map((row) => {

    const exactRow = loadExactLegacyRow(row, 295)

    const mappingPayload = findTextMappingPayload(row, 295, [row.title, row.jiexi])

    return {

      jiexi: asString(row.jiexi || exactRow?.jiexi || mappingPayload?.jiexi || ""),

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

      xiao: asString(row.xiao || exactRow?.xiao || mappingPayload?.xiao || ""),

      zi: asString(row.zi || exactRow?.zi || mappingPayload?.zi || ""),

    }

  })

}



function mapNnnx(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsedObject = parseJsonKeyObject(row.content) || parseJsonKeyObject(row.xiao) || parseJsonKeyObject(row.nan)

    const parsedArray = parseJsonArray(row.content)

    let nan = asString(row.nan).trim()

    let nv = asString(row.nv).trim()

    if (parsedObject) {

      nan = nan || asString(parsedObject.nan || parsedObject.nanx || parsedObject.nan_sx || parsedObject.xiao_1)

      nv = nv || asString(parsedObject.nv || parsedObject.nvx || parsedObject.nv_sx || parsedObject.xiao_2)

    }

    if ((!nan || !nv) && parsedArray.length >= 2) {

      nan = nan || parsedArray[0]

      nv = nv || parsedArray[1]

    }

    return {

      nan,

      nv,

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

    }

  })

}



function mapFourXiaoBaMa(rows: LegacyRow[]) {

  return rows.map((row) => {

    // twsaimahui 的四肖八码脚本会直接 JSON.parse(content)，
    // 但每组号码内部仍用 "." 分隔，因此这里保留旧点分格式并包装成 JSON 字符串。

    const items = parseJsonArray(row.content).map((item) => {

      const [name, codes = ""] = item.split("|")

      return `${name}|${codes.replace(/,/g, ".")}`

    })



    return baseItem(row, {

      content: items.join(","),

    })

  })

}



function mapJiuXiaoYiMa(rows: LegacyRow[]) {

  return rows.map((row) => baseItem(row, { content: asString(row.content) }))

}



function mapJiuXiaoYiMaDetailed(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsedObject = parseJsonKeyObject(row.content) || parseJsonKeyObject(row.xiao) || parseJsonKeyObject(row.code)

    const parsedArray = parseJsonArray(row.content)

    let code = asString(row.code).trim()

    let xiao = asString(row.xiao).trim()

    if (parsedObject) {

      code = code || asString(parsedObject.code || parsedObject.codes || parsedObject.code_list)

      xiao = xiao || asString(parsedObject.xiao || parsedObject.sx || parsedObject.zodiac)

    }

    if (parsedArray.length > 0) {

      const xiaoValues: string[] = []

      const codeValues: string[] = []

      for (const item of parsedArray) {

        const [name = "", codes = ""] = String(item).split("|", 2)

        const normalizedCodes = codes.replace(/\./g, ",").trim()

        if (name) xiaoValues.push(name)

        if (normalizedCodes) codeValues.push(normalizedCodes)

      }

      xiao = xiao || xiaoValues.join(",")

      code = code || codeValues.join(",")

    }

    return {

      code,

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

      xiao,

    }

  })

}



function mapQinQiShuHua(rows: LegacyRow[]) {

  return rows.map((row) => ({

    content: asString(row.content),

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    term: asString(row.term),

    title: asString(row.title),

  }))

}



function mapDanShuangSiXiao(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsed = parseJsonObject(row.xiao_1) || parseJsonObject(row.xiao_2)

    const exactRow = loadExactLegacyRow(row, 31)

    const rawXiao1 = parsed?.xiao_1 || exactRow?.xiao_1 || row.xiao_1

    const rawXiao2 = parsed?.xiao_2 || exactRow?.xiao_2 || row.xiao_2



    return {

      res_code: asString(row.res_code),

      res_sx: asString(row.res_sx),

      term: asString(row.term),

      xiao_1: splitCsv(rawXiao1).join(",") || asString(rawXiao1),

      xiao_2: splitCsv(rawXiao2).join(",") || asString(rawXiao2),

    }

  })

}



function mapDaXiaoDaiTou(rows: LegacyRow[]) {

  return rows.map((row) =>

    baseItem(row, {

      content: asString(row.content),

      tou: asString(row.tou),

    }),

  )

}



function mapRouCaiCao(rows: LegacyRow[]) {

  return rows.map((row) => baseItem(row, { content: asString(row.content) }))

}



function mapDanShuangSiWei(rows: LegacyRow[]) {

  return rows.map((row) => ({

    dan: asString(row.dan),

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    shuang: asString(row.shuang),

    term: asString(row.term),

  }))

}



/**
 * 固定分组（`public.fixed_data`）的只读读取结果。
 *
 * 合数单双（mode 132 / `getHeds`）的正文只有 `合单` / `合双` 这种**纯标签**，
 * 渲染层必须把它们展开成号码集合，才能按「特码是否在集合内」判定命中。
 * 号码表一律来自后端 `public.fixed_data`（`predict.common.load_fixed_data_groups`），
 * 前端不得硬编码。
 */
type FixedDataGroupsPayload = {
  sign: string
  groups: { label: string; codes: string[] }[]
}

const FIXED_DATA_GROUPS_TTL_MS = 60_000

const fixedDataGroupsCache = new Map<string, { expiresAt: number; payload: Promise<FixedDataGroupsPayload> }>()

function loadFixedDataGroups(sign: string): Promise<FixedDataGroupsPayload> {
  const key = sign.trim()
  const now = Date.now()
  const cached = fixedDataGroupsCache.get(key)
  if (cached && cached.expiresAt > now) {
    return cached.payload
  }
  const payload = backendFetchJson<FixedDataGroupsPayload>("/public/fixed-data-groups", {
    query: { sign: key },
  }).catch(() => ({ sign: key, groups: [] }) as FixedDataGroupsPayload)
  fixedDataGroupsCache.set(key, { expiresAt: now + FIXED_DATA_GROUPS_TTL_MS, payload })
  return payload
}

/**
 * 把 label -> 号码集合 的映射代码化成 `标签|号码列表`。
 *
 * 渲染层与 `parseJsonArray` 已按 `标签|值` 结构约定解析，因此这里沿用既有正文形态，
 * 不新增响应字段；找不到该标签的号码集合时保留原始标签，交由渲染层按「无可判定候选」
 * 处理（绝不退化成子串匹配）。
 */
function expandContentWithFixedGroups(
  content: string,
  codesByLabel: Map<string, string[]>,
): string {
  const raw = asString(content).trim()
  if (!raw) return raw
  const items = parseJsonArray(raw)
  const entries = items.length > 0 ? items : [raw]
  const expanded = entries.map((entry) => {
    const text = String(entry || "").trim()
    if (!text) return text
    if (text.includes("|")) return text
    const codes = codesByLabel.get(text)
    if (!codes || codes.length === 0) return text
    return `${text}|${codes.join(",")}`
  })
  return JSON.stringify(expanded)
}

function mapJsonContentRows(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsedArray = parseJsonArray(row.content)

    return baseItem(row, {

      content: parsedArray.length > 0 ? JSON.stringify(parsedArray) : asString(row.content),

    })

  })

}

/**
 * 合数单双（mode 132）：把 `合单` / `合双` 纯标签展开成 `标签|号码集合`。
 *
 * 判定口径与后端 `predict.categories.size_parity.special_combined_parity_from_row`
 * 一致（特码十位 + 个位之和的奇偶），号码表来自 `public.fixed_data` sign `合单双`。
 */
function mapCombinedParityRows(rows: LegacyRow[], codesByLabel: Map<string, string[]>) {

  return rows.map((row) => {

    const parsedArray = parseJsonArray(row.content)

    const rawContent = parsedArray.length > 0 ? JSON.stringify(parsedArray) : asString(row.content)

    return baseItem(row, {

      content: expandContentWithFixedGroups(rawContent, codesByLabel),

    })

  })

}



function mapJiMeiXiongChou(rows: LegacyRow[]) {

  const attach = [
    { code: "牛,狗,猪,猴,虎,鼠", label: "凶丑肖" },
    { code: "兔,羊,蛇,马,鸡,龙", label: "吉美肖" },
  ]

  return {
    data: rows.map((row) => {
      const parsedArray = parseJsonArray(row.content)
      return baseItem(row, {
        content: parsedArray.length > 0 ? JSON.stringify(parsedArray) : asString(row.content),
      })
    }),
    attach,
  }

}

function mapTitleOnlyRows(rows: LegacyRow[]) {

  return rows.map((row) => ({

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    term: asString(row.term),

    title: asString(row.title),

  }))

}

function mapDanShuangTeZhong(rows: LegacyRow[]) {

  return rows.map((row) => ({

    content: asString(row.content),

    res_code: asString(row.res_code),

    res_sx: asString(row.res_sx),

    term: asString(row.term),

    xiao: asString(row.xiao),

  }))

}



function mapOnePhrase(rows: LegacyRow[]) {

  return rows.map((row) => baseItem(row, { content: asString(row.content) }))

}



function mapQxBm(rows: LegacyRow[]) {

  return rows.map((row) => {

    const parsed = parseJsonObject(row.xiao) || parseJsonObject(row.content)

    const parsedArray = parseJsonArray(row.content)

    if (parsedArray.length > 0) {

      const xiaoValues: string[] = []

      const codeValues: string[] = []

      for (const item of parsedArray) {

        const [xiao = "", code = ""] = String(item).split("|")

        if (xiao) xiaoValues.push(xiao)

        if (code) codeValues.push(code)

      }

      return baseItem(row, {

        xiao: xiaoValues.join(","),

        code: codeValues.join(","),

        ping: asString(row.ping),

      })

    }



    return baseItem(row, {

      xiao: splitCsv(parsed?.xiao || row.xiao).join(","),

      code: splitCsv(parsed?.code || row.code).join(","),

      ping: asString(parsed?.ping || row.ping),

    })

  })

}



function mapYiJuZhenYan(rows: LegacyRow[]) {

  return rows.map((row) => {

    const exactRow = loadExactLegacyRow(row, 50)

    const currentTitle = asString(row.title)

    const currentContent = asString(row.content)

    const currentJiexi = asString(row.jiexi)

    const hasMeaningfulCurrentText = currentTitle.length >= 4 && currentContent.length >= 4 && currentJiexi.length >= 4

    const mappingPayload = findTextMappingPayload(row, 50, [row.content, row.title, row.jiexi])



    return baseItem(row, {

      title: hasMeaningfulCurrentText

        ? currentTitle

        : asString(exactRow?.title || mappingPayload?.title || currentTitle),

      content: hasMeaningfulCurrentText

        ? currentContent

        : asString(exactRow?.content || mappingPayload?.content || currentContent),

      jiexi: hasMeaningfulCurrentText

        ? currentJiexi

        : asString(exactRow?.jiexi || mappingPayload?.jiexi || currentJiexi),

      image_url: asString(row.image_url),

      x7m14: ensureJsonArray(row.x7m14),

    })

  })

}



function mapSiZiXuanJi(rows: LegacyRow[]) {

  return rows.map((row) => {

    const exactRow = loadExactLegacyRow(row, 52)

    const currentTitle = asString(row.title)

    const currentJiexi = asString(row.jiexi)

    const hasMeaningfulCurrentText = currentTitle.length >= 4 && currentJiexi.length >= 4

    const mappingPayload = findTextMappingPayload(row, 52, [row.title, row.jiexi])



    return baseItem(row, {

      title: hasMeaningfulCurrentText

        ? currentTitle

        : asString(exactRow?.title || mappingPayload?.title || currentTitle),

      content: asString(row.content),

      jiexi: hasMeaningfulCurrentText

        ? currentJiexi

        : asString(exactRow?.jiexi || mappingPayload?.jiexi || currentJiexi),

      image_url: asString(row.image_url),

      x7m14: ensureJsonArray(row.x7m14),

    })

  })

}



function mapJuziRows(rows: LegacyRow[], num: string) {

  const modesId = num === "yqmtm" ? 68 : 62



  return rows.map((row) => {

    const exactRow = loadExactLegacyRow(row, modesId)

    const titleObject = parseJsonObject(row.title)

    const mappingPayload = findTextMappingPayload(row, modesId, [row.title, row.content, lastCsvValue(row.res_sx)])



    if (num === "yqmtm") {

      const currentTitle = asString(row.title)

      const exactTitle = asString(exactRow?.title)

      const mappedTitle = asString(mappingPayload?.title)

      const resolvedTitle =

        splitCsv(currentTitle).length >= 4

          ? currentTitle

          : splitCsv(exactTitle).length >= 4

            ? exactTitle

            : mappedTitle



      return baseItem(row, {

        title: resolvedTitle || currentTitle,

        content: asString(row.content),

      })

    }



    const currentTitle = asString(titleObject?.title || row.title)

    const exactTitle = asString(exactRow?.title)

    const mappedTitle = asString(mappingPayload?.title)



    return baseItem(row, {

      title:

        currentTitle.length >= 4

          ? currentTitle

          : exactTitle.length >= 4

            ? exactTitle

            : mappedTitle || currentTitle,

      content: asString(row.content),

    })

  })

}



function mapClassic24Codes(rows: LegacyRow[]) {

  return rows.map((row) => {

    const currentContent = asString(row.content)

    const exactRow = loadExactLegacyRow(row, 34)

    const mappingPayload = findTextMappingPayload(row, 34, [])

    const exactContent = asString(exactRow?.content)

    const mappedContent = asString(mappingPayload?.content || mappingPayload?.title)



    const resolvedContent = looksLikeNumberList(currentContent, 24)

      ? currentContent

      : looksLikeNumberList(exactContent, 24)

        ? exactContent

        : looksLikeNumberList(mappedContent, 24)

          ? mappedContent

          : currentContent



    return baseItem(row, { content: resolvedContent })

  })

}



function mapLiuBuZhong(rows: LegacyRow[]) {

  return rows
    .filter((row) => asString(row.u6_code).trim().length > 0)
    .map((row) =>

      baseItem(row, {

        u6_code: asString(row.u6_code),

      }),

    )

}



function jsonResponse(data: LegacyItem[] | LegacyItem, extra: Record<string, unknown> = {}) {
  return jsonWithCors({

    data,

    ...extra,

  })

}

async function proxyUnknownKaijiangEndpoint(url: URL, endpoint: string) {

  const query: Record<string, string> = {}

  for (const [key, value] of url.searchParams.entries()) {

    query[key] = value

  }

  return backendFetchJson<{ data: LegacyItem[] | LegacyItem }>(`/kaijiang/${endpoint}`, {

    query,

  })

}



export async function GET(request: Request, context: { params: Promise<{ path?: string[] }> }) {
  const url = new URL(request.url)

  const params = await context.params

  const joinedPath = params.path?.join("/") ?? ""

  const endpoint = params.path?.[0] ?? ""

  const num = url.searchParams.get("num") || ""



  try {

    switch (endpoint) {

      case "curTerm": {

        const payload = await fetchLegacyCurrentTerm()

        return jsonResponse({

          term: payload.term,

          next_term: payload.next_term,

          issue: payload.issue,

        })

      }



      case "getPingte": {

        const payload = await fetchLegacyRows(
          url,
          num === "3" ? 470 : num === "2" ? 43 : 56,
          num === "2" ? 6 : 8,
        )

        return jsonResponse(mapPingte2(payload.rows))

      }



      case "getSanqiXiao4new": {

        const requestedWeb = Number(url.searchParams.get("web") || "0")

        // mode 197 按「每期一行」存储：最新窗口只有 1 行（其余期未生成），历史窗口 3 行。
        // twsaimahui 的三期必中要逐期渲染窗口内 3 期，必须把每个窗口的 3 行都取全，
        // limit=10 恰好覆盖 4 个完整窗口（1 + 3 + 3 + 3）；其它站点保持原来的 8 行不变。
        const payload = await fetchLegacyRows(url, 197, requestedWeb === 6 ? 10 : 8)

        const filteredRows = filterSanqiDisplayRows(payload.rows)

        if (requestedWeb === 6) {

          return jsonResponse(mapSanqiTwsaimahui(filteredRows) as unknown as LegacyItem[])

        }

        return jsonResponse(mapSanqi(filteredRows))

      }



      case "sbzt": {

        const payload = await fetchLegacyRows(url, 38, 6)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getDsWei": {

        const payload = await fetchLegacyRows(url, 30, 10)

        return jsonResponse(mapDanShuangSiWei(payload.rows))

      }



      case "getXiaoma":
      case "getXiaoma2":
      case "getXiaoMa2": {

        const requestedWeb = Number(url.searchParams.get("web") || "0")
        const isTwsaimahuiWeb = requestedWeb === 6

        if (num === "4") {

          const payload = await fetchLegacyRows(url, 51, 6)

          if (isTwsaimahuiWeb) {

            return jsonResponse(mapTwsaimahuiXiaomaRows(payload.rows))

          }

          return jsonResponse(mapFourXiaoBaMa(payload.rows))

        }

        if (num === "7") {

          const payload = await fetchLegacyRows(url, 22, 6)

          return jsonResponse(mapSevenXiaoQiMa(payload.rows))

        }

        const payload = await fetchLegacyRows(url, 27, 6)

        if (isTwsaimahuiWeb) {

          return jsonResponse(mapTwsaimahuiXiaomaRows(payload.rows))

        }

        return jsonResponse(mapSevenXiaoQiMa(payload.rows))

      }



      case "getHbnx": {

        const payload = await fetchLegacyRows(url, 45, 6)

        return jsonResponse(mapHeiBai(payload.rows))

      }



      case "getYjzy": {

        const payload = await fetchLegacyRows(url, 50, 8)

        return jsonResponse(mapYiJuZhenYan(payload.rows))

      }



      case "lxzt": {

        const payload = await fetchLegacyRows(url, 46, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getHllx": {

        const payload = await fetchLegacyRows(url, 8, 8)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getDxzt": {

        const payload = await fetchLegacyRows(url, 57, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getDxztt1": {

        const payload = await fetchLegacyRows(url, 108, 10)

        return jsonResponse(mapDaXiaoDaiTou(payload.rows))

      }



      case "getJyzt": {

        const payload = await fetchLegacyRows(url, 63, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "ptyw": {

        const payload = await fetchLegacyRows(url, 54, 8)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getXmx1": {

        const payload = await fetchLegacyRows(url, 151, 10)

        return jsonResponse(mapJiuXiaoYiMa(payload.rows))

      }



      case "getXysxma": {

        const payload = await fetchLegacyRows(url, 151, 10)

        return jsonResponse(mapJiuXiaoYiMaDetailed(payload.rows))

      }



      case "getTou": {

        const payload = await fetchLegacyRows(url, num === "2" ? 471 : 12, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getXingte": {

        const payload = await fetchLegacyRows(url, 53, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "sxbm": {

        const payload = await fetchLegacyRows(url, 51, 10)

        return jsonResponse(mapFourXiaoBaMa(payload.rows))

      }



      case "danshuang": {

        const payload = await fetchLegacyRows(url, 28, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "dssx":

      case "getDsnx": {

        const payload = await fetchLegacyRows(url, 31, 10)

        return jsonResponse(mapDanShuangSiXiao(payload.rows))

      }



      case "getCodeDuan": {

        const payload = await fetchLegacyRows(url, 65, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getCyptwei": {

        const payload = await fetchLegacyRows(url, 336, 10)

        return jsonResponse(mapTitleOnlyRows(payload.rows))

      }



      case "getJyxiao2": {

        const payload = await fetchLegacyRows(url, 251, 10)

        return jsonResponse(mapJyxiao2(payload.rows))

      }



      case "getZyx": {

        const payload = await fetchLegacyRows(url, 152, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getYysx": {

        const payload = await fetchLegacyRows(url, 141, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getDsxiao": {

        const payload = await fetchLegacyRows(url, 15, 10)

        return jsonResponse(mapDanShuangTeZhong(payload.rows))

      }



      case "getYbzt": {

        const payload = await fetchLegacyRows(url, 143, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getYzxj": {

        const payload = await fetchLegacyRows(url, 295, 10)

        return jsonResponse(mapYzxj(payload.rows))

      }



      case "getNnnx": {

        const payload = await fetchLegacyRows(url, 24, 10)

        return jsonResponse(mapNnnx(payload.rows))

      }



      case "getWeima2": {

        const payload = await fetchLegacyRows(url, 123, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getWwx": {

        const payload = await fetchLegacyRows(url, 144, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getYwx": {

        const payload = await fetchLegacyRows(url, 147, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getBmzy": {

        const payload = await fetchLegacyRows(url, 149, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getX2jiam8": {

        const payload = await fetchLegacyRows(url, 145, 10)

        return jsonResponse(mapX2jiam8(payload.rows))

      }



      case "getJuzi": {

        const payload = await fetchLegacyRows(url, num === "yqmtm" ? 68 : 62, 10)

        return jsonResponse(mapJuziRows(payload.rows, num))

      }



      case "getShaXiao": {

        const payload = await fetchLegacyRows(
          url,
          num === "1" ? 472 : num === "2" ? 473 : 42,
          10,
        )

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getCode": {

        const payload = await fetchLegacyRows(
          url,
          num === "10" ? 116 : num === "16" ? 9 : num === "20" ? 146 : 34,
          10,
        )

        return jsonResponse(mapClassic24Codes(payload.rows))

      }



      case "qqsh": {

        const payload = await fetchLegacyRows(url, 26, 10)

        return jsonResponse(mapQinQiShuHua(payload.rows))

      }



      case "getShaBanbo": {

        const payload = await fetchLegacyRows(url, 58, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getShaWei": {

        const payload = await fetchLegacyRows(url, 20, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getSzxj": {

        const payload = await fetchLegacyRows(url, 52, 10)

        return jsonResponse(mapSiZiXuanJi(payload.rows))

      }



      case "getDjym": {

        const payload = await fetchLegacyRows(url, 59, 10)

        return jsonResponse(mapStructuredTitleRows(payload.rows))

      }



      case "getSjsx": {

        const payload = await fetchLegacyRows(url, 61, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getRccx": {

        const payload = await fetchLegacyRows(url, 3, 10)

        return jsonResponse(mapJsonContentRows(mapRouCaiCao(payload.rows) as unknown as LegacyRow[]))

      }



      case "yyptj": {

        const payload = await fetchLegacyRows(url, 244, 10)

        return jsonResponse(mapOnePhrase(payload.rows))

      }



      case "wxzt": {

        const payload = await fetchLegacyRows(url, 48, 6)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getWei": {

        const payload = await fetchLegacyRows(url, 2, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getShama": {

        const payload = await fetchLegacyRows(url, 88, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "jxzt": {

        const payload = await fetchLegacyRows(url, 49, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      case "getShatou": {

        const payload = await fetchLegacyRows(url, 41, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "qxbm": {

        const payload = await fetchLegacyRows(url, 246, 10)

        return jsonResponse(mapQxBm(payload.rows))

      }



      case "getPmxjcz": {

        const payload = await fetchLegacyRows(url, 331, 6)

        return jsonResponse(mapStructuredTitleRows(payload.rows))

      }



      case "rd70i73lziizczak": {

        if (joinedPath === "rd70i73lziizczak/0gmqnw/1") {

          const payload = await fetchLegacyRows(url, 333, 10)

          return jsonResponse(mapLiuBuZhong(payload.rows))

        }

        const payload = await proxyUnknownKaijiangEndpoint(url, joinedPath)

        return jsonWithCors(payload)

      }



      // ── 路径别名：前端调用名与已注册 case 名不同 ─────────────────

      case "getHbx": {

        const payload = await fetchLegacyRows(url, 45, 6)

        return jsonResponse(mapHeiBaiContent(payload.rows))

      }



      // ── 中特系列：根据 num 映射到不同 modes_id ─────────────

      case "getTdsx1": {

        const payload = await fetchLegacyRows(url, 5, 10)

        // 天地生肖（mode 5）：每期 `content` 只记录**本期选中的那一组**
        // （判定口径就是「特肖是否落在该组」，因此不能把另一组也塞进 content——
        // 那会让渲染层的 `zj` 恒为真、判定恒「准」）。面板头部需要完整的
        // 天肖/地肖分类，这里把 `fixed_data` sign=天地生肖 的分组作为附加字段下发，
        // 渲染层据此补齐头部；`data` 既有形状与判定口径保持不变。
        const fixedGroups = await loadFixedDataGroups("天地生肖")

        const groups = (fixedGroups.groups || [])
          .map((group) => ({
            label: asString(group.label).trim(),
            codes: (group.codes || []).map((code) => asString(code).trim()).filter(Boolean),
          }))
          .filter((group) => group.label && group.codes.length > 0)

        return jsonResponse(mapJsonContentRows(payload.rows), groups.length > 0 ? { groups } : {})

      }



      case "getHeds": {

        const payload = await fetchLegacyRows(url, 132, 10)

        // mode 132 正文只有 `合单` / `合双` 标签。渲染层必须拿到号码集合才能按集合
        // 语义判定，否则会退化成「拿空串去 indexOf」→ 每期都显示「不中」。
        const fixedGroups = await loadFixedDataGroups("合单双")

        const codesByLabel = new Map<string, string[]>(
          fixedGroups.groups.map((group) => [String(group.label || "").trim(), group.codes || []]),
        )

        return jsonResponse(mapCombinedParityRows(payload.rows, codesByLabel))

      }



      case "getFyld": {

        const payload = await fetchLegacyRows(url, 10, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getCypt": {

        const payload = await fetchLegacyRows(url, 39, 10)

        return jsonResponse(mapTitleOnlyRows(payload.rows))

      }



      case "getJmxc": {

        const payload = await fetchLegacyRows(url, 155, 10)

        // 返回 { data, attach }：前台用 attach 渲染「吉美生肖 / 凶丑生肖」两行分组说明，
        // 只返回 data 会让说明行留空。
        return jsonResponse(mapJiMeiXiongChou(payload.rows))

      }



      case "getFsx": {

        const payload = await fetchLegacyRows(url, 157, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getDxd": {

        const payload = await fetchLegacyRows(url, 158, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getShaBds": {

        const payload = await fetchLegacyRows(url, 159, 10)

        return jsonResponse(mapJsonContentRows(payload.rows))

      }



      case "getZhongte": {

        const modesId = num === "9" ? 49

                      : num === "6" ? 46

                      : num === "5" ? 48

                      : num === "4" ? 47

                      : num === "3" ? 69

                      : 46

        const payload = await fetchLegacyRows(url, modesId, 10)

        return jsonResponse(mapSimpleContent(payload.rows))

      }



      // ── 兜底：未显式处理的端点 ───────────────────────────────

      // 所有 35 个已知 modes_id 已由显式 case 覆盖。

      // 以下端点对应的 modes_id 在数据库中可能不存在，

      // 需要后续创建对应的 mode_payload 表后再添加显式 case。

      //

      // 未映射端点列表 (modes_id 待确定):

      //   getJyxiao2, getZyx, getYysx, getDsWei, getHeds,

      //   getTdsx1, getCyptwei, getDsxiao, getYbzt, getWeima2,

      //   getWwx, getYwx, getBmzy, getX2jiam8, getPtWei,

      //   getShama, getFyld, getYzxj, getCypt, getNnnx,

      //   getXysxma, getShatou, getJmxc, getFsx, getDxd,

      //   getShaBds, rd70i73lziizczak

      //

      // 注意：不代理到 Python /api/kaijiang/* 兜底，

      // 因为 frontend_compat.py 使用 num 作为 modes_id，

      // 可能返回不相关模块的错误数据（如 num=2 会匹配 modes_id=2/六尾中特）。

      default: {

        console.warn(`[kaijiang] unknown endpoint: ${endpoint} (num=${num}) — returning empty, modes_id mapping needed`)

        const payload = await proxyUnknownKaijiangEndpoint(url, joinedPath || endpoint)

        return jsonWithCors(payload)
      }

    }

  } catch (error) {

    return jsonWithCors(

      {

        error: "legacy_kaijiang_failed",

        detail: error instanceof Error ? error.message : String(error),

      },

      { status: 500 },

    )

  }

}

export function OPTIONS() {
  return buildOptionsResponse()
}

