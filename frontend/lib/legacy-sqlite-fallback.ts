/**
 * 旧站兼容兜底 — 已移除 SQLite 依赖。
 *
 * 部署环境使用 PostgreSQL 作为唯一数据源，本地 SQLite 仅用于开发调试。
 * 所有函数直接返回 null，由调用方使用 PostgreSQL 返回的原始数据。
 */

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

/** 已移除 SQLite 回退，始终返回 null */
export function loadLegacySqliteRow(
  _modesId: number,
  _lookup: LegacyRowLookup,
): LegacySqliteRow | null {
  return null
}

/** 已移除 SQLite 回退，始终返回 null */
export function loadLegacyTextMapping(
  _modesId: number,
  _lookup: LegacyTextMappingLookup,
): LegacySqliteRow | null {
  return null
}
