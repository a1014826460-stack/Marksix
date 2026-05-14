"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { adminApi } from "@/lib/admin-api"
import type { NumberRow } from "@/features/shared/types"

// ── Types ──────────────────────────────────────────────

type VisibleOption = "number" | "zodiac" | "wave" | "oddEven" | "animal"

type NumberMappings = {
  colorMap: Map<string, string>
  zodiacMap: Map<string, string>
  elementMap: Map<string, string>
  animalMap: Map<string, string>
}

// ── Ball gradient colors (replicating the PNG ball look) ─

const BALL_GRADIENTS: Record<string, string> = {
  red: "radial-gradient(circle at 35% 35%, rgba(255,255,255,0.3) 0%, #e74c3c 40%, #a71d2a 100%)",
  blue: "radial-gradient(circle at 35% 35%, rgba(255,255,255,0.3) 0%, #3498db 40%, #1b4f72 100%)",
  green: "radial-gradient(circle at 35% 35%, rgba(255,255,255,0.3) 0%, #2ecc71 40%, #1a7a3a 100%)",
}

const ELEMENT_COLORS: Record<string, string> = {
  "金": "#fc0",
  "木": "#3c3",
  "水": "#39f",
  "火": "red",
  "土": "#c90",
}

const ANIMAL_COLORS: Record<string, string> = {
  "家禽": "#654222",
  "家肖": "#654222",
  "野兽": "#b5e61d",
  "野肖": "#b5e61d",
}

// ── Helpers ────────────────────────────────────────────

function parseNumbers(value: string): number[] {
  return value.split(",").map(Number).filter((n) => n >= 1 && n <= 49)
}

function computeSize(n: number) { return n >= 25 ? "大" : "小" }
function computeOddEven(n: number) { return n % 2 === 1 ? "单" : "双" }
function computeCombinedOddEven(n: number) {
  return ((Math.floor(n / 10) + (n % 10)) % 2 === 1) ? "合单" : "合双"
}
function computeSumOddEven(numbers: number[]) {
  return numbers.reduce((s, n) => s + n, 0) % 2 === 1 ? "单" : "双"
}

function mapBallColor(waveName: string): "red" | "blue" | "green" {
  if (waveName.includes("红")) return "red"
  if (waveName.includes("蓝")) return "blue"
  if (waveName.includes("绿")) return "green"
  return "red"
}

// ── Module-level mapping cache ─────────────────────────

let cachedMappings: NumberMappings | null = null
let fetchPromise: Promise<NumberMappings> | null = null

