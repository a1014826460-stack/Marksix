export type SiteDrawSource = {
  current_issue?: string | number | null
  draw_time?: string | null
  result_balls?: SiteDrawBallSource[]
  special_ball?: SiteDrawBallSource | null
}

export type SiteDrawBallSource = {
  value?: string | number | null
  color?: string | null
  zodiac?: string | null
  element?: string | null
}

export type SiteDrawDeadlineSource = {
  next_issue?: string | number | null
  next_time?: string | number | null
}

export type NormalizedSiteDraw = {
  current_issue: string
  opened_at: string | null
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

export function normalizeSiteDraw(
  latest: SiteDrawSource,
  deadline: SiteDrawDeadlineSource
): NormalizedSiteDraw {
  return {
    current_issue: String(latest.current_issue || "").trim(),
    opened_at: latest.draw_time || null,
    next_issue: deadline.next_issue == null ? null : String(deadline.next_issue).trim() || null,
    next_draw_at: deadline.next_time || null,
    balls: [
      ...(latest.result_balls || []).map((ball) => normalizeBall(ball, false)),
      ...(latest.special_ball ? [normalizeBall(latest.special_ball, true)] : []),
    ],
  }
}
