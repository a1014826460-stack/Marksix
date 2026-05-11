"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi } from "@/lib/admin-api"
import { getSitePredictionModuleName } from "@/features/shared/types"
import type { SitePredictionModule } from "@/features/shared/types"

type RegenerateDialogProps = {
  open: boolean
  module: SitePredictionModule
  siteId: number
  tableName: string
  typeFilter: string
  onClose: () => void
  onSuccess: (msg: string) => void
  onError: (msg: string) => void
  onRefresh: () => void
  page: number
}

export function RegenerateDialog({
  open,
  module,
  siteId,
  tableName,
  typeFilter,
  onClose,
  onSuccess,
  onError,
  onRefresh,
}: RegenerateDialogProps) {
  const [numbers, setNumbers] = useState("")
  const [year, setYear] = useState("")
  const [term, setTerm] = useState("")

  if (!open) return null

  async function doRegenerate() {
    const numStr = numbers.trim()
    if (!numStr) {
      onError("请输入开奖号码")
      return
    }

    const codes = numStr
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    if (codes.length !== 7) {
      onError("开奖号码必须为7个数字，逗号分隔")
      return
    }
    for (const c of codes) {
      if (!/^\d{1,2}$/.test(c)) {
        onError(`无效号码: ${c}`)
        return
      }
    }

    const yr = year.trim()
    const tm = term.trim()
    if (yr && !/^\d{4}$/.test(yr)) {
      onError("年份必须为4位数字")
      return
    }
    if (tm) {
      if (!/^\d{1,5}$/.test(tm)) {
        onError("期数必须为1-5位数字")
        return
      }
      if (parseInt(tm) === 0) {
        onError("期数不能为0")
        return
      }
    }

    try {
      await adminApi(
        `/admin/sites/${siteId}/mode-payload/${tableName}/regenerate`,
        {
          method: "POST",
          body: JSON.stringify({
            mechanism_key: module.mechanism_key,
            res_code: numbers.trim(),
            lottery_type: typeFilter || "3",
            year: year.trim() || new Date().getFullYear().toString(),
            term: term.trim() || "",
          }),
        },
      )
      onSuccess("重新生成成功")
      onClose()
      onRefresh()
    } catch (e) {
      onError(e instanceof Error ? e.message : "重新生成失败")
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-[500px] rounded-lg bg-background p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-1 text-base font-semibold">重新生成资料</h3>
        <p className="mb-4 text-xs text-muted-foreground">
          模块: {getSitePredictionModuleName(module)} ({tableName})
        </p>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium">
              开奖号码（逗号分隔）
            </label>
            <Input
              placeholder="01,05,12,23,34,45,49"
              value={numbers}
              onChange={(e) => setNumbers(e.target.value)}
              className="h-9 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium">年份</label>
              <Input
                placeholder={new Date().getFullYear().toString()}
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="h-9 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">期数</label>
              <Input
                placeholder="如 001"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
                className="h-9 text-sm"
              />
            </div>
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            取消
          </Button>
          <Button size="sm" onClick={doRegenerate}>
            执行生成
          </Button>
        </div>
      </div>
    </div>
  )
}
