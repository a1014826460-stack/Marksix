"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import type { LotteryGame } from "@/lib/lotteryData"

type LegacyModulesFrameProps = {
  activeGame: LotteryGame
  onGameChange?: (game: LotteryGame) => void
  onAnchorMapChange?: (anchors: Record<string, number>) => void
  debug?: boolean
  onDebug?: (message: string) => void
  pageSwitchEnabled?: boolean
  shellHeaderHidden?: boolean
}

const GAME_TYPE_MAP: Record<LotteryGame, number> = {
  taiwan: 3,
  macau: 2,
  hongkong: 1,
}

export function LegacyModulesFrame({
  activeGame,
  onGameChange,
  onAnchorMapChange,
  debug = false,
  onDebug,
  pageSwitchEnabled = false,
  shellHeaderHidden = false,
}: LegacyModulesFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const [frameHeight, setFrameHeight] = useState(1600)
  const [displayGame, setDisplayGame] = useState<LotteryGame>(activeGame)

  function pushDebug(message: string) {
    if (!debug) return
    onDebug?.(message)
  }

  useEffect(() => {
    setDisplayGame(activeGame)
    pushDebug(`prop activeGame -> ${activeGame}`)
  }, [activeGame])

  const iframeSrc = useMemo(() => {
    const type = GAME_TYPE_MAP[displayGame]
    const params = new URLSearchParams({
      type: String(type),
      web: "4",
      debug: debug ? "1" : "0",
      page_switch: pageSwitchEnabled ? "1" : "0",
      shell_header: shellHeaderHidden ? "1" : "0",
    })
    return `/vendor/shengshi8800/embed.html?${params.toString()}`
  }, [debug, displayGame, pageSwitchEnabled, shellHeaderHidden])

  useEffect(() => {
    pushDebug(`iframe src -> ${iframeSrc}`)
  }, [iframeSrc])

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (!iframeRef.current) return
      if (event.source !== iframeRef.current.contentWindow) return

      const payload = event.data as
        | {
            kind?: string
            height?: number
            game?: LotteryGame
            message?: string
            type?: number
            anchors?: Record<string, number>
          }
        | undefined

      if (debug) {
        pushDebug(`parent received -> ${JSON.stringify(payload ?? {})}`)
      }

      if (payload?.kind === "legacy-debug-log") {
        if (payload.message) {
          pushDebug(`child debug -> ${payload.message}`)
        }
        return
      }

      if (payload?.kind === "legacy-embed-game-change") {
        if (payload.game && payload.game !== displayGame) {
          pushDebug(
            `apply game-change -> ${payload.game} (type=${GAME_TYPE_MAP[payload.game]})`
          )
          setDisplayGame(payload.game)
          onGameChange?.(payload.game)
        } else {
          pushDebug(
            `ignore game-change -> ${String(payload.game || "")} (current=${displayGame})`
          )
        }
        return
      }

      if (payload?.kind === "legacy-anchor-map") {
        if (payload.anchors && typeof payload.anchors === "object") {
          onAnchorMapChange?.(payload.anchors as Record<string, number>)
        }
        return
      }

      if (payload?.kind === "legacy-embed-height") {
        if (typeof payload.height !== "number") return
        if (!Number.isFinite(payload.height) || payload.height <= 0) return

        pushDebug(`apply height -> ${Math.ceil(payload.height)}`)
        setFrameHeight(Math.max(720, Math.ceil(payload.height) + 12))
      }
    }

    window.addEventListener("message", handleMessage)
    return () => window.removeEventListener("message", handleMessage)
  }, [debug, displayGame, onAnchorMapChange, onGameChange])

  useEffect(() => {
    pushDebug(
      `preserve height for displayGame -> ${displayGame} (type=${GAME_TYPE_MAP[displayGame]})`
    )
  }, [displayGame])

  return (
    <iframe
      key={iframeSrc}
      ref={iframeRef}
      className="legacy-shell-frame"
      src={iframeSrc}
      scrolling="no"
      onLoad={() => {
        pushDebug(
          `iframe onLoad -> game=${displayGame}, type=${GAME_TYPE_MAP[displayGame]}`
        )
      }}
      title="旧站预测模块"
      style={{
        width: "100%",
        height: `${frameHeight}px`,
        border: 0,
        overflow: "hidden",
      }}
    />
  )
}
