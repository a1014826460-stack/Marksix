"use client"

import { useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { adminApi } from "@/lib/admin-api"
import { cn } from "@/lib/utils"
import { ToolbarButton } from "@/features/shared/ToolbarButton"
import { AdminNotice } from "@/features/shared/AdminNotice"
import { isLongSummaryValue } from "@/features/shared/form-helpers"
import type { ApiSummary } from "@/features/shared/types"

export function DashboardPage() {
  const [summary, setSummary] = useState<Record<string, string | number>>({})
  const [message, setMessage] = useState("")

  async function load() {
    try {
      const data = await adminApi<ApiSummary>("/health")
      setSummary(data.summary)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载失败")
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <AdminShell
      title="控制台"
      description="查看本地 SQLite 数据、预测机制和文本历史映射的运行概况。"
      actions={
        <ToolbarButton onClick={load}>
          <RefreshCw className="mr-1 h-4 w-4" />
          刷新
        </ToolbarButton>
      }
    >
      <AdminNotice message={message} />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {Object.entries(summary).map(([key, value]) => (
          <Card key={key} className="min-w-0 p-4">
            <div
              title={String(value)}
              className={cn(
                "min-w-0 font-semibold leading-snug",
                isLongSummaryValue(value)
                  ? "break-all text-xs text-muted-foreground"
                  : "text-2xl tabular-nums",
              )}
            >
              {value}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{key}</div>
          </Card>
        ))}
      </div>
    </AdminShell>
  )
}
