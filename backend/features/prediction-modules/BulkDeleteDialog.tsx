"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ConfirmDialog } from "@/features/site-data/ConfirmDialog"
import { BulkDeleteModuleList } from "@/features/prediction-modules/BulkDeleteModuleList"
import { BulkDeleteSummary } from "@/features/prediction-modules/BulkDeleteSummary"
import type { Mechanism, SitePredictionModule } from "@/features/shared/types"
import type {
  PredictionModulesBulkDeleteEstimate,
  PredictionModulesBulkDeleteRequest,
} from "@/features/prediction-modules/types"

const MAX_DELETE_ROWS = 1000

type BulkDeleteDialogProps = {
  open: boolean
  modules: Array<Mechanism | SitePredictionModule>
  onClose: () => void
  onSubmit: (payload: PredictionModulesBulkDeleteRequest) => Promise<void>
  onEstimate: (
    payload: PredictionModulesBulkDeleteRequest,
  ) => Promise<PredictionModulesBulkDeleteEstimate>
}

function parsePeriod(value: string) {
  const normalized = value.trim()
  if (!/^\d+$/.test(normalized)) return null
  return Number(normalized)
}

export function BulkDeleteDialog({
  open,
  modules,
  onClose,
  onSubmit,
  onEstimate,
}: BulkDeleteDialogProps) {
  const [query, setQuery] = useState("")
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState("")
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [estimate, setEstimate] = useState<PredictionModulesBulkDeleteEstimate | null>(null)
  const [estimating, setEstimating] = useState(false)

  useEffect(() => {
    if (!open) {
      setQuery("")
      setSelectedIds([])
      setStart("")
      setEnd("")
      setSubmitting(false)
      setError("")
      setConfirmOpen(false)
      setEstimate(null)
      setEstimating(false)
    }
  }, [open])

  const normalizedModules = useMemo(() => {
    return modules.map((item) => {
      const maybeMechanism = item as Mechanism
      const maybeSiteModule = item as SitePredictionModule
      return {
        key: String(
          maybeMechanism.key ||
            maybeSiteModule.mechanism_key ||
            "",
        ),
        title: String(
          maybeMechanism.title ||
            maybeSiteModule.display_title ||
            maybeSiteModule.tables_title ||
            maybeSiteModule.title ||
            maybeSiteModule.mechanism_key ||
            "",
        ),
        default_table: String(
          maybeMechanism.default_table ||
            maybeSiteModule.default_table ||
            "",
        ),
        default_modes_id: Number(
          maybeMechanism.default_modes_id ||
            maybeSiteModule.default_modes_id ||
            maybeSiteModule.mode_id ||
            maybeSiteModule.resolved_mode_id ||
            0,
        ),
      }
    })
  }, [modules])

  const filteredModules = useMemo(() => {
    const keyword = query.trim().toLowerCase()
    if (!keyword) return normalizedModules
    return normalizedModules.filter((item) => {
      return (
        item.key.toLowerCase().includes(keyword) ||
        item.title.toLowerCase().includes(keyword) ||
        item.default_table.toLowerCase().includes(keyword) ||
        String(item.default_modes_id).includes(keyword)
      )
    })
  }, [normalizedModules, query])

  const periodRange = useMemo(() => {
    const startValue = parsePeriod(start)
    const endValue = parsePeriod(end)
    if (startValue == null || endValue == null) return null
    return { start: startValue, end: endValue }
  }, [start, end])

  const summaryText = useMemo(() => {
    const moduleCount = selectedIds.length
    const rangeText = periodRange
      ? `${periodRange.start} - ${periodRange.end}`
      : "未填写"
    return `已选 ${moduleCount} 个模块，期数范围 ${rangeText}`
  }, [periodRange, selectedIds.length])

  const selectedNames = useMemo(() => {
    const map = new Map(normalizedModules.map((item) => [item.key, item.title]))
    return selectedIds.map((item) => map.get(item) || item)
  }, [normalizedModules, selectedIds])

  if (!open) return null

  function buildPayload() {
    if (selectedIds.length === 0) {
      throw new Error("请至少选择一个模块")
    }
    if (!periodRange) {
      throw new Error("请填写有效的起始和结束期数")
    }
    if (periodRange.end < periodRange.start) {
      throw new Error("结束期数必须大于或等于起始期数")
    }
    return {
      moduleIds: selectedIds,
      periodRange,
    }
  }

  async function prepareConfirm() {
    setError("")
    try {
      const payload = buildPayload()
      setEstimating(true)
      const nextEstimate = await onEstimate(payload)
      setEstimate(nextEstimate)
      setConfirmOpen(true)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "无法估算删除数量")
    } finally {
      setEstimating(false)
    }
  }

  async function handleConfirmDelete() {
    setError("")
    if (estimate?.limitExceeded) {
      setConfirmOpen(false)
      setError(`预计删除约 ${estimate.estimatedRows} 条记录，已超过单次 ${MAX_DELETE_ROWS} 条限制`)
      return
    }
    setSubmitting(true)
    try {
      const payload = buildPayload()
      await onSubmit(payload)
      toast.success("批量删除完成")
      onClose()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "批量删除失败")
    } finally {
      setSubmitting(false)
      setConfirmOpen(false)
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        onClick={() => !submitting && onClose()}
      >
        <div
          className="w-[600px] max-h-[85vh] overflow-y-auto rounded-lg bg-background p-6 shadow-xl"
          onClick={(event) => event.stopPropagation()}
        >
          <h3 className="mb-1 text-base font-semibold">批量删除预测模块数据</h3>
          <p className="mb-4 text-xs text-muted-foreground">
            参考批量生成流程，按模块和期数范围一次性清理测试数据。
          </p>

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium">搜索模块</label>
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="按标题、key、modes_id 或表名搜索"
              />
            </div>

            <BulkDeleteModuleList
              modules={filteredModules}
              selectedIds={selectedIds}
              onChange={setSelectedIds}
            />

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium">起始期数</label>
                <Input
                  value={start}
                  onChange={(event) => setStart(event.target.value)}
                  placeholder="例如 2026001"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium">结束期数</label>
                <Input
                  value={end}
                  onChange={(event) => setEnd(event.target.value)}
                  placeholder="例如 2026030"
                />
              </div>
            </div>

            <BulkDeleteSummary summaryText={summaryText} estimate={estimate} />

            {error ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="outline" size="sm" disabled={submitting} onClick={onClose}>
              取消
            </Button>
            <Button size="sm" disabled={submitting || estimating} onClick={prepareConfirm}>
              {estimating ? (
                <>
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  估算中...
                </>
              ) : (
                "确认删除"
              )}
            </Button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="确认批量删除"
        message={
          <div className="space-y-2">
            <p>此操作不可逆，是否继续？</p>
            <p>模块：{selectedNames.join("、") || "未选择"}</p>
            <p>
              期数范围：
              {periodRange ? `${periodRange.start} - ${periodRange.end}` : "未填写"}
            </p>
            {estimate ? (
              <p>
                预计删除约 {estimate.estimatedRows} 条记录
                {estimate.estimatedRows > MAX_DELETE_ROWS ? "，可能耗时较久" : ""}
              </p>
            ) : null}
          </div>
        }
        confirmText={submitting ? "删除中..." : "确认删除"}
        onConfirm={handleConfirmDelete}
        onCancel={() => !submitting && setConfirmOpen(false)}
      />
    </>
  )
}
