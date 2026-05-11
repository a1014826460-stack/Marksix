"use client"

import type { FormEvent } from "react"
import { useEffect, useState } from "react"
import { Save, Trash2 } from "lucide-react"
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
import { AdminNotice } from "@/features/shared/AdminNotice"
import { StatusBadge } from "@/features/shared/StatusBadge"
import { formValue, boolValue } from "@/features/shared/form-helpers"
import type { User, AnyRecord } from "@/features/shared/types"

export function UsersPage() {
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
    await adminApi(
      editing ? `/admin/users/${editing.id}` : "/admin/users",
      {
        method: editing ? "PUT" : "POST",
        body: jsonBody(payload),
      },
    )
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
          <h2 className="mb-3 text-base font-semibold">
            {editing ? "修改管理员" : "新增管理员"}
          </h2>
          <form className="space-y-3" onSubmit={submit}>
            <Field label="用户名">
              <Input
                name="username"
                defaultValue={editing?.username || ""}
                required
              />
            </Field>
            <Field label="显示名称">
              <Input
                name="display_name"
                defaultValue={editing?.display_name || ""}
              />
            </Field>
            <Field label="角色">
              <Input name="role" defaultValue={editing?.role || "admin"} />
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
            <Field label={editing ? "新密码（留空不变）" : "密码"}>
              <Input
                name="password"
                type="password"
                required={!editing}
              />
            </Field>
            <Button type="submit" size="sm">
              <Save className="mr-1 h-4 w-4" />
              保存
            </Button>
          </form>
        </Card>
        <Card className="space-y-4 p-4">
          <AdminNotice message={message} />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>用户名</TableHead>
                <TableHead>角色</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell>
                  <TableCell>
                    <b>{row.display_name}</b>
                    <br />
                    <span className="text-xs text-muted-foreground">
                      {row.username}
                    </span>
                  </TableCell>
                  <TableCell>{row.role}</TableCell>
                  <TableCell>
                    <StatusBadge value={row.status} />
                  </TableCell>
                  <TableCell className="space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditing(row)}
                    >
                      修改
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => remove(row.id)}
                    >
                      <Trash2 className="h-4 w-4" />
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
