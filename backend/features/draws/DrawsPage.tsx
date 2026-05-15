"use client"

import type { FormEvent } from "react"
import { useCallback, useEffect, useRef, useState } from "react"
import { Plus, Save } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { adminApi, jsonBody } from "@/lib/admin-api"
import { Field } from "@/features/shared/Field"
import { StatusBadge } from "@/features/shared/StatusBadge"
import { DrawNumbersInput } from "@/features/draws/DrawNumbersInput"
import { DrawBallDisplay, DrawBallDisplayProvider, DrawBallDisplayToggles } from "@/features/draws/DrawBallDisplay"
import type { Draw, LotteryType } from "@/features/shared/types"

const TAIWAN_LOTTERY_ID = 3

function formatDateInput(date: Date) {
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, "0")
  const dd = String(date.getDate()).padStart(2, "0")
  return `${yyyy}-${mm}-${dd}`
}

function parseBeijingDateTime(value: string) {
  return new Date(value.replace(" ", "T") + "+08:00")
}

function buildNextTerm(term: string) {
  const next = Number(term)
  if (!term || Number.isNaN(next) || next <= 0) return ""
  return String(next + 1)
}

function getLatestTaiwanDraw(draws: Draw[]) {
  return draws
    .filter((row) => row.lottery_type_id === TAIWAN_LOTTERY_ID)
    .reduce<Draw | null>((latest, row) => {
      if (!latest) return row
      if (row.year !== latest.year) return row.year > latest.year ? row : latest
      if (row.term !== latest.term) return row.term > latest.term ? row : latest
      return row.id > latest.id ? row : latest
    }, null)
}

function resolveNextTerm(row: Draw) {
  const nextTerm = Number(row.next_term)
  if (Number.isFinite(nextTerm) && nextTerm > 0) {
    return String(nextTerm)
  }
  return buildNextTerm(String(row.term || ""))
}

function buildNextDrawDate(drawTime: string) {
  let nextDate = drawTime ? parseBeijingDateTime(drawTime) : new Date()
  if (Number.isNaN(nextDate.getTime())) {
    nextDate = new Date()
  }
  nextDate.setDate(nextDate.getDate() + 1)
  return formatDateInput(nextDate)
}

