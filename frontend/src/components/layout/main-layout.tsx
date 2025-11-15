import { NavLink, Outlet } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const NAV_LINKS = [
  { to: "/dashboard", label: "仪表盘" },
  { to: "/analysis", label: "分析图表" },
  { to: "/history", label: "历史数据" },
]

/** 主布局，包含顶栏导航与内容区。 */
export default function MainLayout() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/70 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 md:px-8">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">TXFF Lab</p>
            <h1 className="text-2xl font-semibold tracking-tight">腾讯分分彩数据平台</h1>
          </div>
          <nav className="flex gap-2">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1 text-sm font-medium transition-colors",
                    isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <Button variant="outline" asChild>
            <a href="/docs/技术架构.md" target="_blank" rel="noreferrer">
              查看文档
            </a>
          </Button>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
        <Outlet />
      </main>
    </div>
  )
}
