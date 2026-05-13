"use client"

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
import type { Mechanism } from "@/features/shared/types"

type PredictionModulesTableProps = {
  rows: Mechanism[]
  toggling: Set<string>
  loading: boolean
  onToggle: (mechanismKey: string, currentStatus: number) => void
}

export function PredictionModulesTable({
  rows,
  toggling,
  loading,
  onToggle,
}: PredictionModulesTableProps) {
  return (
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
                    disabled={isToggling || loading}
                    onCheckedChange={() => onToggle(row.key, status)}
                  />
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </Card>
  )
}
