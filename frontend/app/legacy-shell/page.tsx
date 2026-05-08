"use client"

import { useEffect, useState } from "react"
import type { LotteryGame } from "@/lib/lotteryData"
import { LegacyModulesFrame } from "@/components/LegacyModulesFrame"

const GAME_OPTIONS: { key: LotteryGame; label: string; description: string }[] = [
  { key: "taiwan", label: "台湾彩", description: "type=3，旧站默认主彩种" },
  { key: "macau", label: "澳门彩", description: "type=2，用于验证旧脚本切换兼容性" },
  { key: "hongkong", label: "香港彩", description: "type=1，用于验证旧脚本切换兼容性" },
]

export default function LegacyShellPage() {
  const [activeGame, setActiveGame] = useState<LotteryGame>("taiwan")
  const [currentTime, setCurrentTime] = useState("")

  useEffect(() => {
    function updateClock() {
      const now = new Date()
      const hours = String(now.getHours()).padStart(2, "0")
      const minutes = String(now.getMinutes()).padStart(2, "0")
      const seconds = String(now.getSeconds()).padStart(2, "0")
      setCurrentTime(`${hours}:${minutes}:${seconds}`)
    }

    updateClock()
    const timer = window.setInterval(updateClock, 1000)
    return () => window.clearInterval(timer)
  }, [])

  return (
    <main className="legacy-shell-page">
      <section className="legacy-shell-panel">
        <p className="legacy-shell-eyebrow">阶段 1 / 旧站完整隔离运行</p>
        <h1 className="legacy-shell-panel__title">
          新站外壳 + 旧 JS iframe 隔离层
        </h1>
        <p className="legacy-shell-panel__desc">
          这里先不碰旧站模块内部业务逻辑，只验证三件事：旧脚本能否按彩种切换、
          旧接口是否还能稳定喂数据、旧页面原生高亮是否完整保留。
        </p>
        <p className="legacy-shell-panel__meta">当前时间：{currentTime}</p>
      </section>

      <section className="legacy-shell-tabs">
        {GAME_OPTIONS.map((option) => {
          const active = option.key === activeGame
          return (
            <button
              key={option.key}
              type="button"
              className={active ? "legacy-shell-tab active" : "legacy-shell-tab"}
              onClick={() => setActiveGame(option.key)}
            >
              <span className="legacy-shell-tab__label">{option.label}</span>
              <span className="legacy-shell-tab__desc">{option.description}</span>
            </button>
          )
        })}
      </section>

      <LegacyModulesFrame activeGame={activeGame} />
    </main>
  )
}
