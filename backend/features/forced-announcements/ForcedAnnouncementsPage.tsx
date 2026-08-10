"use client"

import type { FormEvent } from "react"
import { useEffect, useState } from "react"
import { Megaphone, Pencil, Plus, Save, Trash2, X } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
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
import { AdminNotice } from "@/features/shared/AdminNotice"
import { Field } from "@/features/shared/Field"
import { StatusBadge } from "@/features/shared/StatusBadge"
import type {
  ForcedAnnouncement,
  ForcedAnnouncementScope,
  Site,
} from "@/features/shared/types"
import { adminApi, jsonBody } from "@/lib/admin-api"

type AnnouncementForm = {
  title: string
  html: string
  scope: ForcedAnnouncementScope
  site_ids: number[]
  starts_at: string
  ends_at: string
  enabled: boolean
}

const EMPTY_FORM: AnnouncementForm = {
  title: "",
  html: "",
  scope: "all_sites",
  site_ids: [],
  starts_at: "",
  ends_at: "",
  enabled: true,
}

function toDateTimeLocal(value: string | null | undefined) {
  return value ? value.slice(0, 16) : ""
}

function displayTime(value: string | null | undefined) {
  return value ? value.replace("T", " ").slice(0, 16) : "持续有效"
}

export function ForcedAnnouncementsPage() {
  const [announcements, setAnnouncements] = useState<ForcedAnnouncement[]>([])
  const [sites, setSites] = useState<Site[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<AnnouncementForm>(EMPTY_FORM)
  const [message, setMessage] = useState("")
  const [saving, setSaving] = useState(false)

  async function load() {
    const [announcementData, siteData] = await Promise.all([
      adminApi<{ announcements: ForcedAnnouncement[] }>(
        "/admin/forced-announcements",
      ),
      adminApi<{ sites: Site[] }>("/admin/sites"),
    ])
    setAnnouncements(announcementData.announcements)
    setSites(siteData.sites)
  }

  useEffect(() => {
    void load().catch((error) => {
      setMessage(error instanceof Error ? error.message : "加载失败")
    })
  }, [])

  function startCreate() {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setFormOpen(true)
    setMessage("")
  }

  function startEdit(announcement: ForcedAnnouncement) {
    setEditingId(announcement.id)
    setForm({
      title: announcement.title,
      html: announcement.html,
      scope: announcement.scope,
      site_ids: announcement.site_ids,
      starts_at: toDateTimeLocal(announcement.starts_at),
      ends_at: toDateTimeLocal(announcement.ends_at),
      enabled: announcement.enabled,
    })
    setFormOpen(true)
    setMessage("")
  }

  function closeForm() {
    setEditingId(null)
    setFormOpen(false)
    setForm(EMPTY_FORM)
  }

  function toggleSite(siteId: number, checked: boolean) {
    setForm((current) => ({
      ...current,
      site_ids: checked
        ? [...new Set([...current.site_ids, siteId])].sort((a, b) => a - b)
        : current.site_ids.filter((id) => id !== siteId),
    }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMessage("")
    try {
      await adminApi(
        editingId
          ? `/admin/forced-announcements/${editingId}`
          : "/admin/forced-announcements",
        {
          method: editingId ? "PUT" : "POST",
          body: jsonBody({
            ...form,
            site_ids: form.scope === "selected_sites" ? form.site_ids : [],
            ends_at: form.ends_at || null,
          }),
        },
      )
      closeForm()
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败")
    } finally {
      setSaving(false)
    }
  }

  async function remove(announcement: ForcedAnnouncement) {
    if (!window.confirm(`确认删除公告“${announcement.title}”？`)) return
    try {
      await adminApi(`/admin/forced-announcements/${announcement.id}`, {
        method: "DELETE",
      })
      await load()
      if (editingId === announcement.id) closeForm()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "删除失败")
    }
  }

  function scopeText(announcement: ForcedAnnouncement) {
    if (announcement.scope === "all_sites") return `全站（${sites.length}）`
    return `指定站点（${announcement.site_ids.length}）`
  }

  return (
    <AdminShell
      title="强制公告"
      description="管理各站点在北京时间生效的统一弹窗公告。"
      actions={
        <Button onClick={startCreate} size="sm">
          <Plus className="mr-1 h-4 w-4" />
          新增公告
        </Button>
      }
    >
      <AdminNotice message={message} />
      <div className="space-y-4">
        {formOpen && (
          <Card className="p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <Megaphone className="h-4 w-4 shrink-0" />
                <h2 className="truncate text-base font-semibold">
                  {editingId ? "修改公告" : "新增公告"}
                </h2>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={closeForm}
                title="关闭编辑"
                aria-label="关闭编辑"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <form className="grid grid-cols-1 gap-4 lg:grid-cols-2" onSubmit={submit}>
              <Field label="公告标题" className="lg:col-span-2">
                <Input
                  name="title"
                  value={form.title}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, title: event.target.value }))
                  }
                  required
                />
              </Field>

              <Field label="公告内容（受控 HTML）" className="lg:col-span-2">
                <Textarea
                  name="html"
                  value={form.html}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, html: event.target.value }))
                  }
                  className="min-h-40 font-mono text-sm"
                  required
                />
              </Field>

              <Field label="生效范围">
                <select
                  name="scope"
                  value={form.scope}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      scope: event.target.value as ForcedAnnouncementScope,
                    }))
                  }
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                >
                  <option value="all_sites">全站统一</option>
                  <option value="selected_sites">指定部分站点</option>
                </select>
              </Field>

              <Field label="状态">
                <label className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm">
                  <input
                    name="enabled"
                    type="checkbox"
                    checked={form.enabled}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        enabled: event.target.checked,
                      }))
                    }
                  />
                  启用
                </label>
              </Field>

              {form.scope === "selected_sites" && (
                <fieldset className="lg:col-span-2">
                  <legend className="mb-2 text-sm font-medium">命中站点</legend>
                  <div className="grid grid-cols-1 gap-2 rounded-md border p-3 sm:grid-cols-2 lg:grid-cols-3">
                    {sites.map((site) => (
                      <label key={site.id} className="flex min-h-9 items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={form.site_ids.includes(site.id)}
                          onChange={(event) => toggleSite(site.id, event.target.checked)}
                        />
                        <span className="min-w-0 truncate">
                          {site.name}（{site.web_id}）
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}

              <Field label="开始时间（北京时间）">
                <Input
                  name="starts_at"
                  type="datetime-local"
                  value={form.starts_at}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      starts_at: event.target.value,
                    }))
                  }
                  required
                />
              </Field>

              <Field label="结束时间（北京时间）">
                <Input
                  name="ends_at"
                  type="datetime-local"
                  value={form.ends_at}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, ends_at: event.target.value }))
                  }
                />
              </Field>

              <div className="flex flex-wrap gap-2 lg:col-span-2">
                <Button type="submit" size="sm" disabled={saving}>
                  <Save className="mr-1 h-4 w-4" />
                  {saving ? "保存中" : "保存"}
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={closeForm}>
                  取消
                </Button>
              </div>
            </form>
          </Card>
        )}

        {!formOpen && (
          <Button onClick={startCreate} size="sm" className="md:hidden">
            <Plus className="mr-1 h-4 w-4" />
            新增公告
          </Button>
        )}

        <Card className="overflow-auto p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-48">标题</TableHead>
                <TableHead className="min-w-32">范围</TableHead>
                <TableHead className="min-w-40">开始时间</TableHead>
                <TableHead className="min-w-40">结束时间</TableHead>
                <TableHead className="min-w-24">状态</TableHead>
                <TableHead className="min-w-40">版本</TableHead>
                <TableHead className="min-w-44">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {announcements.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                    暂无公告
                  </TableCell>
                </TableRow>
              )}
              {announcements.map((announcement) => (
                <TableRow key={announcement.id}>
                  <TableCell className="font-medium">{announcement.title}</TableCell>
                  <TableCell>{scopeText(announcement)}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {displayTime(announcement.starts_at)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {displayTime(announcement.ends_at)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge value={announcement.enabled} />
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs" title={announcement.version}>
                      {announcement.version.slice(0, 12)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => startEdit(announcement)}
                        title="修改公告"
                        aria-label="修改公告"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => void remove(announcement)}
                        title="删除公告"
                        aria-label="删除公告"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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

