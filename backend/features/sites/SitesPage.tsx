"use client"

import type { FormEvent } from "react"
import { useEffect, useState } from "react"
import Link from "next/link"
import { Plus, Save } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
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
import { AdminNotice } from "@/features/shared/AdminNotice"
import { StatusBadge } from "@/features/shared/StatusBadge"
import { formValue, boolValue } from "@/features/shared/form-helpers"
import type { Site, LotteryType, AnyRecord } from "@/features/shared/types"

export function SitesPage() {
  const [rows, setRows] = useState<Site[]>([])
  const [lotteries, setLotteries] = useState<LotteryType[]>([])
  const [editing, setEditing] = useState<Site | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [message, setMessage] = useState("")

  async function load() {
    const [siteData, lotteryData] = await Promise.all([
      adminApi<{ sites: Site[] }>("/admin/sites"),
      adminApi<{ lottery_types: LotteryType[] }>("/admin/lottery-types"),
    ])
    setRows(siteData.sites)
    setLotteries(lotteryData.lottery_types)
  }

  useEffect(() => {
    void load()
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const payload: AnyRecord = {
      name: formValue(form, "name"),
      domain: formValue(form, "domain"),
      lottery_type_id: Number(formValue(form, "lottery_type_id")),
      enabled: boolValue(form, "enabled"),
      web_id: Number(formValue(form, "web_id")),
      announcement: formValue(form, "announcement"),
      notes: formValue(form, "notes"),
    }
    try {
      await adminApi(editing ? `/admin/sites/${editing.id}` : "/admin/sites", {
        method: editing ? "PUT" : "POST",
        body: jsonBody(payload),
      })
      setEditing(null)
      setFormOpen(false)
      form.reset()
      await load()
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败")
    }
  }

  function formatDate(iso: string | undefined) {
    if (!iso) return "-"
    return iso.replace("T", " ").slice(0, 19)
  }

  function siteLink(site: Site) {
    return site.domain ? `https://${site.domain}` : ""
  }

  return (
    <AdminShell
      title="站点管理"
      description="维护站点名称、域名、彩种、公告、状态和 web_id。"
    >
      <AdminNotice message={message} />
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
          {editing ? "修改站点" : "新增站点"}
        </Button>

        <div
          className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[1400px] opacity-100" : "max-h-0 opacity-0"}`}
        >
          <Card key={editing?.id || "new"} className="p-4">
            <h2 className="mb-3 text-base font-semibold">
              {editing ? "修改站点" : "新增站点"}
            </h2>
            <form className="grid grid-cols-1 gap-3 sm:grid-cols-2" onSubmit={submit}>
              <Field label="站点名称" className="col-span-2">
                <Input name="name" defaultValue={editing?.name || ""} required />
              </Field>
              <Field label="域名" className="col-span-2">
                <Input
                  name="domain"
                  defaultValue={editing?.domain || ""}
                  placeholder="example.com"
                />
              </Field>
              <Field label="彩种" className="col-span-2">
                <select
                  name="lottery_type_id"
                  defaultValue={editing?.lottery_type_id || lotteries[0]?.id || 1}
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                >
                  {lotteries.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="状态">
                <select
                  name="enabled"
                  defaultValue={editing?.enabled === false ? "0" : "1"}
                  className="h-9 rounded-md border bg-background px-3 text-sm"
                >
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <Field label="web_id">
                <Input
                  name="web_id"
                  type="number"
                  defaultValue={editing?.web_id || editing?.id || 1}
                  required
                />
              </Field>
              <Field label="网站公告" className="col-span-2">
                <Textarea
                  name="announcement"
                  defaultValue={editing?.announcement || ""}
                />
              </Field>
              <Field label="备注" className="col-span-2">
                <Textarea name="notes" defaultValue={editing?.notes || ""} />
              </Field>
              <div className="col-span-2 flex gap-2">
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

        <Card className="overflow-auto p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[60px]">ID</TableHead>
                <TableHead className="min-w-[80px]">web_id</TableHead>
                <TableHead className="min-w-[120px]">站点名称</TableHead>
                <TableHead className="min-w-[140px]">域名</TableHead>
                <TableHead className="min-w-[80px]">彩种</TableHead>
                <TableHead className="min-w-[60px]">状态</TableHead>
                <TableHead className="min-w-[150px]">创建时间</TableHead>
                <TableHead className="min-w-[240px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="py-8 text-center text-muted-foreground"
                  >
                    暂无站点数据
                  </TableCell>
                </TableRow>
              )}
              {rows.map((row) => {
                const link = siteLink(row)
                return (
                  <TableRow key={row.id}>
                    <TableCell>{row.id}</TableCell>
                    <TableCell>{row.web_id}</TableCell>
                    <TableCell className="font-medium">{row.name}</TableCell>
                    <TableCell>
                      {link ? (
                        <a
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block max-w-[200px] truncate text-blue-600 underline hover:text-blue-800"
                          title={link}
                        >
                          {row.domain}
                        </a>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                    <TableCell>{row.lottery_name}</TableCell>
                    <TableCell>
                      <StatusBadge value={row.enabled} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {formatDate(row.created_at)}
                    </TableCell>
                    <TableCell className="space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                          onClick={() => alert(row.announcement || "暂无公告")}
                        >
                        网站公告
                      </Button>
                      <Button asChild variant="outline" size="sm">
                        <Link href={`/sites/${row.id}/data`}>站点数据</Link>
                      </Button>
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
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      </div>
    </AdminShell>
  )
}
