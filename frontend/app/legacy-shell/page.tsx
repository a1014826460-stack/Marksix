"use client"

import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useMemo, useRef, useState } from "react"
import type { LotteryGame } from "@/lib/lotteryData"
import { LegacyModulesFrame } from "@/components/LegacyModulesFrame"

const VALID_GAMES: LotteryGame[] = ["taiwan", "macau", "hongkong"]
const SECTION_ROWS = [
  [
    { id: "7x1m", label: "一肖一码" },
    { id: "4x8m", label: "四肖八码" },
    { id: "gsb", label: "高手资料" },
    { id: "gsb3", label: "精选图片" },
    { id: "msks", label: "买啥开啥" },
  ],
  [
    { id: "9x1m", label: "九肖一码" },
    { id: "yqjt", label: "欲钱解特" },
    { id: "6x", label: "六肖中特" },
    { id: "3t", label: "三头中特" },
    { id: "lx", label: "复式连肖" },
  ],
] as const

function isValidGame(value: string | null): value is LotteryGame {
  return VALID_GAMES.includes(value as LotteryGame)
}

function getForumTitle(game: LotteryGame) {
  if (game === "macau") return "澳门六合彩论坛"
  if (game === "hongkong") return "香港六合彩论坛"
  return "台湾六合彩论坛"
}

function LegacyShellContent() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const navRef = useRef<HTMLDivElement | null>(null)
  const rawGame = searchParams.get("game")
  const initialGame: LotteryGame = isValidGame(rawGame) ? rawGame : "taiwan"
  const [activeGame, setActiveGame] = useState<LotteryGame>(initialGame)
  const [anchorMap, setAnchorMap] = useState<Record<string, number>>({})

  const forumTitle = useMemo(() => getForumTitle(activeGame), [activeGame])

  useEffect(() => {
    setActiveGame(initialGame)
  }, [initialGame])

  function handleGameChange(game: LotteryGame) {
    setActiveGame(game)

    const nextParams = new URLSearchParams(searchParams.toString())
    nextParams.set("game", game)
    router.replace(`${pathname}?${nextParams.toString()}`, { scroll: false })
  }

  function handleJump(anchorId: string) {
    const iframe = document.querySelector(".legacy-shell-frame") as HTMLIFrameElement | null
    const anchorOffset = anchorMap[anchorId]
    if (!iframe || typeof anchorOffset !== "number") return

    const iframeTop = iframe.getBoundingClientRect().top + window.scrollY
    const navHeight = navRef.current?.offsetHeight ?? 0
    const top = Math.max(0, iframeTop + anchorOffset - navHeight - 8)
    window.scrollTo({ top, behavior: "smooth" })
  }

  return (
    <div
      style={{
        maxWidth: 720,
        margin: "0 auto",
        background: "#F4F4F4",
        minHeight: "100dvh",
      }}
    >
      <div className="box news-box">
        <div className="riqi">{forumTitle}</div>
      </div>
      <div className="box pad" id="yxym">
        <img alt="论坛头图" src="/vendor/shengshi8800/static/picture/header.jpg" width="100%" />
      </div>
      <div
        ref={navRef}
        className="nav2"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          boxShadow: "0 5px 10px rgba(0, 0, 0, .1)",
        }}
      >
        <ul>
          <li>
            <a>
              <b>{forumTitle}</b>
            </a>
          </li>
        </ul>
        {SECTION_ROWS.map((row, index) => (
          <ul key={index}>
            {row.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  onClick={(event) => {
                    event.preventDefault()
                    handleJump(item.id)
                  }}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        ))}
      </div>

      <div style={{ padding: 12 }}>
        <LegacyModulesFrame
          activeGame={activeGame}
          onGameChange={handleGameChange}
          onAnchorMapChange={setAnchorMap}
          pageSwitchEnabled
          shellHeaderHidden
        />
      </div>
    </div>
  )
}

export default function LegacyShellPage() {
  return (
    <Suspense fallback={null}>
      <LegacyShellContent />
    </Suspense>
  )
}
