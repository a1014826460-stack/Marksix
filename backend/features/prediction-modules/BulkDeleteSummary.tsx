"use client"

import type { PredictionModulesBulkDeleteEstimate } from "@/features/prediction-modules/types"

type BulkDeleteSummaryProps = {
  summaryText: string
  estimate: PredictionModulesBulkDeleteEstimate | null
}

export function BulkDeleteSummary({
  summaryText,
  estimate,
}: BulkDeleteSummaryProps) {
  return (
    <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
      <div>{summaryText}</div>
      {estimate ? (
        <div className="mt-1 text-xs text-muted-foreground">
          预计删除约 {estimate.estimatedRows} 条记录
          {estimate.limitExceeded ? "，可能耗时较久，且已超过单次限制" : ""}
        </div>
      ) : null}
    </div>
  )
}
