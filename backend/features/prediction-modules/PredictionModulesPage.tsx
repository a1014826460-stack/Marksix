"use client"

import { useEffect, useState } from "react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { adminApi } from "@/lib/admin-api"
import type { Mechanism } from "@/features/shared/types"

export function PredictionModulesPage() {
  const [rows, setRows] = useState<Mechanism[]>([])

  useEffect(() => {
    adminApi<{ mechanisms: Mechanism[] }>("/predict/mechanisms").then(
      (data) => setRows(data.mechanisms),
    )
  }, [])

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
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.key}>
                <TableCell>{row.key}</TableCell>
                <TableCell>{row.title}</TableCell>
                <TableCell>{row.default_modes_id}</TableCell>
                <TableCell>{row.default_table}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </AdminShell>
  )
}
