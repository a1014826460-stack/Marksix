"use client"

import React, { useEffect, useMemo, useRef, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Plus, RefreshCw, Save, Trash2 } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { adminApi, jsonBody, setAdminToken } from "@/lib/admin-api"
import { cn } from "@/lib/utils"

type AnyRecord = Record<string, any>

type ApiSummary = {
  summary: Record<string, string | number>
}

type User = {
  id: number
  username: string
  display_name: string
  role: string
  status: boolean
  last_login_at?: string
}

type LotteryType = {
  id: number
  name: string
  draw_time: string
  collect_url: string
  status: boolean
}

type Draw = {
  id: number
  lottery_type_id: number
  lottery_name: string
  year: number
  term: number
  numbers: string
  draw_time: string
  status: boolean
  is_opened: boolean
  next_term: number
}

type Site = {
  id: number
  name: string
  domain: string
  lottery_type_id: number
  lottery_name?: string
  enabled: boolean
  start_web_id: number
  end_web_id: number
  manage_url_template: string
  modes_data_url: string
  request_limit: number
  request_delay: number
  announcement?: string
  notes?: string
  created_at: string
  token_present?: boolean
  token_preview?: string
}

type NumberRow = {
  id: number
  name: string
  code: string
  category_key: string
  year: string
  status: boolean
  type: number
}

type Mechanism = {
  key: string
  title: string
  mode_id?: number
  default_modes_id: number
  default_table: string
  configured?: boolean
}

type SitePredictionModule = {
  id: number
  mechanism_key: string
  mode_id?: number
  title?: string
  tables_title?: string
  default_modes_id?: number
  default_table?: string
  status: boolean
  sort_order: number
}

type BulkGenerateResult = {
  site_id: number
  site_name: string
  lottery_type: number
  start_issue: string
  end_issue: string
  web_id: number
  total_modules: number
  draw_count: number
  inserted: number
  updated: number
  errors: number
  modules: Array<{
    module_id: number
    mechanism_key: string
    mode_id: number
    table_name: string
    draw_count: number
    inserted: number
    updated: number
    errors: number
    error_message: string
  }>
}

function StatusBadge({ value }: { value: boolean }) {
  return (
    <Badge variant={value ? "default" : "secondary"}>
      {value ? "启用" : "停用"}
    </Badge>
  )
}

function ToolbarButton({
  children,
  onClick,
}: {
  children: ReactNode
  onClick: () => void
}) {
  return (
    <Button variant="outline" size="sm" onClick={onClick}>
      {children}
    </Button>
  )
}

