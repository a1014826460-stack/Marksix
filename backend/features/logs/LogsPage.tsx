"use client"

import { useEffect, useState } from "react"
import { FileDown } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { adminApi } from "@/lib/admin-api"
import { Field } from "@/features/shared/Field"
import { AdminNotice } from "@/features/shared/AdminNotice"
import type { LogEntry } from "@/features/shared/types"
import { formatLogTime, levelBadgeClass } from "@/features/shared/types"

export function LogsPage() {
  const [items, setItems] = useState<LogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  // 筛选状态
  const [level, setLevel] = useState("")
  const [module, setModule] = useState("")
  const [keyword, setKeyword] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [userId, setUserId] = useState("")
  const [siteId, setSiteId] = useState("")
  const [lotteryTypeId, setLotteryTypeId] = useState("")

  // 可用选项（从服务端返回，避免硬编码）
  const [availableLevels, setAvailableLevels] = useState<string[]>([])
  const [availableModules, setAvailableModules] = useState<string[]>([])

  // 详情弹窗
  const [detail, setDetail] = useState<LogEntry | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  async function load(p?: number) {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set("page", String(p ?? page))
      params.set("page_size", String(pageSize))
      if (level) params.set("level", level)
      if (module) params.set("module", module)
      if (keyword) params.set("keyword", keyword)
      if (dateFrom) params.set("date_from", dateFrom)
      if (dateTo) params.set("date_to", dateTo)
      if (userId) params.set("user_id", userId)
      if (siteId) params.set("site_id", siteId)
      if (lotteryTypeId) params.set("lottery_type_id", lotteryTypeId)

      const data = await adminApi<{
        items: LogEntry[]; total: number; page: number
        page_size: number; total_pages: number
        available_levels: string[]; available_modules: string[]
      }>(`/admin/logs?${params}`)
      setItems(data.items)
      setTotal(data.total)
      if (p) setPage(p)
      setAvailableLevels(data.available_levels || [])
      setAvailableModules(data.available_modules || [])
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "加载失败")
    } finally { setLoading(false) }
  }

  useEffect(() => { load(1) }, [])

  async function showDetail(logId: number) {
    setDetailLoading(true)
    try {
      const data = await adminApi<LogEntry>(`/admin/logs/${logId}`)
      setDetail(data)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "加载详情失败")
    } finally { setDetailLoading(false) }
  }

  async function handleExport() {
    try {
      const params = new URLSearchParams()
      if (level) params.set("level", level)
      if (module) params.set("module", module)
      if (keyword) params.set("keyword", keyword)
      if (dateFrom) params.set("date_from", dateFrom)
      if (dateTo) params.set("date_to", dateTo)

      const data = await adminApi<{ rows: LogEntry[] }>(`/admin/logs/export?${params}`)
      // 构建 CSV 内容，BOM 前缀确保 Excel 正确识别 UTF-8 编码
      const csv = [
        ["时间", "等级", "模块", "消息", "错误类型", "错误消息", "文件", "用户ID", "站点ID", "彩种ID", "年份", "期数", "任务类型", "请求路径"].join(","),
        ...data.rows.map(r => [
          r.created_at, r.level, r.module, `"${(r.message || "").replace(/"/g, '""')}"`,
          r.exc_type || "", r.exc_message || "", r.file_path || "", r.user_id || "",
          r.site_id || "", r.lottery_type_id || "", r.year || "", r.term || "",
          r.task_type || "", r.request_path || ""
        ].join(","))
      ].join("\n")

      const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url; a.download = `logs_${new Date().toISOString().slice(0, 10)}.csv`; a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "导出失败")
    }
  }

  function resetFilters() {
    setLevel(""); setModule(""); setKeyword(""); setDateFrom(""); setDateTo("")
    setUserId(""); setSiteId(""); setLotteryTypeId(""); load(1)
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <AdminShell
      title="日志管理"
      description="查看系统错误日志、爬虫日志、调度任务日志、预测生成日志等信息。支持按等级、模块、时间筛选。"
      actions={
        <Button variant="outline" size="sm" onClick={handleExport}>
          <FileDown className="mr-1 h-4 w-4" />导出 CSV
        </Button>
      }
    >
      <AdminNotice message={message} />

      <Card className="mb-4 p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Field label="日志等级">
            <select value={level} onChange={(e) => setLevel(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option value="">全部等级</option>
              {availableLevels.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </Field>
          <Field label="模块">
            <select value={module} onChange={(e) => setModule(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option value="">全部模块</option>
              {availableModules.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="关键词">
            <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="搜索消息内容" />
          </Field>
          <Field label="开始时间">
            <Input type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </Field>
          <Field label="结束时间">
            <Input type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </Field>
          <Field label="用户ID">
            <Input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="用户ID" />
          </Field>
          <Field label="站点ID">
            <Input value={siteId} onChange={(e) => setSiteId(e.target.value)} placeholder="站点ID" />
          </Field>
          <Field label="彩种">
            <select value={lotteryTypeId} onChange={(e) => setLotteryTypeId(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option value="">全部彩种</option>
              <option value="1">香港彩</option>
              <option value="2">澳门彩</option>
              <option value="3">台湾彩</option>
            </select>
          </Field>
        </div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={() => load(1)}>查询</Button>
          <Button variant="outline" size="sm" onClick={resetFilters}>重置</Button>
        </div>
      </Card>

      <Card className="overflow-auto p-0">
        {loading ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">加载中...</div>
        ) : items.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">暂无日志数据</div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[140px]">时间</TableHead>
                  <TableHead className="min-w-[60px]">等级</TableHead>
                  <TableHead className="min-w-[100px]">模块</TableHead>
                  <TableHead className="min-w-[200px]">消息</TableHead>
                  <TableHead className="min-w-[60px]">用户</TableHead>
                  <TableHead className="min-w-[60px]">站点</TableHead>
                  <TableHead className="min-w-[60px]">彩种</TableHead>
                  <TableHead className="min-w-[80px]">期号</TableHead>
                  <TableHead className="min-w-[70px]">耗时</TableHead>
                  <TableHead className="min-w-[70px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="whitespace-nowrap text-xs">{formatLogTime(row.created_at)}</TableCell>
                    <TableCell>
                      <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${levelBadgeClass(row.level)}`}>
                        {row.level}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs">{row.module || "-"}</TableCell>
                    <TableCell className="max-w-[300px] truncate text-xs" title={row.message}>
                      {row.exc_type ? <span className="font-medium text-red-600 mr-1">[{row.exc_type}]</span> : null}
                      {row.message}
                    </TableCell>
                    <TableCell className="text-xs">{row.user_id || "-"}</TableCell>
                    <TableCell className="text-xs">{row.site_id || "-"}</TableCell>
                    <TableCell className="text-xs">
                      {row.lottery_type_id === 1 ? "香港" : row.lottery_type_id === 2 ? "澳门" : row.lottery_type_id === 3 ? "台湾" : row.lottery_type_id || "-"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {row.year && row.term ? `${row.year}-${String(row.term).padStart(3, "0")}` : "-"}
                    </TableCell>
                    <TableCell className="text-xs">{row.duration_ms != null ? `${row.duration_ms}ms` : "-"}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => showDetail(row.id)}>
                        详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="flex items-center justify-between border-t px-4 py-2">
              <span className="text-xs text-muted-foreground">
                共 {total} 条，第 {page}/{totalPages} 页
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">每页</span>
                <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); load(1) }} className="h-7 rounded border bg-background px-1 text-xs">
                  {[20, 30, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
                <div className="flex gap-1 ml-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => load(page - 1)} className="h-7 text-xs">上一页</Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => load(page + 1)} className="h-7 text-xs">下一页</Button>
                </div>
              </div>
            </div>
          </>
        )}
      </Card>

      {detailLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="rounded-lg bg-background p-6 shadow-xl text-sm">加载中...</div>
        </div>
      )}

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDetail(null)}>
          <div className="max-h-[85vh] w-[800px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold">日志详情 #{detail.id}</h3>
              <Button variant="outline" size="sm" onClick={() => setDetail(null)}>关闭</Button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div><span className="text-muted-foreground">时间:</span> {formatLogTime(detail.created_at)}</div>
                <div><span className="text-muted-foreground">等级:</span> <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${levelBadgeClass(detail.level)}`}>{detail.level}</span></div>
                <div><span className="text-muted-foreground">模块:</span> {detail.module || "-"}</div>
                <div><span className="text-muted-foreground">函数:</span> {detail.func_name || "-"}</div>
                <div><span className="text-muted-foreground">文件:</span> {detail.file_path || "-"}:{detail.line_number}</div>
                <div><span className="text-muted-foreground">耗时:</span> {detail.duration_ms != null ? `${detail.duration_ms}ms` : "-"}</div>
                {detail.user_id && <div><span className="text-muted-foreground">用户ID:</span> {detail.user_id}</div>}
                {detail.site_id && <div><span className="text-muted-foreground">站点ID:</span> {detail.site_id}</div>}
                {detail.lottery_type_id && <div><span className="text-muted-foreground">彩种ID:</span> {detail.lottery_type_id}</div>}
                {detail.year && <div><span className="text-muted-foreground">年份:</span> {detail.year}</div>}
                {detail.term && <div><span className="text-muted-foreground">期数:</span> {detail.term}</div>}
                {detail.task_type && <div><span className="text-muted-foreground">任务类型:</span> {detail.task_type}</div>}
                {detail.task_key && <div><span className="text-muted-foreground">任务Key:</span> {detail.task_key}</div>}
                {detail.request_path && <div><span className="text-muted-foreground">请求路径:</span> {detail.request_method || ""} {detail.request_path}</div>}
              </div>
              <div>
                <div className="text-muted-foreground mb-1 font-medium">消息:</div>
                <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[120px] overflow-y-auto">{detail.message}</pre>
              </div>
              {detail.exc_type && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">异常:</div>
                  <div className="text-sm text-red-600">{detail.exc_type}: {detail.exc_message}</div>
                </div>
              )}
              {detail.stack_trace && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">堆栈跟踪:</div>
                  <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[300px] overflow-y-auto font-mono">{detail.stack_trace}</pre>
                </div>
              )}
              {detail.request_params && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">请求参数:</div>
                  <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[120px] overflow-y-auto font-mono">{detail.request_params}</pre>
                </div>
              )}
              <div>
                <div className="text-muted-foreground mb-1 font-medium">原始日志 JSON:</div>
                <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[200px] overflow-y-auto font-mono">{JSON.stringify(detail, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
