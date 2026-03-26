import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useApi } from "@/hooks/use-api";
import { approvals as approvalsApi, conversations as convoApi } from "@/lib/api";
import {
  LayoutDashboard, Palette, FileText, MessageSquare, BookOpen,
  CheckCircle, Settings, LogOut, Zap, ChevronRight, ImageIcon,
  Link2, Menu, X, Layers, BarChart3, Film,
} from "lucide-react";
import { useState } from "react";

const nav = [
  { label: "Tableau de bord", href: "/dashboard", icon: LayoutDashboard },
  { label: "Contenus", href: "/posts", icon: FileText },
  { label: "Galerie IA", href: "/gallery", icon: ImageIcon },
  { label: "Stories", href: "/stories", icon: Film },
  { label: "Inbox", href: "/inbox", icon: MessageSquare, badgeKey: "inbox" as const },
  { label: "Validations", href: "/approvals", icon: CheckCircle, badgeKey: "approvals" as const },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Mes Templates", href: "/templates", icon: Layers },
  { label: "Connexions", href: "/connections", icon: Link2 },
  { label: "Ma marque", href: "/brands", icon: Palette },
  { label: "Connaissances", href: "/knowledge", icon: BookOpen },
  { label: "Paramètres", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Live badge counts (cached — instant on navigation)
  const { data: pendingApprovals } = useApi(() => approvalsApi.list(), [], "sidebar-approvals");
  const { data: openConvos } = useApi(() => convoApi.list("open"), [], "sidebar-convos");

  const badges: Record<string, number> = {
    approvals: pendingApprovals?.length ?? 0,
    inbox: openConvos?.length ?? 0,
  };

  const initials = user
    ? user.full_name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "??";

  const roleLabels: Record<string, string> = {
    owner: "Propriétaire",
    admin: "Administrateur",
    manager: "Manager",
    editor: "Éditeur",
    viewer: "Lecteur",
    support_agent: "Support",
  };

  const sidebarContent = (
    <>
      <div className="flex h-16 items-center gap-3 px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-600 shadow-md shadow-brand-500/20">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[15px] font-bold text-gray-900 tracking-tight">OptimusAI</span>
          <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[9px] font-bold text-brand-600 uppercase tracking-wider">beta</span>
        </div>
        {/* Mobile close */}
        <button onClick={() => setMobileOpen(false)} className="ml-auto lg:hidden rounded-lg p-1 text-gray-400 hover:bg-gray-100">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="px-3 pb-1">
        <Link to="/posts?action=generate" onClick={() => setMobileOpen(false)} className="flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 px-4 py-2.5 text-[13px] font-semibold text-white shadow-sm shadow-brand-500/20 transition-all hover:shadow-md hover:shadow-brand-500/25 active:scale-[0.98]">
          <Zap className="h-4 w-4" /> Créer un post IA
        </Link>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-4 overflow-y-auto">
        <p className="section-label px-3 pb-2">Navigation</p>
        {nav.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const badgeCount = item.badgeKey ? badges[item.badgeKey] : 0;
          return (
            <Link key={item.href} to={item.href} onClick={() => setMobileOpen(false)} className={cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-150",
              active ? "bg-brand-50 text-brand-700 font-semibold" : "text-gray-500 hover:bg-gray-50 hover:text-gray-800",
            )}>
              <item.icon className={cn("h-[18px] w-[18px] shrink-0 transition-colors", active ? "text-brand-500" : "text-gray-400 group-hover:text-gray-600")} />
              <span className="flex-1">{item.label}</span>
              {badgeCount > 0 && <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold leading-none", active ? "bg-brand-500 text-white" : "bg-red-100 text-red-600")}>{badgeCount}</span>}
              {active && <ChevronRight className="h-3.5 w-3.5 text-brand-400" />}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-gray-100 p-3">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand-100 to-brand-200 text-brand-700">
            <span className="text-xs font-bold">{initials}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-gray-800 truncate">{user?.full_name ?? "..."}</p>
            <p className="text-[11px] text-gray-400 truncate">{roleLabels[user?.role ?? ""] ?? user?.role}</p>
          </div>
          <button onClick={logout} className="rounded-lg p-1.5 text-gray-300 hover:bg-gray-100 hover:text-gray-500 transition-colors" title="Déconnexion">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 lg:hidden rounded-xl bg-white border border-gray-200 p-2 shadow-sm"
      >
        <Menu className="h-5 w-5 text-gray-600" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 z-40 flex h-full w-[var(--sidebar-w)] flex-col bg-white border-r border-gray-100 transition-transform duration-200",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
      )}>
        {sidebarContent}
      </aside>
    </>
  );
}
