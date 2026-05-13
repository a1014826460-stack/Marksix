"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Plus, RefreshCw, Trash2 } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi, jsonBody } from "@/lib/admin-api"
import { AdminNotice } from "@/features/shared/AdminNotice"
import { ModuleDataPanel } from "@/features/site-data/ModuleDataPanel"
import { BulkGenerateDialog } from "@/features/site-data/BulkGenerateDialog"
import { ConfirmDialog } from "@/features/site-data/ConfirmDialog"
import { BulkDeleteDialog } from "@/features/prediction-modules/BulkDeleteDialog"
import {
  getSitePredictionModuleName,
  type Site,
  type SitePredictionModule,
  type Mechanism,
} from "@/features/shared/types"
import type { PredictionModulesBulkDeleteRequest } from "@/features/prediction-modules/types"

type SiteDataPageProps = {
  siteId: number
}

export function SiteDataPage({ siteId }: SiteDataPageProps) {
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
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)

  const configuredKeys = useMemo(
    () => new Set(modules.map((item) => item.mechanism_key)),
    [modules],
  )

  const enabledModules = useMemo(
    () => modules.filter((item) => item.status),
    [modules],
  )

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
          data.available_mechanisms[0]?.key ||
          "",
      )
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载失败")
    }
  }

  useEffect(() => {
    load()
  }, [siteId])

  async function addModule(key?: string) {
    const targetKey = key || selectedKey
    if (!targetKey) return
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules`, {
        method: "POST",
        body: jsonBody({
          mechanism_key: targetKey,
          status: true,
          sort_order: modules.length * 10,
        }),
      })
      setSearchTerm("")
      setSelectedKey("")
      setAddOpen(false)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "添加失败")
    }
  }

  function removeModule(id: number) {
    setConfirmRemoveId(id)
  }

  async function doConfirmRemove() {
    if (confirmRemoveId == null) return
    const id = confirmRemoveId
    setConfirmRemoveId(null)
    try {
      await adminApi(`/admin/sites/${siteId}/prediction-modules/${id}`, {
        method: "DELETE",
      })
      if (selectedModId === id) setSelectedModId(null)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "删除失败")
    }
  }

  async function submitGenerate(params: {
    siteId: number
    lotteryType: string
    startIssue: string
    endIssue: string
    mechanismKeys: string[]
    futureOnly: boolean
  }) {
    const { job_id } = await adminApi<{
      ok: boolean
      job_id: string
    }>(`/admin/sites/${params.siteId}/prediction-modules/generate-all`, {
      method: "POST",
      body: JSON.stringify({
        lottery_type: params.lotteryType,
        start_issue: params.startIssue,
        end_issue: params.endIssue,
        mechanism_keys: params.mechanismKeys,
        future_periods: 1,
        future_only: params.futureOnly,
      }),
    })

    for (let index = 0; index < 120; index += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000))
      try {
        const job = await adminApi<{
          status: string
          result?: {
            total_modules: number
            draw_count: number
            inserted: number
            updated: number
            errors: number
          }
          error?: string
        }>(`/admin/jobs/${job_id}`)
        if (job.status === "done" && job.result) {
          return job.result
        }
        if (job.status === "error") {
          throw new Error(job.error || "未知错误")
        }
      } catch (error) {
        if (index === 119) throw error
      }
    }

    throw new Error("批量生成超时，请稍后刷新页面查看结果")
  }

  async function handleBulkDelete(payload: PredictionModulesBulkDeleteRequest) {
    const result = await adminApi<{
      ok: boolean
      deleted: number
      estimated: number
      modules: Array<{
        moduleId: string
        tableName: string
        deleted: number
      }>
    }>(`/admin/sites/${siteId}/prediction-modules/bulk-delete`, {
      method: "DELETE",
      body: jsonBody(payload),
    })
    setMessage(`批量删除成功，共删除 ${result.deleted} 条记录`)
    setBulkDeleteOpen(false)
    setSourceFilter("all")
    setTypeFilter("")
    setWebFilter("")
    setReloadToken((prev) => prev + 1)
  }

  const selectedModule = modules.find((item) => item.id === selectedModId) || null

  return (
    <AdminShell
      title={`${site?.name || "站点"} — 站点数据管理`}
      description="点击模块按钮查看数据库数据。支持编辑、删除、重新生成、彩种筛选。"
      actions={
        <Button asChild variant="outline" size="sm">
          <Link href="/sites">返回站点列表</Link>
        </Button>
      }
    >
      <AdminNotice message={message} />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">站点:</span>
        {[
          "",
          ...Array.from(
            {
              length: (site?.end_web_id || 10) - (site?.start_web_id || 1) + 1,
            },
            (_, index) => String((site?.start_web_id || 1) + index),
          ),
        ].map((webId) => (
          <button
            key={webId}
            onClick={() => setWebFilter(webId)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-all hover:scale-105 active:scale-95 ${
              webFilter === webId
                ? "bg-primary text-primary-foreground shadow-md"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {webId === "" ? "全部" : `web_id=${webId}`}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setBulkGenerateOpen(true)}
            size="sm"
            className="transition-all hover:scale-105 active:scale-95"
          >
            <RefreshCw className="mr-1 h-4 w-4" />
            自动生成资料
          </Button>
          <Button
            variant="destructive"
            onClick={() => setBulkDeleteOpen(true)}
            size="sm"
            className="transition-all hover:scale-105 active:scale-95"
          >
            <Trash2 className="mr-1 h-4 w-4" />
            批量删除
          </Button>
          <Button
            onClick={() => setAddOpen((prev) => !prev)}
            size="sm"
            className="transition-all hover:scale-105 active:scale-95"
          >
            <Plus
              className={`mr-1 h-4 w-4 transition-transform duration-300 ${addOpen ? "rotate-45" : ""}`}
            />
            添加模块
          </Button>
        </div>
      </div>

      <BulkGenerateDialog
        open={bulkGenerateOpen}
        site={site}
        modules={enabledModules}
        onClose={() => setBulkGenerateOpen(false)}
        onMessage={setMessage}
        onGenerated={(nextSourceFilter, nextReloadToken) => {
          setSourceFilter(nextSourceFilter)
          setReloadToken(nextReloadToken)
        }}
        onSubmitGenerate={submitGenerate}
        reloadToken={reloadToken}
      />

      <BulkDeleteDialog
        open={bulkDeleteOpen}
        modules={enabledModules}
        onClose={() => setBulkDeleteOpen(false)}
        onEstimate={(payload) =>
          adminApi(`/admin/sites/${siteId}/prediction-modules/bulk-delete-estimate`, {
            method: "POST",
            body: jsonBody(payload),
          })
        }
        onSubmit={handleBulkDelete}
      />

      <div
        className={`overflow-hidden transition-all duration-300 ${addOpen ? "mb-3 max-h-[620px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        <Card className="p-3">
          <Input
            placeholder="搜索 title / key / modes_id"
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value)
              setSelectedKey("")
            }}
            className="mb-2 h-8 text-sm"
          />
          <div className="max-h-[400px] overflow-y-auto rounded-md border">
            {(() => {
              const filtered = available.filter((item) => {
                if (!searchTerm.trim()) return true
                const query = searchTerm.toLowerCase()
                return (
                  item.title.toLowerCase().includes(query) ||
                  item.key.toLowerCase().includes(query) ||
                  String(item.default_modes_id).includes(query)
                )
              })

              if (filtered.length === 0) {
                return (
                  <div className="p-4 text-center text-xs text-muted-foreground">
                    无匹配模块
                  </div>
                )
              }

              return filtered.map((item) => {
                const configured = configuredKeys.has(item.key)
                return (
                  <button
                    key={item.key}
                    type="button"
                    disabled={configured}
                    onClick={() => addModule(item.key)}
                    className={`w-full border-b px-3 py-2 text-left text-sm transition-colors last:border-b-0 ${
                      configured
                        ? "cursor-not-allowed bg-muted/30 text-muted-foreground"
                        : "cursor-pointer hover:bg-primary/10 hover:text-primary"
                    }`}
                  >
                    <span className="font-medium">{item.title}</span>
                    <span className="ml-2 text-xs text-muted-foreground">[{item.key}]</span>
                    <span className="ml-1 text-xs text-muted-foreground">
                      modes_id={item.default_modes_id}
                    </span>
                    {configured ? (
                      <span className="ml-2 text-xs font-medium text-green-600">已添加</span>
                    ) : null}
                  </button>
                )
              })
            })()}
          </div>
        </Card>
      </div>

      {modules.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          暂无预测模块，请点击“添加模块”按钮添加。
        </Card>
      ) : (
        <>
          <div
            className="mb-3 flex flex-wrap gap-1.5 overflow-x-auto rounded-lg border bg-muted/20 p-2"
            style={{ scrollbarWidth: "thin" }}
          >
            {modules.map((module) => {
              const isSelected = module.id === selectedModId
              const name = getSitePredictionModuleName(module)
              return (
                <button
                  key={module.id}
                  onClick={() => setSelectedModId(isSelected ? null : module.id)}
                  className={`group relative flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200 hover:scale-105 hover:shadow-md active:scale-95 ${
                    isSelected
                      ? "bg-primary text-primary-foreground shadow-lg ring-2 ring-primary/30"
                      : "bg-background text-foreground shadow-sm hover:bg-primary/10 hover:text-primary"
                  }`}
                >
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full transition-colors ${
                      module.status
                        ? "bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.5)]"
                        : "bg-gray-300"
                    }`}
                    title={module.status ? "启用" : "停用"}
                  />
                  <span className="max-w-[160px] truncate">{name}</span>
                  <span
                    onClick={(event) => {
                      event.stopPropagation()
                      removeModule(module.id)
                    }}
                    className="ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] opacity-0 transition-all group-hover:opacity-100 hover:bg-destructive/20 hover:text-destructive"
                    title="移除模块"
                  >
                    ×
                  </span>
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

          <ConfirmDialog
            open={confirmRemoveId != null}
            title="确认移除"
            message={
              <>
                <p className="mb-1">
                  确定要移除预测模块“
                  <span className="font-medium text-foreground">
                    {getSitePredictionModuleName(
                      modules.find((item) => item.id === confirmRemoveId),
                    ) || "?"}
                  </span>
                  ”吗？
                </p>
                <p className="text-xs text-muted-foreground">
                  该操作仅从站点配置中移除，不会删除数据库数据。
                </p>
              </>
            }
            confirmText="确认移除"
            onConfirm={doConfirmRemove}
            onCancel={() => setConfirmRemoveId(null)}
          />
        </>
      )}
    </AdminShell>
  )
}
