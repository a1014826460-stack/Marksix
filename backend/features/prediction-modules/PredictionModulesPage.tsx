"use client"

import { useState } from "react"
import { RefreshCw } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Button } from "@/components/ui/button"
import { AdminNotice } from "@/features/shared/AdminNotice"
import { PredictionModulesTable } from "@/features/prediction-modules/PredictionModulesTable"
import { usePredictionModules } from "@/features/prediction-modules/usePredictionModules"

export function PredictionModulesPage() {
  const [message, setMessage] = useState("")
  const {
    rows,
    loading,
    error,
    toggling,
    load,
    toggleStatus,
  } = usePredictionModules()

  async function handleToggle(mechanismKey: string, currentStatus: number) {
    try {
      await toggleStatus(mechanismKey, currentStatus)
      setMessage("")
    } catch (toggleError) {
      setMessage(toggleError instanceof Error ? toggleError.message : "更新模块状态失败")
    }
  }

  return (
    <AdminShell
      title="预测模块"
      description="管理机制启用状态。批量生成和批量删除入口已放到对应站点的数据管理页。"
      actions={
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="mr-1 h-4 w-4" />
          刷新
        </Button>
      }
    >
      <AdminNotice message={message || error} />
      <PredictionModulesTable
        rows={rows}
        toggling={toggling}
        loading={loading}
        onToggle={handleToggle}
      />
    </AdminShell>
  )
}
