import type { DrawHistoryItem, DrawHistoryResponse } from "./draw-history"

const TAIWAN_FULL_REVEAL_SECONDS = 150

/** Strict Beijing wall time, with calendar overflow rejected. */
export function parseTaiwanDrawTime(value: unknown): number | null {
  const match = String(value || "").trim().match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$/)
  if (!match) return null
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number)
  const wall = Date.UTC(year, month - 1, day, hour, minute, second)
  const checked = new Date(wall)
  if (checked.getUTCFullYear() !== year || checked.getUTCMonth() !== month - 1 || checked.getUTCDate() !== day || checked.getUTCHours() !== hour || checked.getUTCMinutes() !== minute || checked.getUTCSeconds() !== second) return null
  const timestamp = wall - 8 * 60 * 60 * 1000
  return timestamp > 0 ? timestamp : null
}

function validBall(ball: unknown): boolean {
  const value = String((ball as { value?: unknown } | null)?.value || "").trim()
  return /^(?:0?[1-9]|[1-4]\d)$/.test(value)
}

export function isTaiwanHistoryItemReleased(item: DrawHistoryItem, nowMs: number, delayMinutes = 0, responseYear?: number): boolean {
  const planned = parseTaiwanDrawTime(item.draw_time)
  if (planned === null || !Number.isFinite(nowMs)) return false
  const preferredText = String(item.reveal_start || "").trim()
  const preferred = preferredText ? parseTaiwanDrawTime(preferredText) : planned
  if (preferred === null) return false
  const rawIssue = String(item.issue || "").trim()
  const year = String(responseYear ?? "").trim()
  if (responseYear !== undefined && !/^\d{4}$/.test(year)) return false
  // The public history API keeps the year on the response and uses short periods.
  // A short period may borrow only that explicit year, never the device/date clock.
  const issue = /^\d{1,3}$/.test(rawIssue) && /^\d{4}$/.test(year)
    ? `${year}${rawIssue.padStart(3, "0")}` : rawIssue
  if (year && issue.slice(0, 4) !== year) return false
  if (!/^\d{7}$/.test(issue) || Number(issue.slice(4)) < 1 || Number(issue.slice(0, 4)) !== new Date(planned + 8 * 60 * 60 * 1000).getUTCFullYear()) return false
  const anchor = Math.max(planned, preferred)
  const delay = Number.isFinite(delayMinutes) ? Math.max(0, delayMinutes) * 60 * 1000 : 0
  if (nowMs < Math.max(anchor + TAIWAN_FULL_REVEAL_SECONDS * 1000, planned + delay)) return false
  return Array.isArray(item.balls) && item.balls.length === 6 && item.balls.every(validBall) && validBall(item.specialBall)
}

/** The server proxy also caps the backend clock against its own NTP-synced clock.
 * Browser consumers use only the response clock, never the device wall clock. */
export function guardTaiwanHistoryResponse(
  response: DrawHistoryResponse,
  options: { nowMs?: number; lotteryType?: 1 | 2 | 3; delayMinutes?: number } = {},
): DrawHistoryResponse {
  if ((options.lotteryType ?? response.lottery_type) !== 3) return response
  const serverSeconds = Number(response.server_now)
  const serverMs = Number(response.server_now_ms)
  const backendNow = Number.isFinite(serverSeconds) && serverSeconds > 0
    ? Number.isFinite(serverMs) && Math.floor(serverMs / 1000) === Math.floor(serverSeconds) ? serverMs : serverSeconds * 1000
    : Number.NaN
  const nowMs = options.nowMs === undefined ? backendNow : Math.min(backendNow, options.nowMs)
  const original = Array.isArray(response.items) ? response.items : []
  const items = original.filter((item) => isTaiwanHistoryItemReleased(item, nowMs, options.delayMinutes, response.year))
  const removed = original.length - items.length
  const total = Math.max(0, Number(response.total || 0) - removed)
  return {
    ...response, lottery_type: 3, server_now: Number.isFinite(nowMs) ? Math.floor(nowMs / 1000) : 0,
    server_now_ms: Number.isFinite(nowMs) ? Math.floor(nowMs) : 0,
    items, total, total_pages: Math.max(1, Math.ceil(total / Math.max(1, Number(response.page_size || 20)))),
  }
}
