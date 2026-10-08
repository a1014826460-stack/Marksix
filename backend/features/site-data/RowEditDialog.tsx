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
  const [editedFields, setEditedFields] = useState<Set<string>>(new Set())

  function updateField(key: string, value: string) {
    setEditedFields((previous) => new Set(previous).add(key))
    setEditValues({ ...editValues, [key]: value })
  }

  async function saveEdit() {
    try {
      const changes = { ...editValues }
      delete changes.result_restricted
      delete changes.numbers_restricted
      delete changes.id
      delete changes.data_source
      if (editing.result_restricted === true) {
        for (const key of Object.keys(changes)) {
          const actualField = key.startsWith("res_") || key.startsWith("special_") || key.startsWith("specialN")
            || key.startsWith("specialC") || key.startsWith("specialZ")
            // Keep aliases aligned with helpers._hide_public_result_fields;
            // its null/false/empty placeholders must never become table writes.
            || ["numbers", "draw_numbers", "result_numbers", "result", "raw", "domestic_wild_category",
              "outcome", "actual_result", "last_result", "is_correct", "isCorrect", "hit", "is_hit", "verdict",
              "is_opened", "draw_is_opened", "isOpened", "result_text", "resultText", "hit_text",
              "special_ball", "specialBall", "result_balls"].includes(key)
          if (actualField && !editedFields.has(key)) delete changes[key]
        }
      }
      await adminApi(
        `/admin/sites/${siteId}/mode-payload/${tableName}/${editing.id}?source=${source}`,
        {
          method: "PATCH",
          body: JSON.stringify(changes),
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
        {editing.result_restricted === true && (
          <p className="mb-3 text-xs text-muted-foreground">开奖结果完整公开前隐藏；未编辑的结果字段会保留原值。</p>
        )}
        <div className="space-y-3">
          {Object.keys(editing)
            .filter((k) => !["id", "data_source", "result_restricted", "numbers_restricted"].includes(k))
            .map((key) => (
              <div key={key}>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  {key}
                </label>
                {String(editValues[key] ?? "").length > 80 ? (
                  <Textarea
                    value={String(editValues[key] ?? "")}
                    onChange={(e) =>
                      updateField(key, e.target.value)
                    }
                    className="h-20 text-xs"
                  />
                ) : (
                  <Input
                    value={String(editValues[key] ?? "")}
                    onChange={(e) =>
                      updateField(key, e.target.value)
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
