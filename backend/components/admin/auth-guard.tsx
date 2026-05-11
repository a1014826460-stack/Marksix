// 认证守卫 + 侧边栏状态持久化（保存侧边栏状态）
"use client"

import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { adminApi, clearAdminToken, getAdminToken } from "@/lib/admin-api"

export type AuthUser = {
  display_name: string
  username: string
  role?: string
}

type AuthGuardProps = {
  children: (user: AuthUser) => React.ReactNode
}

const SIDEBAR_COLLAPSED_KEY = "liuhecai_admin_sidebar_collapsed"

export function saveSidebarCollapsed(collapsed: boolean) {
  if (typeof window === "undefined") return
  window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed))
}

export function loadSidebarCollapsed(): boolean {
  if (typeof window === "undefined") return false
  return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true"
}

export function AuthGuard({ children }: AuthGuardProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = getAdminToken()
    if (!token && pathname !== "/login") {
      router.replace("/login")
      setReady(true)
      return
    }
    if (!token) {
      setReady(true)
      return
    }
    adminApi<{ user: AuthUser }>("/auth/me")
      .then((data) => {
        setUser(data.user)
        setReady(true)
      })
      .catch(() => {
        clearAdminToken()
        router.replace("/login")
        setReady(true)
      })
  }, [pathname, router])

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-sm text-muted-foreground">加载中...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return <>{children(user)}</>
}
