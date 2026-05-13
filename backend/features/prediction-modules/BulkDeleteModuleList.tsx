"use client"

import type { Mechanism } from "@/features/shared/types"

type BulkDeleteModuleListProps = {
  modules: Mechanism[]
  selectedIds: string[]
  onChange: (value: string[]) => void
}

export function BulkDeleteModuleList({
  modules,
  selectedIds,
  onChange,
}: BulkDeleteModuleListProps) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="text-xs font-medium">模块选择</label>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            className="text-primary hover:underline"
            onClick={() => onChange(modules.map((item) => item.key))}
          >
            全选当前结果
          </button>
          <button
            type="button"
            className="text-muted-foreground hover:underline"
            onClick={() => onChange([])}
          >
            清空
          </button>
        </div>
      </div>
      <div className="max-h-[220px] space-y-1 overflow-y-auto rounded-md border p-2">
        {modules.map((item) => {
          const checked = selectedIds.includes(item.key)
          return (
            <label
              key={item.key}
              className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-xs hover:bg-muted"
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => {
                  if (event.target.checked) {
                    onChange(Array.from(new Set([...selectedIds, item.key])))
                    return
                  }
                  onChange(selectedIds.filter((value) => value !== item.key))
                }}
                className="h-3.5 w-3.5"
              />
              <span className="font-medium">{item.title}</span>
              <span className="text-muted-foreground">[{item.key}]</span>
              <span className="text-muted-foreground">{item.default_table}</span>
            </label>
          )
        })}
      </div>
    </div>
  )
}
