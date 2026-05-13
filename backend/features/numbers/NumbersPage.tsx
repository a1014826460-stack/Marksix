"use client"

import type { FormEvent } from "react"
import { useEffect, useState } from "react"
import { Plus, Save, Trash2 } from "lucide-react"
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
import { StatusBadge } from "@/features/shared/StatusBadge"
import { formValue, boolValue } from "@/features/shared/form-helpers"
import type { NumberRow } from "@/features/shared/types"

export function NumbersPage() {
  const [rows, setRows] = useState<NumberRow[]>([])
  const [keyword, setKeyword] = useState("")
  const [editing, setEditing] = useState<NumberRow | null>(null)
  const [formOpen, setFormOpen] = useState(false)

  async function load() {
    const data = await adminApi<{ numbers: NumberRow[] }>(
      `/admin/numbers?keyword=${encodeURIComponent(keyword)}`,
    )
    setRows(data.numbers)
  }

  useEffect(() => {
    load()
  }, [])

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
      await adminApi(`/admin/numbers/${editing.id}`, {
        method: "PUT",
        body: jsonBody(payload),
      })
    } else {
      await adminApi("/admin/numbers", {
        method: "POST",
        body: jsonBody(payload),
      })
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
    <AdminShell
      title="静态数据管理"
      description="管理固定数据（fixed_data），供预测机制读取的静态号码映射。"
    >
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
          新增静态数据
        </Button>

        <div
          className={`overflow-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"}`}
        >
          <Card key={editing?.id || "new"} className="p-4">
            <h2 className="mb-3 text-base font-semibold">
              {editing ? "修改静态数据" : "新增静态数据"}
            </h2>
            <form className="space-y-3" onSubmit={submit}>
              <Field label="名称">
                <Input
                  name="name"
                  defaultValue={editing?.name || ""}
                  required
                />
              </Field>
              <Field label="开奖号码">
                <Textarea
                  name="code"
                  defaultValue={editing?.code || ""}
                />
              </Field>
              <Field label="分类标识">
                <Input
                  name="category_key"
                  defaultValue={editing?.category_key || ""}
                />
              </Field>
              <Field label="年份">
                <Input name="year" defaultValue={editing?.year || ""} />
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

        <Card className="overflow-auto p-4">
          <div className="mb-3 flex gap-2">
            <Input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="搜索名称、分类标识或号码"
            />
            <Button variant="outline" onClick={load}>
              搜索
            </Button>
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
                  <TableCell className="max-w-[200px] md:max-w-[360px] whitespace-normal">
                    {row.code}
                  </TableCell>
                  <TableCell>{row.category_key}</TableCell>
                  <TableCell>{row.year}</TableCell>
                  <TableCell>
                    <StatusBadge value={row.status} />
                  </TableCell>
                  <TableCell className="flex gap-1 flex-wrap">
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
