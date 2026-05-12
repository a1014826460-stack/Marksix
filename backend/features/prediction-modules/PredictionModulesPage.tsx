"use client"

import { useEffect, useState } from "react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { adminApi, jsonBody } from "@/lib/admin-api"
import type { Mechanism } from "@/features/shared/types"

export function PredictionModulesPage() {
  const [rows, setRows] = useState<Mechanism[]>([])
  const [toggling, setToggling] = useState<Set<string>>(new Set())

  useEffect(() => {
    adminApi<{ mechanisms: Mechanism[] }>("/predict/mechanisms").then(
      (data) => setRows(data.mechanisms),
    )
  }, [])

  const handleToggle = async (mechanismKey: string, currentStatus: number) => {
    const newStatus = currentStatus === 1 ? 0 : 1
    setToggling((prev) => new Set(prev).add(mechanismKey))
    try {
      await adminApi(
        `/admin/predict/mechanisms/${encodeURIComponent(mechanismKey)}/status`,
        { method: "PATCH", body: jsonBody({ status: newStatus }) },
      )
      setRows((prev) =>
        prev.map((r) => (r.key === mechanismKey ? { ...r, status: newStatus } : r)),
      )
    } catch {
      // 操作失败时不更新 UI 状态
    } finally {
      setToggling((prev) => {
        const next = new Set(prev)
        next.delete(mechanismKey)
        return next
      })
    }
  }

  return (
    <AdminShell
      title="预测模块"
      description="由 mechanisms.py 自动提供的预测模块与本地 SQLite 数据源。"
    >
      <Card className="p-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>key</TableHead>
              <TableHead>标题</TableHead>
              <TableHead>modes_id</TableHead>
              <TableHead>数据表</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const status = row.status ?? 1
              const isToggling = toggling.has(row.key)
              return (
                <TableRow key={row.key}>
                  <TableCell>{row.key}</TableCell>
                  <TableCell>{row.title}</TableCell>
                  <TableCell>{row.default_modes_id}</TableCell>
                  <TableCell>{row.default_table}</TableCell>
                  <TableCell>
                    <span className={status === 1 ? "text-green-600" : "text-gray-400"}>
                      {status === 1 ? "启用" : "禁用"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={status === 1}
                      disabled={isToggling}
                      onCheckedChange={() => handleToggle(row.key, status)}
                    />
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </Card>
    </AdminShell>
  )
}
