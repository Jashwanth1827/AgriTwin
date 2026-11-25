import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  ChevronRight,
  FileText,
  LayoutDashboard,
  Leaf,
  LineChart,
  LogOut,
  Menu,
  Scale,
  Settings,
  Sprout,
  TrendingUp,
  Truck,
  Users,
  Wheat,
  X,
} from "lucide-react";

import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { cn, titleCase } from "../../lib/utils";
import type { NotificationItem } from "../../types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/farms", label: "Farms & Crops", icon: Sprout },
  { to: "/crop-health", label: "Crop Health", icon: Leaf },
  { to: "/yield", label: "Yield & Harvest", icon: Wheat },
  { to: "/market", label: "Market Intelligence", icon: LineChart },
  { to: "/buyers", label: "Buyers & Offers", icon: Users },
  { to: "/transport", label: "Transport", icon: Truck },
  { to: "/decisions", label: "Decisions", icon: Scale },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<NotificationItem[]>("/system/notifications"),
  });

  const unread = notifications.data?.filter((item) => !item.is_read).length ?? 0;

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const current = NAV.find((item) => location.pathname.startsWith(item.to));

  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r bg-card transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center gap-2 border-b px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sprout className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">AgriTwin</p>
            <p className="text-[11px] text-muted-foreground">Crop-to-cash decisions</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto lg:hidden"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3 scrollbar-thin">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t p-3">
          <div className="rounded-lg bg-secondary/70 p-3">
            <p className="truncate text-sm font-medium">{user?.full_name}</p>
            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            <div className="mt-2 flex items-center gap-2">
              {user?.is_demo ? <Badge variant="demo">DEMO ACCOUNT</Badge> : null}
              <Badge variant="outline">{titleCase(user?.preferred_language ?? "en")}</Badge>
            </div>
          </div>
        </div>
      </aside>

      {open ? (
        <button
          type="button"
          aria-label="Close navigation overlay"
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b bg-card/90 px-4 backdrop-blur sm:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="hidden sm:inline">AgriTwin</span>
            <ChevronRight className="hidden h-4 w-4 sm:inline" />
            <span className="font-medium text-foreground">{current?.label ?? "Overview"}</span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              onClick={() => navigate("/settings?tab=notifications")}
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              {unread > 0 ? (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-accent-foreground">
                  {unread}
                </span>
              ) : null}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </header>

        <main className="mx-auto max-w-7xl p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function TrendingIcon() {
  return <TrendingUp className="h-4 w-4" />;
}
