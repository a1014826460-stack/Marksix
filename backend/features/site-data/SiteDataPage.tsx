"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Plus, RefreshCw } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi, jsonBody } from "@/lib/admin-api"
import { AdminNotice } from "@/features/shared/AdminNotice"
import { ModuleDataPanel } from "@/features/site-data/ModuleDataPanel"
import { BulkGenerateDialog } from "@/features/site-data/BulkGenerateDialog"
import { ConfirmDialog } from "@/features/site-data/ConfirmDialog"
import {
  getSitePredictionModuleName,
  type Site,
  type SitePredictionModule,
  type Mechanism,
} from "@/features/shared/types"

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

  const configuredKeys = useMemo(
    () => new Set(modules.map((item) => item.mechanism_key)),
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

  async function removeModule(id: number) {
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

  const selectedModule = modules.find((m) => m.id === selectedModId) || null

  return (
    <AdminShell
      title={`${site?.name || "站点"} — 站点数据管理`}
      description="点击模块按钮查看数据库数据。支持编辑、删除、重新生成、彩种筛选。"
      actions={
        <Button asChild variant="outline" size="sm">
          <Link href="/sites">← 返回站点列表</Link>
        </Button>
      }
    >
      <AdminNotice message={message} />

      {/* 顶部：站点筛选 + 添加 */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">站点:</span>
        {[
          "",
          ...Array.from(
            {
              length:
                (site?.end_web_id || 10) - (site?.start_web_id || 1) + 1,
            },
            (_, i) => String((site?.start_web_id || 1) + i),
          ),
        ].map((w) => (
          <button
            key={w}
            onClick={() => setWebFilter(w)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-all hover:scale-105 active:scale-95 ${
              webFilter === w
                ? "bg-primary text-primary-foreground shadow-md"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {w === "" ? "全部" : `web_id=${w}`}
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
            自动生成全部资料
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

      {/* 批量生成弹窗 */}
      <BulkGenerateDialog
        open={bulkGenerateOpen}
        site={site}
        modules={modules}
        onClose={() => setBulkGenerateOpen(false)}
        onMessage={setMessage}
        onGenerated={(sf, rt) => {
          setSourceFilter(sf)
          setReloadToken(rt)
        }}
        reloadToken={reloadToken}
      />

      {/* 添加模块面板 */}
      <div
        className={`overflow-hidden transition-all duration-300 ${addOpen ? "mb-3 max-h-[620px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        <Card className="p-3">
          <Input
            placeholder="搜索 title / key / modes_id（共 335 个可选模块）…"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setSelectedKey("")
            }}
            className="mb-2 h-8 text-sm"
          />
          <div className="max-h-[400px] overflow-y-auto rounded-md border">
            {(() => {
              const filtered = available.filter((item) => {
                if (!searchTerm.trim()) return true
                const q = searchTerm.toLowerCase()
                return (
                  item.title.toLowerCase().includes(q) ||
                  item.key.toLowerCase().includes(q) ||
                  String(item.default_modes_id).includes(q)
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
                    className={`w-full text-left px-3 py-2 text-sm border-b last:border-b-0 transition-colors ${
                      configured
                        ? "bg-muted/30 text-muted-foreground cursor-not-allowed"
                        : "hover:bg-primary/10 hover:text-primary cursor-pointer"
                    }`}
                  >
                    <span className="font-medium">{item.title}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      [{item.key}]
                    </span>
                    <span className="ml-1 text-xs text-muted-foreground">
                      modes_id={item.default_modes_id}
                    </span>
                    {configured && (
                      <span className="ml-2 text-xs text-green-600 font-medium">
                        已添加
                      </span>
                    )}
                  </button>
                )
              })
            })()}
          </div>
        </Card>
      </div>

      {/* 模块按钮栏 */}
      {modules.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          暂无预测模块，请点击「添加模块」按钮添加。
        </Card>
      ) : (
        <>
          <div
            className="mb-3 flex flex-wrap gap-1.5 overflow-x-auto rounded-lg border bg-muted/20 p-2"
            style={{ scrollbarWidth: "thin" }}
          >
            {modules.map((mod) => {
              const isSelected = mod.id === selectedModId
              const name = getSitePredictionModuleName(mod)
              return (
                <button
                  key={mod.id}
                  onClick={() =>
                    setSelectedModId(isSelected ? null : mod.id)
                  }
                  className={`group relative flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200
                    hover:scale-105 hover:shadow-md active:scale-95
                    ${
                      isSelected
                        ? "bg-primary text-primary-foreground shadow-lg ring-2 ring-primary/30"
                        : "bg-background text-foreground shadow-sm hover:bg-primary/10 hover:text-primary"
                    }`}
                >
                  <span
                    className={`h-2 w-2 rounded-full shrink-0 transition-colors ${mod.status ? "bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.5)]" : "bg-gray-300"}`}
                    title={mod.status ? "启用" : "停用"}
                  />
                  <span className="truncate max-w-[160px]">{name}</span>
                  <span
                    onClick={(e) => {
                      e.stopPropagation()
                      removeModule(mod.id)
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

          {/* 删除确认弹窗 */}
          <ConfirmDialog
            open={confirmRemoveId != null}
            title="确认移除"
            message={
              <>
                <p className="mb-1">
                  确定要移除预测模块{" "}
                  <span className="font-medium text-foreground">
                    「
                    {getSitePredictionModuleName(
                      modules.find((m) => m.id === confirmRemoveId),
                    ) || "?"}
                    」
                  </span>{" "}
                  吗？
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
