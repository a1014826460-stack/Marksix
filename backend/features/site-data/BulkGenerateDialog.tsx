"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi, jsonBody } from "@/lib/admin-api"
import type {
  LotteryType,
  Site,
  SitePredictionModule,
} from "@/features/shared/types"

type GenerateJobResult = {
  total_modules: number
  draw_count: number
  inserted: number
  updated: number
  errors: number
}

type CurrentPeriodResponse = {
  lottery_type_id: number
  lottery_name: string
  current_period: string
  current_year: number
  current_term: number
}

type LatestTermResponse = {
  year: number
  term: number
  draw_time: string
}

type BackfillResponse = {
  ok: boolean
  data: {
    lottery_type_id: number
    start_issue: string
    end_issue: string
    draw_count: number
    total_affected: number
    table_names: string[]
  }
}

type BulkGenerateDialogProps = {
  open: boolean
  site: Site | null
  lotteryTypes?: LotteryType[]
  modules: SitePredictionModule[]
  onClose: () => void
  onMessage: (msg: string) => void
  onGenerated: (sourceFilter: string, reloadToken: number) => void
  onSubmitGenerate?: (params: {
    siteId: number
    lotteryType: string
    startIssue: string
    endIssue: string
    mechanismKeys: string[]
    futureOnly: boolean
  }) => Promise<GenerateJobResult>
  reloadToken: number
}

const DEFAULT_LOTTERY_OPTIONS: LotteryType[] = [
  { id: 1, name: "香港", draw_time: "", collect_url: "", status: true },
  { id: 2, name: "澳门", draw_time: "", collect_url: "", status: true },
  { id: 3, name: "台湾", draw_time: "", collect_url: "", status: true },
]

const QUICK_ACTIONS = [
  { key: "future", label: "未来一期", mode: "future" as const, count: 1 },
  { key: "last2", label: "最近两期", mode: "history" as const, count: 2 },
  { key: "last10", label: "最近十期", mode: "history" as const, count: 10 },
  { key: "last20", label: "最近二十期", mode: "history" as const, count: 20 },
]

function padTerm(term: number) {
  return String(term).padStart(3, "0")
}

function formatIssue(year: number, term: number) {
  return `${year}${padTerm(term)}`
}

function parseIssue(issue: string) {
  const digits = issue.trim().replace(/\D/g, "")
  if (digits.length < 5) return null
  const year = Number(digits.slice(0, 4))
  const term = Number(digits.slice(4))
  if (!Number.isFinite(year) || !Number.isFinite(term) || term <= 0) return null
  return { year, term }
}

function shiftIssueBackward(year: number, term: number, offset: number) {
  let nextYear = year
  let nextTerm = term
  let remain = offset

  while (remain > 0) {
    if (nextTerm > 1) {
      nextTerm -= 1
    } else {
      nextYear -= 1
      nextTerm = 365
    }
    remain -= 1
  }

  return formatIssue(nextYear, nextTerm)
}

