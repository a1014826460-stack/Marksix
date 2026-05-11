"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { adminApi } from "@/lib/admin-api"
import type { AnyRecord } from "@/features/shared/types"

type RowEditDialogProps = {
  editing: AnyRecord
  siteId: number
  tableName: string
  source: string
  onClose: () => void
  onSaved: () => void
  onError: (msg: string) => void
}

export function RowEditDialog({
  editing,
  siteId,
  tableName,
  source,
  onClose,
  onSaved,
  onError,
}: RowEditDialogProps) {
  const [editValues, setEditValues] = useState<AnyRecord>({ ...editing })

  async function saveEdit() {
    try {
      await adminApi(
        `/admin/sites/${siteId}/mode-payload/${tableName}/${editing.id}?source=${source}`,
        {
          method: "PATCH",
          body: JSON.stringify(editValues),
        },
      )
      onSaved()
    } catch (e) {
      onError(e instanceof Error ? e.message : "保存失败")
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="max-h-[80vh] w-[600px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-4 text-base font-semibold">
          编辑记录 #{editing.id}
        </h3>
        <div className="space-y-3">
          {Object.keys(editing)
            .filter((k) => k !== "id" && k !== "data_source")
            .map((key) => (
              <div key={key}>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  {key}
                </label>
                {String(editValues[key] ?? "").length > 80 ? (
                  <Textarea
                    value={String(editValues[key] ?? "")}
                    onChange={(e) =>
                      setEditValues({ ...editValues, [key]: e.target.value })
                    }
                    className="h-20 text-xs"
                  />
                ) : (
                  <Input
                    value={String(editValues[key] ?? "")}
                    onChange={(e) =>
                      setEditValues({ ...editValues, [key]: e.target.value })
                    }
                    className="h-8 text-xs"
                  />
                )}
              </div>
            ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            取消
          </Button>
          <Button size="sm" onClick={saveEdit}>
            保存
          </Button>
        </div>
      </div>
    </div>
  )
}
