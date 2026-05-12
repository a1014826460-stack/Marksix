"use client"

import { useEffect, useState } from "react"
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
import { adminApi, jsonBody } from "@/lib/admin-api"
import { Field } from "@/features/shared/Field"
import { AdminNotice } from "@/features/shared/AdminNotice"
import type {
  ConfigEntry, ConfigGroup, ConfigHistoryEntry,
} from "@/features/shared/types"
import { configSourceBadgeClass } from "@/features/shared/types"

export function ConfigsPage() {
  const [configs, setConfigs] = useState<ConfigEntry[]>([])
  const [groups, setGroups] = useState<ConfigGroup[]>([])
  const [activeGroup, setActiveGroup] = useState("")
  const [keyword, setKeyword] = useState("")
  const [sourceFilter, setSourceFilter] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  // 编辑弹窗
  const [editing, setEditing] = useState<ConfigEntry | null>(null)
  const [editValue, setEditValue] = useState("")
  const [editSaving, setEditSaving] = useState(false)
  const [changeReason, setChangeReason] = useState("")

  // 历史弹窗
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyKey, setHistoryKey] = useState("")
  const [historyItems, setHistoryItems] = useState<ConfigHistoryEntry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyTotal, setHistoryTotal] = useState(0)

  async function loadGroups() {
    try {
      const data = await adminApi<{ groups: ConfigGroup[] }>("/admin/configs/groups")
      setGroups(data.groups)
    } catch { /* ignore */ }
  }

  async function loadConfigs() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (activeGroup) params.set("group", activeGroup)
      if (keyword) params.set("keyword", keyword)
      if (sourceFilter) params.set("source", sourceFilter)
      const data = await adminApi<{ configs: ConfigEntry[] }>(`/admin/configs/effective?${params}`)
      setConfigs(data.configs)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "加载失败")
    } finally { setLoading(false) }
  }

  useEffect(() => { loadGroups(); loadConfigs() }, [])
  useEffect(() => { loadConfigs() }, [activeGroup, sourceFilter])

  function showMessage(msg: string) {
    setMessage(msg)
    setTimeout(() => setMessage(""), 5000)
  }

  function startEdit(config: ConfigEntry) {
    setEditing(config)
    if (config.sensitive) {
      setEditValue("")
    } else {
      setEditValue(config.raw_value !== undefined ? String(config.raw_value ?? "") : String(config.value ?? ""))
    }
    setChangeReason("")
  }

  async function saveEdit() {
    if (!editing) return
    setEditSaving(true)
    try {
      const body: any = { value: editValue, value_type: editing.value_type }
      if (editing.sensitive && !editValue) {
        showMessage("敏感配置不能设置为空值"); setEditSaving(false); return
      }
      // 根据 value_type 转换值类型，确保后端收到正确类型
      if (editing.value_type === "bool") {
        body.value = editValue === "true"
      } else if (editing.value_type === "int") {
        body.value = parseInt(editValue) || 0
      } else if (editing.value_type === "float") {
        body.value = parseFloat(editValue) || 0
      } else if (editing.value_type === "json") {
        try { body.value = JSON.parse(editValue) } catch { showMessage("JSON 格式不合法"); setEditSaving(false); return }
      }
      if (changeReason) body.change_reason = changeReason

      await adminApi(`/admin/system-config/${encodeURIComponent(editing.key)}`, {
        method: "PUT",
        body: jsonBody(body),
      })
      showMessage(`配置 '${editing.key}' 已保存`)
      setEditing(null)
      loadConfigs()
    } catch (e) {
      showMessage(e instanceof Error ? e.message : "保存失败")
    } finally { setEditSaving(false) }
  }

  async function handleReset(key: string) {
    if (!confirm(`确定要将 '${key}' 恢复为默认值吗？`)) return
    try {
      await adminApi(`/admin/configs/${encodeURIComponent(key)}/reset`, { method: "POST" })
      showMessage(`配置 '${key}' 已恢复默认值`)
      loadConfigs()
    } catch (e) {
      showMessage(e instanceof Error ? e.message : "恢复失败")
    }
  }

  async function showHistory(key: string) {
    setHistoryKey(key)
    setHistoryOpen(true)
    setHistoryPage(1)
    await loadHistory(key, 1)
  }

  async function loadHistory(key: string, p: number) {
    setHistoryLoading(true)
    try {
      const data = await adminApi<{ items: ConfigHistoryEntry[]; total: number }>(
        `/admin/configs/history?key=${encodeURIComponent(key)}&page=${p}&page_size=20`
      )
      setHistoryItems(data.items)
      setHistoryTotal(data.total)
      setHistoryPage(p)
    } catch { /* ignore */ } finally { setHistoryLoading(false) }
  }

  // 根据配置类型渲染对应的编辑控件
  function renderEditInput(config: ConfigEntry) {
    if (config.sensitive) {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">新值（敏感配置，当前值已脱敏）</label>
          <Input type="password" value={editValue} onChange={(e) => setEditValue(e.target.value)} placeholder="输入新值" className="h-9 text-sm" />
        </div>
      )
    }
    if (config.value_type === "bool") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {config.value ? "true" : "false"}</label>
          <select value={editValue} onChange={(e) => setEditValue(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
            <option value="true">true (启用)</option>
            <option value="false">false (停用)</option>
          </select>
        </div>
      )
    }
    if (config.value_type === "time") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
          <Input value={editValue} onChange={(e) => setEditValue(e.target.value)} placeholder="HH:mm 如 21:30" className="h-9 text-sm" />
        </div>
      )
    }
    if (config.value_type === "json") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
          <Textarea value={editValue} onChange={(e) => setEditValue(e.target.value)} placeholder='合法 JSON，如 {"key": "value"}' className="h-32 text-xs font-mono" />
        </div>
      )
    }
    if (config.value_type === "int" || config.value_type === "float") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
          <Input type="number" value={editValue} onChange={(e) => setEditValue(e.target.value)} step={config.value_type === "float" ? "0.1" : "1"} className="h-9 text-sm" />
        </div>
      )
    }
    return (
      <div>
        <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
        <Input value={editValue} onChange={(e) => setEditValue(e.target.value)} className="h-9 text-sm" />
      </div>
    )
  }

  return (
    <AdminShell
      title="配置信息管理"
      description="统一查看和修改系统运行配置。修改配置需谨慎，部分配置修改后需重启服务生效。"
    >
      <AdminNotice message={message} />

      {/* 分组 Tabs */}
      <div className="mb-4 flex flex-wrap gap-1.5 overflow-x-auto rounded-lg border bg-muted/20 p-2">
        <button
          onClick={() => setActiveGroup("")}
          className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
            activeGroup === "" ? "bg-primary text-primary-foreground" : "bg-background text-foreground hover:bg-primary/10"
          }`}
        >
          全部
        </button>
        {groups.map((g) => (
          <button
            key={g.key}
            onClick={() => setActiveGroup(g.key)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              activeGroup === g.key ? "bg-primary text-primary-foreground" : "bg-background text-foreground hover:bg-primary/10"
            }`}
            title={g.description}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* 搜索 + 来源筛选 */}
      <div className="mb-4 flex gap-2">
        <Input placeholder="搜索配置项或说明..." value={keyword} onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") loadConfigs() }} className="max-w-xs" />
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} className="h-9 rounded-md border bg-background px-3 text-sm">
          <option value="">全部来源</option>
          <option value="database">数据库</option>
          <option value="config.yaml">配置文件</option>
        </select>
        <Button variant="outline" size="sm" onClick={loadConfigs}>搜索</Button>
      </div>

      {/* 配置表格 */}
      <Card className="overflow-auto p-0">
        {loading ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">加载中...</div>
        ) : configs.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">暂无匹配配置</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[220px]">配置项</TableHead>
                <TableHead className="min-w-[120px]">当前值</TableHead>
                <TableHead className="min-w-[100px]">默认值</TableHead>
                <TableHead className="min-w-[60px]">类型</TableHead>
                <TableHead className="min-w-[70px]">来源</TableHead>
                <TableHead className="min-w-[160px]">说明</TableHead>
                <TableHead className="min-w-[60px]">需重启</TableHead>
                <TableHead className="min-w-[120px]">最后修改</TableHead>
                <TableHead className="min-w-[160px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configs.map((config) => (
                <TableRow key={config.key}>
                  <TableCell className="text-xs font-medium font-mono">{config.key}</TableCell>
                  <TableCell className="max-w-[200px] truncate text-xs" title={String(config.value ?? "")}>
                    {config.sensitive ? "***已配置***" : String(config.value ?? "")}
                  </TableCell>
                  <TableCell className="max-w-[100px] truncate text-xs text-muted-foreground">
                    {config.sensitive ? "***" : String(config.default_value ?? "")}
                  </TableCell>
                  <TableCell className="text-xs">{config.value_type}</TableCell>
                  <TableCell>
                    <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${configSourceBadgeClass(config.source)}`}>
                      {config.source === "database" ? "数据库" : config.source === "config.yaml" ? "配置文件" : config.source}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate text-xs" title={config.description}>{config.description}</TableCell>
                  <TableCell className="text-xs">
                    {config.requires_restart ? <span className="text-amber-600 font-medium">是</span> : "否"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs">
                    {config.updated_at ? config.updated_at.replace("T", " ").slice(0, 16) : "-"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {config.editable && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => startEdit(config)}>编辑</Button>
                      )}
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => showHistory(config.key)}>历史</Button>
                      {config.source === "database" && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-amber-600" onClick={() => handleReset(config.key)}>恢复默认</Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setEditing(null)}>
          <div className="max-h-[80vh] w-[500px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-1 text-base font-semibold">编辑配置</h3>
            <div className="mb-3 text-xs text-muted-foreground space-y-1">
              <div>配置项: <code className="font-mono bg-muted px-1 rounded">{editing.key}</code></div>
              <div>类型: {editing.value_type} | 来源: {editing.source} | 需重启: {editing.requires_restart ? "是" : "否"}</div>
              <div>说明: {editing.description || "-"}</div>
            </div>
            {renderEditInput(editing)}
            <div className="mt-3">
              <label className="mb-1 block text-xs font-medium">修改原因（可选）</label>
              <Input value={changeReason} onChange={(e) => setChangeReason(e.target.value)} placeholder="例如：调整开奖时间" className="h-9 text-sm" />
            </div>
            {editing.requires_restart && (
              <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                此配置修改后需要重启服务才能生效。
              </div>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setEditing(null)}>取消</Button>
              <Button size="sm" onClick={saveEdit} disabled={editSaving}>{editSaving ? "保存中..." : "保存"}</Button>
            </div>
          </div>
        </div>
      )}

      {/* 变更历史弹窗 */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setHistoryOpen(false)}>
          <div className="max-h-[80vh] w-[700px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold">变更历史: <code className="font-mono text-sm bg-muted px-1 rounded">{historyKey}</code></h3>
              <Button variant="outline" size="sm" onClick={() => setHistoryOpen(false)}>关闭</Button>
            </div>
            {historyLoading ? (
              <div className="py-4 text-center text-sm text-muted-foreground">加载中...</div>
            ) : historyItems.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">暂无变更记录</div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[140px]">时间</TableHead>
                      <TableHead className="min-w-[200px]">旧值</TableHead>
                      <TableHead className="min-w-[200px]">新值</TableHead>
                      <TableHead className="min-w-[80px]">操作人</TableHead>
                      <TableHead className="min-w-[100px]">原因</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historyItems.map((h) => (
                      <TableRow key={h.id}>
                        <TableCell className="whitespace-nowrap text-xs">{h.changed_at.replace("T", " ").slice(0, 19)}</TableCell>
                        <TableCell className="max-w-[180px] truncate text-xs font-mono" title={h.old_value}>{h.old_value || "(空)"}</TableCell>
                        <TableCell className="max-w-[180px] truncate text-xs font-mono" title={h.new_value}>{h.new_value}</TableCell>
                        <TableCell className="text-xs">{h.changed_by || "-"}</TableCell>
                        <TableCell className="text-xs">{h.change_reason || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {historyTotal > 20 && (
                  <div className="flex justify-center gap-2 mt-3">
                    <Button variant="outline" size="sm" disabled={historyPage <= 1} onClick={() => loadHistory(historyKey, historyPage - 1)}>上一页</Button>
                    <Button variant="outline" size="sm" disabled={historyPage * 20 >= historyTotal} onClick={() => loadHistory(historyKey, historyPage + 1)}>下一页</Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </AdminShell>
  )
}
