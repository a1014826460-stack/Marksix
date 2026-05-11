"use client"

import type { FormEvent } from "react"
import { useEffect, useState } from "react"
import { Plus, Save } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { adminApi, jsonBody } from "@/lib/admin-api"
import { Field } from "@/features/shared/Field"
import { StatusBadge } from "@/features/shared/StatusBadge"
import { formValue, boolValue } from "@/features/shared/form-helpers"
import { formatNextTime, type LotteryType } from "@/features/shared/types"

export function LotteryTypesPage() {
  const [rows, setRows] = useState<LotteryType[]>([])
  const [editing, setEditing] = useState<LotteryType | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [crawlMsg, setCrawlMsg] = useState("")
  const [crawlingId, setCrawlingId] = useState(0)

  async function load() {
    const data = await adminApi<{ lottery_types: LotteryType[] }>(
      "/admin/lottery-types",
    )
    setRows(data.lottery_types)
  }

  useEffect(() => {
    load()
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    await adminApi(
      editing
        ? `/admin/lottery-types/${editing.id}`
        : "/admin/lottery-types",
      {
        method: editing ? "PUT" : "POST",
        body: jsonBody({
          name: formValue(form, "name"),
          draw_time: formValue(form, "draw_time"),
          collect_url: formValue(form, "collect_url"),
          status: boolValue(form, "status"),
        }),
      },
    )
    setEditing(null)
    setFormOpen(false)
    form.reset()
    await load()
  }

  async function crawlAndGenerate(ltId: number, ltName: string) {
    setCrawlingId(ltId)
    setCrawlMsg(`正在爬取 ${ltName} 开奖数据…`)
    try {
      const res = await adminApi<{
        ok: boolean
        saved: number
        fetched: number
        draw?: { year: number; term: number; issue: string } | null
        message?: string
        auto_task_scheduled_seconds?: number | null
      }>(`/admin/lottery-types/${ltId}/crawl-only`, { method: "POST" })
      if (res.message) {
        setCrawlMsg(`${ltName}: ${res.message}`)
      } else if (res.draw) {
        const autoInfo = res.auto_task_scheduled_seconds
          ? ` | 自动预测已预约 ${Math.round(res.auto_task_scheduled_seconds / 60)} 分钟后执行`
          : ""
        setCrawlMsg(
          `${ltName} 爬取完成 ✓ | 期号: ${res.draw.issue} | 存储: ${res.saved}/${res.fetched} 条${autoInfo}`,
        )
      } else {
        setCrawlMsg(`${ltName} 爬取完成（未获取到新数据）`)
      }
      setTimeout(() => setCrawlMsg(""), 12000)
      setCrawlingId(0)
    } catch (e) {
      setCrawlMsg(
        `${ltName} 请求失败: ${e instanceof Error ? e.message : "?"}`,
      )
      setCrawlingId(0)
    }
  }

  return (
    <AdminShell title="彩种管理" description="设置彩种名称、开奖时间、采集地址和状态。">
      {crawlMsg && (
        <div
          className={`rounded-md px-4 py-3 text-sm font-medium ${
            crawlMsg.includes("完成")
              ? "border border-green-300 bg-green-50 text-green-800"
              : crawlMsg.includes("失败") || crawlMsg.includes("超时")
                ? "border border-red-300 bg-red-50 text-red-800"
                : "border border-blue-300 bg-blue-50 text-blue-800"
          }`}
        >
          {crawlMsg}
        </div>
      )}
      <div className="space-y-4">
        <Button
          onClick={() => {
            setFormOpen((prev) => !prev)
            setEditing(null)
          }}
          className="group relative overflow-hidden transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <Plus
            className={`mr-1 h-4 w-4 transition-transform duration-300 ${formOpen ? "rotate-45" : "group-hover:rotate-90"}`}
          />
          新增彩种
        </Button>

        <div
          className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"}`}
        >
          <Card key={editing?.id || "new"} className="space-y-4 p-4">
            <h2 className="mb-3 text-base font-semibold">
              {editing ? "修改彩种" : "新增彩种"}
            </h2>
            <form className="space-y-3" onSubmit={submit}>
              <Field label="彩种名称">
                <Input
                  name="name"
                  defaultValue={editing?.name || ""}
                  required
                />
              </Field>
              <Field label="开奖时间">
                <Input
                  name="draw_time"
                  defaultValue={editing?.draw_time || ""}
                  placeholder="21:30"
                />
              </Field>
              <Field label="下次开奖时间 (自动从开奖记录推导)">
                <span className="block h-9 rounded-md border bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
                  {editing?.next_time
                    ? formatNextTime(editing.next_time)
                    : "暂无（保存后自动计算）"}
                </span>
              </Field>
              <Field label="采集地址">
                <Input
                  name="collect_url"
                  defaultValue={editing?.collect_url || ""}
                />
              </Field>
              <Field label="状态">
                <select
                  name="status"
                  defaultValue={editing?.status === false ? "0" : "1"}
                  className="h-9 rounded-md border bg-background px-3 text-sm"
                >
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <div className="flex gap-2">
                <Button type="submit" size="sm">
                  <Save className="mr-1 h-4 w-4" />
                  保存
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setFormOpen(false)
                    setEditing(null)
                  }}
                >
                  取消
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <Card className="space-y-4 p-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>彩种</TableHead>
                <TableHead>开奖时间</TableHead>
                <TableHead>下次开奖</TableHead>
                <TableHead>采集地址</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.draw_time}</TableCell>
                  <TableCell className="text-xs">
                    {formatNextTime(row.next_time)}
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">
                    {row.collect_url}
                  </TableCell>
                  <TableCell>
                    <StatusBadge value={row.status} />
                  </TableCell>
                  <TableCell className="space-x-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditing(row)
                        setFormOpen(true)
                      }}
                    >
                      修改
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => crawlAndGenerate(row.id, row.name)}
                      disabled={crawlingId !== 0}
                    >
                      {crawlingId === row.id ? "爬取中…" : "更新开奖"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </AdminShell>
  )
}