async function loadMappings(): Promise<NumberMappings> {
  if (cachedMappings) return cachedMappings
  if (fetchPromise) return fetchPromise

  fetchPromise = (async () => {
    const [colorRes, zodiacRes, elementZodiacRes, animalRes1, animalRes2] = await Promise.all([
      adminApi<{ numbers: NumberRow[] }>("/admin/numbers?sign=波色"),
      adminApi<{ numbers: NumberRow[] }>("/admin/numbers?sign=生肖"),
      adminApi<{ numbers: NumberRow[] }>("/admin/numbers?sign=五行肖").catch(() => ({ numbers: [] as NumberRow[] })),
      adminApi<{ numbers: NumberRow[] }>("/admin/numbers?sign=家野肖").catch(() => ({ numbers: [] as NumberRow[] })),
      adminApi<{ numbers: NumberRow[] }>("/admin/numbers?sign=家禽|野兽").catch(() => ({ numbers: [] as NumberRow[] })),
    ])

    // Number → wave color
    const colorMap = new Map<string, string>()
    for (const item of colorRes.numbers) {
      for (const code of item.code.split(",").map((s) => s.trim()).filter(Boolean)) {
        const n = parseInt(code, 10)
        if (n >= 1 && n <= 49) colorMap.set(String(n).padStart(2, "0"), item.name)
      }
    }

    // Number → zodiac
    const zodiacMap = new Map<string, string>()
    for (const item of zodiacRes.numbers) {
      for (const code of item.code.split(",").map((s) => s.trim()).filter(Boolean)) {
        const n = parseInt(code, 10)
        if (n >= 1 && n <= 49) zodiacMap.set(String(n).padStart(2, "0"), item.name)
      }
    }

    // Zodiac → element (五行肖: name like "金肖"/"木肖"/"水肖"/"火肖"/"土肖", code = zodiac names)
    const zodiacElementMap = new Map<string, string>()
    for (const item of elementZodiacRes.numbers) {
      const elementName = item.name.replace("肖", "")
      for (const zodiac of item.code.split(",").map((s) => s.trim()).filter(Boolean)) {
        zodiacElementMap.set(zodiac, elementName)
      }
    }

    // Zodiac → animal category (家野肖 / 家禽|野兽)
    const zodiacAnimalMap = new Map<string, string>()
    for (const item of [...animalRes1.numbers, ...animalRes2.numbers]) {
      const category = item.name
      for (const zodiac of item.code.split(",").map((s) => s.trim()).filter(Boolean)) {
        if (!zodiacAnimalMap.has(zodiac)) zodiacAnimalMap.set(zodiac, category)
      }
    }

    // Build Number → element and Number → animal maps
    const elementMap = new Map<string, string>()
    const animalMap = new Map<string, string>()
    for (let n = 1; n <= 49; n++) {
      const code = String(n).padStart(2, "0")
      const zodiac = zodiacMap.get(code) || ""
      elementMap.set(code, zodiacElementMap.get(zodiac) || "")
      animalMap.set(code, zodiacAnimalMap.get(zodiac) || "")
    }

    const mappings: NumberMappings = { colorMap, zodiacMap, elementMap, animalMap }
    cachedMappings = mappings
    return mappings
  })()

  return fetchPromise
}

// ── Shared visibility context ──────────────────────────

type BallDisplayContextValue = {
  visible: Set<VisibleOption>
  toggleOption: (option: VisibleOption) => void
}

const BallDisplayContext = createContext<BallDisplayContextValue | null>(null)

export function DrawBallDisplayProvider({ children }: { children: React.ReactNode }) {
  const [visible, setVisible] = useState<Set<VisibleOption>>(
    () => new Set<VisibleOption>(["number", "zodiac"]),
  )

  const toggleOption = useCallback((option: VisibleOption) => {
    setVisible((prev) => {
      const next = new Set(prev)
      if (next.has(option)) next.delete(option)
      else next.add(option)
      return next
    })
  }, [])

  const value = useMemo(() => ({ visible, toggleOption }), [visible, toggleOption])

  return (
    <BallDisplayContext.Provider value={value}>
      {children}
    </BallDisplayContext.Provider>
  )
}

function useBallDisplayContext() {
  const ctx = useContext(BallDisplayContext)
  if (!ctx) throw new Error("DrawBallDisplay components must be used within DrawBallDisplayProvider")
  return ctx
}

// ── Toggle bar ─────────────────────────────────────────

const TOGGLE_OPTIONS: { key: VisibleOption; label: string }[] = [
  { key: "number", label: "平码/特码" },
  { key: "zodiac", label: "生肖/五行" },
  { key: "wave", label: "波色/大小" },
  { key: "oddEven", label: "单双/合单双" },
  { key: "animal", label: "家禽野兽/总和单双" },
]

