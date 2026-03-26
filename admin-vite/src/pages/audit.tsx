import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  Shield, Plus, Pencil, Trash2, Eye, ChevronDown, Loader2, Clock,
} from "lucide-react";

const actionColors: Record<string, { bg: string; text: string; icon: typeof Plus }> = {
  create: { bg: "bg-emerald-500/10", text: "text-emerald-400", icon: Plus },
  update: { bg: "bg-sky-500/10", text: "text-sky-400", icon: Pencil },
  delete: { bg: "bg-red-500/10", text: "text-red-400", icon: Trash2 },
  read: { bg: "bg-gray-700/50", text: "text-gray-400", icon: Eye },
  login: { bg: "bg-purple-500/10", text: "text-purple-400", icon: Shield },
};

const actionOptions = ["all", "create", "update", "delete", "read", "login"];

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const diff = now - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "a l'instant";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `il y a ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `il y a ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `il y a ${days}j`;
  return new Date(dateStr).toLocaleDateString("fr-FR");
}

function ActionBadge({ action }: { action: string }) {
  const config = actionColors[action] || actionColors.read;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${config.bg} ${config.text}`}>
      <Icon className="h-3 w-3" />
      {action}
    </span>
  );
}

export default function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const fetchEvents = (action?: string) => {
    setLoading(true);
    admin
      .auditEvents(100, action === "all" ? undefined : action)
      .then(setEvents)
      .catch((e: any) => toast.error(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchEvents(filter);
  }, [filter]);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Journal d'audit</h1>
          <p className="text-sm text-gray-500 mt-1">Historique de toutes les actions sur la plateforme</p>
        </div>

        {/* Filter dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
          >
            <Shield className="h-4 w-4 text-gray-500" />
            {filter === "all" ? "Toutes les actions" : filter}
            <ChevronDown className="h-4 w-4 text-gray-500" />
          </button>
          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-20 w-48 rounded-xl bg-gray-900 border border-gray-800 py-1 shadow-xl">
                {actionOptions.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => { setFilter(opt); setDropdownOpen(false); }}
                    className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                      filter === opt
                        ? "text-white bg-gray-800"
                        : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                    }`}
                  >
                    {opt === "all" ? "Toutes les actions" : opt}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Events list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-5 w-5 animate-spin text-gray-600" />
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-xl bg-gray-900 border border-gray-800 py-16">
          <div className="text-center">
            <Shield className="mx-auto h-8 w-8 text-gray-700 mb-3" />
            <p className="text-sm text-gray-500">Aucun evenement enregistre</p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((e, idx) => (
            <div key={e.id || idx} className="rounded-xl bg-gray-900 border border-gray-800 px-5 py-4 flex items-center gap-4">
              <ActionBadge action={e.action} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {e.resource_type && (
                    <span className="text-xs font-medium text-gray-300">{e.resource_type}</span>
                  )}
                  {e.details && (
                    <span className="text-xs text-gray-500 truncate max-w-xs">{typeof e.details === "string" ? e.details : JSON.stringify(e.details)}</span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1">
                  {e.user_email && <span className="text-[10px] text-gray-500">{e.user_email}</span>}
                  {e.user_name && !e.user_email && <span className="text-[10px] text-gray-500">{e.user_name}</span>}
                  {e.tenant_name && (
                    <span className="text-[10px] text-gray-600 bg-gray-800 rounded px-1.5 py-0.5">{e.tenant_name}</span>
                  )}
                </div>
              </div>
              <span className="text-[10px] text-gray-600 whitespace-nowrap flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {relativeTime(e.created_at || e.timestamp)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
