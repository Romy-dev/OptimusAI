import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  Users, FileText, MessageSquare, Power, PowerOff, Eye, Search,
} from "lucide-react";

export default function TenantsPage() {
  const [tenants, setTenants] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<any>(null);

  useEffect(() => {
    admin.tenants().then(setTenants).catch(() => {});
  }, []);

  const filtered = tenants.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.slug.toLowerCase().includes(search.toLowerCase())
  );

  const handleToggle = async (id: string, isActive: boolean) => {
    try {
      if (isActive) {
        await admin.suspendTenant(id);
        toast.success("Tenant suspendu");
      } else {
        await admin.activateTenant(id);
        toast.success("Tenant reactive");
      }
      const updated = await admin.tenants();
      setTenants(updated);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleViewDetail = async (id: string) => {
    try {
      const d = await admin.tenant(id);
      setDetail(d);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Tenants</h1>
          <p className="text-sm text-gray-500 mt-1">{tenants.length} entreprises inscrites</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher..."
            className="w-56 rounded-lg border border-gray-700 bg-gray-800 py-2 pl-9 pr-3 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Tenants list */}
      <div className="space-y-3">
        {filtered.map((t) => (
          <div key={t.id} className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/10 text-brand-400 font-bold text-sm">
                {t.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-bold text-white">{t.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${t.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                    {t.is_active ? "Actif" : "Suspendu"}
                  </span>
                </div>
                <p className="text-xs text-gray-500">{t.slug} · Cree le {new Date(t.created_at).toLocaleDateString("fr-FR")}</p>
              </div>
              <div className="flex items-center gap-6 text-xs text-gray-400">
                <div className="flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> {t.stats.users}</div>
                <div className="flex items-center gap-1.5"><FileText className="h-3.5 w-3.5" /> {t.stats.posts}</div>
                <div className="flex items-center gap-1.5"><MessageSquare className="h-3.5 w-3.5" /> {t.stats.conversations}</div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => handleViewDetail(t.id)}
                  className="rounded-lg p-2 text-gray-500 hover:text-brand-400 hover:bg-gray-800 transition-colors" title="Details">
                  <Eye className="h-4 w-4" />
                </button>
                <button onClick={() => handleToggle(t.id, t.is_active)}
                  className={`rounded-lg p-2 transition-colors ${t.is_active ? "text-gray-500 hover:text-amber-400 hover:bg-gray-800" : "text-gray-500 hover:text-emerald-400 hover:bg-gray-800"}`}
                  title={t.is_active ? "Suspendre" : "Reactiver"}>
                  {t.is_active ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setDetail(null)}>
          <div className="w-full max-w-lg rounded-2xl bg-gray-900 border border-gray-800 p-6 m-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-white mb-4">{detail.name}</h3>
            <div className="space-y-3">
              <div className="text-xs text-gray-500">ID: {detail.id}</div>
              <div className="text-xs text-gray-500">Cree: {new Date(detail.created_at).toLocaleString("fr-FR")}</div>
              <h4 className="text-sm font-semibold text-gray-300 mt-4">Utilisateurs ({detail.users?.length})</h4>
              {detail.users?.map((u: any) => (
                <div key={u.id} className="flex items-center gap-3 rounded-lg bg-gray-800 p-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20 text-brand-400 text-xs font-bold">
                    {u.full_name.split(" ").map((w: string) => w[0]).join("").toUpperCase().slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-sm text-white">{u.full_name}</p>
                    <p className="text-[10px] text-gray-500">{u.email} · {u.role}</p>
                  </div>
                  <span className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold ${u.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                    {u.is_active ? "Actif" : "Inactif"}
                  </span>
                </div>
              ))}
            </div>
            <button onClick={() => setDetail(null)} className="mt-6 w-full rounded-lg bg-gray-800 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors">Fermer</button>
          </div>
        </div>
      )}
    </div>
  );
}
