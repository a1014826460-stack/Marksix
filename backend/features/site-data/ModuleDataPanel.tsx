"use client"

import { useEffect, useRef, useState } from "react"
import { RefreshCw } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { adminApi, jsonBody } from "@/lib/admin-api"
import { AdminNotice } from "@/features/shared/AdminNotice"
import { RowEditDialog } from "@/features/site-data/RowEditDialog"
import { RegenerateDialog } from "@/features/site-data/RegenerateDialog"
import { ConfirmDialog } from "@/features/site-data/ConfirmDialog"
import {
  getSitePredictionModuleName,
  type SitePredictionModule,
  type AnyRecord,
} from "@/features/shared/types"

type ModuleDataPanelProps = {
  module: SitePredictionModule
  siteId: number
  typeFilter: string
  webFilter: string
  sourceFilter: string
  reloadToken: number
  onTypeFilterChange: (v: string) => void
  onSourceFilterChange: (v: string) => void
  onClose: () => void
}

export function ModuleDataPanel({
  module,
  siteId,
  typeFilter,
  webFilter,
  sourceFilter,
  reloadToken,
  onTypeFilterChange,
  onSourceFilterChange,
  onClose,
}: ModuleDataPanelProps) {
  const resolvedModeId =
    module.resolved_mode_id ?? module.mode_id ?? module.default_modes_id
  const tableName = module.default_table || `mode_payload_${resolvedModeId}`
  const [payload, setPayload] = useState<{
    rows: AnyRecord[]
    total: number
    columns: string[]
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [search, setSearch] = useState("")
  const [msg, setMsg] = useState("")
  const [editing, setEditing] = useState<AnyRecord | null>(null)
  const [regenOpen, setRegenOpen] = useState(false)
  const [confirmDeleteRow, setConfirmDeleteRow] = useState<AnyRecord | null>(null)
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [moduleStatus, setModuleStatus] = useState(module.status)

  useEffect(() => {
    setModuleStatus(module.status)
  }, [module.status])

  const typeFilterRef = useRef(typeFilter)
  typeFilterRef.current = typeFilter
  const webFilterRef = useRef(webFilter)
  webFilterRef.current = webFilter
  const searchRef = useRef(search)
  searchRef.current = search
  const sourceRef = useRef(sourceFilter)
  sourceRef.current = sourceFilter

  function resolveRowSource(row?: AnyRecord | null) {
    const candidate = String(
      row?.data_source ?? sourceRef.current ?? "public",
    )
      .trim()
      .toLowerCase()
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
      const data = await adminApi<{
        rows: AnyRecord[]
        total: number
        columns: string[]
      }>(`/admin/sites/${siteId}/mode-payload/${tableName}?${params}`)
      setPayload(data)
      setPage(p)
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "加载失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setSelectedRows(new Set())
    fetchPayload(1)
  }, [typeFilter, webFilter, sourceFilter, reloadToken, pageSize])

  const totalPages = payload ? Math.ceil(payload.total / pageSize) : 0

  async function handleToggleStatus() {
    const newStatus = !moduleStatus
    setToggling(true)
    try {
      await adminApi(
        `/admin/sites/${siteId}/prediction-modules/${module.id}`,
        { method: "PATCH", body: jsonBody({ status: newStatus }) },
      )
      setModuleStatus(newStatus)
      setMsg(`模块已${newStatus ? "启用" : "停用"}`)
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "操作失败")
    } finally {
      setToggling(false)
    }
  }

  async function deleteRow(row: AnyRecord) {
    setConfirmDeleteRow(row)
  }

  async function doConfirmDeleteRow() {
    if (!confirmDeleteRow) return
    const row = confirmDeleteRow
    setConfirmDeleteRow(null)
    try {
      await adminApi(
        `/admin/sites/${siteId}/mode-payload/${tableName}/${row.id}?source=${resolveRowSource(row)}`,
        { method: "DELETE" },
      )
      setMsg("已删除")
      fetchPayload(page)
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "删除失败")
    }
  }

  async function doBulkDelete() {
    if (selectedRows.size === 0) return
    setConfirmBulkDelete(false)
    let deleted = 0
    let failed = 0
    for (const rowKey of selectedRows) {
      const [src, id] = rowKey.split("::", 2)
      try {
        await adminApi(
          `/admin/sites/${siteId}/mode-payload/${tableName}/${id}?source=${src}`,
          { method: "DELETE" },
        )
        deleted++
      } catch {
        failed++
      }
    }
    setSelectedRows(new Set())
    setMsg(
      `批量删除完成: 成功 ${deleted}${failed > 0 ? `, 失败 ${failed}` : ""}`,
    )
    fetchPayload(page)
  }

  function toggleRowSelection(rowKey: string) {
    setSelectedRows((prev) => {
      const next = new Set(prev)
      if (next.has(rowKey)) next.delete(rowKey)
      else next.add(rowKey)
      return next
    })
  }

  function toggleAllRows() {
    if (!payload) return
    if (selectedRows.size === payload.rows.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(
        new Set(
          payload.rows.map(
            (r) => `${resolveRowSource(r)}::${r.id ?? ""}`,
          ),
        ),
      )
    }
  }

  return (
    <Card className="overflow-hidden border-t-2 border-t-primary/50 shadow-lg">
      {/* 顶部模块信息栏 */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2.5">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-semibold">
            {getSitePredictionModuleName(module)}
          </span>
          <span className="text-muted-foreground">|</span>
          <span className="text-xs text-muted-foreground">
            [{module.mechanism_key}]
          </span>
          <span className="text-xs text-muted-foreground">
            mode_id={resolvedModeId}
          </span>
          <span className="text-xs text-muted-foreground">{tableName}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className={`text-[10px] font-medium ${moduleStatus ? "text-green-600" : "text-gray-400"}`}>
              {moduleStatus ? "启用" : "停用"}
            </span>
            <Switch
              checked={moduleStatus}
              disabled={toggling}
              onCheckedChange={handleToggleStatus}
            />
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-7 text-xs"
          >
            ▲ 收起
          </Button>
        </div>
      </div>

      {/* 筛选工具栏 */}
      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">
          数据源:
        </span>
        {[
          { v: "all", l: "全部数据" },
          { v: "public", l: "原始数据" },
          { v: "created", l: "生成数据" },
        ].map((s) => (
          <button
            key={s.v}
            onClick={() => onSourceFilterChange(s.v)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${
              sourceFilter === s.v
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {s.l}
          </button>
        ))}
        <span className="ml-2 text-xs font-medium text-muted-foreground">
          彩种:
        </span>
        {["", "1", "2", "3"].map((t) => (
          <button
            key={t}
            onClick={() => onTypeFilterChange(t)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${
              typeFilter === t
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {t === ""
              ? "全部"
              : t === "1"
                ? "香港"
                : t === "2"
                  ? "澳门"
                  : "台湾"}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Input
            placeholder="搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") fetchPayload(1)
            }}
            className="h-7 w-36 text-xs"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchPayload(1)}
            className="h-7 text-xs"
          >
            搜索
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRegenOpen(true)}
            className="h-7 text-xs"
            style={{ display: "none" }}
          >
            <RefreshCw className="mr-1 h-3 w-3" />
            重新生成资料
          </Button>
        </div>
      </div>

      <AdminNotice message={msg} />

      {/* 数据表格 */}
      {loading ? (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">
          加载中...
        </div>
      ) : payload && payload.rows.length > 0 ? (
        <>
          <div className="overflow-x-auto" style={{ maxHeight: "55vh" }}>
            <table
              className="w-full text-xs"
              style={{ minWidth: 800 }}
            >
              <thead className="sticky top-0 bg-muted/80">
                <tr>
                  <th
                    className="whitespace-nowrap border-b border-r px-2 py-1.5 text-center font-medium"
                    style={{ width: 36 }}
                  >
                    <input
                      type="checkbox"
                      onChange={toggleAllRows}
                      checked={
                        payload.rows.length > 0 &&
                        selectedRows.size === payload.rows.length
                      }
                      className="h-3.5 w-3.5"
                    />
                  </th>
                  {payload.columns.map((col) => (
                    <th
                      key={col}
                      className="whitespace-nowrap border-b border-r px-2 py-1.5 text-left font-medium"
                      style={{
                        resize: "horizontal",
                        overflow: "auto",
                        minWidth: 80,
                        maxWidth: 400,
                      }}
                    >
                      {col}
                    </th>
                  ))}
                  <th
                    className="whitespace-nowrap border-b px-2 py-1.5 text-left font-medium"
                    style={{ minWidth: 100 }}
                  >
                    操作
                  </th>
                </tr>
              </thead>
              <tbody>
                {payload.rows.map((row, idx) => {
                  const rowKey = `${resolveRowSource(row)}::${row.id ?? `row_${idx}`}`
                  return (
                    <tr
                      key={`${row.data_source ?? sourceFilter}_${row.id ?? `row_${idx}`}`}
                      className={`border-b hover:bg-muted/20 ${selectedRows.has(rowKey) ? "bg-primary/10" : ""}`}
                    >
                      <td className="border-r px-2 py-1 text-center">
                        <input
                          type="checkbox"
                          checked={selectedRows.has(rowKey)}
                          onChange={() => toggleRowSelection(rowKey)}
                          className="h-3.5 w-3.5"
                        />
                      </td>
                      {payload.columns.map((col) => (
                        <td
                          key={col}
                          className="max-w-[300px] truncate border-r px-2 py-1"
                          title={String(row[col] ?? "")}
                        >
                          {row[col] != null ? String(row[col]) : ""}
                        </td>
                      ))}
                      <td className="px-2 py-1">
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-xs"
                            onClick={() => setEditing(row)}
                          >
                            编辑
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-xs text-destructive"
                            onClick={() => deleteRow(row)}
                          >
                            删除
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* 分页栏 */}
          <div className="flex items-center justify-between border-t px-4 py-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                共 {payload.total} 条，第 {page}/{totalPages} 页
              </span>
              {selectedRows.size > 0 && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmBulkDelete(true)}
                  className="h-7 text-xs"
                >
                  删除选中 ({selectedRows.size})
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">每页</span>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="h-7 rounded border bg-background px-1 text-xs"
              >
                {[20, 30, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              <span className="text-xs text-muted-foreground">条</span>
              <div className="flex gap-1 ml-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => fetchPayload(page - 1)}
                  className="h-7 text-xs"
                >
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => fetchPayload(page + 1)}
                  className="h-7 text-xs"
                >
                  下一页
                </Button>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">
          暂无数据
        </div>
      )}

      {/* 行编辑弹窗 */}
      {editing && (
        <RowEditDialog
          editing={editing}
          siteId={siteId}
          tableName={tableName}
          source={resolveRowSource(editing)}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setMsg("已保存")
            setEditing(null)
            fetchPayload(page)
          }}
          onError={(err) => setMsg(err)}
        />
      )}

      {/* 重新生成弹窗 */}
      <RegenerateDialog
        open={regenOpen}
        module={module}
        siteId={siteId}
        tableName={tableName}
        typeFilter={typeFilter}
        onClose={() => setRegenOpen(false)}
        onSuccess={(m) => setMsg(m)}
        onError={(m) => setMsg(m)}
        onRefresh={() => fetchPayload(page)}
        page={page}
      />

      {/* 行删除确认 */}
      <ConfirmDialog
        open={confirmDeleteRow !== null}
        title="确认删除"
        message={
          <p>
            确定要删除{" "}
            <span className="font-medium text-foreground">
              id={confirmDeleteRow?.id}
            </span>{" "}
            的记录吗？此操作不可撤销。
          </p>
        }
        confirmText="确认删除"
        onConfirm={doConfirmDeleteRow}
        onCancel={() => setConfirmDeleteRow(null)}
      />

      {/* 批量删除确认 */}
      <ConfirmDialog
        open={confirmBulkDelete}
        title="确认批量删除"
        message={
          <p>
            确定要删除选中的{" "}
            <span className="font-medium text-foreground">
              {selectedRows.size}
            </span>{" "}
            条记录吗？此操作不可撤销。
          </p>
        }
        confirmText="确认删除"
        onConfirm={doBulkDelete}
        onCancel={() => setConfirmBulkDelete(false)}
      />
    </Card>
  )
}
