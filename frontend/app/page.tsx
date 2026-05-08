import { redirect } from "next/navigation"

/**
 * 根路由入口
 * ---------------------------------------------------------------
 * 公开访问统一导向旧站隔离壳页面。
 * 原先的 React 首页逻辑已封存至 app/_archived/root-home-page.tsx，暂停使用。
 */
export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const nextParams = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        nextParams.append(key, item)
      }
      continue
    }

    if (typeof value === "string" && value.length > 0) {
      nextParams.set(key, value)
    }
  }

  if (!nextParams.has("t")) {
    nextParams.set("t", "3")
  }

  redirect(`/legacy-shell?${nextParams.toString()}`)
}
