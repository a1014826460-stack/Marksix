"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import type { LotteryGame } from "@/lib/lotteryData"

type LegacyModulesFrameProps = {
  activeGame: LotteryGame
}

const GAME_TYPE_MAP: Record<LotteryGame, number> = {
  taiwan: 3,
  macau: 2,
  hongkong: 1,
}

const GAME_LABEL_MAP: Record<LotteryGame, string> = {
  taiwan: "台湾彩",
  macau: "澳门彩",
  hongkong: "香港彩",
}

export function LegacyModulesFrame({ activeGame }: LegacyModulesFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const [frameHeight, setFrameHeight] = useState(1600)

  const iframeSrc = useMemo(() => {
    const type = GAME_TYPE_MAP[activeGame]
    const params = new URLSearchParams({
      type: String(type),
      web: "4",
    })
    return `/vendor/shengshi8800/embed.html?${params.toString()}`
  }, [activeGame])

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (!iframeRef.current) return
      if (event.source !== iframeRef.current.contentWindow) return

      const payload = event.data as
        | { kind?: string; height?: number }
        | undefined

      if (payload?.kind !== "legacy-embed-height") return
      if (typeof payload.height !== "number") return
      if (!Number.isFinite(payload.height) || payload.height <= 0) return

      // 额外补一点底部空间，避免旧站最后一行被裁切。
      setFrameHeight(Math.max(720, Math.ceil(payload.height) + 12))
    }

    window.addEventListener("message", handleMessage)
    return () => window.removeEventListener("message", handleMessage)
  }, [])

  useEffect(() => {
    // 彩种切换后，先给一个保守高度，等旧页重新回传真实高度。
    setFrameHeight(1600)
  }, [activeGame])

  return (
    <section className="legacy-shell-card">
      <div className="legacy-shell-card__header">
        <div>
          <h1 className="legacy-shell-title">旧 JS 隔离嵌入验证页</h1>
          <p className="legacy-shell-subtitle">
            当前显示彩种：{GAME_LABEL_MAP[activeGame]}。这一阶段不改旧站高亮逻辑，
            继续保留旧脚本里“特码命中”和“生肖命中”的原生判断。
          </p>
        </div>
      </div>

      <iframe
        key={iframeSrc}
        ref={iframeRef}
        className="legacy-shell-frame"
        src={iframeSrc}
        title={`旧站隔离嵌入 - ${GAME_LABEL_MAP[activeGame]}`}
        style={{ height: `${frameHeight}px` }}
      />
    </section>
  )
}
