"use client"

import type { FormEvent } from "react"
import { useEffect, useRef, useState } from "react"
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
import { DrawNumbersInput } from "@/features/draws/DrawNumbersInput"
import type { Draw, LotteryType } from "@/features/shared/types"

const TAIWAN_LOTTERY_ID = 3

export function DrawsPage() {
  const [rows, setRows] = useState<Draw[]>([])
  const [lotteries, setLotteries] = useState<LotteryType[]>([])
  const [editing, setEditing] = useState<Draw | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const formRef = useRef<HTMLFormElement | null>(null)

  async function load() {
    const [drawData, lotteryData] = await Promise.all([
      adminApi<{ draws: Draw[] }>("/admin/draws?limit=500"),
      adminApi<{ lottery_types: LotteryType[] }>("/admin/lottery-types"),
    ])
    setRows(drawData.draws)
    setLotteries(lotteryData.lottery_types)
  }

  useEffect(() => {
    void load()
  }, [])

  const taiwanLottery =
    lotteries.find((lottery) => lottery.id === TAIWAN_LOTTERY_ID) || null
  const filteredRows = rows.filter(
    (row) => row.lottery_type_id === TAIWAN_LOTTERY_ID,
  )

  async function populateDraftFields(form: HTMLFormElement) {
    try {
      const info = await adminApi<{
        year: number
        term: number
        draw_time: string
      }>(`/admin/lottery-draws/latest-term?lottery_type_id=${TAIWAN_LOTTERY_ID}`)

      ;(form.elements.namedItem("year") as HTMLInputElement).value = String(
        info.year || new Date().getFullYear(),
      )
      ;(form.elements.namedItem("term") as HTMLInputElement).value = String(
        info.term > 0 ? info.term + 1 : 1,
      )
      ;(form.elements.namedItem("next_term") as HTMLInputElement).value = String(
        info.term > 0 ? info.term + 2 : 2,
      )

      let baseDate = info.draw_time
        ? new Date(info.draw_time.replace(" ", "T"))
        : new Date()
      if (Number.isNaN(baseDate.getTime())) {
        baseDate = new Date()
      }
      baseDate.setDate(baseDate.getDate() + 1)
      const timeStr = taiwanLottery?.draw_time || "22:30:00"
      const parts = timeStr.split(":")
      baseDate.setHours(
        parseInt(parts[0]) || 22,
        parseInt(parts[1]) || 30,
        parseInt(parts[2]) || 0,
        0,
      )
      const yyyy = baseDate.getFullYear()
      const mm = String(baseDate.getMonth() + 1).padStart(2, "0")
      const dd = String(baseDate.getDate()).padStart(2, "0")
      ;(form.elements.namedItem("draw_time") as HTMLInputElement).value =
        `${yyyy}-${mm}-${dd}`
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (!formOpen || editing || !formRef.current) return
    void populateDraftFields(formRef.current)
  }, [editing, formOpen, taiwanLottery])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const ltId = TAIWAN_LOTTERY_ID

    let drawTime = formValue(form, "draw_time")
    if (drawTime) {
      const timeStr = taiwanLottery?.draw_time || "22:30:00"
      const parts = timeStr.split(":")
      const timeWithSec = parts.length >= 3 ? timeStr : `${timeStr}:00`
      drawTime = `${drawTime} ${timeWithSec}`
    }

    let nextTime = ""
    if (drawTime) {
      try {
        nextTime = String(
          new Date(drawTime.replace(" ", "T") + "+08:00").getTime(),
        )
      } catch {
        /* ignore */
      }
    }

    await adminApi(editing ? `/admin/draws/${editing.id}` : "/admin/draws", {
      method: editing ? "PUT" : "POST",
      body: jsonBody({
        lottery_type_id: ltId,
        year: Number(formValue(form, "year")),
        term: Number(formValue(form, "term")),
        numbers: formValue(form, "numbers"),
        draw_time: drawTime,
        next_time: nextTime,
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
    if (!confirm("确认删除该开奖记录吗？")) return
    await adminApi(`/admin/draws/${id}`, { method: "DELETE" })
    await load()
  }

  return (
    <AdminShell
      title="开奖记录管理"
      description="仅管理台湾彩开奖记录，为预测提供统一数据来源。"
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            彩种：{taiwanLottery?.name || "台湾彩"}
          </span>
          <div className="flex-1" />
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
            新增开奖记录
          </Button>
        </div>

        <div
          className={`relative z-20 overflow-y-auto overflow-x-hidden transition-all duration-500 ease-in-out ${formOpen ? "max-h-[720px] opacity-100" : "max-h-0 opacity-0"}`}
        >
          <Card key={editing?.id || "new"} className="relative p-4">
            <h2 className="mb-3 text-base font-semibold">
              {editing ? "修改开奖记录" : "新增开奖记录"}
            </h2>
            <form
              className="grid grid-cols-2 gap-3"
              onSubmit={submit}
              ref={formRef}
            >
              <Field label="彩种" className="col-span-2">
                <input
                  type="hidden"
                  name="lottery_type_id"
                  value={String(TAIWAN_LOTTERY_ID)}
                  readOnly
                />
                <Input value={taiwanLottery?.name || "台湾彩"} readOnly disabled />
                {!editing && (
                  <span className="mt-1 text-xs text-muted-foreground">
                    新增记录固定为台湾彩，期数和开奖日期会自动推算。
                  </span>
                )}
              </Field>
              <Field label="年份">
                <Input
                  name="year"
                  type="number"
                  defaultValue={editing?.year || new Date().getFullYear()}
                />
              </Field>
              <Field label="期数">
                <Input
                  name="term"
                  type="number"
                  defaultValue={editing?.term || ""}
                  placeholder="自动获取"
                />
              </Field>
              <Field label="开奖号码（点击添加/删除）" className="col-span-2">
                <DrawNumbersInput
                  name="numbers"
                  defaultValue={editing?.numbers || ""}
                />
              </Field>
              <Field label="开奖日期" className="col-span-2">
                <Input
                  name="draw_time"
                  type="date"
                  defaultValue={editing?.draw_time?.slice(0, 10) || ""}
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
              <Field label="是否开奖">
                <select
                  name="is_opened"
                  defaultValue={editing?.is_opened ? "1" : "0"}
                  className="h-9 rounded-md border bg-background px-3 text-sm"
                >
                  <option value="1">已开奖</option>
                  <option value="0">未开奖</option>
                </select>
              </Field>
              <Field label="下一期期数" className="col-span-2">
                <Input
                  name="next_term"
                  type="number"
                  defaultValue={editing?.next_term || ""}
                  placeholder="自动获取"
                />
              </Field>
              <div className="col-span-2 sticky bottom-0 z-30 flex gap-2 border-t border-border bg-card py-3 shadow-[0_-8px_20px_rgba(15,23,42,0.08)]">
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

        <Card className="p-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>彩种</TableHead>
                <TableHead>年份</TableHead>
                <TableHead>期数</TableHead>
                <TableHead>开奖号码</TableHead>
                <TableHead>开奖时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>是否开奖</TableHead>
                <TableHead>下一期期数</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.id}</TableCell>
                  <TableCell>{row.lottery_name}</TableCell>
                  <TableCell>{row.year}</TableCell>
                  <TableCell>{row.term}</TableCell>
                  <TableCell>{row.numbers}</TableCell>
                  <TableCell>{row.draw_time}</TableCell>
                  <TableCell>
                    <StatusBadge value={row.status} />
                  </TableCell>
                  <TableCell>{row.is_opened ? "是" : "否"}</TableCell>
                  <TableCell>{row.next_term}</TableCell>
                  <TableCell className="space-x-2">
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
                      删除
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
