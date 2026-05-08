import fs from "node:fs"
import path from "node:path"
import { DatabaseSync } from "node:sqlite"

export type LegacySqliteScalar = string | number | null
export type LegacySqliteRow = Record<string, LegacySqliteScalar>

type LegacyRowLookup = {
  term?: string
  year?: string
  type?: string
  web?: string
}

type LegacyTextMappingLookup = {
  specialCode?: string
  specialZodiac?: string
}

let cachedDatabase: DatabaseSync | null | undefined

function resolveDatabasePath() {
  // Next.js 开发时 cwd 通常是 frontend/；为了避免部署或脚本环境差异，这里同时兼容仓库根目录。
  const candidates = [
    path.resolve(process.cwd(), "../backend/data/lottery_modes.sqlite3"),
    path.resolve(process.cwd(), "backend/data/lottery_modes.sqlite3"),
  ]

  return candidates.find((candidate) => fs.existsSync(candidate)) || null
}

function getDatabase() {
  if (cachedDatabase !== undefined) {
    return cachedDatabase
  }

  const databasePath = resolveDatabasePath()
  if (!databasePath) {
    cachedDatabase = null
    return cachedDatabase
  }

  cachedDatabase = new DatabaseSync(databasePath, { readOnly: true })
  return cachedDatabase
}

function normalizeDatabaseRow(value: unknown) {
  if (!value || typeof value !== "object") {
    return null
  }

  const normalized: LegacySqliteRow = {}
  for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
    if (entry === null || typeof entry === "string" || typeof entry === "number") {
      normalized[key] = entry
      continue
    }
    if (typeof entry === "bigint") {
      normalized[key] = Number(entry)
      continue
    }
    normalized[key] = String(entry)
  }

  return normalized
}

function tableExists(tableName: string) {
  const database = getDatabase()
  if (!database) {
    return false
  }

  try {
    const row = database
      .prepare("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1")
      .get(tableName)
    return Boolean(row)
  } catch {
    return false
  }
}

export function loadLegacySqliteRow(modesId: number, lookup: LegacyRowLookup) {
  const database = getDatabase()
  if (!database || !lookup.term) {
    return null
  }

  const tableName = `mode_payload_${Math.trunc(modesId)}`
  if (!tableExists(tableName)) {
    return null
  }

  try {
    const webValue = lookup.web || "4"
    const typeValue = lookup.type || "3"
    const params: Array<string> = [lookup.term, webValue, typeValue]
    let whereClause = "term = ? AND CAST(web AS TEXT) = ? AND CAST(type AS TEXT) = ?"

    // 同一期号在不同年份理论上可能重复；如果前端已知 year，则优先精确匹配。
    if (lookup.year) {
      whereClause += " AND CAST(year AS TEXT) = ?"
      params.push(lookup.year)
    }

    const row = database
      .prepare(
        `SELECT *
         FROM "${tableName}"
         WHERE ${whereClause}
         ORDER BY CAST(COALESCE(year, '0') AS INTEGER) DESC, CAST(COALESCE(term, '0') AS INTEGER) DESC
         LIMIT 1`,
      )
      .get(...params)

    return normalizeDatabaseRow(row)
  } catch {
    return null
  }
}

export function loadLegacyTextMapping(modesId: number, lookup: LegacyTextMappingLookup) {
  const database = getDatabase()
  if (!database || !tableExists("text_history_mappings")) {
    return null
  }

  try {
    if (lookup.specialZodiac) {
      const row = database
        .prepare(
          `SELECT *
           FROM text_history_mappings
           WHERE modes_id = ?
             AND special_zodiac = ?
           ORDER BY COALESCE(last_year, 0) DESC, COALESCE(last_term, 0) DESC, occurrence_count DESC
           LIMIT 1`,
        )
        .get(Math.trunc(modesId), lookup.specialZodiac)

      const normalized = normalizeDatabaseRow(row)
      if (normalized) {
        return normalized
      }
    }

    if (lookup.specialCode) {
      const row = database
        .prepare(
          `SELECT *
           FROM text_history_mappings
           WHERE modes_id = ?
             AND special_code = ?
           ORDER BY COALESCE(last_year, 0) DESC, COALESCE(last_term, 0) DESC, occurrence_count DESC
           LIMIT 1`,
        )
        .get(Math.trunc(modesId), lookup.specialCode)

      return normalizeDatabaseRow(row)
    }
  } catch {
    return null
  }

  return null
}
