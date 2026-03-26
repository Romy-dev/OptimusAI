import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import { Bell, Send, Users, Clock } from "lucide-react";

const levels = ["info", "warning", "success", "error"] as const;

const levelStyles: Record<string, string> = {
  info: "bg-blue-500/10 text-blue-400",
  warning: "bg-amber-500/10 text-amber-400",
  success: "bg-emerald-500/10 text-emerald-400",
  error: "bg-red-500/10 text-red-400",
};

export default function NotificationsPage() {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [targetTenantId, setTargetTenantId] = useState("");
  const [level, setLevel] = useState<string>("info");
  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);

  useEffect(() => {
    admin.notificationHistory().then(setHistory).catch(() => {});
    admin.tenants().then(setTenants).catch(() => {});
  }, []);

  const handleSend = async () => {
    if (!title.trim() || !message.trim()) {
      toast.error("Titre et message requis");
      return;
    }
    setSending(true);
    try {
      const data: any = { title: title.trim(), message: message.trim(), level };
      if (targetTenantId) data.target_tenant_id = targetTenantId;
      await admin.broadcast(data);
      toast.success("Notification envoyee avec succes");
      setTitle("");
      setMessage("");
      setTargetTenantId("");
      setLevel("info");
      admin.notificationHistory().then(setHistory).catch(() => {});
    } catch (err: any) {
      toast.error(err.message || "Erreur d'envoi");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Notifications</h1>
        <p className="text-sm text-gray-500 mt-1">Envoyer des notifications aux tenants</p>
      </div>

      {/* Broadcast Form */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/10 text-brand-400">
            <Bell className="h-5 w-5" />
          </div>
          <h2 className="text-lg font-semibold text-white">Nouvelle notification</h2>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Titre</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Titre de la notification..."
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Message</label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Contenu du message..."
            rows={4}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              <Users className="inline h-3.5 w-3.5 mr-1" />
              Cible
            </label>
            <select
              value={targetTenantId}
              onChange={(e) => setTargetTenantId(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white focus:border-brand-500 focus:outline-none"
            >
              <option value="">Tous les tenants</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Niveau</label>
            <div className="flex gap-2">
              {levels.map((l) => (
                <button
                  key={l}
                  onClick={() => setLevel(l)}
                  className={`flex-1 rounded-lg px-3 py-2.5 text-xs font-medium transition-colors border ${
                    level === l
                      ? `${levelStyles[l]} border-current`
                      : "border-gray-700 bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={handleSend}
          disabled={sending}
          className="flex items-center gap-2 rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="h-4 w-4" />
          {sending ? "Envoi en cours..." : "Envoyer la notification"}
        </button>
      </div>

      {/* History */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-800">
          <Clock className="h-4 w-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-white">Historique des notifications</h2>
          <span className="ml-auto text-xs text-gray-500">{history.length} notification(s)</span>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Titre</th>
              <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Cible</th>
              <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Niveau</th>
              <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Envoyes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {history.map((n, i) => (
              <tr key={i} className="hover:bg-gray-800/50 transition-colors">
                <td className="px-5 py-4 text-xs text-gray-400">
                  {n.created_at ? new Date(n.created_at).toLocaleString("fr-FR") : "—"}
                </td>
                <td className="px-5 py-4">
                  <p className="text-sm font-medium text-white">{n.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{n.message}</p>
                </td>
                <td className="px-5 py-4 text-xs text-gray-400">
                  {n.target_tenant_name || n.target_tenant_id || "Tous"}
                </td>
                <td className="px-5 py-4">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${levelStyles[n.level] || levelStyles.info}`}>
                    {n.level}
                  </span>
                </td>
                <td className="px-5 py-4 text-sm text-gray-300">{n.sent_count ?? "—"}</td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-8 text-center text-sm text-gray-500">Aucune notification envoyee</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
