import { NextResponse } from "next/server"

import { backendFetchJson } from "@/lib/backend-api"

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
    const xiaos = splitCsv(row.xiao).slice(0, 7)
    const codes = splitCsv(row.code).slice(0, 7)
    const content = JSON.stringify(xiaos.map((xiao, index) => `${xiao}|${codes[index] || ""}`))
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
  return rows.map((row) =>
    baseItem(row, {
      xiao_1: asString(row.xiao_1),
      xiao_2: asString(row.xiao_2),
    }),
  )
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
  return rows.map((row) =>
    baseItem(row, {
      xiao: asString(row.xiao),
      code: asString(row.code),
      ping: asString(row.ping),
    }),
  )
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
        const payload = await fetchLegacyRows(url, 246, 6)
        return jsonResponse(mapSevenXiaoQiMa(payload.rows))
      }

      case "getHbnx": {
        const payload = await fetchLegacyRows(url, 45, 6)
        return jsonResponse(mapHeiBai(payload.rows))
      }

      case "getYjzy": {
        const payload = await fetchLegacyRows(url, 50, 8)
        return jsonResponse(mapStructuredTitleRows(payload.rows))
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
        return jsonResponse(
          payload.rows.map((row) =>
            baseItem(row, {
              title: asString(row.title),
              content: asString(row.content),
            }),
          ),
        )
      }

      case "getShaXiao": {
        const payload = await fetchLegacyRows(url, 42, 10)
        return jsonResponse(mapSimpleContent(payload.rows))
      }

      case "getCode": {
        const payload = await fetchLegacyRows(url, 34, 10)
        return jsonResponse(mapSimpleContent(payload.rows))
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
        return jsonResponse(mapStructuredTitleRows(payload.rows))
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
        const payload = await fetchLegacyRows(url, 246, 10)
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
