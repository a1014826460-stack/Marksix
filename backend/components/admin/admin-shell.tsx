"use client"

import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  Globe2,
  Hash,
  LayoutDashboard,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
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
  { icon: Hash, label: "静态数据管理", href: "/numbers" },
  { icon: BarChart3, label: "预测模块", href: "/prediction-modules" },
  { icon: FileText, label: "日志管理", href: "/logs" },
  { icon: Settings, label: "配置管理", href: "/configs" },
]

type AdminShellProps = {
  title: string
  description: string
  children: ReactNode
  actions?: ReactNode
}

const SIDEBAR_EXPANDED = 256
const SIDEBAR_COLLAPSED = 56

export function AdminShell({ title, description, children, actions }: AdminShellProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<{ display_name: string; username: string } | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

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

  const sidebarW = collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED

  return (
    <div className="flex min-h-screen bg-background">
      {/* 移动端遮罩 */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* 侧边栏 */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-screen border-r border-border bg-card p-3 transition-all duration-200",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
        style={{ width: sidebarW }}
      >
        <div className={cn("flex items-center gap-2 mb-5", collapsed && "justify-center")}>
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Database className="h-4 w-4" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <div className="text-sm font-semibold whitespace-nowrap">彩票软件后台</div>
                <div className="text-[10px] text-muted-foreground">Lottery CMS</div>
              </div>
            )}
          </Link>
        </div>

        <nav className="space-y-1">
          {menuItems.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                  collapsed && "justify-center px-2",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* 折叠按钮 */}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="absolute -right-3 top-10 hidden h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-foreground lg:flex"
        >
          {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </button>
      </aside>

      {/* 主区域 */}
      <main
        className="min-w-0 flex-1 p-4 lg:p-6 transition-all duration-200"
        style={{ marginLeft: sidebarW }}
      >
        {/* 移动端汉堡菜单 */}
        <button
          className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground lg:hidden"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="h-4 w-4" /> 菜单
        </button>

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
