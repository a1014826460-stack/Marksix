"use client"

import { useEffect, useState } from "react"
import { adminApi } from "@/lib/admin-api"

type DrawNumbersInputProps = {
  name: string
  defaultValue: string
}

type NumberMapping = {
  id: number
  name: string
  code: string
}

export function DrawNumbersInput({ name, defaultValue }: DrawNumbersInputProps) {
  const [selected, setSelected] = useState<number[]>(() =>
    defaultValue
      ? defaultValue
          .split(",")
          .map(Number)
          .filter((n) => n >= 1 && n <= 49)
      : [],
  )
  useEffect(() => {
    setSelected(
      defaultValue
        ? defaultValue
            .split(",")
            .map(Number)
            .filter((n) => n >= 1 && n <= 49)
        : [],
    )
  }, [defaultValue])
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)

  const [zodiacData, setZodiacData] = useState<NumberMapping[]>([])
  const [colorData, setColorData] = useState<NumberMapping[]>([])
  const [dataLoading, setDataLoading] = useState(true)
  const [dataError, setDataError] = useState("")

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [zodiacRes, colorRes] = await Promise.all([
          adminApi<{ numbers: NumberMapping[] }>("/admin/numbers?sign=生肖"),
          adminApi<{ numbers: NumberMapping[] }>("/admin/numbers?sign=波色"),
        ])
        if (!cancelled) {
          setZodiacData(zodiacRes.numbers)
          setColorData(colorRes.numbers)
          setDataLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setDataError(err instanceof Error ? err.message : "加载失败")
          setDataLoading(false)
        }
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const colorMap = new Map<number, string>()
  for (const item of colorData) {
    const nums = item.code
      .split(",")
      .map(Number)
      .filter((n) => n >= 1 && n <= 49)
    for (const n of nums) {
      colorMap.set(n, item.name)
    }
  }

  function getColorClass(n: number): string {
    const color = colorMap.get(n)
    if (color === "红波") return "bg-red-500 text-white hover:bg-red-600"
    if (color === "蓝波") return "bg-blue-500 text-white hover:bg-blue-600"
    if (color === "绿波") return "bg-green-500 text-white hover:bg-green-600"
    return "bg-muted text-muted-foreground hover:bg-muted/70"
  }

  function addNumber(n: number) {
    setSelected((prev) => {
      if (prev.includes(n)) return prev
      if (prev.length >= 7) return prev
      return [...prev, n]
    })
  }

  function removeNumber(n: number) {
    setSelected((prev) => prev.filter((x) => x !== n))
  }

  function onDragStart(_e: React.DragEvent, index: number) {
    setDragIndex(index)
  }

  function onDragOver(e: React.DragEvent, index: number) {
    e.preventDefault()
    setDragOverIndex(index)
  }

  function onDragLeave() {
    setDragOverIndex(null)
  }

  function onDrop(e: React.DragEvent, dropIndex: number) {
    e.preventDefault()
    setDragOverIndex(null)
    if (dragIndex === null || dragIndex === dropIndex) return
    setSelected((prev) => {
      const next = [...prev]
      const [item] = next.splice(dragIndex, 1)
      next.splice(dropIndex, 0, item)
      return next
    })
    setDragIndex(null)
  }

  function onDragEnd() {
    setDragIndex(null)
    setDragOverIndex(null)
  }

  const valueStr = selected.map((n) => String(n).padStart(2, "0")).join(",")
  return (
    <div>
      <input type="hidden" name={name} value={valueStr} />
      <div className="flex flex-wrap items-center gap-2 min-h-[56px] p-3 mb-2 rounded-lg border-2 border-dashed border-muted-foreground/25 bg-muted/20 transition-colors">
        {selected.map((n, idx) => (
          <div
            key={n}
            draggable
            onDragStart={(e) => onDragStart(e, idx)}
            onDragOver={(e) => onDragOver(e, idx)}
            onDragLeave={onDragLeave}
            onDrop={(e) => onDrop(e, idx)}
            onDragEnd={onDragEnd}
            className={`flex items-center gap-1.5 rounded-lg bg-primary px-2.5 py-1.5 text-sm font-bold text-primary-foreground shadow-sm cursor-grab active:cursor-grabbing select-none transition-all ${
              dragIndex === idx ? "opacity-40 scale-90" : ""
            } ${
              dragOverIndex === idx && dragIndex !== idx
                ? "ring-2 ring-primary/60 scale-105"
                : ""
            }`}
            title="拖拽可排序"
          >
            <span className="text-[10px] opacity-50 select-none" aria-hidden>
              ⠿
            </span>
            <span>{String(n).padStart(2, "0")}</span>
            <button
              type="button"
              onClick={() => removeNumber(n)}
              className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary-foreground/20 text-[10px] hover:bg-destructive hover:text-destructive-foreground transition-colors"
              title="移除"
            >
              ×
            </button>
          </div>
        ))}
        {selected.length === 0 && (
          <span className="text-xs text-muted-foreground">
            点击下方号码添加（最多7个），选中后可拖拽排序
          </span>
        )}
      </div>

      {dataLoading && (
        <div className="flex items-center justify-center py-4 text-xs text-muted-foreground">
          加载号码映射...
        </div>
      )}
      {dataError && (
        <div className="flex items-center justify-center py-4 text-xs text-red-500">
          加载失败: {dataError}
        </div>
      )}
      {!dataLoading && !dataError && (
        <div className="overflow-x-auto overflow-y-hidden max-h-[260px] md:max-h-[220px] -mx-1 px-1">
          <div className="flex gap-0.5 min-w-max">
            {zodiacData.map((item) => {
              const nums = item.code
                .split(",")
                .map(Number)
                .filter((n) => n >= 1 && n <= 49)
                .sort((a, b) => a - b)
              return (
                <div key={item.id} className="flex flex-col gap-0.5 w-9 md:w-auto md:flex-1 md:min-w-0">
                  <div className="text-center text-[10px] font-medium text-muted-foreground py-0.5 select-none">
                    {item.name}
                  </div>
                  {nums.map((n) => {
                    const isSelected = selected.includes(n)
                    return (
                      <button
                        key={n}
                        type="button"
                        onClick={() =>
                          isSelected ? removeNumber(n) : addNumber(n)
                        }
                        disabled={!isSelected && selected.length >= 7}
                        className={`h-8 w-8 md:h-6 md:w-full rounded text-xs font-medium transition-colors ${
                          isSelected
                            ? "bg-primary text-primary-foreground hover:bg-primary/80"
                            : `${getColorClass(n)} disabled:opacity-30`
                        }`}
                      >
                        {String(n).padStart(2, "0")}
                      </button>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
