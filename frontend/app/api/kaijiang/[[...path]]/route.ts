import { NextResponse } from "next/server"

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
    term: asString(row.term),
    year: asString(row.year),
    res_code: asString(row.res_code),
    res_sx: asString(row.res_sx),
    ...extra,
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
    title: asString(mapping.text_content),
  }
}

async function fetchLegacyRows(url: URL, modesId: number, limit = 10) {
  const web = url.searchParams.get("web")
  const type = url.searchParams.get("type")

  return backendFetchJson<BackendLegacyRowsPayload>("/legacy/module-rows", {
    query: {
      modes_id: modesId,
      limit,
      web: web || undefined,
      type: type || undefined,
    },
  })
}

async function fetchLegacyCurrentTerm() {
  return backendFetchJson<{ term: string; next_term: string; issue: string }>("/legacy/current-term")
}

function mapSimpleContent(rows: LegacyRow[]) {
  return rows.map((row) => baseItem(row, { content: asString(row.content) }))
}

function mapStructuredTitleRows(rows: LegacyRow[]) {
  return rows.map((row) =>
    baseItem(row, {
      title: asString(row.title),
      content: asString(row.content),
      jiexi: asString(row.jiexi),
      image_url: asString(row.image_url),
      x7m14: asString(row.x7m14),
    }),
  )
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
    }),
  )
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
    return baseItem(row, { content })
  })
}

function mapHeiBai(rows: LegacyRow[]) {
  return rows.map((row) =>
    baseItem(row, {
      hei: asString(row.hei),
      bai: asString(row.bai),
    }),
  )
}

function mapFourXiaoBaMa(rows: LegacyRow[]) {
  return rows.map((row) => {
    // 旧脚本这里不是 JSON.parse，而是直接 split(",") 后再用 "." 分隔八码。
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

function mapQinQiShuHua(rows: LegacyRow[]) {
  return rows.map((row) =>
    baseItem(row, {
      title: asString(row.title),
      content: asString(row.content),
    }),
  )
}

function mapDanShuangSiXiao(rows: LegacyRow[]) {
  return rows.map((row) => {
    const parsed = parseJsonObject(row.xiao_1) || parseJsonObject(row.xiao_2)
    const exactRow = loadExactLegacyRow(row, 31)
    const rawXiao1 = parsed?.xiao_1 || exactRow?.xiao_1 || row.xiao_1
    const rawXiao2 = parsed?.xiao_2 || exactRow?.xiao_2 || row.xiao_2

    return baseItem(row, {
      xiao_1: splitCsv(rawXiao1).join(",") || asString(rawXiao1),
      xiao_2: splitCsv(rawXiao2).join(",") || asString(rawXiao2),
    })
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
        ping: "",
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
      x7m14: asString(row.x7m14),
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
      x7m14: asString(row.x7m14),
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

function jsonResponse(data: LegacyItem[] | LegacyItem, extra: Record<string, unknown> = {}) {
  return NextResponse.json({
    data,
    ...extra,
  })
}

export async function GET(request: Request, context: { params: Promise<{ path?: string[] }> }) {
  const url = new URL(request.url)
  const params = await context.params
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
        const payload = await fetchLegacyRows(url, num === "2" ? 43 : 56, num === "2" ? 6 : 8)
        return jsonResponse(mapPingte2(payload.rows))
      }

      case "getSanqiXiao4new": {
        const payload = await fetchLegacyRows(url, 197, 8)
        return jsonResponse(mapSanqi(payload.rows))
      }

      case "sbzt": {
        const payload = await fetchLegacyRows(url, 38, 6)
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "getXiaoma": {
        const payload = await fetchLegacyRows(url, 44, 6)
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
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "ptyw": {
        const payload = await fetchLegacyRows(url, 54, 8)
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "getXmx1": {
        const payload = await fetchLegacyRows(url, 151, 10)
        return jsonResponse(mapJiuXiaoYiMa(payload.rows))
      }

      case "getTou": {
        const payload = await fetchLegacyRows(url, 12, 10)
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
        return jsonResponse(mapSimpleContent(payload.rows))
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

      case "getJuzi": {
        const payload = await fetchLegacyRows(url, num === "yqmtm" ? 68 : 62, 10)
        return jsonResponse(mapJuziRows(payload.rows, num))
      }

      case "getShaXiao": {
        const payload = await fetchLegacyRows(url, 42, 10)
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "getCode": {
        const payload = await fetchLegacyRows(url, 34, 10)
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
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "getRccx": {
        const payload = await fetchLegacyRows(url, 3, 10)
        return jsonResponse(mapRouCaiCao(payload.rows))
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

      case "jxzt": {
        const payload = await fetchLegacyRows(url, 49, 10)
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "qxbm": {
        const payload = await fetchLegacyRows(url, 44, 10)
        return jsonResponse(mapQxBm(payload.rows))
      }

      case "getPmxjcz": {
        const payload = await fetchLegacyRows(url, 331, 6)
        return jsonResponse(mapStructuredTitleRows(payload.rows))
      }

      default:
        return jsonResponse([])
    }
  } catch (error) {
    return NextResponse.json(
      {
        error: "legacy_kaijiang_failed",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
