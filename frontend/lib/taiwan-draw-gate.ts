import { parseTaiwanDrawTime } from "./draw-history-gate"

type ClockPayload = { server_now?: unknown; server_now_ms?: unknown; server_time?: unknown }
type Deadline = ClockPayload & { current_issue?: unknown; current_draw_time?: unknown }

function trustedNowMs(payload: ClockPayload, upperBoundMs: number): number {
  const seconds = Number(payload.server_now ?? payload.server_time)
  if (!Number.isFinite(seconds) || seconds <= 0) return Number.NaN
  const ms = Number(payload.server_now_ms)
  const sampled = Number.isFinite(ms) && Math.floor(ms / 1000) === Math.floor(seconds) ? ms : seconds * 1000
  return Math.min(sampled, upperBoundMs)
}

function beijingTime(ms: number): string {
  return new Date(ms + 8 * 3600000).toISOString().slice(0, 19).replace("T", " ")
}

function validBall(ball: unknown): ball is Record<string, unknown> {
  return Boolean(ball && typeof ball === "object" && /^(?:0?[1-9]|[1-4]\d)$/.test(String((ball as { value?: unknown }).value || "").trim()))
}

/** Independent proxy gate: raw seven/completion/interval never determine progress. */
export function guardTaiwanLiveDraw<T extends ClockPayload & { current_issue?: unknown; draw_time?: unknown; reveal_start?: unknown; result_balls?: unknown; special_ball?: unknown }>(
  payload: T, deadline: Deadline, options: { lotteryType: number; nowMs: number },
): T {
  if (options.lotteryType !== 3) return payload
  const issue = String(payload.current_issue || "").trim()
  const planned = parseTaiwanDrawTime(payload.draw_time)
  const preferredText = String(payload.reveal_start || "").trim()
  const preferred = preferredText ? parseTaiwanDrawTime(preferredText) : planned
  const rawBound = Number(deadline.current_draw_time)
  const bound = rawBound >= 1e12 ? rawBound : rawBound * 1000
  const now = Math.min(trustedNowMs(payload, options.nowMs), trustedNowMs(deadline, options.nowMs))
  const identityOk = /^\d{7}$/.test(issue) && issue === String(deadline.current_issue || "").trim()
  const anchor = planned !== null && preferred !== null && Number.isFinite(bound) && bound > 0 ? Math.max(planned, preferred, bound) : Number.NaN
  const available: Record<string, unknown>[] = []
  if (Array.isArray(payload.result_balls)) {
    for (const ball of payload.result_balls.slice(0, 6)) {
      if (!validBall(ball)) break
      available.push(ball)
    }
    if (available.length === 6 && validBall(payload.special_ball)) available.push(payload.special_ball)
  }
  const allowed = identityOk && Number.isFinite(anchor) && Number.isFinite(now) && now >= anchor
    ? Math.min(available.length, Math.floor((now - anchor) / 25000) + 1) : 0
  return {
    ...payload,
    draw_time: Number.isFinite(bound) && bound > 0 ? beijingTime(bound) : payload.draw_time,
    reveal_start: Number.isFinite(anchor) ? beijingTime(anchor) : payload.reveal_start,
    result_balls: available.slice(0, Math.min(6, allowed)), special_ball: allowed === 7 ? available[6] : null,
    revealed_count: allowed, total_balls: 7, reveal_interval_seconds: 25, is_complete: allowed === 7,
    server_now: Number.isFinite(now) ? Math.floor(now / 1000) : 0,
    server_now_ms: Number.isFinite(now) ? Math.floor(now) : 0,
    next_reveal_at: allowed === 7 || !Number.isFinite(anchor) ? "" : beijingTime(anchor + allowed * 25000),
  } as T
}
