import type { ReactNode } from "react"
import { Button } from "@/components/ui/button"

export function ToolbarButton({
  children,
  onClick,
}: {
  children: ReactNode
  onClick: () => void
}) {
  return (
    <Button variant="outline" size="sm" onClick={onClick}>
      {children}
    </Button>
  )
}
