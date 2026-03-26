import { Search } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useWebSocket } from "@/hooks/use-websocket";
import { NotificationCenter } from "./notification-center";

export function Topbar() {
  const { user } = useAuth();
  const { notifications, unreadCount, markAllRead, clearNotifications } = useWebSocket();

  const initials = user
    ? user.full_name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "??";

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-100 bg-white/80 backdrop-blur-md px-6">
      <div className="lg:hidden w-10" />
      <div className="hidden lg:block" />

      <div className="flex items-center gap-2">
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input type="text" placeholder="Rechercher..." className="w-56 rounded-xl border border-gray-200 bg-gray-50/50 py-2 pl-9 pr-3 text-[13px] placeholder:text-gray-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/10 transition-all" />
        </div>
        <NotificationCenter
          notifications={notifications}
          unreadCount={unreadCount}
          onMarkRead={markAllRead}
          onClear={clearNotifications}
        />
        <button className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-100 to-brand-200 text-brand-700 transition-transform hover:scale-105">
          <span className="text-xs font-bold">{initials}</span>
        </button>
      </div>
    </header>
  );
}
