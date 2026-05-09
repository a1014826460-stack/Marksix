/**
 * 开奖结果展示组件 — LotteryResult.tsx
 * ---------------------------------------------------------------
 * 职责：展示六合彩开奖号码球（通过 iframe 嵌入）+ 下次开奖倒计时。
 *
 * 数据流：
 *   1. 用户切换游戏标签（台湾彩/澳门彩/香港彩）
 *   2. 组件请求 /api/next-draw-deadline?lottery_type=X 获取 next_time
 *   3. 每秒计算倒计时，归零时自动重新加载 iframe 刷新开奖结果
 *   4. iframe 内部 local.html 负责渲染开奖球
 */

"use client"

import { useEffect, useRef, useState } from "react"
import type { LotteryGame } from "@/lib/lotteryData"
import { games, lotteryResultIframes } from "@/lib/lotteryData"

/** 彩种 key → API 的 lottery_type 查询参数值 */
const LOTTERY_TYPE_MAP: Record<LotteryGame, string> = {
  taiwan: "3",
  macau: "2",
  hongkong: "1",
}

/** LotteryResult 组件的 Props */
type LotteryResultProps = {
  activeGame: LotteryGame
  onGameChange: (game: LotteryGame) => void
}

/** 将毫秒时间戳转换为 HH:MM:SS 倒计时文本 */
function formatCountdown(remainingMs: number): string {
  if (remainingMs <= 0) return "00:00:00"
  const totalSec = Math.floor(remainingMs / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

/**
 * 开奖结果展示组件
 * ---------------------------------------------------------------
 * 倒计时覆盖在 iframe 上方，归零时自动刷新 iframe 获取最新开奖数据。
 */
export function LotteryResult({ activeGame, onGameChange }: LotteryResultProps) {
  const [countdown, setCountdown] = useState("--:--:--")
  const [isExpired, setIsExpired] = useState(false)
  const deadlineRef = useRef<number>(0)
  const iframeKeyRef = useRef(0)
  const [iframeKey, setIframeKey] = useState(0)

  // 切换彩种时重新获取 next_time
  useEffect(() => {
    let cancelled = false
    const lt = LOTTERY_TYPE_MAP[activeGame]

    async function fetchDeadline() {
      try {
        const res = await fetch(`/api/next-draw-deadline?lottery_type=${lt}`)
        const data = await res.json()
        if (cancelled) return
        if (data.next_time) {
          deadlineRef.current = Number(data.next_time)
          setIsExpired(false)
        } else {
          deadlineRef.current = 0
          setCountdown("--:--:--")
        }
      } catch {
        if (!cancelled) setCountdown("--:--:--")
      }
    }

    fetchDeadline()
    return () => { cancelled = true }
  }, [activeGame, iframeKey])

  // 每秒更新倒计时
  useEffect(() => {
    const timer = setInterval(() => {
      if (deadlineRef.current > 0) {
        const remaining = deadlineRef.current - Date.now()
        if (remaining <= 0) {
          setCountdown("00:00:00")
          if (!isExpired) {
            setIsExpired(true)
            // 倒计时归零：重新加载 iframe 获取最新开奖结果
            iframeKeyRef.current += 1
            setIframeKey(iframeKeyRef.current)
          }
        } else {
          setIsExpired(false)
          setCountdown(formatCountdown(remaining))
        }
      }
    }, 1000)
    return () => clearInterval(timer)
  }, [activeGame, isExpired, iframeKey])

  return (
    <div className="box pad" id="yxym">
      <div className="KJ-TabBox">
        {/* 倒计时覆盖层 */}
        <div
          style={{
            textAlign: "center",
            padding: "6px 0",
            fontSize: "14px",
            fontWeight: 600,
            color: countdown === "00:00:00" ? "#e53e3e" : "#d4a853",
            background: "#1a1a2e",
            borderRadius: "4px",
            marginBottom: "4px",
          }}
        >
          下次开奖倒计时 {countdown}
        </div>

        <ul>
          {games.map((game) => (
            <li
              className={activeGame === game.key ? "cur" : ""}
              data-game={game.key}
              key={game.key}
              onClick={() => onGameChange(game.key)}
            >
              {game.label}
            </li>
          ))}
        </ul>
        {games.map((game) => {
          const iframeCfg = lotteryResultIframes[game.key]
          const isActive = activeGame === game.key
          return (
            <div
              key={game.key}
              className={isActive ? "cur" : ""}
              data-game-panel={game.key}
              style={{ display: isActive ? "" : "none" }}
            >
              {isActive && (
                <iframe
                  key={`${game.key}-${iframeKey}`}
                  className="KJ-IFRAME"
                  src={iframeCfg.url}
                  width="100%"
                  height={iframeCfg.height}
                  style={{ border: 0, overflow: "hidden" }}
                  title={`${game.label}开奖结果`}
                />
              )}
            </div>
          )
        })}
      </div>
      {/* 旧站底部广告横幅 */}
      <div className="waibox">
        <a
          className="location_to"
          href="http://shengshi8800.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          点击进入台湾彩报码直播开奖
        </a>
      </div>
    </div>
  )
}