export function DrawBallDisplayToggles() {
  const { visible, toggleOption } = useBallDisplayContext()

  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-xs text-muted-foreground mr-1">属性：</span>
      {TOGGLE_OPTIONS.map((opt) => {
        const active = visible.has(opt.key)
        return (
          <button
            key={opt.key}
            type="button"
            onClick={() => toggleOption(opt.key)}
            className={`px-2 py-0.5 text-xs rounded-md border transition-colors ${
              active
                ? "bg-primary text-primary-foreground border-primary shadow-sm"
                : "bg-background text-muted-foreground border-border hover:bg-muted"
            }`}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

// ── Ball cell (used in table rows) ─────────────────────

type DrawBallDisplayProps = {
  numbers: string
}

export function DrawBallDisplay({ numbers }: DrawBallDisplayProps) {
  const { visible } = useBallDisplayContext()
  const [mappings, setMappings] = useState<NumberMappings | null>(null)

  useEffect(() => {
    let cancelled = false
    loadMappings().then((data) => {
      if (!cancelled) setMappings(data)
    })
    return () => { cancelled = true }
  }, [])

  const numList = useMemo(() => parseNumbers(numbers), [numbers])
  if (numList.length === 0) return <span className="text-muted-foreground text-sm">-</span>

  const regularBalls = numList.slice(0, 6)
  const specialBall = numList.length >= 7 ? numList[6] : null
  const sumOddEven = computeSumOddEven(numList)

  function renderBall(num: number, isSpecial: boolean, idx: number) {
    const code = String(num).padStart(2, "0")
    const waveName = mappings?.colorMap.get(code) || ""
    const colorKey = mapBallColor(waveName)
    const gradient = BALL_GRADIENTS[colorKey]
    const zodiac = mappings?.zodiacMap.get(code) || ""
    const element = mappings?.elementMap.get(code) || ""
    const wave = waveName.replace("波", "")
    const size = computeSize(num)
    const oddEven = computeOddEven(num)
    const combinedOddEven = computeCombinedOddEven(num)
    const animalType = mappings?.animalMap.get(code) || ""
    const elementColor = ELEMENT_COLORS[element]
    const animalColor = ANIMAL_COLORS[animalType]

    return (
      <div
        key={`${isSpecial ? "s" : "b"}-${idx}-${num}`}
        className="flex flex-col items-center"
        style={{ minWidth: 34 }}
      >
        {/* Ball */}
        <div
          className="inline-flex items-center justify-center rounded-full text-white font-bold select-none"
          style={{
            width: 26,
            height: 26,
            background: gradient,
            fontSize: 12,
            textShadow: "0 1px 2px rgba(0,0,0,0.35)",
          }}
        >
          {code}
        </div>

        {/* Attribute rows */}
        {visible.has("zodiac") && (
          <div className="text-[9px] text-center mt-px leading-tight px-0.5">
            <span>{zodiac || "-"}</span>
            <span className="text-muted-foreground opacity-50">/</span>
            <span style={{ color: elementColor || undefined }}>{element || "-"}</span>
          </div>
        )}
        {visible.has("wave") && (
          <div className="text-[9px] text-center mt-px leading-tight px-0.5">
            <span>{wave || "-"}</span>
            <span className="text-muted-foreground opacity-50">/</span>
            <span>{size}</span>
          </div>
        )}
        {visible.has("oddEven") && (
          <div className="text-[9px] text-center mt-px leading-tight px-0.5">
            <span>{oddEven}</span>
            <span className="text-muted-foreground opacity-50">/</span>
            <span>{combinedOddEven}</span>
          </div>
        )}
        {visible.has("animal") && (
          <div className="text-[9px] text-center mt-px leading-tight px-0.5">
            <span style={{ color: animalColor || undefined }}>{animalType || "-"}</span>
            <span className="text-muted-foreground opacity-50">/</span>
            <span>{sumOddEven}</span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-start gap-x-1 gap-y-1 py-1">
      {regularBalls.map((num, idx) => renderBall(num, false, idx))}
      {specialBall != null && (
        <>
          <div className="flex items-center self-start pt-1">
            <span className="text-sm font-bold text-muted-foreground opacity-40">+</span>
          </div>
          {renderBall(specialBall, true, 6)}
        </>
      )}
    </div>
  )
}
