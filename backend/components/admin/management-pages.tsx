"use client"

import type { FormEvent, ReactNode } from "react"
import { useEffect, useMemo, useState } from "react"
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
  default_modes_id: number
  default_table: string
  configured?: boolean
}

type SitePredictionModule = {
  id: number
  mechanism_key: string
  title?: string
  default_modes_id?: number
  default_table?: string
  status: boolean
  sort_order: number
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

export function SiteDataPageClient({ siteId }: { siteId: number }) {
  const [site, setSite] = useState<Site | null>(null)
  const [modules, setModules] = useState<SitePredictionModule[]>([])
  const [available, setAvailable] = useState<Mechanism[]>([])
  const [selectedKey, setSelectedKey] = useState("")
  const [predictionResults, setPredictionResults] = useState<Record<string, AnyRecord>>({})
  const [message, setMessage] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const configuredKeys = useMemo(() => new Set(modules.map((item) => item.mechanism_key)), [modules])

  async function load() {
    try {
      const data = await adminApi<{
        site: Site
        modules: SitePredictionModule[]
        available_mechanisms: Mechanism[]
      }>(`/admin/sites/${siteId}/prediction-modules`)
      setSite(data.site)
      setModules(data.modules)
      setAvailable(data.available_mechanisms)
      setSelectedKey(
        data.available_mechanisms.find((item) => !item.configured)?.key ||
          data.available_mechanisms[0]?.key || "",
      )
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载失败")
    }
  }
  useEffect(() => { load() }, [siteId])

  async function addModule() {
    if (!selectedKey) return
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules`, {
        method: "POST",
        body: jsonBody({ mechanism_key: selectedKey, status: true, sort_order: modules.length * 10 }),
      })
      setAddOpen(false)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "添加失败")
    }
  }

  async function saveModule(row: SitePredictionModule) {
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules/${row.id}`, {
        method: "PATCH",
        body: jsonBody({ status: row.status, sort_order: row.sort_order }),
      })
      setMessage("已保存")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败")
    }
  }

  async function toggleStatus(row: SitePredictionModule) {
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules/${row.id}`, {
        method: "PATCH",
        body: jsonBody({ status: !row.status, sort_order: row.sort_order }),
      })
      setModules((prev) => prev.map((m) => m.id === row.id ? { ...m, status: !m.status } : m))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "更新失败")
    }
  }

  async function runModule(mechanismKey: string) {
    try {
      const result = await adminApi<AnyRecord>(`/admin/sites/${siteId}/prediction-modules/run`, {
        method: "POST",
        body: jsonBody({ mechanism_key: mechanismKey, target_hit_rate: 0.65 }),
      })
      setPredictionResults((prev) => ({ ...prev, [mechanismKey]: result }))
      setMessage("预测执行完成")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "预测执行失败")
    }
  }

  async function removeModule(id: number) {
    if (!confirm("确认移除该预测模块？")) return
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules/${id}`, { method: "DELETE" })
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "删除失败")
    }
  }

  function extractPreviewData(result: AnyRecord): AnyRecord[] {
    if (!result) return []
    if (Array.isArray(result.data)) return result.data
    if (Array.isArray(result.history)) return result.history
    if (Array.isArray(result.results)) return result.results
    if (Array.isArray(result)) return result
    for (const val of Object.values(result)) {
      if (Array.isArray(val)) return val
    }
    return []
  }

  function updateSortOrder(moduleId: number, value: number) {
    setModules((prev) => prev.map((m) => m.id === moduleId ? { ...m, sort_order: value } : m))
  }

  return (
    <AdminShell
      title={`${site?.name || "站点"} — 站点数据管理`}
      description="管理该站点的预测模块，配置前端显示的彩票数据内容。"
      actions={
        <Button asChild variant="outline" size="sm">
          <Link href="/sites">← 返回站点列表</Link>
        </Button>
      }
    >
      <AdminNotice message={message} />
      <div className="space-y-4">
        <Button
          onClick={() => setAddOpen((prev) => !prev)}
          className="group relative overflow-hidden transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <Plus className={`mr-1 h-4 w-4 transition-transform duration-300 ${addOpen ? "rotate-45" : "group-hover:rotate-90"}`} />
          添加预测模块
        </Button>

        <div className={`overflow-hidden transition-all duration-500 ease-in-out ${addOpen ? "max-h-[400px] opacity-100" : "max-h-0 opacity-0"}`}>
          <Card className="p-4">
            <h2 className="mb-3 text-base font-semibold">添加预测模块</h2>
            <p className="mb-3 text-sm text-muted-foreground">
              从可用预测机制中选择一个添加到该站点。已配置的机制不可重复添加。
            </p>
            <div className="flex gap-2">
              <select
                value={selectedKey}
                onChange={(e) => setSelectedKey(e.target.value)}
                className="h-9 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm"
              >
                {available.map((item) => (
                  <option key={item.key} value={item.key} disabled={configuredKeys.has(item.key)}>
                    {item.title}（{item.key}）
                  </option>
                ))}
              </select>
              <Button onClick={addModule} disabled={!selectedKey}>确认添加</Button>
            </div>
          </Card>
        </div>

        {modules.length === 0 && (
          <Card className="p-8 text-center text-muted-foreground">
            暂无预测模块，请点击上方按钮添加。
          </Card>
        )}

        {/* Module cards grid — each card maps to a PreResultBlocks-style section */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((module) => {
            const result = predictionResults[module.mechanism_key]
            const previewData = result ? extractPreviewData(result) : null
            return (
              <Card key={module.id} className="flex flex-col overflow-hidden">
                {/* Card header */}
                <div className="flex items-center justify-between border-b px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold">{module.title || module.mechanism_key}</h3>
                    <p className="truncate text-xs text-muted-foreground">{module.mechanism_key} · {module.default_table || "-"}</p>
                  </div>
                  <button
                    onClick={() => toggleStatus(module)}
                    className={`ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                      module.status
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                    }`}
                  >
                    {module.status ? "启用" : "停用"}
                  </button>
                </div>

                {/* Data preview — styled to match PreResultBlocks source tables */}
                <div className="min-h-[100px] flex-1 border-b">
                  {previewData && previewData.length > 0 ? (
                    <table className="w-full text-xs" cellPadding={0}>
                      <tbody>
                        {previewData.slice(0, 10).map((row, idx) => (
                          <tr key={idx} className="border-b last:border-0">
                            <td className="px-3 py-1.5">
                              <span className="text-muted-foreground">{row.issue || row.year || ""}: </span>
                              {row.label && <span>{row.label}</span>}
                              {row.content && <span> → <b>[{row.content}]</b></span>}
                              {row.result && <span> 开:{row.result}</span>}
                              {!row.label && !row.content && row.prediction_text && <span>{row.prediction_text}</span>}
                              {row.result_text && <span> → {row.result_text}</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="flex h-[100px] items-center justify-center text-xs text-muted-foreground">
                      {result ? "暂无数组数据" : "点击「执行预测」生成数据"}
                    </div>
                  )}
                </div>

                {/* Controls */}
                <div className="flex items-center gap-2 px-4 py-2.5">
                  <span className="text-xs text-muted-foreground">排序:</span>
                  <Input
                    type="number"
                    value={module.sort_order}
                    onChange={(e) => updateSortOrder(module.id, Number(e.target.value || 0))}
                    className="h-7 w-20"
                  />
                  <div className="ml-auto flex gap-1">
                    <Button variant="outline" size="sm" onClick={() => saveModule(module)} title="保存配置">
                      <Save className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => runModule(module.mechanism_key)}>
                      执行预测
                    </Button>
                    <Button variant="outline" size="sm" className="text-destructive hover:text-destructive" onClick={() => removeModule(module.id)} title="移除">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Collapsible full JSON results */}
        {Object.keys(predictionResults).length > 0 && (
          <details className="rounded-md border p-3">
            <summary className="cursor-pointer text-sm font-medium text-muted-foreground">
              查看完整预测 JSON 数据
            </summary>
            <pre className="mt-2 max-h-[400px] overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">
              {JSON.stringify(predictionResults, null, 2)}
            </pre>
          </details>
        )}
      </div>
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
