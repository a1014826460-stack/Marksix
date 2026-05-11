export function AdminNotice({ message }: { message: string }) {
  if (!message) return null
  const ts = new Date().toLocaleTimeString("zh-CN", { hour12: false })
  return (
    <div className="mb-3 animate-in fade-in slide-in-from-top-2 rounded-md border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-900 shadow-sm dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
      <span className="mr-2 text-xs text-amber-500">[{ts}]</span>
      {message}
    </div>
  )
}
