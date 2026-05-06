"use client"

import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import {
  BarChart3,
  Database,
  Globe2,
  Hash,
  LayoutDashboard,
  LogOut,
  Ticket,
  Trophy,
  Users,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { adminApi, clearAdminToken, getAdminToken } from "@/lib/admin-api"
import { Button } from "@/components/ui/button"

const menuItems = [
  { icon: LayoutDashboard, label: "控制台", href: "/" },
  { icon: Users, label: "管理员用户", href: "/users" },
  { icon: Trophy, label: "彩种管理", href: "/lottery-types" },
  { icon: Ticket, label: "开奖管理", href: "/draws" },
  { icon: Globe2, label: "站点管理", href: "/sites" },
  { icon: Hash, label: "号码管理", href: "/numbers" },
  { icon: BarChart3, label: "预测模块", href: "/prediction-modules" },
]

type AdminShellProps = {
  title: string
  description: string
  children: ReactNode
  actions?: ReactNode
}

export function AdminShell({ title, description, children, actions }: AdminShellProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<{ display_name: string; username: string } | null>(null)

  useEffect(() => {
    const token = getAdminToken()
    if (!token && pathname !== "/login") {
      router.replace("/login")
      return
    }
    if (token) {
      adminApi<{ user: { display_name: string; username: string } }>("/auth/me")
        .then((data) => setUser(data.user))
        .catch(() => {
          clearAdminToken()
          router.replace("/login")
        })
    }
  }, [pathname, router])

  async function logout() {
    try {
      await adminApi("/auth/logout", { method: "POST" })
    } finally {
      clearAdminToken()
      router.replace("/login")
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="fixed left-0 top-0 hidden h-screen w-64 border-r border-border bg-card p-4 lg:block">
        <Link href="/" className="mb-6 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <div className="text-base font-semibold">彩票软件后台</div>
            <div className="text-[11px] text-muted-foreground">Lottery CMS</div>
          </div>
        </Link>

        <nav className="space-y-1">
          {menuItems.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 p-4 lg:ml-64 lg:p-6">
        <header className="mb-5 flex flex-col gap-3 border-b border-border pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          </div>
          <div className="flex items-center gap-2">
            {actions}
            <div className="hidden text-right text-xs md:block">
              <div className="font-medium">{user?.display_name || "管理员"}</div>
              <div className="text-muted-foreground">{user?.username || "admin"}</div>
            </div>
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut className="mr-1 h-4 w-4" />
              退出
            </Button>
          </div>
        </header>
        {children}
      </main>
    </div>
  )
}
