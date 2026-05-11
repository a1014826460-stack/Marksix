"use client"

import { useState } from "react"

type DrawNumbersInputProps = {
  name: string
  defaultValue: string
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
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const allNumbers = Array.from({ length: 49 }, (_, i) => i + 1)

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
      <div className="flex flex-wrap gap-0.5 max-h-[140px] overflow-y-auto">
        {allNumbers.map((n) => {
          const isSelected = selected.includes(n)
          return (
            <button
              key={n}
              type="button"
              onClick={() =>
                isSelected ? removeNumber(n) : addNumber(n)
              }
              disabled={!isSelected && selected.length >= 7}
              className={`h-7 w-7 rounded text-xs font-medium transition-colors ${
                isSelected
                  ? "bg-primary text-primary-foreground hover:bg-primary/80"
                  : "bg-muted text-muted-foreground hover:bg-muted/70 disabled:opacity-30"
              }`}
            >
              {String(n).padStart(2, "0")}
            </button>
          )
        })}
      </div>
    </div>
  )
}