export function DrawsPage() {
  const [rows, setRows] = useState<Draw[]>([])
  const [lotteries, setLotteries] = useState<LotteryType[]>([])
  const [editing, setEditing] = useState<Draw | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [draftYear, setDraftYear] = useState(String(new Date().getFullYear()))
  const [draftTerm, setDraftTerm] = useState("")
  const [draftNextTerm, setDraftNextTerm] = useState("")
  const [draftDrawDate, setDraftDrawDate] = useState("")
  const [draftNumbers, setDraftNumbers] = useState("")
  const [draftStatus, setDraftStatus] = useState("1")
  const [draftIsOpened, setDraftIsOpened] = useState("0")
  const [numbersInputKey, setNumbersInputKey] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const formRef = useRef<HTMLFormElement | null>(null)

  // Column resize (mouse + touch)
  const defaultColWidths = [50, 70, 56, 56, 220, 140, 56, 62, 76, 90]
  const [colWidths, setColWidths] = useState<number[]>(defaultColWidths)
  const resizeRef = useRef<{ index: number; startX: number; startWidth: number } | null>(null)
  const [resizingIdx, setResizingIdx] = useState<number | null>(null)

  const beginResize = useCallback((index: number, clientX: number) => {
    resizeRef.current = { index, startX: clientX, startWidth: colWidths[index] }
    setResizingIdx(index)
  }, [colWidths])

  useEffect(() => {
    if (resizingIdx === null) return

    function applyDelta(clientX: number) {
      if (!resizeRef.current) return
      const delta = clientX - resizeRef.current.startX
      setColWidths((prev) => {
        const next = [...prev]
        next[resizeRef.current!.index] = Math.max(40, resizeRef.current!.startWidth + delta)
        return next
      })
    }

    function endResize() {
      resizeRef.current = null
      setResizingIdx(null)
    }

    function onMouseMove(e: MouseEvent) { applyDelta(e.clientX) }
    function onTouchMove(e: TouchEvent) { e.preventDefault(); applyDelta(e.touches[0].clientX) }

    window.addEventListener("mousemove", onMouseMove)
    window.addEventListener("mouseup", endResize)
    window.addEventListener("touchmove", onTouchMove, { passive: false })
    window.addEventListener("touchend", endResize)
    window.addEventListener("touchcancel", endResize)
    return () => {
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseup", endResize)
      window.removeEventListener("touchmove", onTouchMove)
      window.removeEventListener("touchend", endResize)
      window.removeEventListener("touchcancel", endResize)
    }
  }, [resizingIdx])

  const taiwanLottery =
    lotteries.find((lottery) => lottery.id === TAIWAN_LOTTERY_ID) || null
  const filteredRows = rows

  async function load(currentPage?: number, currentPageSize?: number): Promise<Draw[]> {
    const p = currentPage ?? page
    const ps = currentPageSize ?? pageSize
    const [drawData, lotteryData] = await Promise.all([
      adminApi<{ draws: Draw[]; total: number; page: number; page_size: number; total_pages: number }>(
        `/admin/draws?lottery_type_id=${TAIWAN_LOTTERY_ID}&page=${p}&page_size=${ps}`,
      ),
      adminApi<{ lottery_types: LotteryType[] }>("/admin/lottery-types"),
    ])
    setRows(drawData.draws)
    if (typeof drawData.total === "number") setTotal(drawData.total)
    if (typeof drawData.total_pages === "number") setTotalPages(drawData.total_pages)
    if (typeof drawData.page === "number") setPage(drawData.page)
    if (typeof drawData.page_size === "number") setPageSize(drawData.page_size)
    setLotteries(lotteryData.lottery_types)
    return drawData.draws
  }

  function applyTermDraft(term: string) {
    setDraftTerm(term)
    setDraftNextTerm(buildNextTerm(term))
  }

  function applyEditingDraft(row: Draw) {
    setDraftYear(String(row.year || new Date().getFullYear()))
    setDraftTerm(String(row.term || ""))
    setDraftNextTerm(resolveNextTerm(row))
    setDraftDrawDate(row.draw_time?.slice(0, 10) || "")
    setDraftNumbers(row.numbers || "")
    setDraftStatus(row.status ? "1" : "0")
    setDraftIsOpened(row.is_opened ? "1" : "0")
    setNumbersInputKey((value) => value + 1)
  }

  function populateCreateDrafts(draws: Draw[]) {
    const latestDraw = getLatestTaiwanDraw(draws)
    if (!latestDraw) {
      const today = new Date()
      setDraftYear(String(today.getFullYear()))
      setDraftTerm("1")
      setDraftNextTerm("2")
      setDraftDrawDate(formatDateInput(today))
      setDraftNumbers("")
      setDraftStatus("1")
      setDraftIsOpened("0")
      setNumbersInputKey((value) => value + 1)
      return
    }

    const currentTerm = buildNextTerm(String(latestDraw.term || "")) || "1"
    const nextTerm = buildNextTerm(currentTerm)

    setDraftYear(String(latestDraw.year || new Date().getFullYear()))
    setDraftTerm(currentTerm)
    setDraftNextTerm(nextTerm)
    setDraftDrawDate(buildNextDrawDate(latestDraw.draw_time || ""))
    setDraftNumbers("")
    setDraftStatus("1")
    setDraftIsOpened("0")
    setNumbersInputKey((value) => value + 1)
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    if (!formOpen) return
    if (editing) {
      applyEditingDraft(editing)
      return
    }
    populateCreateDrafts(rows)
  }, [editing, formOpen, rows])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const numbers = String(new FormData(form).get("numbers") || "").trim()
    const missingFields: string[] = []

    if (!draftYear) missingFields.push("年份")
    if (!draftTerm) missingFields.push("本期期数")
    if (!draftNextTerm) missingFields.push("下一期期数")
    if (!numbers) missingFields.push("开奖号码")
    if (!draftDrawDate) missingFields.push("开奖日期")

    if (missingFields.length > 0) {
      alert(`请先填写完整必填项：${missingFields.join("、")}`)
      return
    }

    const duplicateTerm = filteredRows.some((row) => {
      if (editing && row.id === editing.id) return false
      return String(row.term) === draftTerm
    })
    if (duplicateTerm) {
      alert(`第 ${draftTerm} 期已存在，请勿重复提交。`)
      return
    }

    const duplicateDate = filteredRows.some((row) => {
      if (editing && row.id === editing.id) return false
      return (row.draw_time || "").slice(0, 10) === draftDrawDate
    })
    if (duplicateDate) {
      alert(`开奖日期 ${draftDrawDate} 已存在，请勿重复提交。`)
      return
    }

    const timeStr = taiwanLottery?.draw_time || "22:30:00"
    const parts = timeStr.split(":")
    const timeWithSec = parts.length >= 3 ? timeStr : `${timeStr}:00`
    const drawTime = `${draftDrawDate} ${timeWithSec}`

    if (editing && draftIsOpened === "1") {
      const drawAt = parseBeijingDateTime(drawTime)
      if (!Number.isNaN(drawAt.getTime()) && drawAt.getTime() > Date.now()) {
        alert("当前期开奖时间尚未到达，不能提前设置为已开奖。")
        return
      }
    }

    let nextTime = ""
    try {
      nextTime = String(parseBeijingDateTime(drawTime).getTime())
    } catch {
      nextTime = ""
    }

    try {
      await adminApi(editing ? `/admin/draws/${editing.id}` : "/admin/draws", {
        method: editing ? "PUT" : "POST",
        body: jsonBody({
          lottery_type_id: TAIWAN_LOTTERY_ID,
          year: Number(draftYear),
          term: Number(draftTerm),
          numbers,
          draw_time: drawTime,
          next_time: nextTime,
          status: draftStatus === "1",
          is_opened: draftIsOpened === "1",
          next_term: Number(draftNextTerm),
        }),
      })
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "保存失败，请稍后重试。"
      alert(message)
      return
    }

    const latestDraws = await load(1)

    if (editing) {
      toast.success("保存成功")
      setEditing(null)
      setFormOpen(false)
      return
    }

    setDraftNumbers("")
    setNumbersInputKey((value) => value + 1)
    toast.success("保存成功，可直接录入下一期开奖号码")
    if (latestDraws) populateCreateDrafts(latestDraws)
  }

  async function remove(id: number) {
    if (!confirm("确认删除该开奖记录吗？")) return
    await adminApi(`/admin/draws/${id}`, { method: "DELETE" })
    const targetPage = rows.length <= 1 && page > 1 ? page - 1 : page
    await load(targetPage)
  }

  return (
    <AdminShell
      title="开奖记录管理"
      description="仅管理台湾彩开奖记录，供倒计时、自动开奖与预测资料同步使用。"
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            彩种：{taiwanLottery?.name || "台湾彩"}
          </span>
          <div className="flex-1" />
          <Button
            onClick={() => {
              const nextOpen = !formOpen
              setEditing(null)
              setFormOpen(nextOpen)
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
          <Card className="relative p-4">
            <h2 className="mb-3 text-base font-semibold">
              {editing ? "修改开奖记录" : "新增开奖记录"}
            </h2>
            <form
              className="grid grid-cols-1 sm:grid-cols-2 gap-3"
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
                    默认取数据库中最新一条台湾彩记录作为参考，自动预填下一期信息。
                  </span>
                )}
              </Field>
              <Field label="年份">
                <Input
                  name="year"
                  type="number"
                  value={draftYear}
                  onChange={(event) => setDraftYear(event.target.value)}
                />
              </Field>
              <Field label="本期期数">
                <Input
                  name="term"
                  type="number"
                  value={draftTerm}
                  placeholder="自动获取"
                  onChange={(event) => applyTermDraft(event.target.value)}
                />
              </Field>
              <Field label="开奖号码（点击添加 / 删除）" className="col-span-2">
                <DrawNumbersInput
                  key={numbersInputKey}
                  name="numbers"
                  defaultValue={draftNumbers}
                />
              </Field>
              <Field label="开奖日期" className="col-span-2">
                <Input
                  name="draw_time"
                  type="date"
                  value={draftDrawDate}
                  onChange={(event) => setDraftDrawDate(event.target.value)}
                />
              </Field>
              <Field label="状态">
                <select
                  name="status"
                  value={draftStatus}
                  onChange={(event) => setDraftStatus(event.target.value)}
                  className="h-9 rounded-md border bg-background px-3 text-sm"
                >
                  <option value="1">启用</option>
                  <option value="0">停用</option>
                </select>
              </Field>
              <Field label="是否开奖">
                <select
                  name="is_opened"
                  value={draftIsOpened}
                  onChange={(event) => setDraftIsOpened(event.target.value)}
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
                  value={draftNextTerm}
                  placeholder="自动计算"
                  readOnly
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

        <DrawBallDisplayProvider>
          <Card className="overflow-auto p-4">
            <div className="mb-3">
              <DrawBallDisplayToggles />
            </div>
            <div
              className="overflow-x-auto"
              style={{ cursor: resizingIdx !== null ? "col-resize" : undefined }}
            >
              <Table style={{ tableLayout: "fixed", width: colWidths.reduce((s, w) => s + w, 0), minWidth: "100%" }}>
                <colgroup>
                  {colWidths.map((w, i) => (
                    <col key={i} style={{ width: w }} />
                  ))}
                </colgroup>
                <TableHeader>
                  <TableRow>
                    {["ID", "彩种", "年份", "期数", "开奖号码", "开奖时间", "状态", "是否开奖", "下一期期数", "操作"].map(
                      (label, i) => (
                        <TableHead key={i} className="relative select-none border-r border-border last:border-r-0">
                          <span className="whitespace-nowrap">{label}</span>
                          {/* resize handle: wide touch target with visible center line */}
                          <div
                            className="absolute right-0 top-0 h-full w-5 -mr-2.5 cursor-col-resize z-10 group"
                            onMouseDown={(e) => { e.preventDefault(); beginResize(i, e.clientX) }}
                            onTouchStart={(e) => { e.preventDefault(); beginResize(i, e.touches[0].clientX) }}
                          >
                            <div className="absolute left-1/2 top-1 -translate-x-1/2 h-[calc(100%-8px)] w-[3px] rounded-full bg-border transition-colors group-hover:bg-primary/50 group-active:bg-primary" />
                          </div>
                        </TableHead>
                      ),
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRows.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="border-r border-border">{row.id}</TableCell>
                      <TableCell className="border-r border-border">{row.lottery_name}</TableCell>
                      <TableCell className="border-r border-border">{row.year}</TableCell>
                      <TableCell className="border-r border-border">{row.term}</TableCell>
                      <TableCell className="border-r border-border">
                        <DrawBallDisplay numbers={row.numbers} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs border-r border-border">{row.draw_time}</TableCell>
                      <TableCell className="border-r border-border">
                        <StatusBadge value={row.status} />
                      </TableCell>
                      <TableCell className="border-r border-border">{row.is_opened ? "是" : "否"}</TableCell>
                      <TableCell className="border-r border-border">{row.next_term}</TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-nowrap">
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
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

          {/* Pagination */}
          <div className="flex flex-wrap items-center justify-between gap-3 mt-4 pt-3 border-t">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>共 {total} 条</span>
              <span>|</span>
              <span>第 {page} / {totalPages} 页</span>
              <Select
                value={String(pageSize)}
                onValueChange={(value) => {
                  const newSize = Number(value)
                  setPageSize(newSize)
                  load(1, newSize)
                }}
              >
                <SelectTrigger className="h-8 w-[80px] text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[10, 20, 30, 50].map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size} 条/页
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Pagination className="w-auto mx-0">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      if (page > 1) load(page - 1)
                    }}
                    className={page <= 1 ? "pointer-events-none opacity-50" : ""}
                  />
                </PaginationItem>

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => {
                    if (totalPages <= 7) return true
                    if (p === 1 || p === totalPages) return true
                    if (Math.abs(p - page) <= 1) return true
                    return false
                  })
                  .reduce<(number | "ellipsis")[]>((acc, p, idx, arr) => {
                    if (idx > 0) {
                      const prev = arr[idx - 1]
                      if (p - prev > 1) acc.push("ellipsis")
                    }
                    acc.push(p)
                    return acc
                  }, [])
                  .map((item, idx) =>
                    item === "ellipsis" ? (
                      <PaginationItem key={`e-${idx}`}>
                        <PaginationEllipsis />
                      </PaginationItem>
                    ) : (
                      <PaginationItem key={item}>
                        <PaginationLink
                          href="#"
                          isActive={item === page}
                          onClick={(e) => {
                            e.preventDefault()
                            if (item !== page) load(item)
                          }}
                        >
                          {item}
                        </PaginationLink>
                      </PaginationItem>
                    ),
                  )}

                <PaginationItem>
                  <PaginationNext
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      if (page < totalPages) load(page + 1)
                    }}
                    className={page >= totalPages ? "pointer-events-none opacity-50" : ""}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        </Card>
        </DrawBallDisplayProvider>
      </div>
    </AdminShell>
  )
}
