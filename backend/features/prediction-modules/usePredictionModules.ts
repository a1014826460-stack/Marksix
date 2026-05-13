"use client"

import { useEffect, useState } from "react"
import { adminApi, jsonBody } from "@/lib/admin-api"
import type { Mechanism } from "@/features/shared/types"

export function usePredictionModules() {
  const [rows, setRows] = useState<Mechanism[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [toggling, setToggling] = useState<Set<string>>(new Set())

  async function load() {
    setLoading(true)
    setError("")
    try {
      const data = await adminApi<{ mechanisms: Mechanism[] }>("/predict/mechanisms")
      setRows(data.mechanisms)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载预测模块失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function toggleStatus(mechanismKey: string, currentStatus: number) {
    const newStatus = currentStatus === 1 ? 0 : 1
    setToggling((prev) => new Set(prev).add(mechanismKey))
    try {
      await adminApi(
        `/admin/predict/mechanisms/${encodeURIComponent(mechanismKey)}/status`,
        { method: "PATCH", body: jsonBody({ status: newStatus }) },
      )
      setRows((prev) =>
        prev.map((row) =>
          row.key === mechanismKey ? { ...row, status: newStatus } : row,
        ),
      )
    } finally {
      setToggling((prev) => {
        const next = new Set(prev)
        next.delete(mechanismKey)
        return next
      })
    }
  }

  return {
    rows,
    loading,
    error,
    toggling,
    load,
    toggleStatus,
  }
}