export function BulkGenerateDialog({
  open,
  site,
  lotteryTypes = DEFAULT_LOTTERY_OPTIONS,
  modules,
  onClose,
  onMessage,
  onGenerated,
  onSubmitGenerate,
  reloadToken,
}: BulkGenerateDialogProps) {
  const [bulkLotteryType, setBulkLotteryType] = useState(
    () => String(site?.lottery_type_id || 3),
  )
  const [bulkStartIssue, setBulkStartIssue] = useState("")
  const [bulkEndIssue, setBulkEndIssue] = useState("")
  const [bulkFutureOnly, setBulkFutureOnly] = useState(true)
  const [bulkSubmitting, setBulkSubmitting] = useState(false)
  const [backfilling, setBackfilling] = useState(false)
  const [loadingQuickRange, setLoadingQuickRange] = useState("")
  const [bulkSelectedKeys, setBulkSelectedKeys] = useState<Set<string>>(new Set())

  useEffect(() => {
    setBulkLotteryType(String(site?.lottery_type_id || 3))
  }, [site?.lottery_type_id])

  const enabledModules = useMemo(
    () => modules.filter((item) => item.status),
    [modules],
  )

  const selectedModules = useMemo(
    () => enabledModules.filter((item) => bulkSelectedKeys.has(item.mechanism_key)),
    [enabledModules, bulkSelectedKeys],
  )

  const selectedCount = bulkSelectedKeys.size
  const isBusy = bulkSubmitting || backfilling || loadingQuickRange !== ""

  if (!open) return null

  async function loadCurrentPeriod() {
    const lotteryType = bulkLotteryType || String(site?.lottery_type_id || 3)
    try {
      return await adminApi<CurrentPeriodResponse>(
        `/public/current-period?lottery_type=${encodeURIComponent(lotteryType)}`,
      )
    } catch {
      const legacy = await adminApi<LatestTermResponse>(
        `/admin/lottery-draws/latest-term?lottery_type_id=${encodeURIComponent(lotteryType)}`,
      )
      return {
        lottery_type_id: Number(lotteryType),
        lottery_name: "",
        current_period:
          legacy.year > 0 && legacy.term > 0
            ? formatIssue(legacy.year, legacy.term)
            : "",
        current_year: legacy.year || 0,
        current_term: legacy.term || 0,
      }
    }
  }

  async function applyQuickAction(action: (typeof QUICK_ACTIONS)[number]) {
    setLoadingQuickRange(action.key)
    try {
      const data = await loadCurrentPeriod()
      if (!data.current_period) {
        throw new Error("当前彩种暂无已开奖期号，无法套用快捷范围")
      }

      if (action.mode === "future") {
        const parsed = parseIssue(data.current_period)
        if (!parsed) {
          throw new Error("当前期号格式无效，无法计算未来一期")
        }
        const nextIssue = formatIssue(parsed.year, parsed.term + 1)
        setBulkStartIssue(nextIssue)
        setBulkEndIssue(nextIssue)
        setBulkFutureOnly(true)
        return
      }

      setBulkEndIssue(data.current_period)
      setBulkStartIssue(
        shiftIssueBackward(data.current_year, data.current_term, action.count - 1),
      )
      setBulkFutureOnly(false)
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "快捷期数设置失败")
    } finally {
      setLoadingQuickRange("")
    }
  }

  async function doBulkGenerate() {
    if (!site?.id) {
      onMessage("当前站点信息加载失败，请刷新后重试")
      return
    }
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
      const executor = onSubmitGenerate
      if (!executor) {
        throw new Error("未配置生成执行器")
      }
      const result = await executor({
        siteId: Number(site.id),
        lotteryType: bulkLotteryType || String(site?.lottery_type_id || 3),
        startIssue: bulkStartIssue.trim(),
        endIssue: bulkEndIssue.trim(),
        mechanismKeys: selectedList,
        futureOnly: bulkFutureOnly,
      })
      onGenerated("all", reloadToken + 1)
      onMessage(
        `已生成 ${result.total_modules} 个模块，期数 ${result.draw_count}，新增 ${result.inserted}，覆盖 ${result.updated}，失败 ${result.errors}`,
      )
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "自动生成提交失败")
    } finally {
      setBulkSubmitting(false)
    }
  }

  async function doBackfill() {
    if (!bulkStartIssue.trim() || !bulkEndIssue.trim()) {
      onMessage("请先填写完整的起始期号和结束期号")
      return
    }
    if (selectedModules.length === 0) {
      onMessage("请至少选择一个模块")
      return
    }

    setBackfilling(true)
    try {
      const result = await adminApi<BackfillResponse>("/admin/backfill-predictions", {
        method: "POST",
        body: jsonBody({
          lottery_type_id: Number(bulkLotteryType || site?.lottery_type_id || 3),
          start_issue: bulkStartIssue.trim(),
          end_issue: bulkEndIssue.trim(),
          table_names: selectedModules
            .map((item) => item.default_table)
            .filter((item): item is string => Boolean(item)),
        }),
      })

      onGenerated("all", reloadToken + 1)
      onMessage(
        `历史回填完成：${result.data.draw_count} 期，影响 ${result.data.total_affected} 条记录`,
      )
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "历史回填失败")
    } finally {
      setBackfilling(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => !isBusy && onClose()}
    >
      <div
        className="w-[560px] max-h-[85vh] overflow-y-auto rounded-lg bg-background p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <h3 className="mb-1 text-base font-semibold">自动生成资料</h3>
        <p className="mb-4 text-xs text-muted-foreground">
          选择彩种、模块和期数范围，在当前站点上生成或回填资料。
          {selectedCount > 0 ? (
            <span className="font-medium text-foreground">
              {" "}
              已选 {selectedCount} 个模块
            </span>
          ) : null}
        </p>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium">当前站点</label>
            <div className="flex h-9 items-center rounded-md border bg-muted/20 px-3 text-sm">
              {site?.name || "未加载"}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium">彩种</label>
            <select
              value={bulkLotteryType}
              onChange={(event) => setBulkLotteryType(event.target.value)}
              className="h-9 w-full rounded-md border bg-background px-3 text-sm"
              disabled={isBusy}
            >
              {lotteryTypes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="text-xs font-medium">预测模块</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  disabled={isBusy}
                  onClick={() =>
                    setBulkSelectedKeys(
                      new Set(enabledModules.map((item) => item.mechanism_key)),
                    )
                  }
                >
                  全选
                </button>
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:underline"
                  disabled={isBusy}
                  onClick={() => setBulkSelectedKeys(new Set())}
                >
                  取消全选
                </button>
              </div>
            </div>
            <div className="max-h-[200px] space-y-0.5 overflow-y-auto rounded-md border p-2">
              {enabledModules.map((item) => (
                <label
                  key={item.id}
                  className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-muted"
                >
                  <input
                    type="checkbox"
                    checked={bulkSelectedKeys.has(item.mechanism_key)}
                    onChange={(event) => {
                      const next = new Set(bulkSelectedKeys)
                      if (event.target.checked) {
                        next.add(item.mechanism_key)
                      } else {
                        next.delete(item.mechanism_key)
                      }
                      setBulkSelectedKeys(next)
                    }}
                    disabled={isBusy}
                    className="h-3.5 w-3.5"
                  />
                  <span className="font-medium">
                    {item.display_title || item.mechanism_key}
                  </span>
                  <span className="text-muted-foreground">
                    ({item.mode_id || item.default_modes_id || "?"})
                  </span>
                </label>
              ))}
            </div>
          </div>

          <label className="flex items-start gap-2 rounded-md border px-3 py-2 text-xs">
            <input
              type="checkbox"
              checked={bulkFutureOnly}
              onChange={(event) => setBulkFutureOnly(event.target.checked)}
              disabled={isBusy}
              className="mt-0.5 h-3.5 w-3.5"
            />
            <span>
              只生成未来期
              <span className="ml-1 text-muted-foreground">
                勾选后会保留范围内原有资料，只生成基准期之后的未来期预测。
              </span>
            </span>
          </label>

          <div className="space-y-2">
            <label className="block text-xs font-medium">快捷期数</label>
            <div className="flex flex-wrap gap-2">
              {QUICK_ACTIONS.map((action) => (
                <Button
                  key={action.key}
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={isBusy}
                  onClick={() => applyQuickAction(action)}
                  className="h-8 text-xs"
                >
                  {loadingQuickRange === action.key ? (
                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                  ) : null}
                  {action.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium">起始期号</label>
              <Input
                placeholder="例如 2026001"
                value={bulkStartIssue}
                onChange={(event) => setBulkStartIssue(event.target.value)}
                className="h-9 text-sm"
                disabled={isBusy}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">结束期号</label>
              <Input
                placeholder="例如 2026030"
                value={bulkEndIssue}
                onChange={(event) => setBulkEndIssue(event.target.value)}
                className="h-9 text-sm"
                disabled={isBusy}
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button variant="outline" size="sm" disabled={isBusy} onClick={onClose}>
            取消
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={isBusy}
            onClick={doBackfill}
          >
            {backfilling ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                回填中...
              </>
            ) : (
              "回填历史数据"
            )}
          </Button>
          <Button size="sm" disabled={isBusy} onClick={doBulkGenerate}>
            {bulkSubmitting ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                生成中...
              </>
            ) : (
              "开始生成"
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