function Field({
  label,
  children,
  className,
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <label className={className}>
      <span className="mb-1 block text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  )
}

function AdminNotice({ message }: { message: string }) {
  if (!message) return null
  return (
    <div className="rounded-md border border-border bg-secondary px-3 py-2 text-sm text-secondary-foreground">
      {message}
    </div>
  )
}

function formValue(form: HTMLFormElement, name: string) {
  return String(new FormData(form).get(name) || "").trim()
}

function boolValue(form: HTMLFormElement, name: string) {
  return formValue(form, name) === "1"
}

function isLongSummaryValue(value: string | number) {
  return String(value).length > 24
}

export function LoginPageClient() {
  const router = useRouter()
  const [message, setMessage] = useState("")

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    try {
      const result = await adminApi<{ token: string }>("/auth/login", {
        method: "POST",
        body: jsonBody({
          username: formValue(form, "username"),
          password: formValue(form, "password"),
        }),
      })
      setAdminToken(result.token)
      router.replace("/")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败")
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm p-6">
        <h1 className="text-xl font-semibold">彩票软件后台登录</h1>
        <p className="mt-1 text-sm text-muted-foreground">默认账号：admin，默认密码：admin123。上线后请立即修改。</p>
        <form className="mt-5 space-y-3" onSubmit={submit}>
          <Field label="用户名">
            <Input name="username" defaultValue="admin" autoComplete="username" />
          </Field>
          <Field label="密码">
            <Input name="password" type="password" defaultValue="admin123" autoComplete="current-password" />
          </Field>
          <AdminNotice message={message} />
          <Button className="w-full" type="submit">
            登录
          </Button>
        </form>
      </Card>
    </main>
  )
}

export function DashboardPageClient() {
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

export function UsersPageClient() {
  const [rows, setRows] = useState<User[]>([])
  const [editing, setEditing] = useState<User | null>(null)
  const [message, setMessage] = useState("")

  async function load() {
    const data = await adminApi<{ users: User[] }>("/admin/users")
    setRows(data.users)
  }

  useEffect(() => {
    load().catch((error) => setMessage(error.message))
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const payload: AnyRecord = {
      username: formValue(form, "username"),
      display_name: formValue(form, "display_name"),
      role: formValue(form, "role"),
      status: boolValue(form, "status"),
      password: formValue(form, "password"),
    }
    if (!payload.password) delete payload.password
    await adminApi(editing ? `/admin/users/${editing.id}` : "/admin/users", {
      method: editing ? "PUT" : "POST",
      body: jsonBody(payload),
    })
    setEditing(null)
    form.reset()
    await load()
  }

  async function remove(id: number) {
    if (!confirm("确认删除该管理员？")) return
    await adminApi(`/admin/users/${id}`, { method: "DELETE" })
    await load()
  }

  return (
    <AdminShell title="管理员用户管理" description="决定哪些用户可以登录后台系统。">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_1fr]">
        <Card className="space-y-4 p-4">
          <h2 className="mb-3 text-base font-semibold">{editing ? "修改管理员" : "新增管理员"}</h2>
          <form className="space-y-3" onSubmit={submit}>
            <Field label="用户名"><Input name="username" defaultValue={editing?.username || ""} required /></Field>
            <Field label="显示名称"><Input name="display_name" defaultValue={editing?.display_name || ""} /></Field>
            <Field label="角色"><Input name="role" defaultValue={editing?.role || "admin"} /></Field>
            <Field label="状态">
              <select name="status" defaultValue={editing?.status === false ? "0" : "1"} className="h-9 rounded-md border bg-background px-3 text-sm">
                <option value="1">启用</option>
                <option value="0">停用</option>
              </select>
            </Field>
            <Field label={editing ? "新密码（留空不变）" : "密码"}><Input name="password" type="password" required={!editing} /></Field>
            <Button type="submit" size="sm"><Save className="mr-1 h-4 w-4" />保存</Button>
          </form>
        </Card>
        <Card className="space-y-4 p-4">
          <AdminNotice message={message} />
          <Table>
            <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>用户名</TableHead><TableHead>角色</TableHead><TableHead>状态</TableHead><TableHead>操作</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell>
                  <TableCell><b>{row.display_name}</b><br /><span className="text-xs text-muted-foreground">{row.username}</span></TableCell>
                  <TableCell>{row.role}</TableCell>
                  <TableCell><StatusBadge value={row.status} /></TableCell>
                  <TableCell className="space-x-2">
                    <Button variant="outline" size="sm" onClick={() => setEditing(row)}>修改</Button>
                    <Button variant="outline" size="sm" onClick={() => remove(row.id)}><Trash2 className="h-4 w-4" /></Button>
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

export function LotteryTypesPageClient() {
  const [rows, setRows] = useState<LotteryType[]>([])
  const [editing, setEditing] = useState<LotteryType | null>(null)
  const [formOpen, setFormOpen] = useState(false)

  async function load() {
    const data = await adminApi<{ lottery_types: LotteryType[] }>("/admin/lottery-types")
    setRows(data.lottery_types)
  }

  useEffect(() => { load() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    await adminApi(editing ? `/admin/lottery-types/${editing.id}` : "/admin/lottery-types", {
      method: editing ? "PUT" : "POST",
      body: jsonBody({
        name: formValue(form, "name"),
        draw_time: formValue(form, "draw_time"),
        collect_url: formValue(form, "collect_url"),
        status: boolValue(form, "status"),
      }),
    })
    setEditing(null)
    setFormOpen(false)
    form.reset()
    await load()
  }

  return (
    <AdminShell title="彩种管理" description="设置彩种名称、开奖时间、采集地址和状态。">
      <div className="space-y-4">
        <Button
          onClick={() => { setFormOpen((prev) => !prev); setEditing(null) }}
          className="group relative overflow-hidden transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <Plus className={`mr-1 h-4 w-4 transition-transform duration-300 ${formOpen ? "rotate-45" : "group-hover:rotate-90"}`} />
          新增彩种
        </Button>

        <div className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"}`}>
          <Card key={editing?.id || "new"} className="space-y-4 p-4">
            <h2 className="mb-3 text-base font-semibold">{editing ? "修改彩种" : "新增彩种"}</h2>
            <form className="space-y-3" onSubmit={submit}>
              <Field label="彩种名称"><Input name="name" defaultValue={editing?.name || ""} required /></Field>
              <Field label="开奖时间"><Input name="draw_time" defaultValue={editing?.draw_time || ""} placeholder="21:30" /></Field>
              <Field label="采集地址"><Input name="collect_url" defaultValue={editing?.collect_url || ""} /></Field>
              <Field label="状态">
                <select name="status" defaultValue={editing?.status === false ? "0" : "1"} className="h-9 rounded-md border bg-background px-3 text-sm">
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <div className="flex gap-2">
                <Button type="submit" size="sm"><Save className="mr-1 h-4 w-4" />保存</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => { setFormOpen(false); setEditing(null) }}>取消</Button>
              </div>
            </form>
          </Card>
        </div>

        <Card className="space-y-4 p-4">
          <Table>
            <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>彩种</TableHead><TableHead>开奖时间</TableHead><TableHead>采集地址</TableHead><TableHead>状态</TableHead><TableHead>操作</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell><TableCell>{row.name}</TableCell><TableCell>{row.draw_time}</TableCell><TableCell className="max-w-[280px] truncate">{row.collect_url}</TableCell><TableCell><StatusBadge value={row.status} /></TableCell>
                  <TableCell><Button variant="outline" size="sm" onClick={() => { setEditing(row); setFormOpen(true) }}>修改</Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </AdminShell>
  )
}

export function DrawsPageClient() {
  const [rows, setRows] = useState<Draw[]>([])
  const [lotteries, setLotteries] = useState<LotteryType[]>([])
  const [editing, setEditing] = useState<Draw | null>(null)
  const [formOpen, setFormOpen] = useState(false)

  async function load() {
    const [drawData, lotteryData] = await Promise.all([
      adminApi<{ draws: Draw[] }>("/admin/draws"),
      adminApi<{ lottery_types: LotteryType[] }>("/admin/lottery-types"),
    ])
    setRows(drawData.draws)
    setLotteries(lotteryData.lottery_types)
  }
  useEffect(() => { load() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    await adminApi(editing ? `/admin/draws/${editing.id}` : "/admin/draws", {
      method: editing ? "PUT" : "POST",
      body: jsonBody({
        lottery_type_id: Number(formValue(form, "lottery_type_id")),
        year: Number(formValue(form, "year")),
        term: Number(formValue(form, "term")),
        numbers: formValue(form, "numbers"),
        draw_time: formValue(form, "draw_time"),
        status: boolValue(form, "status"),
        is_opened: boolValue(form, "is_opened"),
        next_term: Number(formValue(form, "next_term")),
      }),
    })
    setEditing(null)
    setFormOpen(false)
    form.reset()
    await load()
  }

  async function remove(id: number) {
    if (!confirm("确认删除该开奖记录？")) return
    await adminApi(`/admin/draws/${id}`, { method: "DELETE" })
    await load()
  }

  return (
    <AdminShell title="开奖管理" description="为台湾彩种添加开奖号码，为预测提供数据依据。">
      <div className="space-y-4">
        <Button
          onClick={() => { setFormOpen((prev) => !prev); setEditing(null) }}
          className="group relative overflow-hidden transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <Plus className={`mr-1 h-4 w-4 transition-transform duration-300 ${formOpen ? "rotate-45" : "group-hover:rotate-90"}`} />
          新增开奖记录
        </Button>

        <div className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"}`}>
          <Card key={editing?.id || "new"} className="p-4">
            <h2 className="mb-3 text-base font-semibold">{editing ? "修改开奖记录" : "新增开奖记录"}</h2>
            <form className="grid grid-cols-2 gap-3" onSubmit={submit}>
              <Field label="彩种" className="col-span-2">
                <select name="lottery_type_id" defaultValue={editing?.lottery_type_id || 3} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
                  {lotteries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </Field>
              <Field label="年份"><Input name="year" type="number" defaultValue={editing?.year || new Date().getFullYear()} /></Field>
              <Field label="期数"><Input name="term" type="number" defaultValue={editing?.term || 1} /></Field>
              <Field label="开奖号码" className="col-span-2"><Input name="numbers" defaultValue={editing?.numbers || ""} placeholder="02,25,11,33,06,41,01" /></Field>
              <Field label="开奖时间" className="col-span-2"><Input name="draw_time" defaultValue={editing?.draw_time || ""} /></Field>
              <Field label="状态">
                <select name="status" defaultValue={editing?.status === false ? "0" : "1"} className="h-9 rounded-md border bg-background px-3 text-sm">
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <Field label="是否开奖">
                <select name="is_opened" defaultValue={editing?.is_opened ? "1" : "0"} className="h-9 rounded-md border bg-background px-3 text-sm">
                  <option value="1">已开奖</option>
                  <option value="0">未开奖</option>
                </select>
              </Field>
              <Field label="下一期数" className="col-span-2"><Input name="next_term" type="number" defaultValue={editing?.next_term || 2} /></Field>
              <div className="col-span-2 flex gap-2">
                <Button type="submit" size="sm"><Save className="mr-1 h-4 w-4" />保存</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => { setFormOpen(false); setEditing(null) }}>取消</Button>
              </div>
            </form>
          </Card>
        </div>

        <Card className="p-4">
          <Table>
            <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>彩种</TableHead><TableHead>年份</TableHead><TableHead>期数</TableHead><TableHead>开奖号码</TableHead><TableHead>开奖时间</TableHead><TableHead>状态</TableHead><TableHead>是否开奖</TableHead><TableHead>下一期数</TableHead><TableHead>操作</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell><TableCell>{row.lottery_name}</TableCell><TableCell>{row.year}</TableCell><TableCell>{row.term}</TableCell><TableCell>{row.numbers}</TableCell><TableCell>{row.draw_time}</TableCell><TableCell><StatusBadge value={row.status} /></TableCell><TableCell>{row.is_opened ? "是" : "否"}</TableCell><TableCell>{row.next_term}</TableCell>
                  <TableCell className="space-x-2"><Button variant="outline" size="sm" onClick={() => { setEditing(row); setFormOpen(true) }}>修改</Button><Button variant="outline" size="sm" onClick={() => remove(row.id)}>删除</Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </AdminShell>
  )
}

export function SitesPageClient() {
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
  useEffect(() => { load() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const payload: AnyRecord = {
      name: formValue(form, "name"),
      domain: formValue(form, "domain"),
      lottery_type_id: Number(formValue(form, "lottery_type_id")),
      enabled: boolValue(form, "enabled"),
      start_web_id: Number(formValue(form, "start_web_id")),
      end_web_id: Number(formValue(form, "end_web_id")),
      manage_url_template: formValue(form, "manage_url_template"),
      modes_data_url: formValue(form, "modes_data_url"),
      token: formValue(form, "token"),
      request_limit: Number(formValue(form, "request_limit")),
      request_delay: Number(formValue(form, "request_delay")),
      announcement: formValue(form, "announcement"),
      notes: formValue(form, "notes"),
    }
    if (!payload.token) delete payload.token
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

  function formatDate(iso: string) {
    if (!iso) return "-"
    return iso.replace("T", " ").replace(/-/g, ":").slice(0, 19)
  }

  function siteLink(site: Site) {
    if (site.domain) return `https://${site.domain}`
    if (site.manage_url_template) return site.manage_url_template.replace("{web_id}", String(site.start_web_id || 1)).replace("{id}", String(site.start_web_id || 1))
    if (site.modes_data_url) return site.modes_data_url
    return ""
  }

  return (
    <AdminShell title="站点管理" description="维护站点名称、域名、彩种、公告、状态和采集接口。">
      <AdminNotice message={message} />
      <div className="space-y-4">
        <Button
          onClick={() => { setFormOpen((prev) => !prev); setEditing(null) }}
          className="group relative overflow-hidden transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <Plus className={`mr-1 h-4 w-4 transition-transform duration-300 ${formOpen ? "rotate-45" : "group-hover:rotate-90"}`} />
          {editing ? "修改站点" : "新增站点"}
        </Button>

        <div className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"}`}>
          <Card key={editing?.id || "new"} className="p-4">
            <h2 className="mb-3 text-base font-semibold">{editing ? "修改站点" : "新增站点"}</h2>
            <form className="grid grid-cols-2 gap-3" onSubmit={submit}>
              <Field label="站点名称" className="col-span-2"><Input name="name" defaultValue={editing?.name || ""} required /></Field>
              <Field label="域名" className="col-span-2"><Input name="domain" defaultValue={editing?.domain || ""} placeholder="example.com" /></Field>
              <Field label="彩种" className="col-span-2">
                <select name="lottery_type_id" defaultValue={editing?.lottery_type_id || lotteries[0]?.id || 1} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
                  {lotteries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </Field>
              <Field label="状态">
                <select name="enabled" defaultValue={editing?.enabled === false ? "0" : "1"} className="h-9 rounded-md border bg-background px-3 text-sm">
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <Field label="web_id 起止"><Input name="start_web_id" type="number" defaultValue={editing?.start_web_id || 1} /></Field>
              <Field label="web_id 结束"><Input name="end_web_id" type="number" defaultValue={editing?.end_web_id || 10} /></Field>
              <Field label="分页 limit"><Input name="request_limit" type="number" defaultValue={editing?.request_limit || 250} /></Field>
              <Field label="请求间隔(秒)"><Input name="request_delay" type="number" step="0.1" defaultValue={editing?.request_delay || 0.5} /></Field>
              <Field label="modes 页面地址模板" className="col-span-2"><Input name="manage_url_template" defaultValue={editing?.manage_url_template || ""} /></Field>
              <Field label="all_data API 地址" className="col-span-2"><Input name="modes_data_url" defaultValue={editing?.modes_data_url || ""} /></Field>
              <Field label="Token" className="col-span-2"><Input name="token" placeholder={editing?.token_present ? "留空保持原 token" : ""} /></Field>
              <Field label="网站公告" className="col-span-2"><Textarea name="announcement" defaultValue={editing?.announcement || ""} /></Field>
              <Field label="备注" className="col-span-2"><Textarea name="notes" defaultValue={editing?.notes || ""} /></Field>
              <div className="col-span-2 flex gap-2">
                <Button type="submit" size="sm"><Save className="mr-1 h-4 w-4" />保存</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => { setFormOpen(false); setEditing(null) }}>取消</Button>
              </div>
            </form>
          </Card>
        </div>

        <Card className="overflow-auto p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[60px]" style={{ resize: "horizontal", overflow: "hidden" }}>ID</TableHead>
                <TableHead className="min-w-[120px]" style={{ resize: "horizontal", overflow: "hidden" }}>站点名称</TableHead>
                <TableHead className="min-w-[140px]" style={{ resize: "horizontal", overflow: "hidden" }}>域名</TableHead>
                <TableHead className="min-w-[80px]" style={{ resize: "horizontal", overflow: "hidden" }}>彩种</TableHead>
                <TableHead className="min-w-[60px]" style={{ resize: "horizontal", overflow: "hidden" }}>状态</TableHead>
                <TableHead className="min-w-[150px]" style={{ resize: "horizontal", overflow: "hidden" }}>创建时间</TableHead>
                <TableHead className="min-w-[240px]" style={{ resize: "horizontal", overflow: "hidden" }}>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow><TableCell colSpan={7} className="py-8 text-center text-muted-foreground">暂无站点数据</TableCell></TableRow>
              )}
              {rows.map((row) => {
                const link = siteLink(row)
                return (
                  <TableRow key={row.id}>
                    <TableCell>{row.id}</TableCell>
                    <TableCell className="font-medium">{row.name}</TableCell>
                    <TableCell>
                      {link ? (
                        <a href={link} target="_blank" rel="noopener noreferrer" className="block max-w-[200px] truncate text-blue-600 underline hover:text-blue-800" title={link}>
                          {row.domain || link}
                        </a>
                      ) : "-"}
                    </TableCell>
                    <TableCell>{row.lottery_name}</TableCell>
                    <TableCell><StatusBadge value={row.enabled} /></TableCell>
                    <TableCell className="whitespace-nowrap">{formatDate(row.created_at)}</TableCell>
                    <TableCell className="space-x-2">
                      <Button variant="outline" size="sm" onClick={() => alert(row.announcement || "暂无公告")}>网站公告</Button>
                      <Button asChild variant="outline" size="sm"><Link href={`/sites/${row.id}/data`}>站点数据</Link></Button>
                      <Button variant="outline" size="sm" onClick={() => { setEditing(row); setFormOpen(true) }}>修改</Button>
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

export function NumbersPageClient() {
  const [rows, setRows] = useState<NumberRow[]>([])
  const [keyword, setKeyword] = useState("")
  const [editing, setEditing] = useState<NumberRow | null>(null)
  const [formOpen, setFormOpen] = useState(false)

  async function load() {
    const data = await adminApi<{ numbers: NumberRow[] }>(`/admin/numbers?keyword=${encodeURIComponent(keyword)}`)
    setRows(data.numbers)
  }
  useEffect(() => { load() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const payload = {
      name: formValue(form, "name"),
      code: formValue(form, "code"),
      category_key: formValue(form, "category_key"),
      year: formValue(form, "year"),
      status: boolValue(form, "status"),
    }
    if (editing) {
      await adminApi(`/admin/numbers/${editing.id}`, { method: "PUT", body: jsonBody(payload) })
    } else {
      await adminApi("/admin/numbers", { method: "POST", body: jsonBody(payload) })
    }
    setEditing(null)
    setFormOpen(false)
    await load()
  }

  async function remove(id: number) {
    if (!confirm("确认删除该记录？")) return
    await adminApi(`/admin/numbers/${id}`, { method: "DELETE" })
    await load()
  }

  return (
    <AdminShell title="静态数据管理" description="管理固定数据（fixed_data），供预测机制读取的静态号码映射。">
      <div className="space-y-4">
        <Button
          onClick={() => { setFormOpen((prev) => !prev); setEditing(null) }}
          className="group relative overflow-hidden transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <Plus className={`mr-1 h-4 w-4 transition-transform duration-300 ${formOpen ? "rotate-45" : "group-hover:rotate-90"}`} />
          新增静态数据
        </Button>

        <div className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"}`}>
          <Card key={editing?.id || "new"} className="p-4">
            <h2 className="mb-3 text-base font-semibold">{editing ? "修改静态数据" : "新增静态数据"}</h2>
            <form className="space-y-3" onSubmit={submit}>
              <Field label="名称"><Input name="name" defaultValue={editing?.name || ""} required /></Field>
              <Field label="开奖号码"><Textarea name="code" defaultValue={editing?.code || ""} /></Field>
              <Field label="分类标识"><Input name="category_key" defaultValue={editing?.category_key || ""} /></Field>
              <Field label="年份"><Input name="year" defaultValue={editing?.year || ""} /></Field>
              <Field label="状态">
                <select name="status" defaultValue={editing?.status === false ? "0" : "1"} className="h-9 rounded-md border bg-background px-3 text-sm">
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <div className="flex gap-2">
                <Button type="submit" size="sm"><Save className="mr-1 h-4 w-4" />保存</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => { setFormOpen(false); setEditing(null) }}>取消</Button>
              </div>
            </form>
          </Card>
        </div>

        <Card className="p-4">
          <div className="mb-3 flex gap-2">
            <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索名称、分类标识或号码" />
            <Button variant="outline" onClick={load}>搜索</Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[60px]">ID</TableHead>
                <TableHead className="min-w-[100px]">名称</TableHead>
                <TableHead className="min-w-[200px]">开奖号码</TableHead>
                <TableHead className="min-w-[100px]">分类标识</TableHead>
                <TableHead className="min-w-[80px]">年份</TableHead>
                <TableHead className="min-w-[60px]">状态</TableHead>
                <TableHead className="min-w-[120px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell className="max-w-[360px] whitespace-normal">{row.code}</TableCell>
                  <TableCell>{row.category_key}</TableCell>
                  <TableCell>{row.year}</TableCell>
                  <TableCell><StatusBadge value={row.status} /></TableCell>
                  <TableCell className="space-x-2">
                    <Button variant="outline" size="sm" onClick={() => { setEditing(row); setFormOpen(true) }}>修改</Button>
                    <Button variant="outline" size="sm" onClick={() => remove(row.id)}><Trash2 className="h-4 w-4" /></Button>
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

// ── 数据面板（展开后显示） ──

function ModuleDataPanel({
  module,
  siteId,
  typeFilter,
  webFilter,
  sourceFilter,
  reloadToken,
  onTypeFilterChange,
  onSourceFilterChange,
  onClose,
}: {
  module: SitePredictionModule
  siteId: number
  typeFilter: string
  webFilter: string
  sourceFilter: string
  reloadToken: number
  onTypeFilterChange: (v: string) => void
  onSourceFilterChange: (v: string) => void
  onClose: () => void
}) {
  const resolvedModeId = module.mode_id ?? module.default_modes_id
  const tableName = module.default_table || `mode_payload_${resolvedModeId}`
  const [payload, setPayload] = useState<{ rows: AnyRecord[]; total: number; columns: string[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [msg, setMsg] = useState("")
  const [editing, setEditing] = useState<AnyRecord | null>(null)
  const [editValues, setEditValues] = useState<AnyRecord>({})
  const [regenOpen, setRegenOpen] = useState(false)
  const [regenNumbers, setRegenNumbers] = useState("")
  const [regenYear, setRegenYear] = useState("")
  const [regenTerm, setRegenTerm] = useState("")
  const [confirmDeleteRow, setConfirmDeleteRow] = useState<AnyRecord | null>(null)
  const pageSize = 30

  // 用 ref 保存最新筛选值，避免 async 闭包捕获旧值
  const typeFilterRef = useRef(typeFilter)
  typeFilterRef.current = typeFilter
  const webFilterRef = useRef(webFilter)
  webFilterRef.current = webFilter
  const searchRef = useRef(search)
  searchRef.current = search
  const sourceRef = useRef(sourceFilter)
  sourceRef.current = sourceFilter
  function resolveRowSource(row?: AnyRecord | null) {
    const candidate = String(row?.data_source ?? sourceRef.current ?? "public").trim().toLowerCase()
    return candidate === "created" ? "created" : "public"
  }

  async function fetchPayload(p: number) {
    setLoading(true)
    try {
      const tf = typeFilterRef.current
      const wf = webFilterRef.current
      const sq = searchRef.current
      const src = sourceRef.current
      const params = new URLSearchParams()
      if (tf) params.set("type", tf)
      if (wf) params.set("web", wf)
      if (src) params.set("source", src)
      params.set("page", String(p))
      params.set("page_size", String(pageSize))
      if (sq.trim()) params.set("search", sq.trim())
      const data = await adminApi<{ rows: AnyRecord[]; total: number; columns: string[] }>(
        `/admin/sites/${siteId}/mode-payload/${tableName}?${params}`
      )
      setPayload(data); setPage(p)
    } catch (e) { setMsg(e instanceof Error ? e.message : "加载失败") }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchPayload(1) }, [typeFilter, webFilter, sourceFilter, reloadToken])
  const totalPages = payload ? Math.ceil(payload.total / pageSize) : 0

  function startEdit(row: AnyRecord) { setEditing(row); setEditValues({ ...row }) }
  async function saveEdit() {
    if (!editing) return
    try {
      await adminApi(`/admin/sites/${siteId}/mode-payload/${tableName}/${editing.id}?source=${resolveRowSource(editing)}`, { method: "PATCH", body: jsonBody(editValues) })
      setMsg("已保存"); setEditing(null); fetchPayload(page)
    } catch (e) { setMsg(e instanceof Error ? e.message : "保存失败") }
  }
  async function deleteRow(row: AnyRecord) { setConfirmDeleteRow(row) }
  async function doConfirmDeleteRow() {
    if (!confirmDeleteRow) return
    const row = confirmDeleteRow
    setConfirmDeleteRow(null)
    try {
      await adminApi(`/admin/sites/${siteId}/mode-payload/${tableName}/${row.id}?source=${resolveRowSource(row)}`, { method: "DELETE" })
      setMsg("已删除"); fetchPayload(page)
    } catch (e) { setMsg(e instanceof Error ? e.message : "删除失败") }
  }
  async function doRegenerate() {
    const numStr = regenNumbers.trim()
    if (!numStr) { setMsg("请输入开奖号码"); return }

    // 校验开奖号码：7 个数字
    const codes = numStr.split(",").map(s => s.trim()).filter(Boolean)
    if (codes.length !== 7) { setMsg("开奖号码必须为7个数字，逗号分隔"); return }
    for (const c of codes) {
      if (!/^\d{1,2}$/.test(c)) { setMsg(`无效号码: ${c}`); return }
    }

    // 校验年份和期数
    const yr = regenYear.trim()
    const tm = regenTerm.trim()
    if (yr && !/^\d{4}$/.test(yr)) { setMsg("年份必须为4位数字"); return }
    if (tm) {
      if (!/^\d{1,5}$/.test(tm)) { setMsg("期数必须为1-5位数字"); return }
      if (parseInt(tm) === 0) { setMsg("期数不能为0"); return }
    }

    try {
      await adminApi(`/admin/sites/${siteId}/mode-payload/${tableName}/regenerate`, {
        method: "POST",
        body: jsonBody({ mechanism_key: module.mechanism_key, res_code: regenNumbers.trim(), lottery_type: typeFilter || "3", year: regenYear.trim() || new Date().getFullYear().toString(), term: regenTerm.trim() || "" }),
      })
      setMsg("重新生成成功"); setRegenOpen(false); fetchPayload(page)
    } catch (e) { setMsg(e instanceof Error ? e.message : "重新生成失败") }
  }

  return (
    <Card className="overflow-hidden border-t-2 border-t-primary/50 shadow-lg">
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2.5">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-semibold">{module.tables_title || module.title}</span>
          <span className="text-muted-foreground">|</span>
          <span className="text-xs text-muted-foreground">[{module.mechanism_key}]</span>
          <span className="text-xs text-muted-foreground">mode_id={resolvedModeId}</span>
          <span className="text-xs text-muted-foreground">{tableName}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={module.status ? "default" : "secondary"} className="text-[10px]">{module.status ? "启用" : "停用"}</Badge>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 text-xs">▲ 收起</Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">数据源:</span>
        {[{ v: "all", l: "全部数据" }, { v: "public", l: "原始数据" }, { v: "created", l: "生成数据" }].map((s) => (
          <button key={s.v} onClick={() => onSourceFilterChange(s.v)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${sourceFilter === s.v ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/70"}`}>
            {s.l}
          </button>
        ))}
        <span className="ml-2 text-xs font-medium text-muted-foreground">彩种:</span>
        {["", "1", "2", "3"].map((t) => (
          <button key={t} onClick={() => onTypeFilterChange(t)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${typeFilter === t ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/70"}`}>
            {t === "" ? "全部" : t === "1" ? "香港" : t === "2" ? "澳门" : "台湾"}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Input placeholder="搜索..." value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") fetchPayload(1) }} className="h-7 w-36 text-xs" />
          <Button variant="outline" size="sm" onClick={() => fetchPayload(1)} className="h-7 text-xs">搜索</Button>
          <Button variant="outline" size="sm" onClick={() => setRegenOpen(true)} className="h-7 text-xs">
            <RefreshCw className="mr-1 h-3 w-3" />重新生成资料
          </Button>
        </div>
      </div>

      <AdminNotice message={msg} />

      {loading ? (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">加载中...</div>
      ) : payload && payload.rows.length > 0 ? (
        <>
          <div className="overflow-x-auto" style={{ maxHeight: "55vh" }}>
            <table className="w-full text-xs" style={{ minWidth: 800 }}>
              <thead className="sticky top-0 bg-muted/80">
                <tr>
                  {payload.columns.map((col) => (
                    <th key={col} className="whitespace-nowrap border-b border-r px-2 py-1.5 text-left font-medium" style={{ resize: "horizontal", overflow: "auto", minWidth: 80, maxWidth: 400 }}>{col}</th>
                  ))}
                  <th className="whitespace-nowrap border-b px-2 py-1.5 text-left font-medium" style={{ minWidth: 100 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {payload.rows.map((row, idx) => (
                  <tr key={`${row.data_source ?? sourceFilter}_${row.id ?? `row_${idx}`}`} className="border-b hover:bg-muted/20">
                    {payload.columns.map((col) => (
                      <td key={col} className="max-w-[300px] truncate border-r px-2 py-1" title={String(row[col] ?? "")}>{row[col] != null ? String(row[col]) : ""}</td>
                    ))}
                    <td className="px-2 py-1">
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => startEdit(row)}>编辑</Button>
                        <Button variant="ghost" size="sm" className="h-6 text-xs text-destructive" onClick={() => deleteRow(row)}>删除</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t px-4 py-2">
            <span className="text-xs text-muted-foreground">共 {payload.total} 条，第 {page}/{totalPages} 页</span>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => fetchPayload(page - 1)} className="h-7 text-xs">上一页</Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => fetchPayload(page + 1)} className="h-7 text-xs">下一页</Button>
            </div>
          </div>
        </>
      ) : (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">暂无数据</div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setEditing(null)}>
          <div className="max-h-[80vh] w-[600px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-4 text-base font-semibold">编辑记录 #{editing.id}</h3>
            <div className="space-y-3">
              {Object.keys(editing).filter((k) => k !== "id" && k !== "data_source").map((key) => (
                <div key={key}>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">{key}</label>
                  {String(editValues[key] ?? "").length > 80 ? (
                    <Textarea value={String(editValues[key] ?? "")} onChange={(e) => setEditValues({ ...editValues, [key]: e.target.value })} className="h-20 text-xs" />
                  ) : (
                    <Input value={String(editValues[key] ?? "")} onChange={(e) => setEditValues({ ...editValues, [key]: e.target.value })} className="h-8 text-xs" />
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setEditing(null)}>取消</Button>
              <Button size="sm" onClick={saveEdit}>保存</Button>
            </div>
          </div>
        </div>
      )}

      {regenOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setRegenOpen(false)}>
          <div className="w-[500px] rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-1 text-base font-semibold">重新生成资料</h3>
            <p className="mb-4 text-xs text-muted-foreground">模块: {module.tables_title || module.title} ({tableName})</p>
            <div className="space-y-3">
              <div><label className="mb-1 block text-xs font-medium">开奖号码（逗号分隔）</label><Input placeholder="01,05,12,23,34,45,49" value={regenNumbers} onChange={(e) => setRegenNumbers(e.target.value)} className="h-9 text-sm" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="mb-1 block text-xs font-medium">年份</label><Input placeholder={new Date().getFullYear().toString()} value={regenYear} onChange={(e) => setRegenYear(e.target.value)} className="h-9 text-sm" /></div>
                <div><label className="mb-1 block text-xs font-medium">期数</label><Input placeholder="如 001" value={regenTerm} onChange={(e) => setRegenTerm(e.target.value)} className="h-9 text-sm" /></div>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setRegenOpen(false)}>取消</Button>
              <Button size="sm" onClick={doRegenerate}>执行生成</Button>
            </div>
          </div>
        </div>
      )}
      {/* 行删除确认弹窗 */}
      {confirmDeleteRow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setConfirmDeleteRow(null)}>
          <div className="w-[400px] rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-2 text-base font-semibold">确认删除</h3>
            <p className="text-sm text-muted-foreground">
              确定要删除 <span className="font-medium text-foreground">id={confirmDeleteRow.id}</span> 的记录吗？此操作不可撤销。
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setConfirmDeleteRow(null)}>取消</Button>
              <Button size="sm" variant="destructive" onClick={doConfirmDeleteRow}>确认删除</Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}


// ── 站点数据管理页 ──

export function SiteDataPageClient({ siteId }: { siteId: number }) {
  const [site, setSite] = useState<Site | null>(null)
  const [modules, setModules] = useState<SitePredictionModule[]>([])
  const [available, setAvailable] = useState<Mechanism[]>([])
  const [selectedKey, setSelectedKey] = useState("")
  const [message, setMessage] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const [typeFilter, setTypeFilter] = useState("")
  const [webFilter, setWebFilter] = useState("")
  const [sourceFilter, setSourceFilter] = useState("all")
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedModId, setSelectedModId] = useState<number | null>(null)
  const [confirmRemoveId, setConfirmRemoveId] = useState<number | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const [bulkGenerateOpen, setBulkGenerateOpen] = useState(false)
  const [bulkLotteryType, setBulkLotteryType] = useState("")
  const [bulkStartIssue, setBulkStartIssue] = useState("")
  const [bulkEndIssue, setBulkEndIssue] = useState("")
  const [bulkSubmitting, setBulkSubmitting] = useState(false)
  const configuredKeys = useMemo(() => new Set(modules.map((item) => item.mechanism_key)), [modules])

  async function load() {
    try {
      const data = await adminApi<{
        site: Site; modules: SitePredictionModule[]; available_mechanisms: Mechanism[]
      }>(`/admin/sites/${siteId}/prediction-modules`)
      setSite(data.site); setModules(data.modules); setAvailable(data.available_mechanisms)
      setSelectedKey(data.available_mechanisms.find((item) => !item.configured)?.key || data.available_mechanisms[0]?.key || "")
      setBulkLotteryType((current) => current || String(data.site.lottery_type_id || 3))
      setMessage("")
    } catch (error) { setMessage(error instanceof Error ? error.message : "加载失败") }
  }
  useEffect(() => { load() }, [siteId])

  async function addModule() {
    if (!selectedKey) return
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules`, { method: "POST", body: jsonBody({ mechanism_key: selectedKey, status: true, sort_order: modules.length * 10 }) })
      setAddOpen(false); await load()
    } catch (error) { setMessage(error instanceof Error ? error.message : "添加失败") }
  }

  async function removeModule(id: number) {
    setConfirmRemoveId(id)
  }
  async function doConfirmRemove() {
    if (confirmRemoveId == null) return
    const id = confirmRemoveId
    setConfirmRemoveId(null)
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules/${id}`, { method: "DELETE" })
      if (selectedModId === id) setSelectedModId(null)
      await load()
    } catch (error) { setMessage(error instanceof Error ? error.message : "删除失败") }
  }

  async function doBulkGenerate() {
    if (!bulkStartIssue.trim() || !bulkEndIssue.trim()) {
      setMessage("请先填写完整的起始期号和结束期号")
      return
    }
    setBulkSubmitting(true)
    try {
      const result = await adminApi<BulkGenerateResult>(`/admin/sites/${siteId}/prediction-modules/generate-all`, {
        method: "POST",
        body: jsonBody({
          lottery_type: bulkLotteryType || String(site?.lottery_type_id || 3),
          start_issue: bulkStartIssue.trim(),
          end_issue: bulkEndIssue.trim(),
        }),
      })
      setBulkGenerateOpen(false)
      setSourceFilter("all")
      setReloadToken((value) => value + 1)
      setMessage(`已生成 ${result.total_modules} 个模块，期数 ${result.draw_count}，新增 ${result.inserted}，覆盖 ${result.updated}，失败 ${result.errors}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "自动生成失败")
    } finally {
      setBulkSubmitting(false)
    }
  }

  const selectedModule = modules.find((m) => m.id === selectedModId) || null

  return (
    <AdminShell
      title={`${site?.name || "站点"} — 站点数据管理`}
      description="点击模块按钮查看数据库数据。支持编辑、删除、重新生成、彩种筛选。"
      actions={<Button asChild variant="outline" size="sm"><Link href="/sites">← 返回站点列表</Link></Button>}
    >
      <AdminNotice message={message} />

      {/* 顶部：站点筛选 + 添加 */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">站点:</span>
        {["", ...Array.from({ length: (site?.end_web_id || 10) - (site?.start_web_id || 1) + 1 }, (_, i) => String((site?.start_web_id || 1) + i))].map((w) => (
          <button key={w} onClick={() => setWebFilter(w)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-all hover:scale-105 active:scale-95 ${
              webFilter === w ? "bg-primary text-primary-foreground shadow-md" : "bg-muted text-muted-foreground hover:bg-muted/70"}`}>
            {w === "" ? "全部" : `web_id=${w}`}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" onClick={() => setBulkGenerateOpen(true)} size="sm" className="transition-all hover:scale-105 active:scale-95">
            <RefreshCw className="mr-1 h-4 w-4" />自动生成全部资料
          </Button>
          <Button onClick={() => setAddOpen((prev) => !prev)} size="sm" className="transition-all hover:scale-105 active:scale-95">
            <Plus className={`mr-1 h-4 w-4 transition-transform duration-300 ${addOpen ? "rotate-45" : ""}`} />添加模块
          </Button>
        </div>
      </div>

      {bulkGenerateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => !bulkSubmitting && setBulkGenerateOpen(false)}>
          <div className="w-[520px] rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-1 text-base font-semibold">自动生成全部资料</h3>
            <p className="mb-4 text-xs text-muted-foreground">会按当前站点启用模块批量生成 created schema 数据，统计结果会带上 mode_id。</p>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium">彩种</label>
                <select value={bulkLotteryType} onChange={(e) => setBulkLotteryType(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
                  <option value="1">香港</option>
                  <option value="2">澳门</option>
                  <option value="3">台湾</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium">起始期号</label>
                  <Input placeholder="例如 2026001" value={bulkStartIssue} onChange={(e) => setBulkStartIssue(e.target.value)} className="h-9 text-sm" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium">结束期号</label>
                  <Input placeholder="例如 2026030" value={bulkEndIssue} onChange={(e) => setBulkEndIssue(e.target.value)} className="h-9 text-sm" />
                </div>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" disabled={bulkSubmitting} onClick={() => setBulkGenerateOpen(false)}>取消</Button>
              <Button size="sm" disabled={bulkSubmitting} onClick={doBulkGenerate}>{bulkSubmitting ? "生成中..." : "开始生成"}</Button>
            </div>
          </div>
        </div>
      )}

      {/* 添加模块面板 */}
      <div className={`overflow-hidden transition-all duration-300 ${addOpen ? "mb-3 max-h-[520px] opacity-100" : "max-h-0 opacity-0"}`}>
        <Card className="p-4">
          <Input placeholder="搜索机制名称 / key / modes_id..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="mb-2 h-8 text-sm" />
          <div className="flex gap-2">
            <select value={selectedKey} onChange={(e) => setSelectedKey(e.target.value)} className="h-9 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm" size={12}>
              {available.filter((item) => {
                if (!searchTerm.trim()) return true
                const q = searchTerm.toLowerCase()
                return item.title.toLowerCase().includes(q) || item.key.toLowerCase().includes(q) || String(item.default_modes_id).includes(q)
              }).map((item) => (
                <option key={item.key} value={item.key} disabled={configuredKeys.has(item.key)}>
                  {item.title} [{item.key}] modes_id={item.default_modes_id}{configuredKeys.has(item.key) ? " ✓" : ""}
                </option>
              ))}
            </select>
            <Button onClick={addModule} disabled={!selectedKey} className="transition-all hover:scale-105 active:scale-95">确认添加</Button>
          </div>
        </Card>
      </div>

      {/* 模块按钮栏 */}
      {modules.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">暂无预测模块，请点击「添加模块」按钮添加。</Card>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap gap-1.5 overflow-x-auto rounded-lg border bg-muted/20 p-2" style={{ scrollbarWidth: "thin" }}>
            {modules.map((mod) => {
              const isSelected = mod.id === selectedModId
              const name = mod.tables_title || mod.title || mod.mechanism_key
              return (
                <button
                  key={mod.id}
                  onClick={() => setSelectedModId(isSelected ? null : mod.id)}
                  className={`group relative flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200
                    hover:scale-105 hover:shadow-md active:scale-95
                    ${
                      isSelected
                        ? "bg-primary text-primary-foreground shadow-lg ring-2 ring-primary/30"
                        : "bg-background text-foreground shadow-sm hover:bg-primary/10 hover:text-primary"}`}
                >
                  <span className={`h-2 w-2 rounded-full shrink-0 transition-colors ${mod.status ? "bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.5)]" : "bg-gray-300"}`} title={mod.status ? "启用" : "停用"} />
                  <span className="truncate max-w-[160px]">{name}</span>
                  <span
                    onClick={(e) => { e.stopPropagation(); removeModule(mod.id) }}
                    className="ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] opacity-0 transition-all group-hover:opacity-100 hover:bg-destructive/20 hover:text-destructive"
                    title="移除模块"
                  >×</span>
                </button>
              )
            })}
          </div>

          {selectedModule ? (
            <div className="animate-in fade-in slide-in-from-top-2 duration-300">
              <ModuleDataPanel
                key={selectedModule.id}
                module={selectedModule}
                siteId={siteId}
                typeFilter={typeFilter}
                webFilter={webFilter}
                sourceFilter={sourceFilter}
                reloadToken={reloadToken}
                onTypeFilterChange={setTypeFilter}
                onSourceFilterChange={setSourceFilter}
                onClose={() => setSelectedModId(null)}
              />
            </div>
          ) : (
            <Card className="p-6 text-center text-sm text-muted-foreground">
              点击上方模块按钮查看数据库数据
            </Card>
          )}

          {/* 删除确认弹窗 */}
          {confirmRemoveId != null && (() => {
            const mod = modules.find(m => m.id === confirmRemoveId)
            return (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setConfirmRemoveId(null)}>
                <div className="w-[400px] rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
                  <h3 className="mb-2 text-base font-semibold">确认移除</h3>
                  <p className="mb-1 text-sm text-muted-foreground">
                    确定要移除预测模块 <span className="font-medium text-foreground">「{mod?.tables_title || mod?.title || "?"}」</span> 吗？
                  </p>
                  <p className="text-xs text-muted-foreground">该操作仅从站点配置中移除，不会删除数据库数据。</p>
                  <div className="mt-4 flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => setConfirmRemoveId(null)}>取消</Button>
                    <Button size="sm" variant="destructive" onClick={doConfirmRemove}>确认移除</Button>
                  </div>
                </div>
              </div>
            )
          })()}
        </>
      )}
    </AdminShell>
  )
}

export function PredictionModulesPageClient() {
  const [rows, setRows] = useState<Mechanism[]>([])
  useEffect(() => {
    adminApi<{ mechanisms: Mechanism[] }>("/predict/mechanisms").then((data) => setRows(data.mechanisms))
  }, [])

  return (
    <AdminShell title="预测模块" description="由 mechanisms.py 自动提供的预测模块与本地 SQLite 数据源。">
      <Card className="p-4">
        <Table>
          <TableHeader><TableRow><TableHead>key</TableHead><TableHead>标题</TableHead><TableHead>modes_id</TableHead><TableHead>数据表</TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.key}>
                <TableCell>{row.key}</TableCell><TableCell>{row.title}</TableCell><TableCell>{row.default_modes_id}</TableCell><TableCell>{row.default_table}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </AdminShell>
  )
}
