import { useState, useRef, useEffect } from "react";
import { Bell, MessageSquare, CheckCircle, AlertTriangle, Image, Zap, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { WsEvent } from "@/hooks/use-websocket";

const EVENT_CONFIG: Record<string, { icon: typeof Bell; color: string; label: string }> = {
  new_message: { icon: MessageSquare, color: "text-blue-500 bg-blue-50", label: "Nouveau message" },
  post_published: { icon: CheckCircle, color: "text-green-500 bg-green-50", label: "Post publié" },
  approval_needed: { icon: AlertTriangle, color: "text-amber-500 bg-amber-50", label: "Validation requise" },
  escalation: { icon: AlertTriangle, color: "text-red-500 bg-red-50", label: "Escalade" },
  image_generated: { icon: Image, color: "text-purple-500 bg-purple-50", label: "Image générée" },
  post_generated: { icon: Zap, color: "text-brand-500 bg-brand-50", label: "Post généré" },
};

interface Props {
  notifications: WsEvent[];
  unreadCount: number;
  onMarkRead: () => void;
  onClear: () => void;
}

export function NotificationCenter({ notifications, unreadCount, onMarkRead, onClear }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleToggle = () => {
    setOpen(!open);
    if (!open) onMarkRead();
  };

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / 1000;
    if (diff < 60) return "À l'instant";
    if (diff < 3600) return `${Math.floor(diff / 60)}min`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return d.toLocaleDateString("fr");
  };

  return (
    <div ref={ref} className="relative">
      <button onClick={handleToggle} className="relative rounded-xl p-2.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors">
        <Bell className="h-[18px] w-[18px]" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white ring-2 ring-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-50 w-80 rounded-2xl border border-gray-100 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <p className="text-sm font-semibold text-gray-900">Notifications</p>
            {notifications.length > 0 && (
              <button onClick={onClear} className="text-xs text-gray-400 hover:text-gray-600">Tout effacer</button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center py-8 text-center">
                <Bell className="h-8 w-8 text-gray-200" />
                <p className="mt-2 text-xs text-gray-400">Aucune notification</p>
              </div>
            ) : (
              notifications.map((n) => {
                const config = EVENT_CONFIG[n.type] || { icon: Bell, color: "text-gray-500 bg-gray-50", label: n.type };
                const Icon = config.icon;
                return (
                  <div key={n.id} className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0">
                    <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg shrink-0", config.color)}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-gray-800">{config.label}</p>
                      <p className="text-[11px] text-gray-500 truncate">{n.data.message || n.data.title || JSON.stringify(n.data).slice(0, 60)}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{formatTime(n.timestamp)}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
