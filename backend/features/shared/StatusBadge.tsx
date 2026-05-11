import { Badge } from "@/components/ui/badge"

export function StatusBadge({ value }: { value: boolean }) {
  return (
    <Badge variant={value ? "default" : "secondary"}>
      {value ? "启用" : "停用"}
    </Badge>
  )
}
