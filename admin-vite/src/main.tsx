import React, { Suspense, lazy, useState, useEffect, createContext, useContext } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { auth } from "./lib/api";
import {
  LayoutDashboard, Users, Bot, HardDrive, LogOut, Shield,
  FileText, AlertTriangle, ScrollText, Settings, Image,
  CreditCard, Bell, ToggleLeft,
} from "lucide-react";
import "./index.css";

// Auth context
const AuthCtx = createContext<{ user: any; logout: () => void } | null>(null);
function useAuth() { return useContext(AuthCtx)!; }

// Lazy pages
const LoginPage = lazy(() => import("./pages/login"));
const OverviewPage = lazy(() => import("./pages/overview"));
const TenantsPage = lazy(() => import("./pages/tenants"));
const UsersPage = lazy(() => import("./pages/users"));
const AgentsPage = lazy(() => import("./pages/agents"));
const ModerationPage = lazy(() => import("./pages/moderation"));
const ContentPage = lazy(() => import("./pages/content"));
const AuditPage = lazy(() => import("./pages/audit"));
const ConfigPage = lazy(() => import("./pages/config"));
const SystemPage = lazy(() => import("./pages/system"));
const BillingPage = lazy(() => import("./pages/billing"));
const NotificationsPage = lazy(() => import("./pages/notifications"));
const FeatureFlagsPage = lazy(() => import("./pages/feature-flags"));

// Sidebar nav
const nav = [
  { label: "Vue d'ensemble", href: "/", icon: LayoutDashboard },
  { label: "Tenants", href: "/tenants", icon: Users },
  { label: "Utilisateurs", href: "/users", icon: Shield },
  { label: "Agents IA", href: "/agents", icon: Bot },
  { label: "Moderation", href: "/moderation", icon: AlertTriangle },
  { label: "Contenu", href: "/content", icon: FileText },
  { label: "Audit", href: "/audit", icon: ScrollText },
  { label: "Configuration", href: "/config", icon: Settings },
  { label: "Systeme", href: "/system", icon: HardDrive },
  { label: "Facturation", href: "/billing", icon: CreditCard },
  { label: "Notifications", href: "/notifications", icon: Bell },
  { label: "Feature Flags", href: "/feature-flags", icon: ToggleLeft },
];

function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();

  return (
    <div className="flex min-h-screen bg-gray-950">
      <aside className="fixed left-0 top-0 z-40 flex h-full w-60 flex-col bg-gray-900 border-r border-gray-800">
        <div className="flex h-16 items-center gap-3 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <div>
            <span className="text-sm font-bold text-white">OptimusAI</span>
            <span className="ml-1.5 rounded bg-red-500/20 px-1.5 py-0.5 text-[9px] font-bold text-red-400 uppercase">Admin</span>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-4 overflow-y-auto">
          {nav.map((item) => {
            const active = item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                to={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
                  active ? "bg-brand-500/10 text-brand-400" : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-gray-800 p-3">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20 text-brand-400 text-xs font-bold">
              {user?.full_name?.split(" ").map((w: string) => w[0]).join("").toUpperCase().slice(0, 2) || "AD"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-300 truncate">{user?.full_name || "Admin"}</p>
              <p className="text-[10px] text-gray-500 truncate">{user?.email}</p>
            </div>
            <button onClick={logout} className="rounded-lg p-1.5 text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 pl-60 p-8">
        {children}
      </main>
    </div>
  );
}

function App() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("admin_token");
    if (!token) { setLoading(false); return; }
    auth.me().then(setUser).catch(() => localStorage.removeItem("admin_token")).finally(() => setLoading(false));
  }, []);

  const logout = () => {
    localStorage.removeItem("admin_token");
    setUser(null);
  };

  if (loading) return <div className="flex items-center justify-center h-screen bg-gray-950"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>;

  const P = ({ children }: { children: React.ReactNode }) =>
    user ? <AdminShell>{children}</AdminShell> : <Navigate to="/login" replace />;

  return (
    <AuthCtx.Provider value={{ user, logout }}>
      <Toaster position="top-right" richColors theme="dark" closeButton />
      <Suspense fallback={<div className="flex items-center justify-center h-screen bg-gray-950"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>}>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage onLogin={(u: any) => setUser(u)} />} />
          <Route path="/" element={<P><OverviewPage /></P>} />
          <Route path="/tenants" element={<P><TenantsPage /></P>} />
          <Route path="/users" element={<P><UsersPage /></P>} />
          <Route path="/agents" element={<P><AgentsPage /></P>} />
          <Route path="/moderation" element={<P><ModerationPage /></P>} />
          <Route path="/content" element={<P><ContentPage /></P>} />
          <Route path="/audit" element={<P><AuditPage /></P>} />
          <Route path="/config" element={<P><ConfigPage /></P>} />
          <Route path="/system" element={<P><SystemPage /></P>} />
          <Route path="/billing" element={<P><BillingPage /></P>} />
          <Route path="/notifications" element={<P><NotificationsPage /></P>} />
          <Route path="/feature-flags" element={<P><FeatureFlagsPage /></P>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthCtx.Provider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
