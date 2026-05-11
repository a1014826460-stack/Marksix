"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi } from "@/lib/admin-api"
import type { Site, SitePredictionModule } from "@/features/shared/types"

type BulkGenerateDialogProps = {
  open: boolean
  site: Site | null
  modules: SitePredictionModule[]
  onClose: () => void
  onMessage: (msg: string) => void
  onGenerated: (sourceFilter: string, reloadToken: number) => void
  reloadToken: number
}

export function BulkGenerateDialog({
  open,
  site,
  modules,
  onClose,
  onMessage,
  onGenerated,
  reloadToken,
}: BulkGenerateDialogProps) {
  const [bulkLotteryType, setBulkLotteryType] = useState(
    () => String(site?.lottery_type_id || 3),
  )
  const [bulkStartIssue, setBulkStartIssue] = useState("")
  const [bulkEndIssue, setBulkEndIssue] = useState("")
  const [bulkSubmitting, setBulkSubmitting] = useState(false)
  const [bulkSelectedKeys, setBulkSelectedKeys] = useState<Set<string>>(
    new Set(),
  )

  if (!open) return null

  async function doBulkGenerate() {
    if (!bulkStartIssue.trim() || !bulkEndIssue.trim()) {
      onMessage("请先填写完整的起始期号和结束期号")
      return
    }
    const selectedList = Array.from(bulkSelectedKeys)
    if (selectedList.length === 0) {
      onMessage("请至少选择一个模块")
      return
    }
    setBulkSubmitting(true)
    onClose()
    onMessage(`批量生成已提交后台执行（${selectedList.length} 个模块），正在处理中…`)
    try {
      const { job_id } = await adminApi<{
        ok: boolean
        job_id: string
      }>(
        `/admin/sites/${site?.id}/prediction-modules/generate-all`,
        {
          method: "POST",
          body: JSON.stringify({
            lottery_type:
              bulkLotteryType || String(site?.lottery_type_id || 3),
            start_issue: bulkStartIssue.trim(),
            end_issue: bulkEndIssue.trim(),
            mechanism_keys: selectedList,
            future_periods: 1,
          }),
        },
      )
      for (let i = 0; i < 120; i++) {
        await new Promise((r) => setTimeout(r, 3000))
        try {
          const job = await adminApi<{
            status: string
            result?: {
              total_modules: number
              draw_count: number
              inserted: number
              updated: number
              errors: number
            }
            error?: string
          }>(`/admin/jobs/${job_id}`)
          if (job.status === "done" && job.result) {
            onGenerated("all", reloadToken + 1)
            onMessage(
              `已生成 ${job.result.total_modules} 个模块，期数 ${job.result.draw_count}，新增 ${job.result.inserted}，覆盖 ${job.result.updated}，失败 ${job.result.errors}`,
            )
            return
          }
          if (job.status === "error") {
            onMessage(`自动生成失败: ${job.error || "未知错误"}`)
            return
          }
        } catch {
          /* 继续轮询 */
        }
      }
      onMessage("批量生成超时，请稍后刷新页面查看结果")
    } catch (error) {
      onMessage(
        error instanceof Error ? error.message : "自动生成提交失败",
      )
    } finally {
      setBulkSubmitting(false)
    }
  }

  async function setQuickRange(n: number) {
    try {
      const lt = bulkLotteryType || String(site?.lottery_type_id || 3)
      const info = await adminApi<{ year: number; term: number }>(
        `/admin/lottery-draws/latest-term?lottery_type_id=${lt}`,
      )
      if (info.term > 0) {
        const endTerm = info.term + 1
        const startTerm = Math.max(1, endTerm - n + 1)
        setBulkStartIssue(
          `${info.year}${String(startTerm).padStart(3, "0")}`,
        )
        setBulkEndIssue(
          `${info.year}${String(endTerm).padStart(3, "0")}`,
        )
      } else {
        onMessage("未找到该彩种的已开奖数据")
      }
    } catch {
      onMessage("获取最新期数失败，请手动输入期号")
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => !bulkSubmitting && onClose()}
    >
      <div
        className="w-[560px] max-h-[85vh] overflow-y-auto rounded-lg bg-background p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-1 text-base font-semibold">自动生成资料</h3>
        <p className="mb-4 text-xs text-muted-foreground">
          选择模块和期数范围，在后台异步生成。
          {bulkSelectedKeys.size > 0 && (
            <span className="font-medium text-foreground">
              已选 {bulkSelectedKeys.size} 个模块
            </span>
          )}
        </p>

        <div className="mb-3">
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs font-medium">选择模块</label>
            <div className="flex gap-2">
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() =>
                  setBulkSelectedKeys(
                    new Set(modules.map((m) => m.mechanism_key)),
                  )
                }
              >
                全选
              </button>
              <button
                type="button"
                className="text-xs text-muted-foreground hover:underline"
                onClick={() => setBulkSelectedKeys(new Set())}
              >
                取消全选
              </button>
            </div>
          </div>
          <div className="max-h-[200px] overflow-y-auto rounded-md border p-2 space-y-0.5">
            {modules.map((m) => (
              <label
                key={m.id}
                className="flex items-center gap-2 cursor-pointer rounded px-1 py-0.5 hover:bg-muted text-xs"
              >
                <input
                  type="checkbox"
                  checked={bulkSelectedKeys.has(m.mechanism_key)}
                  onChange={(e) => {
                    const next = new Set(bulkSelectedKeys)
                    e.target.checked
                      ? next.add(m.mechanism_key)
                      : next.delete(m.mechanism_key)
                    setBulkSelectedKeys(next)
                  }}
                  className="h-3.5 w-3.5"
                />
                <span className="font-medium">
                  {m.display_title || m.mechanism_key}
                </span>
                <span className="text-muted-foreground">({m.mode_id})</span>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium">彩种</label>
            <select
              value={bulkLotteryType}
              onChange={(e) => setBulkLotteryType(e.target.value)}
              className="h-9 w-full rounded-md border bg-background px-3 text-sm"
            >
              <option value="1">香港</option>
              <option value="2">澳门</option>
              <option value="3">台湾</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">
              快捷期数范围（基于 lottery_draws 最新开奖数据）
            </label>
            <div className="flex gap-1.5">
              {[2, 10, 20, 50, 100].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setQuickRange(n)}
                  className="rounded-md border px-2.5 py-1 text-xs hover:bg-muted transition-colors"
                >
                  最近 {n} 期
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium">
                起始期号
              </label>
              <Input
                placeholder="例如 2026001"
                value={bulkStartIssue}
                onChange={(e) => setBulkStartIssue(e.target.value)}
                className="h-9 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">
                结束期号
              </label>
              <Input
                placeholder="例如 2026030"
                value={bulkEndIssue}
                onChange={(e) => setBulkEndIssue(e.target.value)}
                className="h-9 text-sm"
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={bulkSubmitting}
            onClick={onClose}
          >
            取消
          </Button>
          <Button size="sm" disabled={bulkSubmitting} onClick={doBulkGenerate}>
            {bulkSubmitting ? "生成中..." : "开始生成"}
          </Button>
        </div>
      </div>
    </div>
  )
}
