export type SiteDrawSource = {
  current_issue?: string | number | null
  draw_time?: string | null
  // 服务端分片揭示字段（backend/src/public/draw_reveal.py）：
  // 号码按 reveal_start + 25s×N 逐球开放，前端据 revealed_count/is_complete 决定是否继续轮询。
  reveal_start?: string | null
  result_balls?: SiteDrawBallSource[]
  special_ball?: SiteDrawBallSource | null
  revealed_count?: number | null
  total_balls?: number | null
  reveal_interval_seconds?: number | null
  is_complete?: boolean | null
  next_reveal_at?: string | null
  server_now?: number | null
  server_now_ms?: number | null
}

export type SiteDrawBallSource = {
  value?: string | number | null
  color?: string | null
  zodiac?: string | null
  element?: string | null
}

export type SiteDrawDeadlineSource = {
  current_issue?: string | number | null
  current_draw_time?: number | null
  server_now?: number | null
  server_now_ms?: number | null
  next_issue?: string | number | null
  next_time?: string | number | null
}

export type NormalizedSiteDraw = {
  current_issue: string
  opened_at: string | null
  reveal_start: string | null
  revealed_count: number | null
  total_balls: number
  reveal_interval_seconds: number
  is_complete: boolean
  next_reveal_at: string | null
  next_issue: string | null
  next_draw_at: string | number | null
  balls: Array<{
    value: string
    color: "red" | "blue" | "green"
    zodiac: string
    element: string | null
    is_special: boolean
  }>
}

function normalizeZodiac(value: unknown) {
  return String(value || "")
    .trim()
    .replaceAll("龍", "龙")
    .replaceAll("馬", "马")
    .replaceAll("雞", "鸡")
    .replaceAll("豬", "猪")
}

function normalizeColor(value: unknown): "red" | "blue" | "green" {
  const normalized = String(value || "").trim().toLowerCase()
  if (normalized === "blue" || normalized === "蓝" || normalized === "蓝波") return "blue"
  if (normalized === "green" || normalized === "绿" || normalized === "绿波") return "green"
  return "red"
}

function normalizeBall(ball: SiteDrawBallSource, isSpecial: boolean) {
  const rawValue = String(ball.value || "").trim()
  const numericValue = Number(rawValue)
  return {
    value: Number.isInteger(numericValue) && numericValue >= 0 && numericValue < 100
      ? String(numericValue).padStart(2, "0")
      : rawValue,
    color: normalizeColor(ball.color),
    zodiac: normalizeZodiac(ball.zodiac),
    element: ball.element ? String(ball.element).trim() : null,
    is_special: isSpecial,
  }
}

function normalizeCount(value: unknown): number | null {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.floor(parsed)
}

export function normalizeSiteDraw(
  latest: SiteDrawSource,
  deadline: SiteDrawDeadlineSource
): NormalizedSiteDraw {
  const balls = [
    ...(latest.result_balls || []).map((ball) => normalizeBall(ball, false)),
    ...(latest.special_ball ? [normalizeBall(latest.special_ball, true)] : []),
  ]
  const totalBalls = normalizeCount(latest.total_balls) ?? 7
  const revealedCount = normalizeCount(latest.revealed_count)
  const isComplete = typeof latest.is_complete === "boolean"
    ? latest.is_complete
    : revealedCount !== null
      ? revealedCount >= totalBalls
      : balls.length >= totalBalls
  return {
    current_issue: String(latest.current_issue || "").trim(),
    opened_at: latest.draw_time || null,
    reveal_start: latest.reveal_start || latest.draw_time || null,
    revealed_count: revealedCount,
    total_balls: totalBalls,
    reveal_interval_seconds: normalizeCount(latest.reveal_interval_seconds) ?? 25,
    is_complete: isComplete,
    next_reveal_at: latest.next_reveal_at || null,
    next_issue: deadline.next_issue == null ? null : String(deadline.next_issue).trim() || null,
    next_draw_at: deadline.next_time || null,
    balls,
  }
}
